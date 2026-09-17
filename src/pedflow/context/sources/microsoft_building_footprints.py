"""Microsoft Global ML Building Footprints context-feature adapter.

External release-index and tile I/O is kept separate from deterministic geometry
calculations so scientific behaviour can be tested without a live network. The
adapter accepts the shared, already validated site table and never reads the model
dataset or writes integrated workflow outputs.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from shapely.geometry import shape
from shapely.ops import unary_union
from urllib3.util.retry import Retry

from pedflow.context.contracts import FeatureResult, SourceConfig, SourceDefinition
from pedflow.exceptions import ConfigurationError, ContractError, SourceExecutionError
from pedflow.paths import resolve_project_path

SOURCE_NAME = "microsoft_building_footprints"
CATALOGUE_URL = "https://github.com/microsoft/GlobalMLBuildingFootprints"
DEFAULT_SOURCE_RELEASE = "2026-07-24"
DEFAULT_INDEX_URL_TEMPLATE = (
    "https://bfppub.blob.core.windows.net/%24web/{release}/dataset-links.csv"
)
DEFAULT_CACHE_DIRECTORY = "data/external_raw/microsoft_building_footprints/{release}"
DEFAULT_COUNTRY = "Australia"
DEFAULT_BUFFER_RADIUS_M = 500.0
DEFAULT_QUADKEY_ZOOM = 9
DEFAULT_CONNECT_TIMEOUT_S = 30.0
DEFAULT_READ_TIMEOUT_S = 300.0
DEFAULT_MAX_RETRIES = 3
BUFFER_RESOLUTION = 32

INDEX_COLUMNS = ("Location", "QuadKey", "Url", "Size", "UploadDate")
FEATURE_COLUMNS = (
    "site_id",
    "ms_building_data_status",
    "ms_building_count_500m",
    "ms_building_count_per_sqkm_500m",
    "ms_building_footprint_area_m2_500m",
    "ms_building_coverage_ratio_500m",
)
VALID_STATUSES = {
    "complete_with_buildings",
    "complete_no_detected_buildings",
    "source_tile_not_listed",
}


@dataclass(frozen=True)
class SourceSettings:
    """Validated run settings derived from one source configuration."""

    release: str
    country: str
    index_url: str
    cache_directory: Path
    buffer_radius_m: float
    quadkey_zoom: int
    connect_timeout_s: float
    read_timeout_s: float
    max_retries: int
    allow_download: bool

    @property
    def index_path(self) -> Path:
        return self.cache_directory / "dataset-links.csv"

    @property
    def tile_directory(self) -> Path:
        return self.cache_directory / "australia_tiles"


@dataclass(frozen=True)
class SiteContext:
    """Projected buffer and required source partitions for one site."""

    site_id: str
    metric_crs: Any
    buffer_metric: Any
    buffer_wgs84: Any
    quadkeys: frozenset[str]


@dataclass(frozen=True)
class ParsedTile:
    """One parsed source partition plus source-specific QA counts."""

    footprints: gpd.GeoDataFrame
    repaired_geometry_count: int = 0
    dropped_geometry_count: int = 0


@dataclass(frozen=True)
class AcquiredSource:
    """Validated release index and local paths for required source partitions."""

    index: pd.DataFrame
    selected_tiles: pd.DataFrame
    tile_paths: Mapping[str, Path]
    missing_quadkeys: frozenset[str]
    index_sha256: str
    tile_set_sha256: str
    cache_hits: int
    downloads: int


@dataclass(frozen=True)
class FeatureBuild:
    """Deterministic feature result plus calculation QA information."""

    features: pd.DataFrame
    duplicate_geometry_count: int = 0


def _text_option(options: Mapping[str, Any], name: str, default: str) -> str:
    value = options.get(name, default)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{SOURCE_NAME}.{name} must be non-empty text.")
    return value.strip()


def _positive_float_option(
    options: Mapping[str, Any], name: str, default: float
) -> float:
    value = options.get(name, default)
    if isinstance(value, bool):
        raise ConfigurationError(f"{SOURCE_NAME}.{name} must be a positive number.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(
            f"{SOURCE_NAME}.{name} must be a positive number."
        ) from exc
    if not math.isfinite(number) or number <= 0:
        raise ConfigurationError(f"{SOURCE_NAME}.{name} must be a positive number.")
    return number


def _nonnegative_int_option(
    options: Mapping[str, Any], name: str, default: int
) -> int:
    value = options.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ConfigurationError(f"{SOURCE_NAME}.{name} must be a non-negative integer.")
    return value


def settings_from_config(config: SourceConfig, project_root: Path) -> SourceSettings:
    """Validate source options and resolve cache paths without performing I/O."""

    options = config.options
    release = _text_option(options, "source_release", DEFAULT_SOURCE_RELEASE)
    country = _text_option(options, "country", DEFAULT_COUNTRY)
    index_url = _text_option(
        options,
        "index_url",
        DEFAULT_INDEX_URL_TEMPLATE.format(release=release),
    )
    cache_setting = _text_option(
        options,
        "cache_directory",
        DEFAULT_CACHE_DIRECTORY.format(release=release),
    )
    quadkey_zoom = _nonnegative_int_option(
        options, "quadkey_zoom", DEFAULT_QUADKEY_ZOOM
    )
    if quadkey_zoom == 0:
        raise ConfigurationError(f"{SOURCE_NAME}.quadkey_zoom must be at least 1.")

    allow_download = options.get("allow_download", True)
    if not isinstance(allow_download, bool):
        raise ConfigurationError(f"{SOURCE_NAME}.allow_download must be true or false.")

    return SourceSettings(
        release=release,
        country=country,
        index_url=index_url,
        cache_directory=resolve_project_path(project_root, cache_setting),
        buffer_radius_m=_positive_float_option(
            options, "buffer_radius_m", DEFAULT_BUFFER_RADIUS_M
        ),
        quadkey_zoom=quadkey_zoom,
        connect_timeout_s=_positive_float_option(
            options, "connect_timeout_seconds", DEFAULT_CONNECT_TIMEOUT_S
        ),
        read_timeout_s=_positive_float_option(
            options, "read_timeout_seconds", DEFAULT_READ_TIMEOUT_S
        ),
        max_retries=_nonnegative_int_option(
            options, "max_retries", DEFAULT_MAX_RETRIES
        ),
        allow_download=allow_download,
    )


def tile_xy(latitude: float, longitude: float, zoom: int) -> tuple[int, int]:
    """Convert WGS84 coordinates to a Bing tile position."""

    latitude = min(max(latitude, -85.05112878), 85.05112878)
    scale = 1 << zoom
    x_fraction = (longitude + 180.0) / 360.0
    sin_latitude = math.sin(math.radians(latitude))
    y_fraction = 0.5 - math.log(
        (1 + sin_latitude) / (1 - sin_latitude)
    ) / (4 * math.pi)
    return (
        min(max(int(x_fraction * scale), 0), scale - 1),
        min(max(int(y_fraction * scale), 0), scale - 1),
    )


def quadkey(tile_x: int, tile_y: int, zoom: int) -> str:
    """Return the Bing quadkey for a tile position."""

    digits: list[str] = []
    for level in range(zoom, 0, -1):
        mask = 1 << (level - 1)
        digit = (1 if tile_x & mask else 0) + (2 if tile_y & mask else 0)
        digits.append(str(digit))
    return "".join(digits)


def quadkeys_for_bounds(
    bounds: tuple[float, float, float, float], zoom: int
) -> frozenset[str]:
    """Return all Bing quadkeys touched by a WGS84 bounding box."""

    west, south, east, north = bounds
    x_min, y_min = tile_xy(north, west, zoom)
    x_max, y_max = tile_xy(south, east, zoom)
    return frozenset(
        quadkey(x, y, zoom)
        for x in range(min(x_min, x_max), max(x_min, x_max) + 1)
        for y in range(min(y_min, y_max), max(y_min, y_max) + 1)
    )


def build_site_contexts(
    sites: pd.DataFrame,
    buffer_radius_m: float,
    quadkey_zoom: int,
) -> dict[str, SiteContext]:
    """Build local projected buffers and partition requirements deterministically."""

    contexts: dict[str, SiteContext] = {}
    for row in sites.itertuples(index=False):
        point = gpd.GeoDataFrame(
            {"site_id": [row.site_id]},
            geometry=gpd.points_from_xy([row.longitude], [row.latitude]),
            crs="EPSG:4326",
        )
        metric_crs = point.estimate_utm_crs()
        if metric_crs is None:
            raise ContractError(f"Could not select a projected CRS for site_id '{row.site_id}'.")
        buffer_metric = point.to_crs(metric_crs).geometry.iloc[0].buffer(
            buffer_radius_m,
            quad_segs=BUFFER_RESOLUTION,
        )
        buffer_wgs84 = gpd.GeoSeries([buffer_metric], crs=metric_crs).to_crs(4326).iloc[0]
        contexts[str(row.site_id)] = SiteContext(
            site_id=str(row.site_id),
            metric_crs=metric_crs,
            buffer_metric=buffer_metric,
            buffer_wgs84=buffer_wgs84,
            quadkeys=quadkeys_for_bounds(buffer_wgs84.bounds, quadkey_zoom),
        )
    return contexts


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_nonempty(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise SourceExecutionError(f"Source file is missing or empty: {path}")


def _validate_gzip(path: Path) -> None:
    _validate_nonempty(path)
    try:
        with gzip.open(path, "rb") as source:
            source.read(1)
    except (OSError, EOFError) as exc:
        raise SourceExecutionError(f"Cached source tile is not valid gzip: {path}") from exc


def _build_http_session(max_retries: int) -> requests.Session:
    retry = Retry(
        total=max_retries,
        connect=max_retries,
        read=max_retries,
        status=max_retries,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


def download_file(
    url: str,
    destination: Path,
    *,
    session: Any,
    timeout: tuple[float, float],
    validator: Callable[[Path], None] = _validate_nonempty,
) -> bool:
    """Download one file atomically; return True only when network I/O occurred."""

    if destination.is_file():
        validator(destination)
        return False

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.part")
    temporary.unlink(missing_ok=True)
    try:
        with session.get(url, stream=True, timeout=timeout) as response:
            response.raise_for_status()
            with temporary.open("wb") as output:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        output.write(chunk)
        validator(temporary)
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return True


def load_release_index(path: Path, country: str) -> pd.DataFrame:
    """Read and validate the pinned release index for one country."""

    try:
        index = pd.read_csv(path, dtype={"QuadKey": "string"})
    except Exception as exc:
        raise SourceExecutionError(f"Could not read Microsoft release index: {path}") from exc

    missing_columns = set(INDEX_COLUMNS).difference(index.columns)
    if missing_columns:
        raise SourceExecutionError(
            f"Microsoft release index is missing fields: {sorted(missing_columns)}"
        )
    index = index.loc[index["Location"].eq(country), list(INDEX_COLUMNS)].copy()
    index["QuadKey"] = index["QuadKey"].astype("string").str.strip()
    if index.empty:
        raise SourceExecutionError(
            f"Microsoft release index contains no rows for Location='{country}'."
        )
    if index["QuadKey"].isna().any() or index["QuadKey"].eq("").any():
        raise SourceExecutionError("Microsoft release index contains blank QuadKey values.")
    if index["QuadKey"].duplicated().any():
        duplicates = sorted(
            index.loc[index["QuadKey"].duplicated(keep=False), "QuadKey"].unique()
        )
        raise SourceExecutionError(
            f"Microsoft release index contains duplicate QuadKey values: {duplicates[:20]}"
        )
    if index["Url"].isna().any() or index["Url"].astype(str).str.strip().eq("").any():
        raise SourceExecutionError("Microsoft release index contains blank tile URLs.")
    return index.reset_index(drop=True)


def select_required_tiles(
    index: pd.DataFrame,
    contexts: Mapping[str, SiteContext],
) -> tuple[pd.DataFrame, frozenset[str]]:
    """Select index rows required by supplied sites and report missing partitions."""

    required = frozenset(
        key for context in contexts.values() for key in context.quadkeys
    )
    selected = index.loc[
        index["QuadKey"].isin(required), list(INDEX_COLUMNS)
    ].sort_values("QuadKey")
    available = frozenset(selected["QuadKey"].astype(str))
    return selected.reset_index(drop=True), required.difference(available)


def acquire_or_load_source(
    contexts: Mapping[str, SiteContext],
    settings: SourceSettings,
    *,
    session: Any | None = None,
) -> AcquiredSource:
    """Load a validated cache or retrieve only required release partitions."""

    settings.cache_directory.mkdir(parents=True, exist_ok=True)
    settings.tile_directory.mkdir(parents=True, exist_ok=True)
    owned_session = session is None
    http = session or _build_http_session(settings.max_retries)
    timeout = (settings.connect_timeout_s, settings.read_timeout_s)
    cache_hits = 0
    downloads = 0

    try:
        if not settings.index_path.is_file() and not settings.allow_download:
            raise SourceExecutionError(
                f"Microsoft release index is not cached and downloads are disabled: "
                f"{settings.index_path}"
            )
        downloaded = download_file(
            settings.index_url,
            settings.index_path,
            session=http,
            timeout=timeout,
        )
        downloads += int(downloaded)
        cache_hits += int(not downloaded)

        index = load_release_index(settings.index_path, settings.country)
        selected, missing_quadkeys = select_required_tiles(index, contexts)
        tile_paths: dict[str, Path] = {}
        tile_hashes: list[str] = []

        for tile in selected.itertuples(index=False):
            path = settings.tile_directory / f"{tile.QuadKey}.csv.gz"
            if not path.is_file() and not settings.allow_download:
                raise SourceExecutionError(
                    f"Required Microsoft tile is not cached and downloads are disabled: {path}"
                )
            downloaded = download_file(
                str(tile.Url),
                path,
                session=http,
                timeout=timeout,
                validator=_validate_gzip,
            )
            downloads += int(downloaded)
            cache_hits += int(not downloaded)
            tile_paths[str(tile.QuadKey)] = path
            tile_hashes.append(f"{tile.QuadKey}:{_sha256(path)}")
    except SourceExecutionError:
        raise
    except Exception as exc:
        raise SourceExecutionError(f"Microsoft source acquisition failed: {exc}") from exc
    finally:
        if owned_session:
            http.close()

    tile_set_sha256 = hashlib.sha256("\n".join(tile_hashes).encode("utf-8")).hexdigest()
    return AcquiredSource(
        index=index,
        selected_tiles=selected,
        tile_paths=tile_paths,
        missing_quadkeys=missing_quadkeys,
        index_sha256=_sha256(settings.index_path),
        tile_set_sha256=tile_set_sha256,
        cache_hits=cache_hits,
        downloads=downloads,
    )


def read_building_geometries(path: Path) -> ParsedTile:
    """Parse geometry only from one GeoJSONL gzip partition."""

    geometries: list[Any] = []
    dropped = 0
    try:
        with gzip.open(path, "rt", encoding="utf-8") as source:
            for line_number, line in enumerate(source, start=1):
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                    geometry_payload = payload.get("geometry")
                    geometry = shape(geometry_payload) if geometry_payload else None
                except (TypeError, ValueError, json.JSONDecodeError) as exc:
                    raise SourceExecutionError(
                        f"Invalid GeoJSON geometry in {path.name} at line {line_number}."
                    ) from exc
                if geometry is None or geometry.is_empty:
                    dropped += 1
                    continue
                geometries.append(geometry)
    except SourceExecutionError:
        raise
    except (OSError, EOFError, UnicodeError) as exc:
        raise SourceExecutionError(f"Could not parse Microsoft tile: {path}") from exc

    footprints = gpd.GeoDataFrame(geometry=geometries, crs="EPSG:4326")
    repaired = 0
    if not footprints.empty:
        invalid = ~footprints.geometry.is_valid
        repaired = int(invalid.sum())
        if repaired:
            footprints.loc[invalid, "geometry"] = footprints.loc[
                invalid, "geometry"
            ].make_valid()
        unusable = footprints.geometry.isna() | footprints.geometry.is_empty
        dropped += int(unusable.sum())
        footprints = footprints.loc[~unusable].copy()
    return ParsedTile(
        footprints=footprints.reset_index(drop=True),
        repaired_geometry_count=repaired,
        dropped_geometry_count=dropped,
    )


def prepare_source(acquired: AcquiredSource) -> tuple[dict[str, gpd.GeoDataFrame], int, int]:
    """Parse acquired tile files and return geometry frames with QA totals."""

    tiles: dict[str, gpd.GeoDataFrame] = {}
    repaired = 0
    dropped = 0
    for key, path in acquired.tile_paths.items():
        parsed = read_building_geometries(path)
        tiles[key] = parsed.footprints
        repaired += parsed.repaired_geometry_count
        dropped += parsed.dropped_geometry_count
    return tiles, repaired, dropped


def build_features(
    sites: pd.DataFrame,
    contexts: Mapping[str, SiteContext],
    tile_footprints: Mapping[str, gpd.GeoDataFrame],
) -> FeatureBuild:
    """Calculate deterministic building features for every supplied site."""

    rows: list[dict[str, Any]] = []
    duplicate_geometry_count = 0
    available_keys = frozenset(tile_footprints)

    for site_id in sites["site_id"].astype(str):
        context = contexts[site_id]
        if context.quadkeys.difference(available_keys):
            rows.append(
                {
                    "site_id": site_id,
                    "ms_building_data_status": "source_tile_not_listed",
                    "ms_building_count_500m": pd.NA,
                    "ms_building_count_per_sqkm_500m": pd.NA,
                    "ms_building_footprint_area_m2_500m": pd.NA,
                    "ms_building_coverage_ratio_500m": pd.NA,
                }
            )
            continue

        frames = [tile_footprints[key] for key in sorted(context.quadkeys)]
        geometries = [
            geometry
            for frame in frames
            for geometry in frame.geometry
            if geometry is not None and not geometry.is_empty
        ]
        buildings = gpd.GeoDataFrame(geometry=geometries, crs="EPSG:4326")
        if not buildings.empty:
            geometry_keys = buildings.geometry.map(lambda geometry: geometry.wkb_hex)
            duplicate_mask = geometry_keys.duplicated(keep="first")
            duplicate_geometry_count += int(duplicate_mask.sum())
            buildings = buildings.loc[~duplicate_mask].copy()

        candidates = buildings.loc[
            buildings.geometry.intersects(context.buffer_wgs84)
        ].to_crs(context.metric_crs)
        intersections = candidates.geometry.intersection(context.buffer_metric)
        intersections = intersections.loc[
            ~intersections.is_empty & intersections.area.gt(0)
        ]

        building_count = len(intersections)
        footprint_area_m2 = (
            float(unary_union(intersections.tolist()).area) if building_count else 0.0
        )
        buffer_area_m2 = float(context.buffer_metric.area)
        rows.append(
            {
                "site_id": site_id,
                "ms_building_data_status": (
                    "complete_with_buildings"
                    if building_count
                    else "complete_no_detected_buildings"
                ),
                "ms_building_count_500m": building_count,
                "ms_building_count_per_sqkm_500m": building_count
                / (buffer_area_m2 / 1_000_000),
                "ms_building_footprint_area_m2_500m": footprint_area_m2,
                "ms_building_coverage_ratio_500m": footprint_area_m2
                / buffer_area_m2,
            }
        )

    features = pd.DataFrame(rows, columns=FEATURE_COLUMNS)
    features["ms_building_count_500m"] = features[
        "ms_building_count_500m"
    ].astype("Int64")
    for column, decimals in {
        "ms_building_count_per_sqkm_500m": 3,
        "ms_building_footprint_area_m2_500m": 3,
        "ms_building_coverage_ratio_500m": 6,
    }.items():
        features[column] = pd.to_numeric(features[column], errors="coerce").round(decimals)
    return FeatureBuild(
        features=features,
        duplicate_geometry_count=duplicate_geometry_count,
    )


def validate_source_specific(
    features: pd.DataFrame,
    sites: pd.DataFrame,
    buffer_radius_m: float,
) -> None:
    """Apply Microsoft-specific scientific checks beyond the shared contract."""

    if tuple(features.columns) != FEATURE_COLUMNS:
        raise ContractError(
            f"Microsoft feature columns differ from the approved contract: "
            f"{list(features.columns)}"
        )
    expected_ids = sites["site_id"].astype(str).tolist()
    if features["site_id"].astype(str).tolist() != expected_ids:
        raise ContractError("Microsoft features must preserve supplied site_id order and coverage.")

    invalid_statuses = sorted(
        set(features["ms_building_data_status"].dropna()).difference(VALID_STATUSES)
    )
    if invalid_statuses:
        raise ContractError(f"Unexpected Microsoft data statuses: {invalid_statuses}")

    metric_columns = list(FEATURE_COLUMNS[2:])
    unavailable = features["ms_building_data_status"].eq("source_tile_not_listed")
    if features.loc[unavailable, metric_columns].notna().any().any():
        raise ContractError("Unavailable Microsoft source partitions must not produce zero values.")
    complete = ~unavailable
    if features.loc[complete, metric_columns].isna().any().any():
        raise ContractError("Completed Microsoft rows must contain every approved metric.")
    if (features.loc[complete, "ms_building_count_500m"] < 0).any():
        raise ContractError("Microsoft building counts cannot be negative.")
    if (
        features.loc[complete, "ms_building_footprint_area_m2_500m"] < 0
    ).any():
        raise ContractError("Microsoft footprint areas cannot be negative.")
    coverage = features.loc[complete, "ms_building_coverage_ratio_500m"]
    if (~coverage.between(0, 1)).any():
        raise ContractError("Microsoft building coverage ratios must lie between zero and one.")

    # Shapely approximates a circle with 4 * resolution straight segments. Use
    # that exact regular-polygon area rather than pi*r^2 when checking the
    # notebook's resolution-32 calculations.
    expected_buffer_area = (
        2
        * BUFFER_RESOLUTION
        * buffer_radius_m**2
        * math.sin(math.pi / (2 * BUFFER_RESOLUTION))
    )
    expected_density = (
        features.loc[complete, "ms_building_count_500m"].astype(float)
        / (expected_buffer_area / 1_000_000)
    )
    density_error = (
        features.loc[complete, "ms_building_count_per_sqkm_500m"] - expected_density
    ).abs()
    if (density_error > 0.0015).any():
        raise ContractError("Microsoft count densities are inconsistent with the buffer area.")

    expected_coverage = (
        features.loc[complete, "ms_building_footprint_area_m2_500m"]
        / expected_buffer_area
    )
    coverage_error = (coverage - expected_coverage).abs()
    if (coverage_error > 0.0000015).any():
        raise ContractError("Microsoft coverage ratios are inconsistent with footprint area.")


def _safe_cache_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.name


def extract(sites: pd.DataFrame, config: SourceConfig, project_root: Path) -> FeatureResult:
    """Return one validated Microsoft feature row per supplied site."""

    settings = settings_from_config(config, project_root)
    contexts = build_site_contexts(
        sites,
        buffer_radius_m=settings.buffer_radius_m,
        quadkey_zoom=settings.quadkey_zoom,
    )
    acquired = acquire_or_load_source(contexts, settings)
    tile_footprints, repaired_count, dropped_count = prepare_source(acquired)
    built = build_features(sites, contexts, tile_footprints)
    validate_source_specific(built.features, sites, settings.buffer_radius_m)

    warnings: list[str] = []
    if acquired.missing_quadkeys:
        warnings.append(
            f"{len(acquired.missing_quadkeys)} required quadkey(s) were not listed in "
            f"Microsoft release {settings.release}."
        )
    if repaired_count:
        warnings.append(f"Repaired {repaired_count} invalid source geometries.")
    if dropped_count:
        warnings.append(f"Dropped {dropped_count} empty or unusable source geometries.")
    if built.duplicate_geometry_count:
        warnings.append(
            f"Removed {built.duplicate_geometry_count} exact duplicate geometries before counting."
        )

    metadata = {
        "catalogue_url": CATALOGUE_URL,
        "release": settings.release,
        "country": settings.country,
        "retrieval_method": "Microsoft release CSV index and HTTPS partition downloads",
        "buffer_radius_m": settings.buffer_radius_m,
        "buffer_definition": "straight-line point buffer in a site-local UTM CRS",
        "buffer_resolution": BUFFER_RESOLUTION,
        "quadkey_zoom": settings.quadkey_zoom,
        "cache_directory": _safe_cache_path(settings.cache_directory, project_root),
        "index_sha256": acquired.index_sha256,
        "tile_set_sha256": acquired.tile_set_sha256,
        "selected_tile_count": len(acquired.selected_tiles),
        "source_geometry_count": sum(len(frame) for frame in tile_footprints.values()),
        "missing_quadkey_count": len(acquired.missing_quadkeys),
        "cache_hit_count": acquired.cache_hits,
        "download_count": acquired.downloads,
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
    description="Building count, density, footprint area, and coverage within 500 m.",
    column_prefixes=("ms_",),
    extractor=extract,
)
