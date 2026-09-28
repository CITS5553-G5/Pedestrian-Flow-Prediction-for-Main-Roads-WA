"""Shared input and feature-table validation for context sources."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from pedflow.exceptions import ContractError
from pedflow.validation import (
    REQUIRED_SITE_COLUMNS,
    merge_source_features,
    validate_and_normalise_sites,
    validate_feature_table,
)

__all__ = [
    "REQUIRED_SITE_COLUMNS",
    "merge_source_features",
    "validate_and_normalise_sites",
    "validate_source_features",
]

FORBIDDEN_FEATURE_FRAGMENTS = (
    "obs_peak_",
    "ped_peak_",
    "max_ped_peak_",
)


def validate_source_features(
    source_name: str,
    features: pd.DataFrame,
    expected_site_ids: pd.Series,
    column_prefixes: Sequence[str],
) -> pd.DataFrame:
    """Validate the common output contract for one source."""

    checked = validate_feature_table(features, expected_site_ids, source_name=source_name)

    forbidden = [
        column
        for column in checked.columns
        if column != "site_id"
        and any(fragment in column.lower() for fragment in FORBIDDEN_FEATURE_FRAGMENTS)
    ]
    if forbidden:
        raise ContractError(f"Source '{source_name}' returned target-derived columns: {forbidden}")

    unprefixed = [
        column
        for column in checked.columns
        if column != "site_id" and not any(column.startswith(prefix) for prefix in column_prefixes)
    ]
    if unprefixed:
        raise ContractError(
            f"Source '{source_name}' returned columns outside its approved prefixes "
            f"{tuple(column_prefixes)}: {unprefixed}"
        )

    return checked
