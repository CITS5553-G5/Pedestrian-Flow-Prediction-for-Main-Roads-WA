"""Integrated, fail-fast workflow for building context features."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pandas as pd

from pedflow.context.contracts import (
    ContextBuildResult,
    ContextPipelineConfig,
    FeatureResult,
    SourceDefinition,
)
from pedflow.context.sources.registry import build_default_registry
from pedflow.context.validation import (
    merge_source_features,
    validate_and_normalise_sites,
    validate_source_features,
)
from pedflow.exceptions import (
    ConfigurationError,
    SourceExecutionError,
)


def build_context_features(
    sites: pd.DataFrame,
    config: ContextPipelineConfig,
    project_root: Path,
    registry: Mapping[str, SourceDefinition] | None = None,
) -> ContextBuildResult:
    """Run enabled sources, validate each table, and combine them one-to-one."""

    active_registry = build_default_registry() if registry is None else registry

    # The shared site contract is checked once before any source performs
    # network, file, or spatial work.
    normalised_sites = validate_and_normalise_sites(sites)
    enabled_sources = config.enabled_sources()

    if not enabled_sources:
        raise ConfigurationError(
            "No context sources are enabled. Enable a source in the configuration "
            "or select one explicitly for a development run."
        )

    # Validate the complete request before ABS or any explicitly supplied research
    # source performs I/O. Old multi-source configs must not partly execute.
    unavailable = [source.name for source in enabled_sources if source.name not in active_registry]
    if unavailable:
        raise ConfigurationError(
            f"Context sources are not available in this workflow: {unavailable}. "
            f"Available sources: {', '.join(active_registry) or '(none)'}. "
            "The default prediction workflow supports ABS only; research workflows "
            "must supply their source registry explicitly."
        )

    source_results: list[FeatureResult] = []
    validated_tables: list[pd.DataFrame] = []

    for source_config in enabled_sources:
        definition = active_registry[source_config.name]

        try:
            result = definition.extractor(normalised_sites.copy(), source_config, project_root)
        except SourceExecutionError:
            raise
        except Exception as exc:
            raise SourceExecutionError(f"Context source '{definition.name}' failed: {exc}") from exc

        if result.source_name != definition.name:
            raise SourceExecutionError(
                f"Source '{definition.name}' returned the mismatched name '{result.source_name}'."
            )

        checked = validate_source_features(
            source_name=definition.name,
            features=result.features,
            expected_site_ids=normalised_sites["site_id"],
            column_prefixes=definition.column_prefixes,
        )
        result.features = checked
        source_results.append(result)
        validated_tables.append(checked)

    # Merge only validated, complete source tables so a partial source cannot
    # silently change the modelling population.
    combined = merge_source_features(normalised_sites, validated_tables)
    return ContextBuildResult(
        feature_set_version=config.feature_set_version,
        features=combined,
        source_results=tuple(source_results),
    )
