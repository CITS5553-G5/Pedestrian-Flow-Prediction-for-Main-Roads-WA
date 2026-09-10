"""ABS 2021 Mesh Block and SA1 context-feature adapter.

External I/O is separated from deterministic source preparation and feature
construction so the scientific calculations can be tested without network access.
The notebook remains the reviewed explanation and standalone regression reference.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

from pedflow.context.contracts import FeatureResult, SourceConfig, SourceDefinition
from pedflow.exceptions import SourceExecutionError
from pedflow.paths import resolve_project_path

SOURCE_NAME = "abs_meshblock_sa1"
SOURCE_VERSION = "ABS Mesh Block Counts 2021 + ASGS Edition 3 (2021) MB layer 0"
DEFAULT_COUNTS_PATH = "data/external_raw/Mesh Block Counts, 2021.xlsx"
DEFAULT_COUNTS_SHEET = "Table 5"
DEFAULT_COUNTS_HEADER_ROW = 6
DEFAULT_STATE_CODE = 5
DEFAULT_QUERY_URL = (
    "https://geo.abs.gov.au/arcgis/rest/services/ASGS2021/MB/MapServer/0/query"
)
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_USER_AGENT = "CITS5553-pedflow-abs-meshblock-sa1/1.0"

SOURCE_COLUMNS = (
    "MB_CODE_2021",
    "MB_CATEGORY_NAME_2021",
    "AREA_ALBERS_SQKM",
    "Dwelling",
    "Person",
    "State",
)
API_COLUMNS = (
    "site_id",
    "abs_match_status",
    "abs_error_message",
    "abs_mb_code_2021",
    "abs_sa1_code_2021",
)
FEATURE_COLUMNS = (
    "site_id",
    "abs_match_status",
    "abs_error_message",
    "abs_mb_code_2021",
    "abs_sa1_code_2021",
    "abs_mb_category_2021",
    "abs_mb_area_sqkm_2021",
    "abs_mb_dwellings_2021",
    "abs_mb_persons_usual_resident_2021",
    "abs_mb_dwellings_per_sqkm_2021",
    "abs_mb_persons_per_sqkm_2021",
)
EXACT_REGRESSION_COLUMNS = (
    "site_id",
    "abs_match_status",
    "abs_error_message",
    "abs_mb_code_2021",
    "abs_sa1_code_2021",
    "abs_mb_category_2021",
    "abs_mb_dwellings_2021",
    "abs_mb_persons_usual_resident_2021",
)
FLOAT_REGRESSION_COLUMNS = (
    "abs_mb_area_sqkm_2021",
    "abs_mb_dwellings_per_sqkm_2021",
    "abs_mb_persons_per_sqkm_2021",
)
# Densities are simple divisions of reviewed source values. This tolerance permits
# only insignificant floating-point representation differences.
REGRESSION_RTOL = 1e-10
REGRESSION_ATOL = 1e-10


@dataclass(frozen=True)
class MeshBlockCountSnapshot:
    """Loaded local ABS workbook plus safe, reproducible provenance."""

    frame: pd.DataFrame
    configured_path: str
    sha256: str
    sheet_name: str
    header_row: int


def _option(config: SourceConfig, name: str, default: Any) -> Any:
    return config.options.get(name, default)


def _positive_float(value: Any, option_name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise SourceExecutionError(
            f"ABS option '{option_name}' must be a positive number."
        ) from exc
    if not np.isfinite(parsed) or parsed <= 0:
        raise SourceExecutionError(f"ABS option '{option_name}' must be a positive number.")
    return parsed


def _non_negative_int(value: Any, option_name: str) -> int:
    if isinstance(value, bool):
        raise SourceExecutionError(f"ABS option '{option_name}' must be a non-negative integer.")
    try:
        numeric = float(value)
        parsed = int(numeric)
    except (TypeError, ValueError) as exc:
        raise SourceExecutionError(
            f"ABS option '{option_name}' must be a non-negative integer."
        ) from exc
    if not np.isfinite(numeric) or parsed < 0 or parsed != numeric:
        raise SourceExecutionError(
            f"ABS option '{option_name}' must be a non-negative integer."
        )
    return parsed


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def acquire_or_load_source(
    config: SourceConfig,
    project_root: Path,
) -> MeshBlockCountSnapshot:
    """Load the approved local ABS Mesh Block count workbook."""

    configured_path = str(_option(config, "counts_path", DEFAULT_COUNTS_PATH)).strip()
    if not configured_path:
        raise SourceExecutionError("ABS option 'counts_path' must be non-empty text.")

    sheet_name = str(_option(config, "counts_sheet", DEFAULT_COUNTS_SHEET)).strip()
    if not sheet_name:
        raise SourceExecutionError("ABS option 'counts_sheet' must be non-empty text.")
    header_row = _non_negative_int(
        _option(config, "counts_header_row", DEFAULT_COUNTS_HEADER_ROW),
        "counts_header_row",
    )

    path = resolve_project_path(project_root, configured_path)
    if not path.is_file():
        raise SourceExecutionError(f"ABS Mesh Block count workbook does not exist: {path}")

    try:
        frame = pd.read_excel(
            path,
            sheet_name=sheet_name,
            header=header_row,
            dtype={"MB_CODE_2021": "string"},
        )
    except Exception as exc:
        raise SourceExecutionError(
            "Could not read the configured ABS Mesh Block count workbook."
        ) from exc

    return MeshBlockCountSnapshot(
        frame=frame,
        configured_path=configured_path,
        sha256=_sha256(path),
        sheet_name=sheet_name,
        header_row=header_row,
    )


def prepare_source(
    snapshot: MeshBlockCountSnapshot,
    config: SourceConfig,
) -> pd.DataFrame:
    """Validate and clean WA Mesh Block attributes independently of project sites."""

    missing = set(SOURCE_COLUMNS).difference(snapshot.frame.columns)
    if missing:
        raise SourceExecutionError(
            f"ABS count table is missing required fields: {sorted(missing)}"
        )

    state_code = _non_negative_int(
        _option(config, "state_code", DEFAULT_STATE_CODE),
        "state_code",
    )
    if state_code > 9:
        raise SourceExecutionError("ABS option 'state_code' must be a one-digit code.")

    counts = snapshot.frame.loc[:, list(SOURCE_COLUMNS)].copy()
    counts["MB_CODE_2021"] = counts["MB_CODE_2021"].astype("string").str.strip()
    counts["MB_CATEGORY_NAME_2021"] = (
        counts["MB_CATEGORY_NAME_2021"].astype("string").str.strip()
    )
    counts["State"] = pd.to_numeric(counts["State"], errors="coerce")
    counts = counts.loc[
        counts["State"].eq(state_code)
        & counts["MB_CODE_2021"].str.fullmatch(rf"{state_code}\d{{10}}", na=False)
    ].copy()

    if counts.empty:
        raise SourceExecutionError(
            f"ABS count table contains no valid Mesh Blocks for state code {state_code}."
        )

    numeric_columns = ("AREA_ALBERS_SQKM", "Dwelling", "Person")
    for column in numeric_columns:
        counts[column] = pd.to_numeric(counts[column], errors="coerce")

    if counts["MB_CODE_2021"].duplicated().any():
        duplicates = counts.loc[
            counts["MB_CODE_2021"].duplicated(keep=False), "MB_CODE_2021"
        ].tolist()
        raise SourceExecutionError(
            f"ABS count table contains duplicate MB_CODE_2021 values: {duplicates[:10]}"
        )
    if counts["MB_CATEGORY_NAME_2021"].isna().any() or counts[
        "MB_CATEGORY_NAME_2021"
    ].eq("").any():
        raise SourceExecutionError("ABS count table contains blank Mesh Block categories.")
    # The official WA table includes special SHIPPING/MIGRATORY Mesh Blocks with
    # no land area and one record with a missing dwelling count. Preserve those
    # source records; a supplied site that actually matches incomplete attributes
    # is rejected later by source-specific output validation.
    invalid_area = counts["AREA_ALBERS_SQKM"].notna() & counts[
        "AREA_ALBERS_SQKM"
    ].le(0)
    if invalid_area.any():
        raise SourceExecutionError("ABS count table contains non-positive Mesh Block areas.")
    if counts[["Dwelling", "Person"]].lt(0).any().any():
        raise SourceExecutionError("ABS count table contains negative dwelling or person counts.")
    for column in ("Dwelling", "Person"):
        observed = counts[column].dropna()
        if not np.allclose(observed, np.round(observed), rtol=0, atol=0):
            raise SourceExecutionError(f"ABS count field '{column}' contains non-integer values.")
        counts[column] = counts[column].astype("Int64")

    return counts.rename(
        columns={
            "MB_CODE_2021": "abs_mb_code_2021",
            "MB_CATEGORY_NAME_2021": "abs_mb_category_2021",
            "AREA_ALBERS_SQKM": "abs_mb_area_sqkm_2021",
            "Dwelling": "abs_mb_dwellings_2021",
            "Person": "abs_mb_persons_usual_resident_2021",
        }
    ).drop(columns="State")


def build_query_params(longitude: float, latitude: float) -> dict[str, Any]:
    """Build the deterministic ArcGIS point-in-polygon query parameters."""

    return {
        "f": "json",
        "where": "1=1",
        "geometry": json.dumps(
            {
                "x": float(longitude),
                "y": float(latitude),
                "spatialReference": {"wkid": 4326},
            }
        ),
        "geometryType": "esriGeometryPoint",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "mb_code_2021,sa1_code_2021",
        "returnGeometry": "false",
    }


def _empty_match(site_id: str) -> dict[str, Any]:
    return {
        "site_id": site_id,
        "abs_match_status": pd.NA,
        "abs_error_message": pd.NA,
        "abs_mb_code_2021": pd.NA,
        "abs_sa1_code_2021": pd.NA,
    }


def _parse_query_payload(site_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    result = _empty_match(site_id)
    if "error" in payload:
        raise ValueError("ABS ArcGIS service returned an error object.")

    matches = payload.get("features", [])
    if not isinstance(matches, list):
        raise TypeError("ABS ArcGIS response field 'features' is not a list.")
    if len(matches) == 0:
        result["abs_match_status"] = "no_match"
        return result
    if len(matches) > 1:
        result["abs_match_status"] = "multiple_matches"
        result["abs_error_message"] = (
            f"ABS returned {len(matches)} intersecting Mesh Blocks."
        )
        return result

    match = matches[0]
    attributes = match.get("attributes", {}) if isinstance(match, Mapping) else {}
    mb_code = attributes.get("mb_code_2021")
    sa1_code = attributes.get("sa1_code_2021")
    if mb_code is None or sa1_code is None:
        result["abs_match_status"] = "unexpected_response"
        result["abs_error_message"] = "ABS response omitted MB or SA1 code."
        return result

    result["abs_match_status"] = "matched"
    result["abs_mb_code_2021"] = str(mb_code)
    result["abs_sa1_code_2021"] = str(sa1_code)
    return result


def query_meshblock_codes(
    sites: pd.DataFrame,
    config: SourceConfig,
    session: Any | None = None,
) -> pd.DataFrame:
    """Query the ABS service and retain an explicit status for every supplied site."""

    required = {"site_id", "latitude", "longitude"}
    missing = required.difference(sites.columns)
    if missing:
        raise SourceExecutionError(f"ABS site input is missing fields: {sorted(missing)}")

    query_url = str(_option(config, "query_url", DEFAULT_QUERY_URL)).strip()
    if not query_url:
        raise SourceExecutionError("ABS option 'query_url' must be non-empty text.")
    timeout = _positive_float(
        _option(config, "timeout_seconds", DEFAULT_TIMEOUT_SECONDS),
        "timeout_seconds",
    )

    active_session = session or requests.Session()
    if session is None:
        active_session.headers.update(
            {"User-Agent": str(_option(config, "user_agent", DEFAULT_USER_AGENT))}
        )

    rows: list[dict[str, Any]] = []
    for row in sites.itertuples(index=False):
        site_id = str(row.site_id)
        try:
            response = active_session.get(
                query_url,
                params=build_query_params(row.longitude, row.latitude),
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, Mapping):
                raise TypeError("ABS ArcGIS response is not a JSON object.")
            rows.append(_parse_query_payload(site_id, payload))
        except Exception as exc:  # noqa: BLE001 - each site must retain a safe QA row
            result = _empty_match(site_id)
            result["abs_match_status"] = "request_failed"
            # Do not expose raw responses, request URLs, coordinates, or secrets in output.
            result["abs_error_message"] = (
                f"{type(exc).__name__}: ABS Mesh Block request failed."
            )
            rows.append(result)

    matches = pd.DataFrame(rows, columns=list(API_COLUMNS))
    matches["site_id"] = matches["site_id"].astype("string")
    matches["abs_mb_code_2021"] = matches["abs_mb_code_2021"].astype("string")
    matches["abs_sa1_code_2021"] = matches["abs_sa1_code_2021"].astype("string")
    return matches


def build_features(
    sites: pd.DataFrame,
    api_matches: pd.DataFrame,
    prepared_source: pd.DataFrame,
) -> pd.DataFrame:
    """Build deterministic ABS features from prepared matches and count attributes."""

    missing_match_columns = set(API_COLUMNS).difference(api_matches.columns)
    if missing_match_columns:
        raise SourceExecutionError(
            f"ABS API match table is missing fields: {sorted(missing_match_columns)}"
        )
    if api_matches["site_id"].duplicated().any():
        raise SourceExecutionError("ABS API match table contains duplicate site_id values.")

    site_ids = sites[["site_id"]].copy()
    site_ids["site_id"] = site_ids["site_id"].astype("string")
    matches = api_matches.loc[:, list(API_COLUMNS)].copy()
    matches["site_id"] = matches["site_id"].astype("string")
    matches["abs_match_status"] = matches["abs_match_status"].astype("string")
    matches["abs_error_message"] = matches["abs_error_message"].astype("string")
    matches["abs_mb_code_2021"] = matches["abs_mb_code_2021"].astype("string")
    matches["abs_sa1_code_2021"] = matches["abs_sa1_code_2021"].astype("string")
    if set(matches["site_id"]) != set(site_ids["site_id"]):
        raise SourceExecutionError("ABS API match coverage differs from the supplied sites.")

    ordered_matches = site_ids.merge(
        matches,
        on="site_id",
        how="left",
        sort=False,
        validate="one_to_one",
    )
    features = ordered_matches.merge(
        prepared_source,
        on="abs_mb_code_2021",
        how="left",
        sort=False,
        validate="many_to_one",
    )

    missing_local_counts = (
        features["abs_match_status"].eq("matched")
        & features["abs_mb_category_2021"].isna()
    )
    features.loc[missing_local_counts, "abs_match_status"] = "matched_no_local_counts"
    features.loc[missing_local_counts, "abs_error_message"] = (
        "MB matched by the API but was not found in the local WA counts table."
    )

    valid_area = features["abs_mb_area_sqkm_2021"].gt(0)
    features["abs_mb_dwellings_per_sqkm_2021"] = (
        features["abs_mb_dwellings_2021"]
        .div(features["abs_mb_area_sqkm_2021"])
        .where(valid_area)
    )
    features["abs_mb_persons_per_sqkm_2021"] = (
        features["abs_mb_persons_usual_resident_2021"]
        .div(features["abs_mb_area_sqkm_2021"])
        .where(valid_area)
    )

    features = features.loc[:, list(FEATURE_COLUMNS)].copy()
    features["site_id"] = features["site_id"].astype("string")
    features["abs_mb_code_2021"] = features["abs_mb_code_2021"].astype("string")
    features["abs_sa1_code_2021"] = features["abs_sa1_code_2021"].astype("string")
    return features


def validate_source_specific(
    features: pd.DataFrame,
    expected_site_ids: pd.Series,
) -> None:
    """Apply ABS-specific checks beyond the shared source-output contract."""

    if tuple(features.columns) != FEATURE_COLUMNS:
        raise SourceExecutionError("ABS feature columns differ from the approved schema.")
    expected = expected_site_ids.astype("string").tolist()
    if features["site_id"].astype("string").tolist() != expected:
        raise SourceExecutionError("ABS feature rows do not preserve supplied site order.")
    if features["site_id"].duplicated().any():
        raise SourceExecutionError("ABS features contain duplicate site_id values.")

    allowed_statuses = {
        "matched",
        "no_match",
        "multiple_matches",
        "unexpected_response",
        "request_failed",
        "matched_no_local_counts",
    }
    unexpected_statuses = set(features["abs_match_status"].dropna()).difference(
        allowed_statuses
    )
    if unexpected_statuses:
        raise SourceExecutionError(
            f"ABS features contain unexpected statuses: {sorted(unexpected_statuses)}"
        )

    matched = features["abs_match_status"].eq("matched")
    required_matched = [
        "abs_mb_code_2021",
        "abs_sa1_code_2021",
        "abs_mb_category_2021",
        "abs_mb_area_sqkm_2021",
        "abs_mb_dwellings_2021",
        "abs_mb_persons_usual_resident_2021",
        "abs_mb_dwellings_per_sqkm_2021",
        "abs_mb_persons_per_sqkm_2021",
    ]
    if features.loc[matched, required_matched].isna().any().any():
        raise SourceExecutionError("Matched ABS rows contain missing feature values.")
    if features.loc[matched, "abs_mb_area_sqkm_2021"].le(0).any():
        raise SourceExecutionError("Matched ABS rows contain non-positive areas.")
    if features.loc[
        matched,
        ["abs_mb_dwellings_2021", "abs_mb_persons_usual_resident_2021"],
    ].lt(0).any().any():
        raise SourceExecutionError("Matched ABS rows contain negative counts.")

    for column in ("abs_mb_code_2021", "abs_sa1_code_2021"):
        invalid_codes = ~features.loc[matched, column].astype("string").str.fullmatch(
            r"\d{11}", na=False
        )
        if invalid_codes.any():
            raise SourceExecutionError(f"Matched ABS rows contain invalid {column} values.")

    expected_dwelling_density = features.loc[matched, "abs_mb_dwellings_2021"].div(
        features.loc[matched, "abs_mb_area_sqkm_2021"]
    )
    expected_person_density = features.loc[
        matched, "abs_mb_persons_usual_resident_2021"
    ].div(features.loc[matched, "abs_mb_area_sqkm_2021"])
    if not np.allclose(
        features.loc[matched, "abs_mb_dwellings_per_sqkm_2021"],
        expected_dwelling_density,
        rtol=REGRESSION_RTOL,
        atol=REGRESSION_ATOL,
    ):
        raise SourceExecutionError("ABS dwelling densities do not equal count divided by area.")
    if not np.allclose(
        features.loc[matched, "abs_mb_persons_per_sqkm_2021"],
        expected_person_density,
        rtol=REGRESSION_RTOL,
        atol=REGRESSION_ATOL,
    ):
        raise SourceExecutionError("ABS person densities do not equal count divided by area.")


def make_feature_result(
    sites: pd.DataFrame,
    features: pd.DataFrame,
    snapshot: MeshBlockCountSnapshot,
    prepared_source: pd.DataFrame,
    config: SourceConfig,
) -> FeatureResult:
    """Validate features and attach safe source version, metadata, and warnings."""

    validate_source_specific(features, sites["site_id"])
    query_url = str(_option(config, "query_url", DEFAULT_QUERY_URL)).strip()
    timeout = _positive_float(
        _option(config, "timeout_seconds", DEFAULT_TIMEOUT_SECONDS),
        "timeout_seconds",
    )
    state_code = _non_negative_int(
        _option(config, "state_code", DEFAULT_STATE_CODE),
        "state_code",
    )
    source_version = str(_option(config, "source_version", SOURCE_VERSION)).strip()
    if not source_version:
        raise SourceExecutionError("ABS option 'source_version' must be non-empty text.")

    warnings = [
        "ABS features describe the containing 2021 Mesh Block, not a site-centred neighbourhood.",
        "The 2021 Census reference period may differ from the pedestrian survey period.",
    ]
    incomplete_source_rows = int(
        prepared_source[
            [
                "abs_mb_area_sqkm_2021",
                "abs_mb_dwellings_2021",
                "abs_mb_persons_usual_resident_2021",
            ]
        ]
        .isna()
        .any(axis=1)
        .sum()
    )
    if incomplete_source_rows:
        warnings.append(
            f"The official source contains {incomplete_source_rows} special-purpose Mesh Blocks "
            "with incomplete area or count attributes."
        )
    status_counts = features["abs_match_status"].value_counts(dropna=False)
    non_matched = int((~features["abs_match_status"].eq("matched")).sum())
    if non_matched:
        summary = ", ".join(
            f"{status}={int(count)}"
            for status, count in status_counts.items()
            if status != "matched"
        )
        warnings.append(f"ABS source produced {non_matched} non-matched rows: {summary}.")

    metadata = {
        "provider": "Australian Bureau of Statistics",
        "dataset": "Census of Population and Housing: Mesh Block counts, 2021",
        "source_file": snapshot.configured_path,
        "source_file_sha256": snapshot.sha256,
        "source_sheet": snapshot.sheet_name,
        "source_header_row_zero_based": snapshot.header_row,
        "source_record_count": len(prepared_source),
        "source_incomplete_attribute_rows": incomplete_source_rows,
        "state_code": state_code,
        "api_service_url": query_url,
        "api_layer_identifier": "ASGS2021/MB/MapServer/0",
        "api_out_fields": ["mb_code_2021", "sa1_code_2021"],
        "input_crs": "EPSG:4326",
        "spatial_relation": "esriSpatialRelIntersects",
        "request_timeout_seconds": timeout,
        "retrieval_method": "ArcGIS REST point-polygon query plus local workbook join",
    }
    return FeatureResult(
        source_name=SOURCE_NAME,
        source_version=source_version,
        features=features,
        metadata=metadata,
        warnings=tuple(warnings),
    )


def extract(sites: pd.DataFrame, config: SourceConfig, project_root: Path) -> FeatureResult:
    """Build one ABS Mesh Block/SA1 feature row per supplied validated site."""

    snapshot = acquire_or_load_source(config, project_root)
    prepared_source = prepare_source(snapshot, config)
    api_matches = query_meshblock_codes(sites, config)
    features = build_features(sites, api_matches, prepared_source)
    return make_feature_result(sites, features, snapshot, prepared_source, config)


DEFINITION = SourceDefinition(
    name=SOURCE_NAME,
    description="ABS 2021 Mesh Block category, counts, area, and densities.",
    column_prefixes=("abs_",),
    extractor=extract,
)
