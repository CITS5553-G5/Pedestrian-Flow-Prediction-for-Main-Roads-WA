"""Stable contracts shared by all context-feature sources."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SourceConfig:
    """Configuration supplied to one source extractor."""

    name: str
    enabled: bool
    options: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContextPipelineConfig:
    """Configuration for one integrated Stage 2 context-feature run."""

    feature_set_version: str
    input_path: str
    input_sheet: str
    output_directory: str
    output_stem: str
    output_formats: tuple[str, ...]
    sources: tuple[SourceConfig, ...]

    def enabled_sources(self) -> tuple[SourceConfig, ...]:
        """Return configured sources in their declared execution order."""

        return tuple(source for source in self.sources if source.enabled)


@dataclass
class FeatureResult:
    """Validated output returned by one source extractor."""

    source_name: str
    source_version: str
    features: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()


@dataclass
class ContextBuildResult:
    """Combined context table plus source-level provenance."""

    feature_set_version: str
    features: Any
    source_results: tuple[FeatureResult, ...]


Extractor = Callable[[Any, SourceConfig, Path], FeatureResult]


@dataclass(frozen=True)
class SourceDefinition:
    """Name, output prefixes and callable for one context source."""

    name: str
    description: str
    column_prefixes: Sequence[str]
    extractor: Extractor
