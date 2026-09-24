"""JSON configuration loading for the integrated context-feature workflow."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path
from typing import Any

from pedflow.context.contracts import ContextPipelineConfig, SourceConfig
from pedflow.exceptions import ConfigurationError


def _required_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    """Require a settings object before reading nested fields."""
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ConfigurationError(f"Configuration field '{key}' must be an object.")
    return value


def _required_text(payload: dict[str, Any], key: str) -> str:
    """Reject blank identifiers and paths at configuration load time."""
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"Configuration field '{key}' must be non-empty text.")
    return value.strip()


def load_context_config(path: Path) -> ContextPipelineConfig:
    """Load and validate a Stage 2 JSON configuration file."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigurationError(f"Configuration file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"Configuration file is not valid JSON: {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ConfigurationError("The configuration root must be a JSON object.")

    input_config = _required_mapping(payload, "input")
    output_config = _required_mapping(payload, "output")
    source_payload = _required_mapping(payload, "sources")

    formats = output_config.get("formats", ["xlsx"])
    if not isinstance(formats, list) or not formats:
        raise ConfigurationError("output.formats must be a non-empty list.")

    normalised_formats = tuple(str(value).lower() for value in formats)
    unsupported = set(normalised_formats).difference({"xlsx", "parquet"})
    if unsupported:
        raise ConfigurationError(f"Unsupported output formats: {sorted(unsupported)}")

    sources: list[SourceConfig] = []
    for name, raw_settings in source_payload.items():
        if not isinstance(raw_settings, dict):
            raise ConfigurationError(f"Source '{name}' settings must be an object.")

        enabled = raw_settings.get("enabled", False)
        if not isinstance(enabled, bool):
            raise ConfigurationError(f"Source '{name}'.enabled must be true or false.")

        options = raw_settings.get("options", {})
        if not isinstance(options, dict):
            raise ConfigurationError(f"Source '{name}'.options must be an object.")

        sources.append(SourceConfig(name=name, enabled=enabled, options=options))

    return ContextPipelineConfig(
        feature_set_version=_required_text(payload, "feature_set_version"),
        input_path=_required_text(input_config, "path"),
        input_sheet=_required_text(input_config, "sheet"),
        output_directory=_required_text(output_config, "directory"),
        output_stem=_required_text(output_config, "stem"),
        output_formats=normalised_formats,
        sources=tuple(sources),
    )


def select_sources(
    config: ContextPipelineConfig,
    selected_names: Iterable[str],
) -> ContextPipelineConfig:
    """Return a copy with only explicitly selected registered sources enabled."""

    selected = {name.strip() for name in selected_names if name.strip()}
    known = {source.name for source in config.sources}
    unknown = selected.difference(known)
    if unknown:
        raise ConfigurationError(f"Unknown configured sources: {sorted(unknown)}")

    sources = tuple(replace(source, enabled=source.name in selected) for source in config.sources)
    return replace(config, sources=sources)
