"""Python inference for the two fitted R log1p linear models; no runtime training."""

from __future__ import annotations

import copy
import json
import math
from importlib.resources import files
from pathlib import Path

import numpy as np
import pandas as pd

from pedflow.exceptions import ConfigurationError, ContractError

FEATURES = ("commercial_buildings", "footpath_both_sides", "abs_mb_category_simple")
TARGETS = {
    "cross": "obs_peak_cross_ped_per_h",
    "along": "obs_peak_along_ped_per_h",
}
DEFAULT_RELEASE = "pedestrian_linear_v1.json"


def _finite_number(value: object) -> bool:
    """Reject nonfinite coefficients and boolean values in a model release."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _validate_release(release: dict) -> None:
    """Reject incompatible releases before processing any client data."""
    try:
        valid = (
            type(release["schema_version"]) is int
            and release["schema_version"] == 1
            and release["model_type"] == "linear_log1p"
            and release["features"] == list(FEATURES)
            and release["prediction_units"] == "pedestrians_per_hour"
            and release["inverse_transform"] == "max(expm1(eta), 0)"
            and isinstance(release["model_version"], str)
            and bool(release["model_version"].strip())
            and set(release["models"]) == set(TARGETS)
        )
        numeric = release["numeric_preprocessing"][FEATURES[0]]
        valid = valid and all(
            _finite_number(numeric[key]) for key in ("median", "training_min", "training_max")
        )
        valid = (
            valid and 0 <= numeric["training_min"] <= numeric["median"] <= numeric["training_max"]
        )
        expected_levels = {
            FEATURES[1]: {"FALSE", "TRUE"},
            FEATURES[2]: {"Residential", "Other", "Commercial"},
        }
        for feature, expected in expected_levels.items():
            prep = release["categorical_preprocessing"][feature]
            valid = (
                valid
                and isinstance(prep["levels"], list)
                and len(prep["levels"]) == len(expected)
                and set(prep["levels"]) == expected
                and prep["mode"] in expected
            )
        for name, target in TARGETS.items():
            model = release["models"][name]
            valid = (
                valid
                and model["target"] == target
                and model["prediction_column"] == target.replace("obs_", "pred_", 1)
                and _finite_number(model["intercept"])
                and _finite_number(model["commercial_buildings_coefficient"])
            )
            for feature, expected in expected_levels.items():
                effects = model["categorical_effects"][feature]
                base = release["categorical_preprocessing"][feature]["levels"][0]
                valid = (
                    valid
                    and set(effects) == expected
                    and all(_finite_number(value) for value in effects.values())
                    and effects[base] == 0
                )
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, OverflowError) as exc:
        raise ConfigurationError(f"Malformed pedestrian model release: {exc}") from exc
    if not valid:
        raise ConfigurationError("Unsupported or inconsistent pedestrian model release.")


def _is_missing(value: object) -> bool:
    """Define missing feature cells consistently across validation and preprocessing."""
    if not pd.api.types.is_scalar(value):
        raise ContractError("Feature cells must contain scalar values.")
    return bool(pd.isna(value)) or (isinstance(value, str) and value.strip() == "")


def simplify_abs_categories(categories: pd.Series) -> pd.Series:
    """Map known ABS source categories; preserve missing source data as missing.

    The research notebook also maps missing raw categories to Other. The client
    boundary deliberately preserves them so an unavailable source is not hidden.
    """

    def simplify(value: object) -> object:
        """Preserve missing geography; map non-selected ABS land-use categories to Other."""
        if _is_missing(value):
            return pd.NA
        if not isinstance(value, str):
            raise ContractError("ABS categories must be strings or missing values.")
        return value if value in ("Residential", "Commercial") else "Other"

    return categories.map(simplify).astype("string")


class PedestrianFlowModel:
    """Loaded model with strict input checks and explicit optional R fallbacks."""

    def __init__(self, release: dict) -> None:
        """Validate and copy the release so callers cannot mutate loaded coefficients."""
        _validate_release(release)
        self._release = copy.deepcopy(release)

    @property
    def model_version(self) -> str:
        """Identify the immutable model release attached to each prediction."""
        return self._release["model_version"]

    def predict(self, features: pd.DataFrame, *, allow_fallback: bool = False) -> pd.DataFrame:
        """Predict from site_id and three features, retaining row order and index.

        Default: reject missing values and unknown simplified categories. Explicit
        allow_fallback=True uses the saved R median/modes, with per-row warnings.
        Missing columns, malformed values and duplicate site IDs always fail.
        Extra columns are ignored. Returned feature columns are the effective
        values used in prediction, which may include flagged replacements.
        """
        if not isinstance(features, pd.DataFrame):
            raise ContractError("Prediction input must be a pandas DataFrame.")
        if features.columns.duplicated().any():
            raise ContractError("Prediction input contains duplicate columns.")
        missing = {"site_id", *FEATURES}.difference(features.columns)
        if missing:
            raise ContractError(f"Prediction input is missing required columns: {sorted(missing)}")
        if features.empty:
            raise ContractError("Prediction input must contain at least one site.")
        checked = features.loc[:, ["site_id", *FEATURES]].copy()
        checked["site_id"] = checked["site_id"].astype("string").str.strip()
        if checked["site_id"].isna().any() or checked["site_id"].eq("").any():
            raise ContractError("site_id contains missing or blank values.")
        if checked["site_id"].duplicated().any():
            raise ContractError("site_id must be unique.")

        rows = []
        for site_id, buildings, footpath, category in checked.itertuples(index=False, name=None):
            warnings: list[str] = []
            numeric = self._release["numeric_preprocessing"][FEATURES[0]]
            if _is_missing(buildings):
                if not allow_fallback:
                    raise ContractError(f"Site {site_id}: commercial_buildings is missing.")
                buildings = numeric["median"]
                warnings.append("commercial_buildings: training median used")
            else:
                if isinstance(buildings, (bool, np.bool_)):
                    raise ContractError(f"Site {site_id}: commercial_buildings must be numeric.")
                try:
                    buildings = float(
                        buildings.replace(",", "") if isinstance(buildings, str) else buildings
                    )
                except (TypeError, ValueError, OverflowError) as exc:
                    raise ContractError(
                        f"Site {site_id}: commercial_buildings must be numeric."
                    ) from exc
            if not math.isfinite(buildings) or buildings < 0:
                raise ContractError(
                    f"Site {site_id}: commercial_buildings must be finite and non-negative."
                )
            if not numeric["training_min"] <= buildings <= numeric["training_max"]:
                warnings.append("commercial_buildings: outside training range")

            effective = {}
            for feature, value in zip(FEATURES[1:], (footpath, category)):
                prep = self._release["categorical_preprocessing"][feature]
                if _is_missing(value):
                    if not allow_fallback:
                        raise ContractError(f"Site {site_id}: {feature} is missing.")
                    value = prep["mode"]
                    warnings.append(f"{feature}: training mode used for missing value")
                elif feature == "footpath_both_sides":
                    if isinstance(value, (bool, np.bool_)):
                        value = "TRUE" if value else "FALSE"
                    if not isinstance(value, str) or value not in prep["levels"]:
                        raise ContractError(
                            f"Site {site_id}: footpath_both_sides must be boolean or TRUE/FALSE."
                        )
                elif not isinstance(value, str):
                    raise ContractError(f"Site {site_id}: {feature} must be a string.")
                elif value not in prep["levels"]:
                    if not allow_fallback:
                        raise ContractError(f"Site {site_id}: unknown {feature}: {value!r}.")
                    value = prep["mode"]
                    warnings.append(f"{feature}: training mode used for unknown category")
                effective[feature] = value

            result = {"site_id": site_id, "commercial_buildings": buildings, **effective}
            for model in self._release["models"].values():
                eta = model["intercept"] + buildings * model["commercial_buildings_coefficient"]
                for feature, value in effective.items():
                    eta += model["categorical_effects"][feature][value]
                try:
                    prediction = max(math.expm1(eta), 0.0)
                except OverflowError as exc:
                    raise ContractError(
                        f"Site {site_id}: prediction overflow; check inputs."
                    ) from exc
                if not math.isfinite(prediction):
                    raise ContractError(f"Site {site_id}: prediction is not finite; check inputs.")
                result[model["prediction_column"]] = prediction
            result.update(
                model_version=self.model_version,
                status="warning" if warnings else "ok",
                warnings="; ".join(warnings),
            )
            rows.append(result)
        return pd.DataFrame(rows, index=features.index)


def load_model(release_path: str | Path | None = None) -> PedestrianFlowModel:
    """Load the packaged release or an explicit compatible JSON release path."""
    source = (
        Path(release_path)
        if release_path is not None
        else files("pedflow.modeling").joinpath("releases", DEFAULT_RELEASE)
    )
    try:
        release = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConfigurationError(f"Cannot load pedestrian model release: {exc}") from exc
    return PedestrianFlowModel(release)
