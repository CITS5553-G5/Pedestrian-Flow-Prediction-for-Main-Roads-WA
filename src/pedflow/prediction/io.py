"""Write the results workbook and the run's provenance manifest."""

import json
import math
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl.styles import Alignment, Border, Font, Side

from pedflow.exceptions import ContractError
from pedflow.io import atomic_path, write_json_atomic
from pedflow.prediction.comparison import FEATURE_COLUMNS, OUTPUT_SCHEMA_VERSION, add_comparisons
from pedflow.prediction.workflow import PredictionResult
from pedflow.validation import (
    merge_source_features,
    validate_and_normalise_sites,
    validate_feature_table,
)


def metadata_table(metadata: dict) -> pd.DataFrame:
    """Keep batch-wide settings and comparison definitions in a readable worksheet."""
    values = {
        key: metadata.get(key, "")
        for key in (
            "run_id",
            "output_schema_version",
            "model_version",
            "coordinate_crs",
            "prediction_units",
            "started_at_utc",
            "finished_at_utc",
            "comparison_refreshed_at_utc",
            "row_count",
        )
    }
    values.update(
        {
            "selected_features": "commercial_buildings, footpath_both_sides, abs_mb_category_simple",
            "observations": "obs_peak_* uses the reconciled model dataset; missing observations stay blank.",
            "benchmark_scope": "The 49 observed benchmark sites trained the released model; these are in-sample comparisons.",
            "irap_numeric_reference": "Ped_iRAP_merged.csv: Ped_Peak_Cross / Ped_Peak_Along copied unchanged. Client estimates from recoded bands averaged over overlapping SLK +/- 0.1 km segments; not measured counts.",
            "irap_labels": "Original text from the registered AusRAP row. Labels and client numeric references use different spatial aggregation; no conversion is inferred.",
            "irap_none_label": "The literal source label 'None' is retained as text; it is distinct from an empty cell.",
            "comparison_coverage": "Only registered site IDs with matching coordinates receive road-segment labels. New sites need verified links in comparison_sites.csv; prediction is independent of comparison availability.",
            "missing_values": "Blank means unavailable, not zero. Feature extraction status is in Features; iRAP references and matching status are in Predictions.",
            "comparison_provenance": "Predictions contains iRAP source identifiers. Full per-site source rows, survey dates and match diagnostics are in the manifest under comparison.site_records.",
            "road_fields": "Input hints unless comparison_status=matched; matched rows use the approved site register.",
        }
    )
    for source in metadata.get("comparison", {}).get("sources", []):
        prefix = source["path"]
        for key in ("status", "message"):
            if key in source:
                values[f"{prefix}: {key}"] = source[key]
    if "segment_error" in metadata.get("comparison", {}):
        values["comparison_error"] = metadata["comparison"]["segment_error"]
    return pd.DataFrame(values.items(), columns=["field", "value"])


def write_prediction_outputs(result: PredictionResult, directory: str | Path) -> dict[str, Path]:
    """Export predictions, features and the run's settings and source descriptions."""
    folder = Path(directory)
    workbook = folder / "predictions.xlsx"
    with (
        atomic_path(workbook) as temporary,
        pd.ExcelWriter(temporary, engine="openpyxl") as writer,
    ):
        result.predictions.to_excel(writer, sheet_name="Predictions", index=False)
        result.features.to_excel(writer, sheet_name="Features", index=False)
        metadata_table(result.metadata).to_excel(writer, sheet_name="Metadata", index=False)
        for sheet in writer.book:
            sheet.freeze_panes = "B2" if sheet.title != "Metadata" else "A2"
            sheet.sheet_view.showGridLines = False
            sheet.auto_filter.ref = sheet.dimensions
            sheet.row_dimensions[1].height = 42
            # Match Model_Data: Arial, unfilled cells, black text and thin grey borders.
            side = Side(style="thin", color="D9D9D9")
            for column in sheet.columns:
                # User-provided IDs are text, never workbook formulas.
                for cell in column:
                    if cell.data_type == "f":
                        cell.data_type = "s"
                    cell.font = Font(name="Arial", size=10, color="000000")
                    cell.alignment = Alignment(vertical="center")
                    if sheet.title != "Metadata":
                        cell.border = Border(left=side, right=side, top=side, bottom=side)
                        if cell.row > 1:
                            sheet.row_dimensions[cell.row].height = max(
                                sheet.row_dimensions[cell.row].height or 0, 13.55
                            )
                header = column[0]
                header.font = Font(name="Arial", size=10, bold=True, color="000000")
                header.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
                text_length = max(
                    (len(str(cell.value)) for cell in column[1:] if cell.value is not None),
                    default=0,
                )
                width = min(44, max(18, len(str(header.value)) + 2, text_length + 2))
                if sheet.title == "Metadata":
                    width = 60 if header.column == 1 else 110
                    for cell in column[1:]:
                        cell.alignment = Alignment(wrap_text=True, vertical="top")
                        sheet.row_dimensions[cell.row].height = 42
                sheet.column_dimensions[header.column_letter].width = width
                for cell in column[1:]:
                    if (
                        sheet.title != "Metadata"
                        and isinstance(cell.value, str)
                        and len(cell.value) > width
                    ):
                        cell.alignment = Alignment(wrap_text=True, vertical="top")
                        sheet.row_dimensions[cell.row].height = max(
                            sheet.row_dimensions[cell.row].height or 15,
                            16 * math.ceil(len(cell.value) / (width - 2)),
                        )
                    if header.value in {"latitude", "longitude"}:
                        cell.number_format = "0.000000"
                    elif header.value == "slk_km":
                        cell.number_format = "0.000"
                    elif str(header.value).endswith("_per_h") or header.value in {
                        "irap_peak_cross_reference",
                        "irap_peak_along_reference",
                        "irap_peak_driver_reference",
                        "irap_peak_passenger_reference",
                    }:
                        cell.number_format = "0.00"
    manifest = folder / "predictions.manifest.json"
    write_json_atomic(manifest, result.metadata)
    return {"workbook": workbook, "manifest": manifest}


def refresh_prediction_outputs(directory, project_root, *, sites=None) -> dict[str, Path]:
    """Refresh comparison columns offline, preserving the original inference and run ID."""
    folder = Path(directory)
    workbook = folder / "predictions.xlsx"
    try:
        metadata = json.loads((folder / "predictions.manifest.json").read_text())
        # Older reports may contain file fingerprints; refresh no longer uses them.
        for key in ("input_sha256", "workbook_sha256", "previous_workbook_sha256"):
            metadata.pop(key, None)
        predictions = pd.read_excel(
            workbook,
            sheet_name="Predictions",
            dtype={"site_id": "string"},
            keep_default_na=False,
        )
        features = pd.read_excel(
            workbook,
            sheet_name="Features",
            dtype={
                "site_id": "string",
                "abs_mb_code_2021": "string",
                "abs_sa1_code_2021": "string",
            },
            keep_default_na=False,
        )
        saved_sites = predictions.copy()
        if "coordinate_crs" not in saved_sites:
            saved_sites["coordinate_crs"] = metadata.get("coordinate_crs", "EPSG:4326")
        validated = validate_and_normalise_sites(saved_sites)
        if sites is not None:
            supplied = validate_and_normalise_sites(sites)
            if set(supplied.site_id) != set(validated.site_id):
                raise ContractError(
                    "Comparison refresh requires the same site IDs as the saved run."
                )
            supplied = supplied.set_index("site_id").loc[validated.site_id].reset_index()
            if not np.allclose(
                supplied[["latitude", "longitude"]],
                validated[["latitude", "longitude"]],
                atol=1e-10,
                rtol=0,
            ):
                raise ContractError("Comparison refresh cannot change the saved coordinates.")
            sites = sites.copy()
            sites["site_id"] = sites.site_id.astype("string").str.strip()
            saved_sites = sites.set_index("site_id").loc[validated.site_id].reset_index()
        features = validate_feature_table(features, validated.site_id, source_name="Saved features")
        predictions, _, provenance = add_comparisons(predictions, saved_sites, project_root)
        features = merge_source_features(validated, [features])
        features = features.reindex(columns=FEATURE_COLUMNS)
        metadata.update(
            output_schema_version=OUTPUT_SCHEMA_VERSION,
            coordinate_crs="EPSG:4326",
            model_version=metadata["configuration"]["model_version"],
            comparison=provenance,
            comparison_refreshed_at_utc=datetime.now(UTC).isoformat(),
        )
    except (OSError, ValueError, KeyError) as exc:
        raise ContractError(f"Cannot refresh saved comparisons: {exc}") from exc
    return write_prediction_outputs(PredictionResult(predictions, features, metadata), folder)
