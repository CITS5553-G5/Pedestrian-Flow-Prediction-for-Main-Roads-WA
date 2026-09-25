"""Validate locations, extract ABS and imagery, then run the released model."""

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from pathlib import Path
from uuid import uuid4

import pandas as pd

from pedflow.context.io import build_manifest
from pedflow.context.workflow import build_context_features
from pedflow.exceptions import ContractError
from pedflow.imagery.workflow import build_imagery_features
from pedflow.modeling import simplify_abs_categories
from pedflow.modeling.model import FEATURES
from pedflow.prediction.config import load_settings
from pedflow.prediction.location import RoadLocator, resolve_locations
from pedflow.prediction.schema import FEATURE_COLUMNS, OUTPUT_COLUMNS, OUTPUT_SCHEMA_VERSION
from pedflow.validation import (
    merge_source_features,
    validate_and_normalise_sites,
    validate_feature_table,
)

PREDICTION_COLUMNS = ("pred_peak_cross_ped_per_h", "pred_peak_along_ped_per_h")


@dataclass
class PredictionResult:
    """One adapter-independent result: display table, feature evidence and run provenance."""

    predictions: pd.DataFrame
    features: pd.DataFrame
    metadata: dict


def _text(value):
    """Keep missing diagnostic cells out of human-readable messages."""
    return "" if pd.isna(value) else str(value)


def predict_sites(
    sites: pd.DataFrame,
    project_root: str | Path,
    *,
    config_path: str | Path = "configs/prediction/workflow_v1.json",
    workers: int | None = None,
    checkpoint_path: str | Path | None = None,
    resume: bool = False,
    progress=None,
    locator=None,
) -> PredictionResult:
    """One service for all interfaces; no training, fallback values or file export.

    Sites require an ID and either WGS84 coordinates or road number plus SLK.
    Progress is the imagery callback (done, total, site_id, status). A checkpoint
    reuses imagery; ABS is refreshed on each run. Partial source failures keep
    their rows with null predictions. Invalid schemas/configurations fail the run.
    Library callers load environment credentials before calling this function.
    """
    root = Path(project_root).resolve()
    if locator is None:
        locator = RoadLocator(root / "data/external_raw/main_roads_slk/road_slk.sqlite.gz")
    snapshot_path = getattr(locator, "path", None)
    snapshot_sha256 = (
        hashlib.sha256(Path(snapshot_path).read_bytes()).hexdigest()
        if snapshot_path is not None and Path(snapshot_path).is_file() else None
    )
    input_sites = resolve_locations(sites, locator=locator)
    eligible = input_sites.latitude.notna() & input_sites.longitude.notna() & ~input_sites.location_status.isin(
        ["road_reference_not_found", "ambiguous_carriageway", "road_coordinate_conflict", "road_lookup_failed"]
    )
    # A failed reverse lookup does not prevent coordinate-based feature extraction.
    eligible |= input_sites.input_type.eq("coordinates")
    sites = validate_and_normalise_sites(input_sites.loc[eligible]).reset_index(drop=True) if eligible.any() else None
    started = datetime.now(UTC).isoformat()
    settings, context_config, imagery_config, model = load_settings(
        root, config_path, workers=workers
    )
    if sites is None:
        predictions = input_sites.reindex(columns=OUTPUT_COLUMNS).copy()
        predictions["status"] = "not_predicted"
        predictions["message"] = predictions.location_status
        features = pd.DataFrame({"site_id": input_sites.site_id}).reindex(columns=FEATURE_COLUMNS)
        return PredictionResult(predictions, features, {
            "run_id": uuid4().hex, "workflow_version": settings["workflow_version"],
            "output_schema_version": OUTPUT_SCHEMA_VERSION, "coordinate_crs": "EPSG:4326",
            "model_version": model.model_version, "started_at_utc": started,
            "finished_at_utc": datetime.now(UTC).isoformat(), "row_count": len(input_sites),
            "prediction_units": "pedestrians_per_hour", "status_counts": {"not_predicted": len(input_sites)},
            "configuration": settings, "location_status_counts": input_sites.location_status.value_counts().to_dict(),
            "road_snapshot_sha256": snapshot_sha256,
        })
    context = build_context_features(sites, context_config, root)
    context.features = validate_feature_table(
        context.features,
        sites.site_id,
        source_name="ABS",
        required_columns=["abs_mb_category_2021", "abs_match_status"],
    )
    # Keep the same location set on resume, even if ABS match status has changed.
    imagery = build_imagery_features(
        sites, imagery_config, checkpoint_path=checkpoint_path, resume=resume, progress=progress
    )
    imagery.features = validate_feature_table(
        imagery.features,
        sites.site_id,
        source_name="Imagery",
        required_columns=[*FEATURES[:2], "imagery_status", "imagery_error", "imagery_warnings"],
    )
    features = merge_source_features(sites, [context.features, imagery.features])
    features["abs_mb_category_simple"] = simplify_abs_categories(features.abs_mb_category_2021)
    rows = []
    resolved = input_sites.set_index("site_id", drop=False)
    for index, feature in features.iterrows():
        location = resolved.loc[sites.iloc[index].site_id]
        result = {
            **location.to_dict(),
            **dict.fromkeys(PREDICTION_COLUMNS, float("nan")),
            "status": "not_predicted",
            "message": "",
        }
        blocked, warnings = [], []
        if location.location_status != "matched":
            warnings.append(f"road:{location.location_status}")
        abs_status = _text(feature.abs_match_status)
        if abs_status not in {"matched", "matched_no_local_counts"}:
            blocked.append(f"abs:{abs_status or 'missing_status'}")
        elif abs_status == "matched_no_local_counts":
            # Local population counts are not an input to this three-feature model.
            warnings.append("abs:matched_no_local_counts")
        imagery_status = _text(feature.imagery_status)
        if imagery_status != "complete":
            blocked.append(f"imagery:{imagery_status or 'missing_status'}")
            if _text(feature.imagery_error):
                blocked.append(_text(feature.imagery_error))
        missing = [name for name in FEATURES if pd.isna(feature[name])]
        if missing:
            blocked.append("missing:" + ",".join(missing))
        if blocked:
            result["message"] = "; ".join(blocked)
        else:
            try:
                # Isolate invalid/overflowing sites without imputing failed source values.
                prediction = model.predict(features.loc[[index], ["site_id", *FEATURES]]).iloc[0]
                result.update({name: prediction[name] for name in PREDICTION_COLUMNS})
                warnings.extend(
                    text
                    for text in (_text(feature.imagery_warnings), _text(prediction.warnings))
                    if text
                )
                result["status"] = "predicted_with_warning" if warnings else "predicted"
                result["message"] = "; ".join(warnings)
            except ContractError as exc:
                result["status"] = "prediction_failed"
                result["message"] = str(exc)
        rows.append(result)
    predictions = pd.DataFrame(rows).set_index("site_id", drop=False)
    for location in input_sites.loc[~eligible].to_dict("records"):
        predictions.loc[location["site_id"]] = {
            **location, **dict.fromkeys(PREDICTION_COLUMNS, float("nan")),
            "status": "not_predicted", "message": location["location_status"],
        }
    predictions = predictions.loc[input_sites.site_id].reset_index(drop=True).reindex(columns=OUTPUT_COLUMNS)
    features = pd.DataFrame({"site_id": input_sites.site_id}).merge(
        features.reindex(columns=FEATURE_COLUMNS), on="site_id", how="left", validate="one_to_one"
    ).reindex(columns=FEATURE_COLUMNS)
    return PredictionResult(
        predictions=predictions,
        features=features,
        metadata={
            "run_id": uuid4().hex,
            "workflow_version": settings["workflow_version"],
            "output_schema_version": OUTPUT_SCHEMA_VERSION,
            "coordinate_crs": "EPSG:4326",
            "model_version": model.model_version,
            "started_at_utc": started,
            "finished_at_utc": datetime.now(UTC).isoformat(),
            "row_count": len(input_sites),
            "prediction_units": "pedestrians_per_hour",
            "status_counts": predictions.status.value_counts().to_dict(),
            "configuration": settings,
            "context": build_manifest(context),
            "imagery": imagery.metadata,
            "location_status_counts": input_sites.location_status.value_counts().to_dict(),
            "road_snapshot_sha256": snapshot_sha256,
        },
    )
