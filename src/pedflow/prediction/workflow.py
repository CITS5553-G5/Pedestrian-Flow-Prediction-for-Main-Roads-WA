"""Validate locations, extract ABS and imagery, then run the released model."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd

from pedflow.context.io import build_manifest
from pedflow.context.workflow import build_context_features
from pedflow.exceptions import ContractError
from pedflow.imagery.workflow import build_imagery_features
from pedflow.modeling import simplify_abs_categories
from pedflow.modeling.model import FEATURES
from pedflow.prediction.comparison import FEATURE_COLUMNS, OUTPUT_SCHEMA_VERSION, add_comparisons
from pedflow.prediction.config import load_settings
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
) -> PredictionResult:
    """One service for all interfaces; no training, fallback values or file export.

    Sites require site_id, latitude, longitude and coordinate_crs='EPSG:4326'.
    Progress is the imagery callback (done, total, site_id, status). A checkpoint
    reuses imagery; ABS is refreshed on each run. Partial source failures keep
    their rows with null predictions. Invalid schemas/configurations fail the run.
    Library callers load environment credentials before calling this function.
    """
    input_sites = sites.reset_index(drop=True).copy()
    sites = validate_and_normalise_sites(sites).reset_index(drop=True)
    # Keep road hints for reporting while extractors receive only validated locations.
    input_sites[list(sites.columns)] = sites
    started = datetime.now(UTC).isoformat()
    root = Path(project_root).resolve()
    settings, context_config, imagery_config, model = load_settings(
        root, config_path, workers=workers
    )
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
    for index, feature in features.iterrows():
        result = {
            **sites.iloc[index].to_dict(),
            **dict.fromkeys(PREDICTION_COLUMNS, float("nan")),
            "status": "not_predicted",
            "message": "",
        }
        blocked, warnings = [], []
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
    predictions, _, comparison_metadata = add_comparisons(pd.DataFrame(rows), input_sites, root)
    features = features.reindex(columns=FEATURE_COLUMNS)
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
            "row_count": len(sites),
            "prediction_units": "pedestrians_per_hour",
            "status_counts": predictions.status.value_counts().to_dict(),
            "configuration": settings,
            "context": build_manifest(context),
            "imagery": imagery.metadata,
            "comparison": comparison_metadata,
        },
    )
