"""WA Health establishment-proximity feature adapter.

External snapshot acquisition is separated from deterministic validation and
geodesic feature construction. The notebook remains the scientific explanation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
from pyproj import Geod

from pedflow.context.contracts import FeatureResult, SourceConfig, SourceDefinition
from pedflow.exceptions import SourceExecutionError
from pedflow.paths import resolve_project_path

SOURCE_NAME = "wa_health_establishments"
DATASET_ID = "Health-001"
DEFAULT_SNAPSHOT_DATE = "2026-08-24"
DEFAULT_SNAPSHOT_PATH = (
    "data/external_raw/wa_health_establishments/2026-08-24/"
    "health_hospitals_health_001.geojson"
)
DEFAULT_CATALOGUE_URL = "https://catalogue.data.wa.gov.au/dataset/health-establishments"
DEFAULT_LAYER_URL = (
    "https://public-services.slip.wa.gov.au/public/rest/services/"
    "SLIP_Public_Services/Health_WFS/MapServer/1"
)
DEFAULT_USER_AGENT = "CITS5553-pedflow-wa-health/1.0"

REQUIRED_SOURCE_FIELDS = (
    "estab_id", "establishm", "is_open", "category", "est",
    "no_of_beds", "longitude", "latitude",
)
FEATURE_COLUMNS = (
    "site_id",
    "health_nearest_establishment_distance_m",
    "health_nearest_establishment_category",
    "health_nearest_establishment_type",
    "health_nearest_establishment_id",
    "health_nearest_establishment_name",
    "health_data_status",
)
EXACT_REGRESSION_COLUMNS = (
    "site_id",
    "health_nearest_establishment_category",
    "health_nearest_establishment_type",
    "health_nearest_establishment_id",
    "health_nearest_establishment_name",
    "health_data_status",
)
# The reviewed workbook stores distances to 0.1 m. Permit only that rounding
# precision and negligible geodesic-library floating-point differences.
DISTANCE_REGRESSION_ATOL_M = 0.1


@dataclass(frozen=True)
class AcquiredHealthSource:
    """Raw Health-001 payload with safe snapshot provenance."""

    payload: Mapping[str, Any]
    configured_path: str
    snapshot_date: str
    sha256: str
    retrieval_method: str


@dataclass(frozen=True)
class PreparedHealthSource:
    """Validated source records and source-level QA summaries."""

    records: pd.DataFrame
    eligible_records: pd.DataFrame
    source_record_count: int
    eligible_record_count: int
    maximum_coordinate_difference_deg: float


def _option(config: SourceConfig, name: str, default: Any) -> Any:
    return config.options.get(name, default)


def _text(config: SourceConfig, name: str, default: str) -> str:
    value = str(_option(config, name, default)).strip()
    if not value:
        raise SourceExecutionError(f"WA Health option '{name}' must be non-empty text.")
    return value


def _number(config: SourceConfig, name: str, default: float) -> float:
    try:
        value = float(_option(config, name, default))
    except (TypeError, ValueError) as exc:
        raise SourceExecutionError(
            f"WA Health option '{name}' must be a finite number."
        ) from exc
    if not np.isfinite(value):
        raise SourceExecutionError(f"WA Health option '{name}' must be a finite number.")
    return value


def _boolean(config: SourceConfig, name: str, default: bool) -> bool:
    value = _option(config, name, default)
    if not isinstance(value, bool):
        raise SourceExecutionError(f"WA Health option '{name}' must be true or false.")
    return value


def _public_https_url(config: SourceConfig, name: str, default: str) -> str:
    value = _text(config, name, default)
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise SourceExecutionError(
            f"WA Health option '{name}' must be a public HTTPS URL without "
            "credentials, query parameters, or fragments."
        )
    return value


def _vocabulary(
    config: SourceConfig, name: str, default: tuple[str, ...]
) -> tuple[str, ...]:
    value = _option(config, name, default)
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise SourceExecutionError(f"WA Health option '{name}' must be a text list.")
    result = tuple(str(item).strip() for item in value)
    if not result or any(not item for item in result) or len(set(result)) != len(result):
        raise SourceExecutionError(
            f"WA Health option '{name}' must contain unique non-empty values."
        )
    return result


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json_url(
    url: str,
    params: Mapping[str, Any] | None = None,
    timeout: float = 120.0,
    user_agent: str = DEFAULT_USER_AGENT,
    opener: Callable[..., Any] | None = None,
) -> Mapping[str, Any]:
    """Read a JSON object from an official endpoint using injectable HTTP I/O."""

    full_url = f"{url}?{urlencode(params)}" if params else url
    request = Request(full_url, headers={"User-Agent": user_agent})
    try:
        with (opener or urlopen)(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        # Do not expose raw responses, URLs, coordinates, tokens, or credentials.
        raise SourceExecutionError(
            f"{type(exc).__name__}: WA Health source request failed."
        ) from exc
    if not isinstance(payload, Mapping):
        raise SourceExecutionError("WA Health endpoint did not return a JSON object.")
    return payload


def _write_snapshot_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as temporary:
            json.dump(payload, temporary, ensure_ascii=False)
            temporary_name = temporary.name
        Path(temporary_name).replace(path)
    except Exception as exc:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)
        raise SourceExecutionError("Could not atomically cache WA Health data.") from exc


def acquire_or_load_source(
    config: SourceConfig,
    project_root: Path,
    opener: Callable[..., Any] | None = None,
) -> AcquiredHealthSource:
    """Load the approved cache or retrieve and atomically cache Health-001."""

    configured_path = _text(config, "snapshot_path", DEFAULT_SNAPSHOT_PATH)
    snapshot_date = _text(config, "snapshot_date", DEFAULT_SNAPSHOT_DATE)
    path = resolve_project_path(project_root, configured_path)
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise SourceExecutionError("Could not read cached WA Health data.") from exc
        method = "cached dated GeoJSON snapshot"
    else:
        if not _boolean(config, "allow_download", True):
            raise SourceExecutionError(
                "WA Health snapshot is missing and controlled download is disabled."
            )
        layer_url = _public_https_url(config, "layer_url", DEFAULT_LAYER_URL)
        timeout = _number(config, "timeout_seconds", 120.0)
        if timeout <= 0:
            raise SourceExecutionError("WA Health timeout must be greater than zero.")
        user_agent = _text(config, "user_agent", DEFAULT_USER_AGENT)
        metadata = read_json_url(
            layer_url, {"f": "pjson"}, timeout, user_agent, opener
        )
        if metadata.get("type") != "Feature Layer":
            raise SourceExecutionError("WA Health endpoint is not a Feature Layer.")
        payload = read_json_url(
            f"{layer_url}/query",
            {
                "where": "1=1", "outFields": "*", "returnGeometry": "true",
                "outSR": 4326, "f": "geojson",
            },
            timeout,
            user_agent,
            opener,
        )
        _write_snapshot_atomic(path, payload)
        method = "controlled ArcGIS REST retrieval cached as dated GeoJSON"
    if not isinstance(payload, Mapping):
        raise SourceExecutionError("WA Health snapshot is not a JSON object.")
    return AcquiredHealthSource(
        payload, configured_path, snapshot_date, _file_sha256(path), method
    )


def _normalise_id(value: Any) -> Any:
    if pd.isna(value):
        return pd.NA
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value).strip()
    return str(int(number)) if number.is_integer() else str(value).strip()


def prepare_source(
    raw_source: Mapping[str, Any] | AcquiredHealthSource,
    config: SourceConfig,
) -> PreparedHealthSource:
    """Validate and clean Health-001 records independently of project sites."""

    payload = raw_source.payload if isinstance(raw_source, AcquiredHealthSource) else raw_source
    if payload.get("type") != "FeatureCollection":
        raise SourceExecutionError("WA Health data must be a GeoJSON FeatureCollection.")
    source_features = payload.get("features")
    if not isinstance(source_features, list) or not source_features:
        raise SourceExecutionError("WA Health snapshot contains no source features.")

    rows: list[dict[str, Any]] = []
    invalid_geometries = 0
    for feature in source_features:
        properties = feature.get("properties") if isinstance(feature, Mapping) else None
        geometry = feature.get("geometry") if isinstance(feature, Mapping) else None
        coordinates = geometry.get("coordinates") if isinstance(geometry, Mapping) else None
        if (
            not isinstance(properties, Mapping)
            or not isinstance(geometry, Mapping)
            or geometry.get("type") != "Point"
            or not isinstance(coordinates, (list, tuple))
            or len(coordinates) < 2
        ):
            invalid_geometries += 1
            continue
        row = dict(properties)
        row["_geometry_longitude"] = coordinates[0]
        row["_geometry_latitude"] = coordinates[1]
        rows.append(row)
    if invalid_geometries:
        raise SourceExecutionError(
            f"WA Health data contains {invalid_geometries} invalid point geometries."
        )

    records = pd.DataFrame(rows)
    missing = set(REQUIRED_SOURCE_FIELDS).difference(records.columns)
    if missing:
        raise SourceExecutionError(f"WA Health data is missing fields: {sorted(missing)}")
    records = records.loc[
        :, [*REQUIRED_SOURCE_FIELDS, "_geometry_longitude", "_geometry_latitude"]
    ].copy()
    for column in ("is_open", "category", "est", "establishm"):
        records[column] = records[column].astype("string").str.strip()
    for column in (
        "longitude", "latitude", "no_of_beds",
        "_geometry_longitude", "_geometry_latitude",
    ):
        records[column] = pd.to_numeric(records[column], errors="coerce")
    records["estab_id"] = records["estab_id"].map(_normalise_id).astype("string")

    if records["estab_id"].isna().any() or records["estab_id"].eq("").any():
        raise SourceExecutionError("WA Health data contains missing establishment IDs.")
    if records["estab_id"].duplicated().any():
        duplicates = records.loc[
            records["estab_id"].duplicated(keep=False), "estab_id"
        ].tolist()
        raise SourceExecutionError(
            f"WA Health data contains duplicate establishment IDs: {duplicates[:10]}"
        )
    if records[["is_open", "category", "est", "establishm"]].isna().any().any():
        raise SourceExecutionError("WA Health data contains missing required text.")
    coordinate_columns = [
        "longitude", "latitude", "_geometry_longitude", "_geometry_latitude"
    ]
    if records[coordinate_columns].isna().any().any():
        raise SourceExecutionError("WA Health data contains invalid coordinates.")

    domains = {
        "is_open": _vocabulary(config, "allowed_open_statuses", ("Y", "N")),
        "category": _vocabulary(
            config, "eligible_categories", ("Acute Hospital", "Nursing Post")
        ),
        "est": _vocabulary(
            config, "allowed_establishment_types", ("Public", "Private")
        ),
    }
    for column, allowed in domains.items():
        unexpected = set(records[column].unique()).difference(allowed)
        if unexpected:
            raise SourceExecutionError(
                f"WA Health data contains unexpected {column}: {sorted(unexpected)}"
            )

    within_bounds = records["_geometry_latitude"].between(
        _number(config, "wa_min_latitude", -36),
        _number(config, "wa_max_latitude", -13),
    ) & records["_geometry_longitude"].between(
        _number(config, "wa_min_longitude", 112),
        _number(config, "wa_max_longitude", 130),
    )
    if not within_bounds.all():
        raise SourceExecutionError("WA Health geometries fall outside broad WA bounds.")
    maximum_difference = float(max(
        (records["longitude"] - records["_geometry_longitude"]).abs().max(),
        (records["latitude"] - records["_geometry_latitude"]).abs().max(),
    ))
    permitted = _number(config, "max_coordinate_difference_deg", 0.001)
    if permitted < 0 or maximum_difference > permitted:
        raise SourceExecutionError(
            "WA Health attribute and geometry coordinates are inconsistent."
        )

    open_value = _text(config, "open_status_value", "Y")
    eligible = records.loc[
        records["is_open"].eq(open_value)
        & records["category"].isin(domains["category"])
    ].copy()
    if eligible.empty:
        raise SourceExecutionError("WA Health data has no open eligible establishments.")
    return PreparedHealthSource(
        records, eligible, len(records), len(eligible), maximum_difference
    )


def build_features(
    sites: pd.DataFrame,
    prepared_source: PreparedHealthSource,
    config: SourceConfig,
) -> pd.DataFrame:
    """Build deterministic nearest-establishment features for arbitrary sites."""

    required = {"site_id", "latitude", "longitude", "coordinate_crs"}
    missing = required.difference(sites.columns)
    if missing:
        raise SourceExecutionError(f"WA Health sites are missing fields: {sorted(missing)}")
    if sites["site_id"].duplicated().any():
        raise SourceExecutionError("WA Health sites contain duplicate site_id values.")
    if not sites["coordinate_crs"].astype("string").str.upper().eq("EPSG:4326").all():
        raise SourceExecutionError("WA Health sites must use coordinate_crs EPSG:4326.")

    raw_decimals = _option(config, "distance_round_decimals", 1)
    if isinstance(raw_decimals, bool):
        raise SourceExecutionError("WA Health distance precision must be an integer.")
    try:
        decimals = int(raw_decimals)
    except (TypeError, ValueError) as exc:
        raise SourceExecutionError("WA Health distance precision must be an integer.") from exc
    if decimals < 0 or decimals != raw_decimals:
        raise SourceExecutionError("WA Health distance precision must be non-negative.")

    geod = Geod(ellps=_text(config, "geodesic_ellipsoid", "WGS84"))
    source = prepared_source.eligible_records
    source_lon = source["_geometry_longitude"].to_numpy(dtype=float)
    source_lat = source["_geometry_latitude"].to_numpy(dtype=float)
    rows: list[dict[str, Any]] = []
    for site in sites.itertuples(index=False):
        latitude = float(site.latitude)
        longitude = float(site.longitude)
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise SourceExecutionError(f"WA Health site '{site.site_id}' has invalid coordinates.")
        _, _, distances = geod.inv(
            np.full(len(source), longitude),
            np.full(len(source), latitude),
            source_lon,
            source_lat,
        )
        position = int(np.argmin(distances))
        nearest = source.iloc[position]
        rows.append(
            {
                "site_id": str(site.site_id),
                "health_nearest_establishment_distance_m": round(
                    float(distances[position]), decimals
                ),
                "health_nearest_establishment_category": nearest["category"],
                "health_nearest_establishment_type": nearest["est"],
                "health_nearest_establishment_id": nearest["estab_id"],
                "health_nearest_establishment_name": nearest["establishm"],
                "health_data_status": "matched",
            }
        )

    result = pd.DataFrame(rows, columns=list(FEATURE_COLUMNS))
    result["site_id"] = result["site_id"].astype("string")
    result["health_nearest_establishment_id"] = result[
        "health_nearest_establishment_id"
    ].astype("string")
    return result


def validate_source_specific(
    features: pd.DataFrame,
    sites: pd.DataFrame,
    prepared_source: PreparedHealthSource,
    config: SourceConfig,
) -> None:
    """Apply WA Health checks beyond the common source-output contract."""

    if tuple(features.columns) != FEATURE_COLUMNS:
        raise SourceExecutionError("WA Health columns differ from the approved schema.")
    expected_ids = sites["site_id"].astype("string").tolist()
    if features["site_id"].astype("string").tolist() != expected_ids:
        raise SourceExecutionError("WA Health features do not preserve site order.")
    if features["site_id"].duplicated().any():
        raise SourceExecutionError("WA Health features contain duplicate site_id values.")
    if prepared_source.eligible_records.empty:
        raise SourceExecutionError("WA Health prepared data has no eligible records.")
    if not features["health_data_status"].eq("matched").all():
        raise SourceExecutionError("WA Health features contain unexpected statuses.")
    if features.drop(columns="site_id").isna().any().any():
        raise SourceExecutionError("WA Health matched features contain missing values.")
    distances = pd.to_numeric(
        features["health_nearest_establishment_distance_m"], errors="coerce"
    )
    if distances.isna().any() or distances.lt(0).any():
        raise SourceExecutionError("WA Health features contain invalid distances.")
    approved_categories = set(_vocabulary(
        config, "eligible_categories", ("Acute Hospital", "Nursing Post")
    ))
    observed_categories = set(features["health_nearest_establishment_category"])
    if not observed_categories.issubset(approved_categories):
        raise SourceExecutionError("WA Health features contain unapproved categories.")


def make_feature_result(
    sites: pd.DataFrame,
    features: pd.DataFrame,
    acquired: AcquiredHealthSource,
    prepared: PreparedHealthSource,
    config: SourceConfig,
) -> FeatureResult:
    """Validate output and attach safe version, provenance, and caveats."""

    validate_source_specific(features, sites, prepared, config)
    source_version = (
        f"{DATASET_ID} snapshot {acquired.snapshot_date} ({acquired.sha256[:12]})"
    )
    metadata = {
        "provider": "Western Australian Department of Health",
        "dataset_id": DATASET_ID,
        "dataset_title": "Health Establishments",
        "catalogue_url": _public_https_url(
            config, "catalogue_url", DEFAULT_CATALOGUE_URL
        ),
        "api_layer_url": _public_https_url(config, "layer_url", DEFAULT_LAYER_URL),
        "api_layer_identifier": "SLIP_Public_Services/Health_WFS/MapServer/1",
        "snapshot_date": acquired.snapshot_date,
        "source_file": acquired.configured_path,
        "source_file_sha256": acquired.sha256,
        "retrieval_method": acquired.retrieval_method,
        "source_record_count": prepared.source_record_count,
        "eligible_record_count": prepared.eligible_record_count,
        "maximum_coordinate_difference_deg": prepared.maximum_coordinate_difference_deg,
        "eligible_categories": list(_vocabulary(
            config, "eligible_categories", ("Acute Hospital", "Nursing Post")
        )),
        "open_status_value": _text(config, "open_status_value", "Y"),
        "input_crs": "EPSG:4326",
        "distance_method": "pyproj.Geod inverse geodesic",
        "geodesic_ellipsoid": _text(config, "geodesic_ellipsoid", "WGS84"),
        "distance_unit": "metres",
    }
    warnings = (
        "Distance is WGS84 geodesic distance, not walking-network distance.",
        (
            "Nearest open hospital or nursing post is proximity context, not service "
            "capacity or pedestrian demand."
        ),
        "Number of beds is used for source QA only and is not an approved output feature.",
    )
    return FeatureResult(SOURCE_NAME, source_version, features, metadata, warnings)


def extract(sites: pd.DataFrame, config: SourceConfig, project_root: Path) -> FeatureResult:
    """Return one Health-001 feature row per supplied validated site."""

    acquired = acquire_or_load_source(config, project_root)
    prepared = prepare_source(acquired, config)
    features = build_features(sites, prepared, config)
    return make_feature_result(sites, features, acquired, prepared, config)


DEFINITION = SourceDefinition(
    name=SOURCE_NAME,
    description="Nearest open WA Health acute hospital or nursing post.",
    column_prefixes=("health_",),
    extractor=extract,
)
