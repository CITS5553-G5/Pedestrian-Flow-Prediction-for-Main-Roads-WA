"""Overture Maps Places context-feature adapter.

The official Overture Python client is used only for bounded source acquisition.
Downloaded site snapshots are cached as GeoParquet. Cleaning, exact geodesic
distance filtering, taxonomy aggregation and feature construction are deterministic
and can therefore be tested without live network access.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Geod

from pedflow.context.contracts import FeatureResult, SourceConfig, SourceDefinition
from pedflow.exceptions import ConfigurationError, ContractError, SourceExecutionError
from pedflow.paths import resolve_project_path

SOURCE_NAME = "overture_places"
CATALOGUE_URL = "https://docs.overturemaps.org/guides/places/"
ACCESS_URL = "https://docs.overturemaps.org/getting-data/"
TAXONOMY_URL = "https://docs.overturemaps.org/guides/places/taxonomy/"
ATTRIBUTION_URL = "https://docs.overturemaps.org/attribution/"
DEFAULT_RELEASE = "2026-08-19.0"
DEFAULT_BUFFER_RADIUS_M = 500.0
DEFAULT_CACHE_DIRECTORY = "data/external_raw/overture_places/{release}"
DEFAULT_CONNECT_TIMEOUT_S = 15
DEFAULT_REQUEST_TIMEOUT_S = 120
DEFAULT_MAX_WORKERS = 4

FOOD_DRINK_ANCESTOR = "food_and_drink"
SHOPPING_ANCESTOR = "shopping"
ROUTINE_SHOPPING_ANCESTORS = frozenset(
    {
        "food_and_beverage_store",
        "convenience_store",
        "pharmacy_and_drug_store",
    }
)
SHOPPING_MALL_ANCESTOR = "shopping_mall"
CLOSED_OPERATING_STATUSES = frozenset(
    {"temporarily_closed", "permanently_closed"}
)
ALLOWED_OPERATING_STATUSES = frozenset(
    {"open", "temporarily_closed", "permanently_closed"}
)

FEATURE_COLUMNS = (
    "site_id",
    "overture_places_data_status",
    "overture_food_drink_count_500m",
    "overture_grocery_convenience_pharmacy_count_500m",
    "overture_shopping_mall_present_500m",
    "overture_other_shopping_count_500m",
)
VALID_STATUSES = frozenset({"complete", "complete_no_eligible_places"})

WGS84_GEOD = Geod(ellps="WGS84")


@dataclass(frozen=True)
class SourceSettings:
    """Validated source configuration for one extraction run."""

    release: str
    buffer_radius_m: float
    cache_directory: Path
    allow_download: bool
    connect_timeout_s: int
    request_timeout_s: int
    max_workers: int


@dataclass(frozen=True)
class SiteRequest:
    """One site, its conservative query box and deterministic cache path."""

    site_id: str
    latitude: float
    longitude: float
    bbox: tuple[float, float, float, float]
    cache_path: Path


@dataclass(frozen=True)
class AcquiredSitePlaces:
    """One cache-backed Overture response."""

    request: SiteRequest
    places: gpd.GeoDataFrame
    cache_hit: bool
    sha256: str


@dataclass(frozen=True)
class AcquiredSource:
    """All site responses plus safe acquisition provenance."""

    sites: Mapping[str, AcquiredSitePlaces]
    cache_hits: int
    downloads: int
    cache_set_sha256: str


@dataclass(frozen=True)
class FeatureBuild:
    """Deterministic features and source-specific QA counts."""

    features: pd.DataFrame
    source_record_count: int
    unique_record_count: int
    within_buffer_count: int
    eligible_record_count: int
    duplicate_id_count: int
    missing_taxonomy_count: int
    unknown_operating_status_count: int
    excluded_closed_count: int
    operating_status_counts: Mapping[str, int]


PlaceQuery = Callable[
    [tuple[float, float, float, float], SourceSettings],
    gpd.GeoDataFrame,
]


def _text_option(options: Mapping[str, Any], name: str, default: str) -> str:
    value = str(options.get(name, default)).strip()
    if not value:
        raise ConfigurationError(f"Overture option '{name}' cannot be blank.")
    return value


def _positive_number(options: Mapping[str, Any], name: str, default: float) -> float:
    try:
        value = float(options.get(name, default))
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"Overture option '{name}' must be numeric.") from exc
    if not math.isfinite(value) or value <= 0:
        raise ConfigurationError(f"Overture option '{name}' must be positive.")
    return value


def _positive_integer(options: Mapping[str, Any], name: str, default: int) -> int:
    try:
        value = int(options.get(name, default))
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"Overture option '{name}' must be an integer.") from exc
    if value <= 0:
        raise ConfigurationError(f"Overture option '{name}' must be positive.")
    return value


def settings_from_config(config: SourceConfig, project_root: Path) -> SourceSettings:
    """Validate source options without reading project inputs or contacting Overture."""

    if config.name != SOURCE_NAME:
        raise ConfigurationError(
            f"Overture Places adapter received source config '{config.name}'."
        )
    options = config.options
    release = _text_option(options, "release", DEFAULT_RELEASE)
    radius = _positive_number(
        options, "buffer_radius_m", DEFAULT_BUFFER_RADIUS_M
    )
    if not math.isclose(radius, DEFAULT_BUFFER_RADIUS_M, abs_tol=1e-9):
        raise ConfigurationError(
            "The approved Overture feature names require a 500 m buffer."
        )
    cache_template = _text_option(
        options,
        "cache_directory",
        DEFAULT_CACHE_DIRECTORY,
    )
    cache_directory = resolve_project_path(
        project_root,
        cache_template.format(release=release),
    )
    return SourceSettings(
        release=release,
        buffer_radius_m=radius,
        cache_directory=cache_directory,
        allow_download=bool(options.get("allow_download", True)),
        connect_timeout_s=_positive_integer(
            options, "connect_timeout_seconds", DEFAULT_CONNECT_TIMEOUT_S
        ),
        request_timeout_s=_positive_integer(
            options, "request_timeout_seconds", DEFAULT_REQUEST_TIMEOUT_S
        ),
        max_workers=_positive_integer(
            options, "max_workers", DEFAULT_MAX_WORKERS
        ),
    )


def geodesic_query_bbox(
    latitude: float,
    longitude: float,
    radius_m: float,
) -> tuple[float, float, float, float]:
    """Return the cardinal WGS84 bounds enclosing a geodesic point buffer."""

    east_lon, _, _ = WGS84_GEOD.fwd(longitude, latitude, 90, radius_m)
    west_lon, _, _ = WGS84_GEOD.fwd(longitude, latitude, 270, radius_m)
    _, north_lat, _ = WGS84_GEOD.fwd(longitude, latitude, 0, radius_m)
    _, south_lat, _ = WGS84_GEOD.fwd(longitude, latitude, 180, radius_m)
    return (west_lon, south_lat, east_lon, north_lat)


def _cache_file_name(
    site_id: str,
    latitude: float,
    longitude: float,
    radius_m: float,
) -> str:
    safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", site_id).strip("._") or "site"
    fingerprint = hashlib.sha256(
        f"{site_id}|{latitude:.10f}|{longitude:.10f}|{radius_m:.3f}".encode()
    ).hexdigest()[:12]
    return f"{safe_id}_{fingerprint}.geoparquet"


def build_site_requests(
    sites: pd.DataFrame,
    settings: SourceSettings,
) -> tuple[SiteRequest, ...]:
    """Build deterministic bounded requests for every already validated site."""

    requests: list[SiteRequest] = []
    for site in sites.itertuples(index=False):
        site_id = str(site.site_id)
        latitude = float(site.latitude)
        longitude = float(site.longitude)
        requests.append(
            SiteRequest(
                site_id=site_id,
                latitude=latitude,
                longitude=longitude,
                bbox=geodesic_query_bbox(
                    latitude,
                    longitude,
                    settings.buffer_radius_m,
                ),
                cache_path=settings.cache_directory
                / _cache_file_name(
                    site_id,
                    latitude,
                    longitude,
                    settings.buffer_radius_m,
                ),
            )
        )
    return tuple(requests)


def query_overture_places(
    bbox: tuple[float, float, float, float],
    settings: SourceSettings,
) -> gpd.GeoDataFrame:
    """Query one bounded area through the official Overture Python client."""

    try:
        from overturemaps import geodataframe
    except ImportError as exc:
        raise SourceExecutionError(
            "The official overturemaps package is not installed. "
            "Run python -m pip install -r requirements.txt."
        ) from exc

    try:
        places = geodataframe(
            "place",
            bbox=bbox,
            release=settings.release,
            connect_timeout=settings.connect_timeout_s,
            request_timeout=settings.request_timeout_s,
            stac=True,
        )
    except Exception as exc:
        raise SourceExecutionError(
            f"Overture release {settings.release} query failed: {exc}"
        ) from exc

    if places is None:
        return gpd.GeoDataFrame(
            columns=[
                "id",
                "geometry",
                "confidence",
                "operating_status",
                "basic_category",
                "taxonomy",
                "sources",
            ],
            geometry="geometry",
            crs="EPSG:4326",
        )
    if not isinstance(places, gpd.GeoDataFrame):
        raise SourceExecutionError("Overture client did not return a GeoDataFrame.")
    return places


def _validate_source_frame(places: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    required = {"id", "geometry", "basic_category", "taxonomy"}
    missing = required.difference(places.columns)
    if missing:
        raise SourceExecutionError(
            f"Overture Places schema is missing required fields: {sorted(missing)}"
        )
    checked = places.copy()
    if checked.crs is None:
        checked = checked.set_crs("EPSG:4326")
    elif checked.crs.to_epsg() != 4326:
        checked = checked.to_crs("EPSG:4326")
    if not checked.empty:
        geometry_types = set(checked.geometry.geom_type.dropna())
        if geometry_types.difference({"Point"}):
            raise SourceExecutionError(
                f"Overture Places returned non-point geometries: {geometry_types}"
            )
    return checked


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_geoparquet_atomic(places: gpd.GeoDataFrame, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    try:
        places.to_parquet(temporary, index=False)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def _acquire_one_site(
    request: SiteRequest,
    settings: SourceSettings,
    query: PlaceQuery,
) -> AcquiredSitePlaces:
    if request.cache_path.is_file():
        try:
            places = gpd.read_parquet(request.cache_path)
        except Exception as exc:
            raise SourceExecutionError(
                f"Could not read cached Overture file {request.cache_path.name}: {exc}"
            ) from exc
        places = _validate_source_frame(places)
        return AcquiredSitePlaces(
            request=request,
            places=places,
            cache_hit=True,
            sha256=_sha256(request.cache_path),
        )

    if not settings.allow_download:
        raise SourceExecutionError(
            f"Overture cache is missing for site_id={request.site_id} and downloads are disabled."
        )

    places = _validate_source_frame(query(request.bbox, settings))
    _write_geoparquet_atomic(places, request.cache_path)
    return AcquiredSitePlaces(
        request=request,
        places=places,
        cache_hit=False,
        sha256=_sha256(request.cache_path),
    )


def acquire_or_load_source(
    sites: pd.DataFrame,
    settings: SourceSettings,
    query: PlaceQuery = query_overture_places,
) -> AcquiredSource:
    """Acquire bounded per-site snapshots concurrently while preserving site order."""

    requests = build_site_requests(sites, settings)
    acquired_by_id: dict[str, AcquiredSitePlaces] = {}
    errors: list[str] = []

    if not requests:
        return AcquiredSource(
            sites={},
            cache_hits=0,
            downloads=0,
            cache_set_sha256=hashlib.sha256(b"").hexdigest(),
        )

    with ThreadPoolExecutor(max_workers=min(settings.max_workers, len(requests))) as pool:
        futures = {
            pool.submit(_acquire_one_site, request, settings, query): request
            for request in requests
        }
        for future in as_completed(futures):
            request = futures[future]
            try:
                acquired_by_id[request.site_id] = future.result()
            except (SourceExecutionError, ContractError, OSError) as exc:
                errors.append(f"{request.site_id}: {exc}")

    if errors:
        preview = "; ".join(sorted(errors)[:5])
        suffix = "" if len(errors) <= 5 else f"; and {len(errors) - 5} more"
        raise SourceExecutionError(
            f"Overture acquisition failed for {len(errors)} site(s): {preview}{suffix}"
        )

    ordered = {request.site_id: acquired_by_id[request.site_id] for request in requests}
    combined_hash = hashlib.sha256(
        "\n".join(f"{site_id}:{item.sha256}" for site_id, item in ordered.items()).encode()
    ).hexdigest()
    return AcquiredSource(
        sites=ordered,
        cache_hits=sum(item.cache_hit for item in ordered.values()),
        downloads=sum(not item.cache_hit for item in ordered.values()),
        cache_set_sha256=combined_hash,
    )


def _normalise_hierarchy(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Mapping):
        return ()
    hierarchy = value.get("hierarchy")
    if hierarchy is None:
        return ()
    if isinstance(hierarchy, str):
        values = [hierarchy]
    else:
        try:
            values = list(hierarchy)
        except TypeError:
            return ()
    return tuple(str(item).strip() for item in values if str(item).strip())


def prepare_places(places: gpd.GeoDataFrame) -> tuple[pd.DataFrame, int]:
    """Normalise only fields needed for deterministic feature calculation."""

    checked = _validate_source_frame(places)
    rows: list[dict[str, Any]] = []
    for record in checked.itertuples(index=False):
        geometry = record.geometry
        if geometry is None or geometry.is_empty or geometry.geom_type != "Point":
            continue
        operating_status = getattr(record, "operating_status", None)
        if pd.isna(operating_status):
            operating_status = None
        else:
            operating_status = str(operating_status).strip().lower() or None
        confidence = pd.to_numeric(
            pd.Series([getattr(record, "confidence", np.nan)]),
            errors="coerce",
        ).iloc[0]
        rows.append(
            {
                "id": str(record.id).strip(),
                "longitude": float(geometry.x),
                "latitude": float(geometry.y),
                "basic_category": (
                    None
                    if pd.isna(record.basic_category)
                    else str(record.basic_category).strip()
                ),
                "taxonomy_hierarchy": _normalise_hierarchy(record.taxonomy),
                "operating_status": operating_status,
                "confidence": confidence,
            }
        )

    normalised = pd.DataFrame(
        rows,
        columns=[
            "id",
            "longitude",
            "latitude",
            "basic_category",
            "taxonomy_hierarchy",
            "operating_status",
            "confidence",
        ],
    )
    if normalised.empty:
        return normalised, 0
    if normalised["id"].eq("").any():
        raise ContractError("Overture Places contains a blank GERS ID.")
    invalid_confidence = normalised["confidence"].notna() & ~normalised[
        "confidence"
    ].between(0, 1)
    if invalid_confidence.any():
        raise ContractError("Overture Places contains confidence outside [0, 1].")
    invalid_statuses = set(normalised["operating_status"].dropna()).difference(
        ALLOWED_OPERATING_STATUSES
    )
    if invalid_statuses:
        raise ContractError(
            f"Overture Places contains unexpected operating statuses: {sorted(invalid_statuses)}"
        )
    duplicate_count = int(normalised["id"].duplicated().sum())
    normalised = normalised.drop_duplicates("id", keep="first").reset_index(drop=True)
    return normalised, duplicate_count


def _within_radius(
    places: pd.DataFrame,
    latitude: float,
    longitude: float,
    radius_m: float,
) -> pd.DataFrame:
    if places.empty:
        result = places.copy()
        result["distance_m"] = pd.Series(dtype="float64")
        return result
    _, _, distances = WGS84_GEOD.inv(
        np.full(len(places), longitude),
        np.full(len(places), latitude),
        places["longitude"].to_numpy(),
        places["latitude"].to_numpy(),
    )
    result = places.copy()
    result["distance_m"] = distances
    return result.loc[result["distance_m"].le(radius_m + 1e-6)].copy()


def _contains_any(hierarchy: tuple[str, ...], categories: frozenset[str]) -> bool:
    return not categories.isdisjoint(hierarchy)


def build_features(
    sites: pd.DataFrame,
    acquired: AcquiredSource,
    radius_m: float = DEFAULT_BUFFER_RADIUS_M,
) -> FeatureBuild:
    """Calculate the four approved Overture POI features for all supplied sites."""

    rows: list[dict[str, Any]] = []
    source_records = 0
    unique_records = 0
    within_records = 0
    eligible_records = 0
    duplicate_ids = 0
    missing_taxonomy = 0
    unknown_status = 0
    excluded_closed = 0
    status_counts: Counter[str] = Counter()

    for site in sites.itertuples(index=False):
        site_id = str(site.site_id)
        try:
            item = acquired.sites[site_id]
        except KeyError as exc:
            raise ContractError(f"Overture acquisition is missing site_id={site_id}.") from exc

        source_records += len(item.places)
        prepared, site_duplicates = prepare_places(item.places)
        duplicate_ids += site_duplicates
        unique_records += len(prepared)
        within = _within_radius(
            prepared,
            float(site.latitude),
            float(site.longitude),
            radius_m,
        )
        within_records += len(within)
        missing_taxonomy += int(within["taxonomy_hierarchy"].map(len).eq(0).sum())
        for status, count in within["operating_status"].fillna("unknown").value_counts().items():
            status_counts[str(status)] += int(count)
        closed = within["operating_status"].isin(CLOSED_OPERATING_STATUSES)
        excluded_closed += int(closed.sum())
        eligible = within.loc[~closed].copy()
        eligible_records += len(eligible)
        unknown_status += int(eligible["operating_status"].isna().sum())

        hierarchies = eligible["taxonomy_hierarchy"]
        food_drink = hierarchies.map(lambda value: FOOD_DRINK_ANCESTOR in value)
        shopping = hierarchies.map(lambda value: SHOPPING_ANCESTOR in value)
        routine = hierarchies.map(
            lambda value: _contains_any(value, ROUTINE_SHOPPING_ANCESTORS)
        )
        shopping_mall = hierarchies.map(
            lambda value: SHOPPING_MALL_ANCESTOR in value
        )
        other_shopping = shopping & ~routine & ~shopping_mall

        feature_values = {
            "overture_food_drink_count_500m": int(food_drink.sum()),
            "overture_grocery_convenience_pharmacy_count_500m": int(routine.sum()),
            "overture_shopping_mall_present_500m": bool(shopping_mall.any()),
            "overture_other_shopping_count_500m": int(other_shopping.sum()),
        }
        has_eligible = any(
            value if isinstance(value, bool) else value > 0
            for value in feature_values.values()
        )
        rows.append(
            {
                "site_id": site_id,
                "overture_places_data_status": (
                    "complete" if has_eligible else "complete_no_eligible_places"
                ),
                **feature_values,
            }
        )

    features = pd.DataFrame(rows, columns=list(FEATURE_COLUMNS))
    features["site_id"] = features["site_id"].astype("string")
    features["overture_places_data_status"] = features[
        "overture_places_data_status"
    ].astype("string")
    return FeatureBuild(
        features=features,
        source_record_count=source_records,
        unique_record_count=unique_records,
        within_buffer_count=within_records,
        eligible_record_count=eligible_records,
        duplicate_id_count=duplicate_ids,
        missing_taxonomy_count=missing_taxonomy,
        unknown_operating_status_count=unknown_status,
        excluded_closed_count=excluded_closed,
        operating_status_counts=dict(sorted(status_counts.items())),
    )


def validate_source_specific(
    features: pd.DataFrame,
    sites: pd.DataFrame,
) -> None:
    """Enforce Overture feature schema, site order, types and value domains."""

    if tuple(features.columns) != FEATURE_COLUMNS:
        raise ContractError("Overture feature columns differ from the approved contract.")
    if features["site_id"].tolist() != sites["site_id"].astype("string").tolist():
        raise ContractError("Overture features changed the supplied site order or coverage.")
    if features["site_id"].duplicated().any():
        raise ContractError("Overture features contain duplicate site_id values.")
    invalid_statuses = set(features["overture_places_data_status"]).difference(
        VALID_STATUSES
    )
    if invalid_statuses:
        raise ContractError(
            f"Overture features contain unexpected statuses: {sorted(invalid_statuses)}"
        )
    count_columns = (
        "overture_food_drink_count_500m",
        "overture_grocery_convenience_pharmacy_count_500m",
        "overture_other_shopping_count_500m",
    )
    for column in count_columns:
        values = pd.to_numeric(features[column], errors="coerce")
        if values.isna().any() or values.lt(0).any() or (values % 1).ne(0).any():
            raise ContractError(f"Overture count field {column} must contain non-negative integers.")
    if not features["overture_shopping_mall_present_500m"].map(
        lambda value: isinstance(value, (bool, np.bool_))
    ).all():
        raise ContractError("Overture shopping-mall field must be boolean.")


def _safe_cache_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.name


def extract(
    sites: pd.DataFrame,
    config: SourceConfig,
    project_root: Path,
) -> FeatureResult:
    """Return one validated Overture Places feature row per supplied site."""

    settings = settings_from_config(config, project_root)
    acquired = acquire_or_load_source(sites, settings)
    built = build_features(sites, acquired, settings.buffer_radius_m)
    validate_source_specific(built.features, sites)

    warnings: list[str] = []
    if built.unknown_operating_status_count:
        warnings.append(
            f"{built.unknown_operating_status_count} in-buffer records have no "
            "operating_status; they are included because the source does not mark them closed."
        )
    if built.missing_taxonomy_count:
        warnings.append(
            f"{built.missing_taxonomy_count} in-buffer records have no taxonomy hierarchy "
            "and cannot enter the four category aggregates."
        )
    zero_sites = int(
        built.features["overture_places_data_status"]
        .eq("complete_no_eligible_places")
        .sum()
    )
    if zero_sites:
        warnings.append(
            f"{zero_sites} site(s) have no eligible food/drink or shopping place in 500 m."
        )
    if built.duplicate_id_count:
        warnings.append(
            f"Removed {built.duplicate_id_count} duplicate GERS ID occurrence(s) within site queries."
        )

    metadata = {
        "catalogue_url": CATALOGUE_URL,
        "access_url": ACCESS_URL,
        "taxonomy_url": TAXONOMY_URL,
        "attribution_url": ATTRIBUTION_URL,
        "release": settings.release,
        "retrieval_method": "Official overturemaps Python client, bounded place queries",
        "buffer_radius_m": settings.buffer_radius_m,
        "distance_method": "WGS84 geodesic distance from site point",
        "cache_directory": _safe_cache_path(settings.cache_directory, project_root),
        "cache_hit_count": acquired.cache_hits,
        "download_count": acquired.downloads,
        "cache_set_sha256": acquired.cache_set_sha256,
        "source_record_count": built.source_record_count,
        "unique_record_count": built.unique_record_count,
        "within_buffer_count": built.within_buffer_count,
        "eligible_record_count": built.eligible_record_count,
        "excluded_closed_count": built.excluded_closed_count,
        "operating_status_counts": dict(built.operating_status_counts),
        "category_contract": {
            "food_drink": {"taxonomy_ancestor": FOOD_DRINK_ANCESTOR},
            "grocery_convenience_pharmacy": {
                "taxonomy_ancestors": sorted(ROUTINE_SHOPPING_ANCESTORS)
            },
            "shopping_mall": {"taxonomy_ancestor": SHOPPING_MALL_ANCESTOR},
            "other_shopping": {
                "taxonomy_ancestor": SHOPPING_ANCESTOR,
                "excludes": [
                    *sorted(ROUTINE_SHOPPING_ANCESTORS),
                    SHOPPING_MALL_ANCESTOR,
                ],
            },
        },
        "additional_confidence_filter_applied": False,
        "explicit_closed_records_excluded": True,
    }
    return FeatureResult(
        source_name=SOURCE_NAME,
        source_version=settings.release,
        features=built.features,
        metadata=metadata,
        warnings=tuple(warnings),
    )


DEFINITION = SourceDefinition(
    name=SOURCE_NAME,
    description=(
        "Food/drink and shopping context from Overture Places within an exact 500 m radius."
    ),
    column_prefixes=("overture_",),
    extractor=extract,
)
