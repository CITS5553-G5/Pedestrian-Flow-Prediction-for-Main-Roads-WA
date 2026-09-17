"""Public Transport Authority stop-context feature adapter.

The adapter keeps ArcGIS/cache I/O separate from deterministic cleaning and spatial
calculation. It accepts the common, already validated site table and never reads the
model dataset or writes integrated workflow outputs.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import numpy as np
import pandas as pd
import requests
from pyproj import Transformer
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pedflow.context.contracts import FeatureResult, SourceConfig, SourceDefinition
from pedflow.exceptions import SourceExecutionError

DEFAULT_LAYER_URL = (
    "https://public-services.slip.wa.gov.au/public/rest/services/"
    "SLIP_Public_Services/Transport/MapServer/14"
)
DEFAULT_BUFFER_RADIUS_M = 500.0
DEFAULT_TIMEOUT_SECONDS = 120.0
DEFAULT_RETRY_COUNT = 4
DEFAULT_USER_AGENT = "CITS5553-pedflow-pta-stops/1.0"
APPROVED_FEATURE_COLUMNS = (
    "site_id",
    "pta_data_status",
    "pta_nearest_active_stop_distance_m",
    "pta_nearest_active_stop_type",
    "pta_active_stops_within_500m",
    "pta_nearest_stop_id",
)
SOURCE_RECORD_COLUMNS = (
    "gid",
    "stopid",
    "stopnumber",
    "status",
    "stopname",
    "location",
    "stoptype",
    "suburb",
    "accessible",
    "shelter",
    "longitude",
    "latitude",
)
REQUIRED_SOURCE_PROPERTIES = frozenset(SOURCE_RECORD_COLUMNS[:-2])
ALLOWED_STATUSES = frozenset(
    {"matched", "valid_no_stop_within_500m", "invalid_coordinate"}
)


@dataclass(frozen=True)
class PTASnapshot:
    """One cache-backed ArcGIS snapshot before deterministic preparation."""

    layer_metadata: Mapping[str, Any]
    feature_collection: Mapping[str, Any]
    snapshot_date: str
    retrieval_method: str
    geojson_path: Path
    metadata_path: Path
    geojson_sha256: str
    metadata_sha256: str


@dataclass(frozen=True)
class PreparedPTAStops:
    """Validated and cleaned stop records used by spatial calculation."""

    all_stops: pd.DataFrame
    active_stops: pd.DataFrame
    exact_duplicate_count: int
    status_counts: Mapping[str, int]
    active_stop_type_counts: Mapping[str, int]


def _positive_number(options: Mapping[str, Any], key: str, default: float) -> float:
    value = options.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SourceExecutionError(f"PTA option '{key}' must be a positive number.")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise SourceExecutionError(f"PTA option '{key}' must be a positive number.")
    return number


def _non_negative_integer(options: Mapping[str, Any], key: str, default: int) -> int:
    value = options.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SourceExecutionError(f"PTA option '{key}' must be a non-negative integer.")
    return value


def _snapshot_date(options: Mapping[str, Any]) -> str:
    local_date = datetime.now().astimezone().date().isoformat()
    value = str(options.get("snapshot_date", local_date)).strip()
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise SourceExecutionError(
            "PTA option 'snapshot_date' must use ISO format YYYY-MM-DD."
        ) from exc
    return parsed.isoformat()


def _safe_relative_path(project_root: Path, configured: Any, default: str) -> Path:
    raw = Path(str(configured if configured is not None else default))
    path = raw if raw.is_absolute() else project_root / raw
    resolved_root = project_root.resolve()
    resolved_path = path.resolve()
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        raise SourceExecutionError("PTA cache_directory must remain inside project_root.")
    return resolved_path


def _validated_layer_url(value: Any) -> str:
    layer_url = str(value).strip().rstrip("/")
    parsed = urlsplit(layer_url)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise SourceExecutionError(
            "PTA layer_url must be a credential-free HTTPS endpoint without query or fragment."
        )
    return layer_url


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceExecutionError(f"PTA cache file is unreadable or invalid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise SourceExecutionError(f"PTA cache file must contain a JSON object: {path}")
    return payload


def _write_json_atomic(path: Path, payload: Mapping[str, Any], *, compact: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        text = json.dumps(
            payload,
            separators=(",", ":") if compact else None,
            indent=None if compact else 2,
            ensure_ascii=False,
        )
        temporary.write_text(text + ("" if compact else "\n"), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def create_http_session(retry_count: int = DEFAULT_RETRY_COUNT) -> requests.Session:
    """Create the controlled retrying session used for ArcGIS GET requests."""

    retry = Retry(
        total=retry_count,
        connect=retry_count,
        read=retry_count,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session = requests.Session()
    session.headers.update({"User-Agent": DEFAULT_USER_AGENT})
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def _get_arcgis_json(
    session: requests.Session,
    url: str,
    params: Mapping[str, Any],
    timeout_seconds: float,
) -> Mapping[str, Any]:
    try:
        response = session.get(url, params=dict(params), timeout=timeout_seconds)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise SourceExecutionError(f"PTA ArcGIS request failed for {url}.") from exc
    except ValueError as exc:
        raise SourceExecutionError(f"PTA ArcGIS returned invalid JSON for {url}.") from exc

    if not isinstance(payload, dict):
        raise SourceExecutionError("PTA ArcGIS response must be a JSON object.")
    if "error" in payload:
        error = payload.get("error")
        if isinstance(error, dict):
            code = error.get("code", "unknown")
            message = error.get("message", "unspecified ArcGIS error")
            raise SourceExecutionError(f"PTA ArcGIS error {code}: {message}")
        raise SourceExecutionError("PTA ArcGIS returned an error payload.")
    return payload


def download_arcgis_snapshot(
    session: requests.Session,
    layer_url: str = DEFAULT_LAYER_URL,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    """Download and count-verify the complete PTA point layer."""

    layer_url = _validated_layer_url(layer_url)
    query_url = f"{layer_url.rstrip('/')}/query"
    metadata = _get_arcgis_json(session, layer_url, {"f": "json"}, timeout_seconds)
    count_payload = _get_arcgis_json(
        session,
        query_url,
        {"where": "1=1", "returnCountOnly": "true", "f": "json"},
        timeout_seconds,
    )
    try:
        expected_count = int(count_payload["count"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SourceExecutionError("PTA ArcGIS count response has no valid integer count.") from exc
    if expected_count <= 0:
        raise SourceExecutionError("PTA ArcGIS reported no source records.")

    try:
        page_size = min(int(metadata.get("maxRecordCount", 2000)), 5000)
    except (TypeError, ValueError) as exc:
        raise SourceExecutionError("PTA ArcGIS metadata has an invalid maxRecordCount.") from exc
    if page_size <= 0:
        raise SourceExecutionError("PTA ArcGIS maxRecordCount must be positive.")

    arcgis_features: list[Mapping[str, Any]] = []
    for offset in range(0, expected_count, page_size):
        page_payload = _get_arcgis_json(
            session,
            query_url,
            {
                "where": "1=1",
                "outFields": (
                    "gid,stopid,stopnumber,status,stopname,location,stoptype,"
                    "suburb,accessible,shelter"
                ),
                "returnGeometry": "true",
                "outSR": 4326,
                "orderByFields": "gid ASC",
                "resultOffset": offset,
                "resultRecordCount": page_size,
                "f": "json",
            },
            timeout_seconds,
        )
        page = page_payload.get("features")
        if not isinstance(page, list) or not page:
            raise SourceExecutionError(f"PTA ArcGIS returned an empty page at offset {offset}.")
        arcgis_features.extend(page)

    if len(arcgis_features) != expected_count:
        raise SourceExecutionError(
            "PTA snapshot count mismatch: "
            f"expected {expected_count}, received {len(arcgis_features)}."
        )

    geojson_features: list[dict[str, Any]] = []
    for record in arcgis_features:
        if not isinstance(record, dict):
            raise SourceExecutionError("PTA ArcGIS feature must be a JSON object.")
        attributes = record.get("attributes")
        geometry = record.get("geometry")
        if not isinstance(attributes, dict):
            raise SourceExecutionError("PTA ArcGIS feature is missing attributes.")
        point_geometry = None
        if isinstance(geometry, dict):
            x_value = geometry.get("x")
            y_value = geometry.get("y")
            if x_value is not None and y_value is not None:
                point_geometry = {"type": "Point", "coordinates": [x_value, y_value]}
        geojson_features.append(
            {"type": "Feature", "properties": attributes, "geometry": point_geometry}
        )

    feature_collection = {
        "type": "FeatureCollection",
        "name": metadata.get("name", "PTA-001"),
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": geojson_features,
    }
    return metadata, feature_collection


def acquire_or_load_source(
    config: SourceConfig,
    project_root: Path,
    session: requests.Session | None = None,
) -> PTASnapshot:
    """Load the configured dated cache or retrieve and atomically save it."""

    options = config.options
    snapshot_date = _snapshot_date(options)
    cache_root = _safe_relative_path(
        project_root,
        options.get("cache_directory"),
        "data/external_raw/pta_stops",
    )
    snapshot_directory = cache_root / snapshot_date
    geojson_path = snapshot_directory / "pta_stops.geojson"
    metadata_path = snapshot_directory / "pta_layer_metadata.json"

    geojson_exists = geojson_path.is_file()
    metadata_exists = metadata_path.is_file()
    if geojson_exists != metadata_exists:
        raise SourceExecutionError(
            "PTA snapshot cache is incomplete; both GeoJSON and metadata are required."
        )

    if geojson_exists:
        layer_metadata = _read_json(metadata_path)
        feature_collection = _read_json(geojson_path)
        retrieval_method = "cached"
    else:
        allow_download = options.get("allow_download", True)
        if not isinstance(allow_download, bool):
            raise SourceExecutionError("PTA option 'allow_download' must be true or false.")
        if not allow_download:
            raise SourceExecutionError(
                f"PTA snapshot {snapshot_date} is not cached and downloading is disabled."
            )
        retry_count = _non_negative_integer(options, "retry_count", DEFAULT_RETRY_COUNT)
        timeout_seconds = _positive_number(
            options, "timeout_seconds", DEFAULT_TIMEOUT_SECONDS
        )
        layer_url = _validated_layer_url(options.get("layer_url", DEFAULT_LAYER_URL))
        owned_session = session is None
        active_session = session or create_http_session(retry_count)
        try:
            layer_metadata, feature_collection = download_arcgis_snapshot(
                active_session,
                layer_url=layer_url,
                timeout_seconds=timeout_seconds,
            )
        finally:
            if owned_session:
                active_session.close()
        _write_json_atomic(metadata_path, layer_metadata, compact=False)
        _write_json_atomic(geojson_path, feature_collection, compact=True)
        retrieval_method = "downloaded"

    return PTASnapshot(
        layer_metadata=layer_metadata,
        feature_collection=feature_collection,
        snapshot_date=snapshot_date,
        retrieval_method=retrieval_method,
        geojson_path=geojson_path,
        metadata_path=metadata_path,
        geojson_sha256=_sha256(geojson_path),
        metadata_sha256=_sha256(metadata_path),
    )


def _count_mapping(series: pd.Series) -> dict[str, int]:
    counts = series.value_counts(dropna=False)
    return {
        "<missing>" if pd.isna(key) else str(key): int(value)
        for key, value in counts.items()
    }


def _normalise_stop_id(value: Any) -> str:
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if (
        isinstance(value, (float, np.floating))
        and math.isfinite(float(value))
        and float(value).is_integer()
    ):
        return str(int(value))
    return str(value).strip()


def prepare_source(feature_collection: Mapping[str, Any]) -> PreparedPTAStops:
    """Validate GeoJSON records, remove exact duplicates and retain active stops."""

    if feature_collection.get("type") != "FeatureCollection":
        raise SourceExecutionError("PTA source must be a GeoJSON FeatureCollection.")
    raw_features = feature_collection.get("features")
    if not isinstance(raw_features, list) or not raw_features:
        raise SourceExecutionError("PTA FeatureCollection contains no features.")

    rows: list[dict[str, Any]] = []
    for position, feature in enumerate(raw_features):
        if not isinstance(feature, dict):
            raise SourceExecutionError(f"PTA feature {position} is not a JSON object.")
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            raise SourceExecutionError(f"PTA feature {position} has no properties object.")
        missing = REQUIRED_SOURCE_PROPERTIES.difference(properties)
        if missing:
            raise SourceExecutionError(
                f"PTA feature {position} is missing required properties: {sorted(missing)}"
            )

        geometry = feature.get("geometry")
        longitude: Any = None
        latitude: Any = None
        if geometry is not None:
            if not isinstance(geometry, dict) or geometry.get("type") != "Point":
                raise SourceExecutionError(f"PTA feature {position} has non-point geometry.")
            coordinates = geometry.get("coordinates")
            if not isinstance(coordinates, list) or len(coordinates) < 2:
                raise SourceExecutionError(f"PTA feature {position} has invalid coordinates.")
            longitude, latitude = coordinates[:2]

        row = dict(properties)
        row["longitude"] = longitude
        row["latitude"] = latitude
        rows.append(row)

    stops = pd.DataFrame(rows)
    stops["longitude"] = pd.to_numeric(stops["longitude"], errors="coerce")
    stops["latitude"] = pd.to_numeric(stops["latitude"], errors="coerce")
    stops["status"] = stops["status"].astype("string").str.strip()
    stops["stoptype"] = stops["stoptype"].astype("string").str.strip()

    exact_duplicate_count = int(stops.duplicated(list(SOURCE_RECORD_COLUMNS)).sum())
    analysis_stops = stops.drop_duplicates(list(SOURCE_RECORD_COLUMNS)).copy()
    duplicate_stop_ids = analysis_stops.loc[
        analysis_stops["stopid"].notna()
        & analysis_stops["stopid"].duplicated(keep=False),
        "stopid",
    ].unique()
    if len(duplicate_stop_ids):
        values = [_normalise_stop_id(value) for value in duplicate_stop_ids]
        raise SourceExecutionError(
            f"Repeated PTA stopid values have conflicting source rows: {values}"
        )

    active = analysis_stops.loc[
        analysis_stops["status"].eq("Active")
        & analysis_stops["longitude"].notna()
        & analysis_stops["latitude"].notna()
    ].copy()
    if active.empty:
        raise SourceExecutionError("PTA snapshot contains no geocoded Active stops.")

    invalid_coordinates = (
        ~active["latitude"].between(-90, 90)
        | ~active["longitude"].between(-180, 180)
    )
    if invalid_coordinates.any():
        raise SourceExecutionError("PTA snapshot contains invalid Active-stop coordinates.")
    if active["stopid"].isna().any() or active["stoptype"].isna().any():
        raise SourceExecutionError("Geocoded Active PTA stops require stopid and stoptype.")
    if active["stoptype"].eq("").any():
        raise SourceExecutionError("Geocoded Active PTA stops require a non-blank stoptype.")

    active["stopid"] = active["stopid"].map(_normalise_stop_id).astype("string")
    return PreparedPTAStops(
        all_stops=stops,
        active_stops=active.reset_index(drop=True),
        exact_duplicate_count=exact_duplicate_count,
        status_counts=_count_mapping(stops["status"]),
        active_stop_type_counts=_count_mapping(active["stoptype"]),
    )


def utm_epsg(longitude: float, latitude: float) -> int:
    """Return the local WGS84 UTM EPSG code for one coordinate."""

    zone = int((longitude + 180) // 6) + 1
    zone = min(max(zone, 1), 60)
    return (32600 if latitude >= 0 else 32700) + zone


def count_within_radius(distances_m: np.ndarray, radius_m: float) -> int:
    """Count finite distances on or inside the inclusive radius boundary."""

    return int(np.count_nonzero(np.isfinite(distances_m) & (distances_m <= radius_m)))


def build_features(
    sites: pd.DataFrame,
    prepared_source: PreparedPTAStops,
    buffer_radius_m: float = DEFAULT_BUFFER_RADIUS_M,
) -> pd.DataFrame:
    """Deterministically build one approved PTA feature row per supplied site."""

    required_site_columns = {"site_id", "latitude", "longitude", "coordinate_crs"}
    missing = required_site_columns.difference(sites.columns)
    if missing:
        raise SourceExecutionError(f"PTA sites are missing required columns: {sorted(missing)}")
    if not math.isfinite(float(buffer_radius_m)) or float(buffer_radius_m) <= 0:
        raise SourceExecutionError("PTA buffer_radius_m must be positive.")

    working_sites = sites[
        ["site_id", "latitude", "longitude", "coordinate_crs"]
    ].copy()
    working_sites["site_id"] = working_sites["site_id"].astype("string").str.strip()
    working_sites["coordinate_crs"] = (
        working_sites["coordinate_crs"].astype("string").str.strip().str.upper()
    )
    working_sites["latitude"] = pd.to_numeric(working_sites["latitude"], errors="coerce")
    working_sites["longitude"] = pd.to_numeric(
        working_sites["longitude"], errors="coerce"
    )
    if working_sites["site_id"].isna().any() or working_sites["site_id"].eq("").any():
        raise SourceExecutionError("PTA sites contain missing or blank site_id values.")
    if working_sites["site_id"].duplicated().any():
        raise SourceExecutionError("PTA sites must contain unique site_id values.")

    working_sites["valid_coordinate"] = (
        working_sites["latitude"].between(-36, -13)
        & working_sites["longitude"].between(112, 130)
        & working_sites["coordinate_crs"].eq("EPSG:4326")
    )
    valid_sites = working_sites.loc[working_sites["valid_coordinate"]].copy()
    valid_sites["utm_epsg"] = [
        utm_epsg(row.longitude, row.latitude) for row in valid_sites.itertuples()
    ]

    active_stops = prepared_source.active_stops
    projected_stops_by_crs: dict[int, tuple[Transformer, np.ndarray, np.ndarray]] = {}
    for epsg in sorted(valid_sites["utm_epsg"].unique()):
        transformer = Transformer.from_crs(4326, int(epsg), always_xy=True)
        stop_x, stop_y = transformer.transform(
            active_stops["longitude"].to_numpy(),
            active_stops["latitude"].to_numpy(),
        )
        projected_stops_by_crs[int(epsg)] = (
            transformer,
            np.asarray(stop_x, dtype=float),
            np.asarray(stop_y, dtype=float),
        )

    rows: list[dict[str, Any]] = []
    for site in working_sites.itertuples():
        if not site.valid_coordinate:
            rows.append(
                {
                    "site_id": site.site_id,
                    "pta_data_status": "invalid_coordinate",
                    "pta_nearest_active_stop_distance_m": np.nan,
                    "pta_nearest_active_stop_type": pd.NA,
                    "pta_active_stops_within_500m": pd.NA,
                    "pta_nearest_stop_id": pd.NA,
                }
            )
            continue

        epsg = utm_epsg(float(site.longitude), float(site.latitude))
        transformer, stop_x, stop_y = projected_stops_by_crs[epsg]
        site_x, site_y = transformer.transform(float(site.longitude), float(site.latitude))
        distances = np.hypot(stop_x - site_x, stop_y - site_y)
        nearest_position = int(np.argmin(distances))
        nearest_stop = active_stops.iloc[nearest_position]
        within_count = count_within_radius(distances, float(buffer_radius_m))
        rows.append(
            {
                "site_id": site.site_id,
                "pta_data_status": (
                    "matched" if within_count > 0 else "valid_no_stop_within_500m"
                ),
                "pta_nearest_active_stop_distance_m": round(
                    float(distances[nearest_position]), 1
                ),
                "pta_nearest_active_stop_type": nearest_stop["stoptype"],
                "pta_active_stops_within_500m": within_count,
                "pta_nearest_stop_id": nearest_stop["stopid"],
            }
        )

    features = pd.DataFrame(rows, columns=APPROVED_FEATURE_COLUMNS)
    features["site_id"] = features["site_id"].astype("string")
    features["pta_data_status"] = features["pta_data_status"].astype("string")
    features["pta_nearest_active_stop_type"] = features[
        "pta_nearest_active_stop_type"
    ].astype("string")
    features["pta_active_stops_within_500m"] = pd.array(
        features["pta_active_stops_within_500m"], dtype="Int64"
    )
    features["pta_nearest_stop_id"] = features["pta_nearest_stop_id"].astype("string")
    return features


def validate_source_specific(features: pd.DataFrame, sites: pd.DataFrame) -> None:
    """Apply PTA scientific checks beyond the shared source contract."""

    if tuple(features.columns) != APPROVED_FEATURE_COLUMNS:
        raise SourceExecutionError("PTA feature columns differ from the approved schema.")
    if len(features) != len(sites):
        raise SourceExecutionError("PTA feature row count differs from supplied sites.")
    if features["site_id"].duplicated().any():
        raise SourceExecutionError("PTA features contain duplicate site_id values.")
    if set(features["site_id"].astype(str)) != set(sites["site_id"].astype(str)):
        raise SourceExecutionError("PTA feature site_id coverage differs from supplied sites.")

    unexpected = set(features["pta_data_status"].dropna()) - ALLOWED_STATUSES
    if unexpected:
        raise SourceExecutionError(f"PTA features contain unexpected statuses: {unexpected}")

    valid = features["pta_data_status"].ne("invalid_coordinate").fillna(False)
    if features.loc[valid, "pta_nearest_active_stop_distance_m"].isna().any():
        raise SourceExecutionError("Valid PTA sites require a nearest-stop distance.")
    if features.loc[valid, "pta_nearest_active_stop_type"].isna().any():
        raise SourceExecutionError("Valid PTA sites require a nearest-stop type.")
    if features.loc[valid, "pta_nearest_stop_id"].isna().any():
        raise SourceExecutionError("Valid PTA sites require a nearest-stop identifier.")
    if (features.loc[valid, "pta_nearest_active_stop_distance_m"] < 0).any():
        raise SourceExecutionError("PTA nearest-stop distance cannot be negative.")
    if (features.loc[valid, "pta_active_stops_within_500m"] < 0).any():
        raise SourceExecutionError("PTA stop count cannot be negative.")

    zero_count = (
        features["pta_active_stops_within_500m"].eq(0).fillna(False).astype(bool)
    )
    zero_status = (
        features["pta_data_status"]
        .eq("valid_no_stop_within_500m")
        .fillna(False)
        .astype(bool)
    )
    if zero_count.ne(zero_status).any():
        raise SourceExecutionError(
            "PTA zero stop counts and valid-no-stop statuses are inconsistent."
        )

    invalid = features["pta_data_status"].eq("invalid_coordinate").fillna(False)
    value_columns = list(APPROVED_FEATURE_COLUMNS[2:])
    if features.loc[invalid, value_columns].notna().any(axis=None):
        raise SourceExecutionError("Invalid-coordinate PTA rows must have missing feature values.")


def _result_metadata(
    snapshot: PTASnapshot,
    prepared: PreparedPTAStops,
    buffer_radius_m: float,
    layer_url: str,
    project_root: Path,
) -> dict[str, Any]:
    try:
        cache_path = str(snapshot.geojson_path.relative_to(project_root.resolve()))
    except ValueError:
        cache_path = snapshot.geojson_path.name
    return {
        "dataset": "Public Transport Authority Stops (PTA-001)",
        "catalogue_url": "https://catalogue.data.wa.gov.au/dataset/public-transport-authority-stops-pta-001",
        "layer_url": layer_url,
        "snapshot_date": snapshot.snapshot_date,
        "retrieval_method": snapshot.retrieval_method,
        "cache_path": cache_path,
        "geojson_sha256": snapshot.geojson_sha256,
        "metadata_sha256": snapshot.metadata_sha256,
        "layer_name": str(snapshot.layer_metadata.get("name", "PTA-001")),
        "buffer_radius_m": buffer_radius_m,
        "distance_method": "Euclidean distance in each site's local WGS84 UTM zone",
        "raw_record_count": len(prepared.all_stops),
        "exact_duplicate_records_excluded": prepared.exact_duplicate_count,
        "unique_geocoded_active_stop_count": len(prepared.active_stops),
        "source_status_counts": dict(prepared.status_counts),
        "active_stop_type_counts": dict(prepared.active_stop_type_counts),
    }


def extract(sites: pd.DataFrame, config: SourceConfig, project_root: Path) -> FeatureResult:
    """Acquire, prepare, calculate and validate PTA features for supplied sites."""

    if config.name != "pta_stops":
        raise SourceExecutionError(
            f"PTA extractor received mismatched source configuration '{config.name}'."
        )
    buffer_radius_m = _positive_number(
        config.options, "buffer_radius_m", DEFAULT_BUFFER_RADIUS_M
    )
    layer_url = _validated_layer_url(config.options.get("layer_url", DEFAULT_LAYER_URL))
    snapshot = acquire_or_load_source(config, project_root)
    prepared = prepare_source(snapshot.feature_collection)
    features = build_features(sites, prepared, buffer_radius_m=buffer_radius_m)
    validate_source_specific(features, sites)

    warnings: list[str] = []
    if prepared.exact_duplicate_count:
        warnings.append(
            f"Excluded {prepared.exact_duplicate_count} exact duplicate source rows from analysis."
        )

    return FeatureResult(
        source_name="pta_stops",
        source_version=f"PTA-001-{snapshot.snapshot_date}-{snapshot.geojson_sha256[:12]}",
        features=features,
        metadata=_result_metadata(
            snapshot,
            prepared,
            buffer_radius_m,
            layer_url,
            project_root,
        ),
        warnings=tuple(warnings),
    )


DEFINITION = SourceDefinition(
    name="pta_stops",
    description="Nearest active PTA stop and active-stop supply within 500 m.",
    column_prefixes=("pta_",),
    extractor=extract,
)
