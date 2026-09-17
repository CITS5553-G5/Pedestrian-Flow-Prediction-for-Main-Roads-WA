"""Shared input and feature-table validation for context sources."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from pedflow.exceptions import ContractError

REQUIRED_SITE_COLUMNS = ("site_id", "latitude", "longitude", "coordinate_crs")
FORBIDDEN_FEATURE_FRAGMENTS = (
    "obs_peak_",
    "ped_peak_",
    "max_ped_peak_",
)


def validate_and_normalise_sites(
    sites: pd.DataFrame,
    required_columns: Sequence[str] = REQUIRED_SITE_COLUMNS,
) -> pd.DataFrame:
    """Validate the common site input contract and return a normalised copy."""

    missing = set(required_columns).difference(sites.columns)
    if missing:
        raise ContractError(f"Model sites are missing required columns: {sorted(missing)}")

    normalised = sites.loc[:, list(required_columns)].copy()
    normalised["site_id"] = normalised["site_id"].astype("string").str.strip()
    normalised["coordinate_crs"] = (
        normalised["coordinate_crs"].astype("string").str.strip().str.upper()
    )
    normalised["latitude"] = pd.to_numeric(normalised["latitude"], errors="coerce")
    normalised["longitude"] = pd.to_numeric(normalised["longitude"], errors="coerce")

    if normalised["site_id"].isna().any() or normalised["site_id"].eq("").any():
        raise ContractError("site_id contains missing or blank values.")

    if normalised["site_id"].duplicated().any():
        duplicates = normalised.loc[
            normalised["site_id"].duplicated(keep=False), "site_id"
        ].tolist()
        raise ContractError(f"site_id must be unique. Duplicates: {duplicates}")

    invalid_coordinates = (
        normalised["latitude"].isna()
        | normalised["longitude"].isna()
        | ~normalised["latitude"].between(-90, 90)
        | ~normalised["longitude"].between(-180, 180)
    )
    if invalid_coordinates.any():
        invalid_ids = normalised.loc[invalid_coordinates, "site_id"].tolist()
        raise ContractError(f"Invalid WGS84 coordinates for site_id values: {invalid_ids}")

    unsupported_crs = normalised.loc[
        normalised["coordinate_crs"].ne("EPSG:4326"), "site_id"
    ].tolist()
    if unsupported_crs:
        raise ContractError(
            "All context extractors currently require coordinate_crs='EPSG:4326'. "
            f"Affected site_id values: {unsupported_crs}"
        )

    return normalised


def validate_source_features(
    source_name: str,
    features: pd.DataFrame,
    expected_site_ids: pd.Series,
    column_prefixes: Sequence[str],
) -> pd.DataFrame:
    """Validate the common output contract for one source."""

    if not isinstance(features, pd.DataFrame):
        raise ContractError(f"Source '{source_name}' did not return a pandas DataFrame.")
    if "site_id" not in features.columns:
        raise ContractError(f"Source '{source_name}' output is missing site_id.")
    if features.columns.duplicated().any():
        duplicates = features.columns[features.columns.duplicated()].tolist()
        raise ContractError(
            f"Source '{source_name}' returned duplicate columns: {duplicates}"
        )

    checked = features.copy()
    checked["site_id"] = checked["site_id"].astype("string").str.strip()
    if checked["site_id"].isna().any() or checked["site_id"].eq("").any():
        raise ContractError(f"Source '{source_name}' returned blank site_id values.")
    if checked["site_id"].duplicated().any():
        duplicates = checked.loc[
            checked["site_id"].duplicated(keep=False), "site_id"
        ].tolist()
        raise ContractError(
            f"Source '{source_name}' must return one row per site_id. Duplicates: {duplicates}"
        )

    expected = set(expected_site_ids.astype("string"))
    actual = set(checked["site_id"])
    if actual != expected:
        missing = sorted(expected.difference(actual))
        extra = sorted(actual.difference(expected))
        raise ContractError(
            f"Source '{source_name}' site coverage differs from the input. "
            f"Missing: {missing}; extra: {extra}"
        )

    forbidden = [
        column
        for column in checked.columns
        if column != "site_id"
        and any(fragment in column.lower() for fragment in FORBIDDEN_FEATURE_FRAGMENTS)
    ]
    if forbidden:
        raise ContractError(
            f"Source '{source_name}' returned target-derived columns: {forbidden}"
        )

    unprefixed = [
        column
        for column in checked.columns
        if column != "site_id"
        and not any(column.startswith(prefix) for prefix in column_prefixes)
    ]
    if unprefixed:
        raise ContractError(
            f"Source '{source_name}' returned columns outside its approved prefixes "
            f"{tuple(column_prefixes)}: {unprefixed}"
        )

    return checked


def merge_source_features(
    sites: pd.DataFrame,
    source_tables: Sequence[pd.DataFrame],
) -> pd.DataFrame:
    """Join validated source tables one-to-one while preserving input site order."""

    combined = sites[["site_id"]].copy()
    used_columns = {"site_id"}

    for table in source_tables:
        overlap = used_columns.intersection(set(table.columns).difference({"site_id"}))
        if overlap:
            raise ContractError(
                f"Context sources produced overlapping columns: {sorted(overlap)}"
            )

        try:
            combined = combined.merge(
                table,
                on="site_id",
                how="left",
                sort=False,
                validate="one_to_one",
            )
        except Exception as exc:
            raise ContractError(f"Could not join a context feature table: {exc}") from exc

        used_columns.update(table.columns)

    if len(combined) != len(sites):
        raise ContractError("The context merge changed the input site row count.")
    if combined["site_id"].tolist() != sites["site_id"].tolist():
        raise ContractError("The context merge changed the input site order.")

    return combined
