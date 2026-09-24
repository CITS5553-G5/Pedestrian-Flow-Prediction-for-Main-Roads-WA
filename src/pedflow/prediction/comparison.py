"""Attach local comparison evidence after inference; never supply model features.

The approved site/segment register is separate from the output template. An ID
must also match its registered coordinates; unknown locations remain predictable
without inheriting another location's observations or iRAP values.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROAD_COLUMNS = ("road_no", "slk_km", "road_name", "local_government_name")
OBS_COLUMNS = ("obs_peak_cross_ped_per_h", "obs_peak_along_ped_per_h")
BAND_COLUMNS = {
    "Pedestrian peak hour flow across the road": "irap_ped_cross_band",
    "Pedestrian peak hour flow along the road driver-side": "irap_ped_along_driver_band",
    "Pedestrian peak hour flow along the road passenger-side": "irap_ped_along_passenger_band",
}
NUMERIC_COLUMNS = {
    "Ped_Peak_Cross": "irap_peak_cross_reference",
    "Ped_Peak_Along": "irap_peak_along_reference",
    "Ped_Peak_Driver": "irap_peak_driver_reference",
    "Ped_Peak_Passenger": "irap_peak_passenger_reference",
}
OUTPUT_SCHEMA_VERSION = "prediction_output_v3"
OUTPUT_COLUMNS = (
    "site_id",
    *ROAD_COLUMNS,
    "latitude",
    "longitude",
    "location_role",
    OBS_COLUMNS[0],
    "pred_peak_cross_ped_per_h",
    "irap_peak_cross_reference",
    "irap_ped_cross_band",
    OBS_COLUMNS[1],
    "pred_peak_along_ped_per_h",
    "irap_peak_along_reference",
    "irap_peak_driver_reference",
    "irap_peak_passenger_reference",
    "irap_ped_along_driver_band",
    "irap_ped_along_passenger_band",
    "status",
    "message",
    "comparison_status",
    "irap_numeric_status",
    "matched_segment_id",
    "irap_numeric_source_id",
)
AUDIT_COLUMNS = (
    "benchmark_match_status",
    "irap_match_status",
    "irap_numeric_status",
    "matched_segment_id",
    "irap_source_excel_row",
    "irap_road_survey_date",
    "irap_numeric_source_id",
    "irap_peak_driver_reference",
    "irap_peak_passenger_reference",
)
FEATURE_COLUMNS = (
    "site_id",
    "commercial_buildings",
    "footpath_both_sides",
    "abs_mb_category_simple",
    "abs_mb_category_2021",
    "abs_mb_code_2021",
    "abs_sa1_code_2021",
    "abs_match_status",
    "abs_error_message",
    "imagery_status",
    "imagery_error",
    "imagery_warnings",
    "image_count",
    "processed_at_utc",
)


def _read_source(root, relative, metadata, *, required=(), **kwargs):
    """Record optional comparison source failures without invalidating predictions."""
    path = root / relative
    record = {"path": relative}
    metadata["sources"].append(record)
    try:
        reader = pd.read_excel if path.suffix == ".xlsx" else pd.read_csv
        table = reader(path, keep_default_na=False, na_values=[""], **kwargs)
        if set(required).difference(table.columns):
            raise ValueError(
                f"Comparison source is missing columns: {sorted(set(required) - set(table))}"
            )
        key = "site_id" if "site_id" in table else "ID" if "ID" in table else None
        if key and (table[key].isna().any() or table[key].duplicated().any()):
            raise ValueError(f"Comparison source requires unique, nonblank {key} values.")
        record["status"] = "loaded"
        return table
    except (OSError, ValueError) as exc:
        record.update(status="unavailable", message=str(exc))
        return pd.DataFrame()


def _align(sites, reference):
    """Use exact IDs plus coordinates (1e-7 degrees), never row position or ID alone."""
    if reference.empty:
        return pd.DataFrame(index=sites.index), pd.Series(False, index=sites.index)
    if reference.site_id.duplicated().any():
        raise ValueError("Comparison source has duplicate site_id values.")
    reference = reference.set_index("site_id").reindex(sites.site_id).reset_index()
    matches = pd.Series(
        np.isclose(
            sites.latitude, pd.to_numeric(reference.latitude, errors="coerce"), atol=1e-7, rtol=0
        )
        & np.isclose(
            sites.longitude, pd.to_numeric(reference.longitude, errors="coerce"), atol=1e-7, rtol=0
        ),
        index=sites.index,
    )
    return reference, matches


def add_comparisons(predictions, sites, project_root):
    """Return the display table, row-level evidence and source provenance.

    Raw numeric references are preserved from the client CSV. They are coded,
    spatially aggregated estimates, not observations or newly decoded word labels.
    """
    root = Path(project_root)
    sites = sites.reset_index(drop=True)
    output = predictions.reset_index(drop=True).reindex(columns=OUTPUT_COLUMNS).copy()
    inference_columns = {
        "site_id",
        "latitude",
        "longitude",
        "pred_peak_cross_ped_per_h",
        "pred_peak_along_ped_per_h",
        "status",
        "message",
    }
    # A refresh must clear old references before reading today's source state.
    for column in set(OUTPUT_COLUMNS).difference(inference_columns):
        output[column] = pd.Series(pd.NA, index=sites.index, dtype="object")
    audit = pd.DataFrame({"site_id": sites.site_id})
    for column in AUDIT_COLUMNS:
        audit[column] = pd.Series(pd.NA, index=sites.index, dtype="object")
    metadata = {"sources": [], "join": "site_id and WGS84 coordinates within 1e-7 degrees"}
    # Road names/SLKs remain input hints until the registered source link is verified.
    for column in ROAD_COLUMNS:
        output[column] = sites[column].values if column in sites else pd.NA
    output["location_role"] = "unobserved"
    output["comparison_status"] = "unregistered_site"
    audit["benchmark_match_status"] = "no_match"
    audit["irap_match_status"] = "unregistered_site"
    audit["irap_numeric_status"] = "no_reference"

    model = _read_source(
        root,
        "data/processed/model_dataset.xlsx",
        metadata,
        sheet_name="Model_Data",
        dtype={"site_id": "string", "source_location_id": "string"},
        required=["site_id", "latitude", "longitude", "source_location_id", *OBS_COLUMNS],
    )
    benchmark, observed = _align(sites, model)
    if not model.empty:
        output.loc[observed, "location_role"] = "observed_benchmark"
        output.loc[observed, list(OBS_COLUMNS)] = benchmark.loc[observed, list(OBS_COLUMNS)].values
        audit.loc[observed, "benchmark_match_status"] = "matched"
        audit.loc[observed, "irap_numeric_source_id"] = benchmark.loc[
            observed, "source_location_id"
        ].values
    else:
        audit["benchmark_match_status"] = "source_unavailable"

    links = _read_source(
        root,
        "data/processed/comparison_sites.csv",
        metadata,
        dtype={"site_id": "string"},
        required=[
            "site_id",
            "latitude",
            "longitude",
            *ROAD_COLUMNS,
            "matched_segment_id",
            "irap_source_excel_row",
        ],
    )
    registered, matched = _align(sites, links)
    if not links.empty:
        known = sites.site_id.isin(links.site_id)
        audit.loc[known & ~matched, "irap_match_status"] = "coordinate_mismatch"
        output.loc[known & ~matched, "comparison_status"] = "coordinate_mismatch"
        # Conflicting user road hints are visible failures, never silently overwritten.
        for column in ("road_no", "slk_km"):
            if column in sites:
                supplied = sites[column].notna() & sites[column].astype(str).str.strip().ne("")
                if column == "slk_km":
                    same = np.isclose(
                        pd.to_numeric(sites[column], errors="coerce"),
                        registered[column],
                        atol=1e-6,
                        rtol=0,
                    )
                else:
                    same = (
                        sites[column]
                        .astype("string")
                        .str.strip()
                        .str.upper()
                        .eq(registered[column])
                        .fillna(False)
                    )
                conflict = matched & supplied & ~same
                audit.loc[conflict, "irap_match_status"] = "road_reference_conflict"
                output.loc[conflict, "comparison_status"] = "road_reference_conflict"
                matched &= ~conflict
        for column in ROAD_COLUMNS:
            output.loc[matched, column] = registered.loc[matched, column].values
    else:
        audit["irap_match_status"] = "source_unavailable_or_changed"
        output["comparison_status"] = "source_unavailable_or_changed"

    if matched.any():
        raw_path = "data/raw/AusRAP Data - Words - MSDS.xlsx"
        try:
            raw = _read_source(
                root,
                raw_path,
                metadata,
                usecols=["Road No", "Start SLK", "End SLK", "Road survey date", *BAND_COLUMNS],
            )
            # Excel row 1 is the header; confirm each stored row still matches its road/SLK.
            rows = registered.loc[matched, "irap_source_excel_row"].astype(int)
            selected = raw.iloc[rows.to_numpy() - 2].copy()
            selected.index = rows.index
            valid = (
                selected["Road No"].eq(registered.loc[matched, "road_no"])
                & registered.loc[matched, "slk_km"].ge(
                    selected[["Start SLK", "End SLK"]].min(axis=1) - 1e-9
                )
                & registered.loc[matched, "slk_km"].le(
                    selected[["Start SLK", "End SLK"]].max(axis=1) + 1e-9
                )
            )
            if not valid.all():
                raise ValueError("Registered source rows do not match their road/SLK.")
            for source, column in BAND_COLUMNS.items():
                output.loc[matched, column] = selected[source].values
            audit.loc[matched, "irap_match_status"] = "matched"
            audit.loc[matched, "matched_segment_id"] = registered.loc[
                matched, "matched_segment_id"
            ].values
            audit.loc[matched, "irap_source_excel_row"] = rows.values
            audit.loc[matched, "irap_road_survey_date"] = (
                pd.to_datetime(selected["Road survey date"]).dt.strftime("%Y-%m-%d").values
            )
            output.loc[matched, "comparison_status"] = "matched"
        except (OSError, ValueError, KeyError, IndexError) as exc:
            audit.loc[matched, "irap_match_status"] = "source_unavailable_or_changed"
            output.loc[matched, "comparison_status"] = "source_unavailable_or_changed"
            metadata["segment_error"] = str(exc)

    if observed.any():
        numeric = _read_source(
            root,
            "data/raw/Ped_iRAP_merged.csv",
            metadata,
            dtype={"ID": "string"},
            required=["ID", *NUMERIC_COLUMNS],
        )
        if not numeric.empty and not numeric.ID.duplicated().any():
            numeric = numeric.set_index("ID").reindex(audit.irap_numeric_source_id)
            numeric.index = sites.index
            for source, column in NUMERIC_COLUMNS.items():
                target = audit if column in AUDIT_COLUMNS else output
                target[column] = pd.to_numeric(numeric[source], errors="coerce").values
            available = numeric[list(NUMERIC_COLUMNS)].notna().all(axis=1)
            audit.loc[observed & available, "irap_numeric_status"] = "matched"
            audit.loc[observed & ~available, "irap_numeric_status"] = "missing_in_source"
        else:
            audit.loc[observed, "irap_numeric_status"] = "source_unavailable_or_invalid"
    metadata["status_counts"] = output.comparison_status.value_counts().to_dict()
    # Comparison evidence belongs to the result/provenance, not the model input table.
    for column in set(OUTPUT_COLUMNS).intersection(AUDIT_COLUMNS):
        output[column] = audit[column]
    metadata["site_records"] = json.loads(audit.to_json(orient="records"))
    # Keep quantitative cells typed even when an entire batch lacks a reference.
    for column in (*OBS_COLUMNS, "irap_peak_cross_reference", "irap_peak_along_reference"):
        output[column] = pd.to_numeric(output[column], errors="coerce")
    return output, audit, metadata
