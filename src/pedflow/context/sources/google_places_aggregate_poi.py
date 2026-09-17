"""Governance guard for the excluded Google Places Aggregate experiment.

Google Support did not interpret or authorise the proposed modelling use. UWA
subsequently directed the project to exclude Google POI features from the
pedestrian-flow models and continue with the other contextual sources. The
pre-exclusion implementation and outputs are preserved only in the dated archive.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, NoReturn

from pedflow.context.contracts import SourceConfig, SourceDefinition
from pedflow.exceptions import SourceExecutionError

SOURCE_NAME = "google_places_aggregate_poi"
MODEL_USE_APPROVED = False
ARCHIVE_LOCATION = "07_Archive/20260908_google_places_aggregate_poi_experiment"
GOVERNANCE_MESSAGE = (
    "Google Places Aggregate POI features are excluded from pedestrian-flow "
    "training, validation, testing and prediction by the recorded UWA project "
    f"decision. The pre-exclusion experiment is preserved under {ARCHIVE_LOCATION}."
)


def extract(
    sites: Any,
    config: SourceConfig,
    project_root: Path,
) -> NoReturn:
    """Stop accidental use of the excluded source before any external I/O."""

    del sites, config, project_root
    raise SourceExecutionError(GOVERNANCE_MESSAGE)


DEFINITION = SourceDefinition(
    name=SOURCE_NAME,
    description=(
        "Excluded Google Places experiment retained only as a governance guard; "
        "the original implementation is available in the dated project archive."
    ),
    column_prefixes=("google_",),
    extractor=extract,
)
