"""WA active-school proximity source adapter.

The adapter owns controlled snapshot acquisition, source validation, cleaning,
nearest-school calculation, source-specific QA, and safe provenance. It accepts
already validated sites and never reads the model workbook or writes workflow outputs.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen
from uuid import uuid4

from pedflow.context.contracts import FeatureResult, SourceConfig, SourceDefinition
from pedflow.exceptions import SourceExecutionError
from pedflow.paths import resolve_project_path

SOURCE_NAME = "wa_education_schools"
DEFAULT_SOURCE_VERSION = "DET-024-2026-S1"
DEFAULT_SOURCE_PATH = (
    "data/external_raw/wa_education/2026_S1/currentactiveschools20261.xlsx"
)
DEFAULT_SOURCE_URL = (
    "https://catalogue.data.wa.gov.au/dataset/"
    "90b5a308-edd6-4814-89f7-1af4df14687b/resource/"
    "d1bec5f9-e284-4484-af4d-cc7a69a55c5a/download/"
    "currentactiveschools20261.xlsx"
)
DEFAULT_CATALOGUE_URL = (
    "https://catalogue.data.wa.gov.au/dataset/"
    "current-active-schools-semester-1-2026-public-det-024"
)
DEFAULT_LICENCE_URL = "https://creativecommons.org/licenses/by-nc/4.0/"
DEFAULT_SOURCE_SHA256 = (
    "ac4257d76e333dcbf2042c7e89b6337fd66b4a990667bc936ed2b1172dd2ffbd"
)
DEFAULT_PROJECT_BOUNDS = {
    "minimum_longitude": 112.0,
    "maximum_longitude": 129.0,
    "minimum_latitude": -36.0,
    "maximum_latitude": -13.0,
}
DEFAULT_APPROVED_SECTORS = (
    "GOVERNMENT",
    "NON-GOVERNMENT",
    "COMMUNITY KINDER",
)
DEFAULT_APPROVED_LOW_YEAR_CODES = (
    "KIN",
    "PKG",
    "PRP",
    "Y01",
    "Y03",
    "Y04",
    "Y05",
    "Y07",
    "Y08",
    "Y09",
    "Y10",
    "Y11",
)
DEFAULT_APPROVED_HIGH_YEAR_CODES = (
    "KIN",
    "Y02",
    "Y03",
    "Y04",
    "Y06",
    "Y07",
    "Y09",
    "Y10",
    "Y11",
    "Y12",
)

REQUIRED_SOURCE_COLUMNS = (
    "Code",
    "SchoolName",
    "PhysicalTown",
    "Latitude",
    "Longitude",
    "EducationRegionName",
    "Sector",
    "RemCode",
    "RemoteArea",
    "LowYear",
    "HighYear",
    "TotalPrimaryK_6",
    "TotalSecondary7_12",
    "TotalSchool",
)
FEATURE_COLUMNS = (
    "site_id",
    "education_nearest_active_school_distance_m",
    "education_nearest_school_sector",
    "education_nearest_school_low_year",
    "education_nearest_school_high_year",
    "education_nearest_school_code",
    "education_nearest_school_name",
    "education_data_status",
)


@dataclass(frozen=True)
class SourceSnapshot:
    """Integrity-checked local source snapshot."""

    path: Path
    sha256: str
    retrieval_method: str
    size_bytes: int


@dataclass(frozen=True)
class PreparedSchoolSource:
    """Validated school records and source-level QA facts."""

    schools: Any
    outside_scope_schools: Any
    source_row_count: int
    zero_total_school_count: int
    sector_counts: Mapping[str, int]
    low_year_codes: tuple[str, ...]
    high_year_codes: tuple[str, ...]
    project_bounds: Mapping[str, float]


def _text_option(config: SourceConfig, key: str, default: str) -> str:
    value = config.options.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise SourceExecutionError(f"Configuration option '{key}' must be non-empty text.")
    return value.strip()


def _positive_number_option(config: SourceConfig, key: str, default: float) -> float:
    value = config.options.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise SourceExecutionError(f"Configuration option '{key}' must be positive.")
    return float(value)


def _text_sequence_option(
    config: SourceConfig,
    key: str,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    value = config.options.get(key, default)
    if not isinstance(value, (list, tuple)) or not value:
        raise SourceExecutionError(f"Configuration option '{key}' must be a non-empty list.")
    normalised = tuple(str(item).strip() for item in value)
    if any(not item for item in normalised):
        raise SourceExecutionError(f"Configuration option '{key}' contains a blank value.")
    return normalised


def _project_bounds(config: SourceConfig) -> dict[str, float]:
    raw_bounds = config.options.get("project_bounds", DEFAULT_PROJECT_BOUNDS)
    if not isinstance(raw_bounds, Mapping):
        raise SourceExecutionError("Configuration option 'project_bounds' must be an object.")

    bounds: dict[str, float] = {}
    for key, default in DEFAULT_PROJECT_BOUNDS.items():
        value = raw_bounds.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise SourceExecutionError(f"Project bound '{key}' must be numeric.")
        bounds[key] = float(value)

    if bounds["minimum_longitude"] >= bounds["maximum_longitude"]:
        raise SourceExecutionError("Project longitude bounds are not ordered.")
    if bounds["minimum_latitude"] >= bounds["maximum_latitude"]:
        raise SourceExecutionError("Project latitude bounds are not ordered.")
    return bounds


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_url(value: str) -> str:
    """Remove credentials, query parameters, and fragments from provenance URLs."""

    parts = urlsplit(value)
    hostname = parts.hostname or ""
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    netloc = hostname
    if parts.port is not None:
        netloc = f"{netloc}:{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, "", ""))


def _expected_sha256(config: SourceConfig) -> str:
    value = _text_option(config, "source_sha256", DEFAULT_SOURCE_SHA256).lower()
    if re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise SourceExecutionError("Configuration option 'source_sha256' must be 64 hex digits.")
    return value


def acquire_or_load_source(
    config: SourceConfig,
    project_root: Path,
) -> SourceSnapshot:
    """Return an integrity-checked local snapshot, downloading it atomically if absent."""

    source_path = resolve_project_path(
        project_root,
        _text_option(config, "source_path", DEFAULT_SOURCE_PATH),
    )
    expected_hash = _expected_sha256(config)

    if source_path.is_file():
        actual_hash = _sha256_file(source_path)
        if actual_hash != expected_hash:
            raise SourceExecutionError(
                f"WA education snapshot hash mismatch for {source_path.name}."
            )
        return SourceSnapshot(
            path=source_path,
            sha256=actual_hash,
            retrieval_method="local_snapshot",
            size_bytes=source_path.stat().st_size,
        )

    source_url = _text_option(config, "source_url", DEFAULT_SOURCE_URL)
    timeout_seconds = _positive_number_option(config, "download_timeout_seconds", 120)
    minimum_bytes = int(_positive_number_option(config, "minimum_source_bytes", 10_000))
    source_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = source_path.with_name(f".{source_path.name}.{uuid4().hex}.tmp")
    digest = hashlib.sha256()
    downloaded_bytes = 0

    try:
        request = Request(source_url, headers={"User-Agent": "CITS5553-pedflow/1.0"})
        with urlopen(request, timeout=timeout_seconds) as response, temporary_path.open(
            "wb"
        ) as destination:
            while chunk := response.read(1024 * 1024):
                destination.write(chunk)
                digest.update(chunk)
                downloaded_bytes += len(chunk)

        if downloaded_bytes < minimum_bytes:
            raise SourceExecutionError("Downloaded WA education snapshot is unexpectedly small.")
        actual_hash = digest.hexdigest()
        if actual_hash != expected_hash:
            raise SourceExecutionError(
                "Downloaded WA education snapshot failed integrity checking."
            )
        temporary_path.replace(source_path)
    except SourceExecutionError:
        raise
    except Exception as exc:
        raise SourceExecutionError(
            "Could not retrieve the approved WA education snapshot."
        ) from exc
    finally:
        temporary_path.unlink(missing_ok=True)

    return SourceSnapshot(
        path=source_path,
        sha256=expected_hash,
        retrieval_method="downloaded_snapshot",
        size_bytes=downloaded_bytes,
    )


def load_source_workbook(snapshot: SourceSnapshot, config: SourceConfig) -> Any:
    """Read the configured worksheet from an integrity-checked snapshot."""

    import pandas as pd

    sheet_name = _text_option(config, "source_sheet", "ActiveSchools")
    try:
        with pd.ExcelFile(snapshot.path) as workbook:
            if workbook.sheet_names != [sheet_name]:
                raise SourceExecutionError(
                    f"Unexpected WA education worksheets: {workbook.sheet_names}."
                )
            return pd.read_excel(
                workbook,
                sheet_name=sheet_name,
                dtype={"Code": "string"},
            )
    except SourceExecutionError:
        raise
    except Exception as exc:
        raise SourceExecutionError(
            f"Could not read worksheet '{sheet_name}' from {snapshot.path.name}."
        ) from exc


def _inside_bounds(frame: Any, bounds: Mapping[str, float]) -> Any:
    return (
        frame["longitude"].between(
            bounds["minimum_longitude"], bounds["maximum_longitude"]
        )
        & frame["latitude"].between(
            bounds["minimum_latitude"], bounds["maximum_latitude"]
        )
    )


def prepare_source(raw_source: Any, config: SourceConfig) -> PreparedSchoolSource:
    """Validate, normalise, and geographically filter active-school records."""

    import pandas as pd

    if not isinstance(raw_source, pd.DataFrame):
        raise SourceExecutionError("WA education source must be a pandas DataFrame.")
    missing_columns = set(REQUIRED_SOURCE_COLUMNS).difference(raw_source.columns)
    if missing_columns:
        raise SourceExecutionError(
            f"WA education source is missing columns: {sorted(missing_columns)}"
        )

    schools = raw_source.loc[:, list(REQUIRED_SOURCE_COLUMNS)].copy()
    rename_map = {
        "Code": "school_code",
        "SchoolName": "school_name",
        "PhysicalTown": "physical_town",
        "Latitude": "latitude",
        "Longitude": "longitude",
        "EducationRegionName": "education_region_name",
        "Sector": "sector",
        "RemCode": "remoteness_code",
        "RemoteArea": "remote_area",
        "LowYear": "low_year",
        "HighYear": "high_year",
        "TotalPrimaryK_6": "total_primary_k_6",
        "TotalSecondary7_12": "total_secondary_7_12",
        "TotalSchool": "total_school",
    }
    schools = schools.rename(columns=rename_map)

    text_columns = (
        "school_code",
        "school_name",
        "physical_town",
        "education_region_name",
        "sector",
        "remote_area",
        "low_year",
        "high_year",
    )
    for column in text_columns:
        schools[column] = schools[column].astype("string").str.strip()
    for column in (
        "latitude",
        "longitude",
        "remoteness_code",
        "total_primary_k_6",
        "total_secondary_7_12",
        "total_school",
    ):
        schools[column] = pd.to_numeric(schools[column], errors="coerce")

    if schools.empty:
        raise SourceExecutionError("WA education source contains no school records.")
    if schools.isna().any().any():
        raise SourceExecutionError("WA education source contains missing required values.")
    if schools["school_code"].eq("").any() or schools["school_code"].duplicated().any():
        raise SourceExecutionError("WA education school codes must be non-blank and unique.")

    invalid_coordinates = (
        ~schools["latitude"].between(-90, 90)
        | ~schools["longitude"].between(-180, 180)
    )
    if invalid_coordinates.any():
        raise SourceExecutionError("WA education source contains invalid WGS84 coordinates.")

    approved_sectors = set(
        _text_sequence_option(config, "approved_sectors", DEFAULT_APPROVED_SECTORS)
    )
    approved_low_years = set(
        _text_sequence_option(
            config,
            "approved_low_year_codes",
            DEFAULT_APPROVED_LOW_YEAR_CODES,
        )
    )
    approved_high_years = set(
        _text_sequence_option(
            config,
            "approved_high_year_codes",
            DEFAULT_APPROVED_HIGH_YEAR_CODES,
        )
    )
    unknown_sectors = set(schools["sector"]).difference(approved_sectors)
    unknown_low_years = set(schools["low_year"]).difference(approved_low_years)
    unknown_high_years = set(schools["high_year"]).difference(approved_high_years)
    if unknown_sectors:
        raise SourceExecutionError(f"Unexpected WA education sectors: {sorted(unknown_sectors)}")
    if unknown_low_years:
        raise SourceExecutionError(
            f"Unexpected WA education low-year codes: {sorted(unknown_low_years)}"
        )
    if unknown_high_years:
        raise SourceExecutionError(
            f"Unexpected WA education high-year codes: {sorted(unknown_high_years)}"
        )

    source_row_count = len(schools)
    zero_total_school_count = int(schools["total_school"].eq(0).sum())
    sector_counts = {
        str(key): int(value) for key, value in schools["sector"].value_counts().items()
    }
    low_year_codes = tuple(sorted(str(value) for value in schools["low_year"].unique()))
    high_year_codes = tuple(
        sorted(str(value) for value in schools["high_year"].unique())
    )

    bounds = _project_bounds(config)
    in_scope = _inside_bounds(schools, bounds)
    outside_scope = schools.loc[~in_scope].copy().reset_index(drop=True)
    schools = schools.loc[in_scope].copy().reset_index(drop=True)
    if schools.empty:
        raise SourceExecutionError(
            "No active schools remain inside the configured WA project bounds."
        )

    return PreparedSchoolSource(
        schools=schools,
        outside_scope_schools=outside_scope,
        source_row_count=source_row_count,
        zero_total_school_count=zero_total_school_count,
        sector_counts=sector_counts,
        low_year_codes=low_year_codes,
        high_year_codes=high_year_codes,
        project_bounds=bounds,
    )


def local_utm_epsg(latitude: float, longitude: float) -> int:
    """Return the WGS84 UTM EPSG code for a valid coordinate."""

    zone = int((longitude + 180.0) // 6.0) + 1
    zone = min(max(zone, 1), 60)
    return (32600 if latitude >= 0 else 32700) + zone


def build_features(
    sites: Any,
    prepared_source: PreparedSchoolSource,
    config: SourceConfig,
) -> Any:
    """Deterministically build one nearest-active-school row per supplied site."""

    import numpy as np
    import pandas as pd
    from pyproj import Transformer

    required_site_columns = ("site_id", "latitude", "longitude", "coordinate_crs")
    missing_columns = set(required_site_columns).difference(sites.columns)
    if missing_columns:
        raise SourceExecutionError(
            f"Validated sites are missing required columns: {sorted(missing_columns)}"
        )

    site_frame = sites.loc[:, list(required_site_columns)].copy()
    site_frame["site_id"] = site_frame["site_id"].astype("string").str.strip()
    site_frame["latitude"] = pd.to_numeric(site_frame["latitude"], errors="coerce")
    site_frame["longitude"] = pd.to_numeric(site_frame["longitude"], errors="coerce")
    if site_frame["site_id"].isna().any() or site_frame["site_id"].duplicated().any():
        raise SourceExecutionError(
            "Validated sites must contain unique, non-missing site_id values."
        )
    if site_frame[["latitude", "longitude"]].isna().any().any():
        raise SourceExecutionError("Validated sites contain missing coordinates.")
    if not _inside_bounds(site_frame, prepared_source.project_bounds).all():
        outside_ids = site_frame.loc[
            ~_inside_bounds(site_frame, prepared_source.project_bounds), "site_id"
        ].tolist()
        raise SourceExecutionError(
            f"Sites outside the configured WA education bounds: {outside_ids}"
        )

    schools = prepared_source.schools
    school_longitudes = schools["longitude"].to_numpy(dtype=float)
    school_latitudes = schools["latitude"].to_numpy(dtype=float)
    rows: list[dict[str, Any]] = []

    for site in site_frame.itertuples(index=False):
        epsg = local_utm_epsg(float(site.latitude), float(site.longitude))
        transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
        site_x, site_y = transformer.transform(float(site.longitude), float(site.latitude))
        school_x, school_y = transformer.transform(school_longitudes, school_latitudes)
        distances = np.hypot(school_x - site_x, school_y - site_y)
        if not np.isfinite(distances).all():
            raise SourceExecutionError(
                f"Projection returned a non-finite distance for site_id '{site.site_id}'."
            )

        minimum_distance = float(distances.min())
        tied_positions = np.flatnonzero(
            np.isclose(distances, minimum_distance, rtol=0.0, atol=1e-9)
        )
        nearest_position = min(
            tied_positions.tolist(),
            key=lambda position: str(schools.iloc[position]["school_code"]),
        )
        nearest = schools.iloc[nearest_position]
        rows.append(
            {
                "site_id": site.site_id,
                "education_nearest_active_school_distance_m": float(
                    distances[nearest_position]
                ),
                "education_nearest_school_sector": nearest["sector"],
                "education_nearest_school_low_year": nearest["low_year"],
                "education_nearest_school_high_year": nearest["high_year"],
                "education_nearest_school_code": nearest["school_code"],
                "education_nearest_school_name": nearest["school_name"],
                "education_data_status": "matched",
            }
        )

    features = pd.DataFrame(rows, columns=FEATURE_COLUMNS)
    features["site_id"] = features["site_id"].astype("string")
    features["education_nearest_school_code"] = features[
        "education_nearest_school_code"
    ].astype("string")
    return features


def validate_source_specific(
    features: Any,
    prepared_source: PreparedSchoolSource,
    config: SourceConfig,
) -> None:
    """Apply WA education checks beyond the shared source-output contract."""

    import numpy as np
    import pandas as pd

    if not isinstance(features, pd.DataFrame):
        raise SourceExecutionError("WA education features must be a pandas DataFrame.")
    if tuple(features.columns) != FEATURE_COLUMNS:
        raise SourceExecutionError("WA education feature columns or ordering changed.")
    if features["site_id"].duplicated().any():
        raise SourceExecutionError("WA education features contain duplicate site_id values.")
    if features.isna().any().any():
        raise SourceExecutionError("WA education features contain missing values.")
    if not features["education_data_status"].eq("matched").all():
        raise SourceExecutionError("A successful WA education run must mark every row matched.")

    distances = features["education_nearest_active_school_distance_m"].to_numpy(
        dtype=float
    )
    if not np.isfinite(distances).all() or (distances < 0).any():
        raise SourceExecutionError("WA education distances must be finite and non-negative.")

    schools = prepared_source.schools
    source_codes = set(schools["school_code"])
    if not set(features["education_nearest_school_code"]).issubset(source_codes):
        raise SourceExecutionError("WA education features contain an unknown school code.")
    if not set(features["education_nearest_school_sector"]).issubset(
        set(schools["sector"])
    ):
        raise SourceExecutionError("WA education features contain an unknown sector.")
    if not set(features["education_nearest_school_low_year"]).issubset(
        set(schools["low_year"])
    ):
        raise SourceExecutionError("WA education features contain an unknown low-year code.")
    if not set(features["education_nearest_school_high_year"]).issubset(
        set(schools["high_year"])
    ):
        raise SourceExecutionError("WA education features contain an unknown high-year code.")

    expected_names = schools.set_index("school_code")["school_name"]
    actual_names = features.set_index("education_nearest_school_code")[
        "education_nearest_school_name"
    ]
    if not actual_names.eq(actual_names.index.map(expected_names)).all():
        raise SourceExecutionError("WA education school codes and names are inconsistent.")


def extract(sites: Any, config: SourceConfig, project_root: Path) -> FeatureResult:
    """Build one WA education feature row per supplied site."""

    snapshot = acquire_or_load_source(config, project_root)
    raw_source = load_source_workbook(snapshot, config)
    prepared_source = prepare_source(raw_source, config)
    features = build_features(sites, prepared_source, config)
    validate_source_specific(features, prepared_source, config)

    outside_count = len(prepared_source.outside_scope_schools)
    warnings: list[str] = []
    if outside_count:
        warnings.append(
            f"Filtered {outside_count} school records outside the configured WA project bounds."
        )
    if prepared_source.zero_total_school_count:
        warnings.append(
            f"{prepared_source.zero_total_school_count} source records report TotalSchool=0; "
            "enrolment fields are not included as features."
        )

    configured_source_path = Path(
        _text_option(config, "source_path", DEFAULT_SOURCE_PATH)
    )
    safe_source_path = (
        configured_source_path.name
        if configured_source_path.is_absolute()
        else configured_source_path.as_posix()
    )
    metadata = {
        "publisher": "Western Australia Department of Education",
        "catalogue_url": _safe_url(
            _text_option(config, "catalogue_url", DEFAULT_CATALOGUE_URL)
        ),
        "source_url": _safe_url(_text_option(config, "source_url", DEFAULT_SOURCE_URL)),
        "licence_url": _safe_url(
            _text_option(config, "licence_url", DEFAULT_LICENCE_URL)
        ),
        "snapshot_label": _text_option(config, "snapshot_label", "2026 Semester 1"),
        "source_sheet": _text_option(config, "source_sheet", "ActiveSchools"),
        "source_path": safe_source_path,
        "source_file_sha256": snapshot.sha256,
        "source_file_size_bytes": snapshot.size_bytes,
        "retrieval_method": snapshot.retrieval_method,
        "source_row_count": prepared_source.source_row_count,
        "in_scope_school_count": len(prepared_source.schools),
        "outside_scope_school_count": outside_count,
        "sector_counts": dict(prepared_source.sector_counts),
        "low_year_codes": list(prepared_source.low_year_codes),
        "high_year_codes": list(prepared_source.high_year_codes),
        "project_bounds": dict(prepared_source.project_bounds),
        "distance_method": "site-local WGS84 UTM planar Euclidean distance in metres",
    }
    return FeatureResult(
        source_name=SOURCE_NAME,
        source_version=_text_option(config, "source_version", DEFAULT_SOURCE_VERSION),
        features=features,
        metadata=metadata,
        warnings=tuple(warnings),
    )


DEFINITION = SourceDefinition(
    name=SOURCE_NAME,
    description="Nearest active WA school, sector, and year-level context.",
    column_prefixes=("education_",),
    extractor=extract,
)
