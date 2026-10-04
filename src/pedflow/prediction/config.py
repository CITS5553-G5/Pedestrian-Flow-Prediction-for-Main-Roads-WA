"""Bind existing feature configurations to the selected model release."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

from pedflow.context.config import load_context_config
from pedflow.exceptions import ConfigurationError
from pedflow.imagery.contracts import load_imagery_config
from pedflow.io import fingerprint
from pedflow.modeling import load_model
from pedflow.paths import resolve_project_path


def load_settings(root: Path, path: str | Path, *, workers: int | None = None):
    """Fail before extraction if a feature recipe or model changed without review."""
    try:
        settings = json.loads(resolve_project_path(root, path).read_text("utf-8"))
        # Catch misspelled/extra settings rather than silently running another recipe.
        required = {
            "workflow_version",
            "context_config",
            "context_feature_set_version",
            "imagery_config",
            "imagery_recipe_sha256",
            "model_release",
            "model_version",
            "model_release_sha256",
        }
        if (
            not isinstance(settings, dict)
            or not required.issubset(settings)
            or set(settings) - required - {"ausrap_source"}
            or any(not isinstance(value, str) or not value.strip() for value in settings.values())
        ):
            raise ConfigurationError(
                "Prediction configuration requires exactly the documented text fields."
            )
        if settings["workflow_version"] not in {"prediction_v1", "prediction_v2"}:
            raise ConfigurationError("Unsupported prediction workflow version.")
        context = load_context_config(resolve_project_path(root, settings["context_config"]))
        imagery = load_imagery_config(resolve_project_path(root, settings["imagery_config"]))
        if context.feature_set_version != settings["context_feature_set_version"] or [
            source.name for source in context.enabled_sources()
        ] != ["abs_meshblock_sa1"]:
            raise ConfigurationError("Prediction requires the selected ABS-only Context recipe.")
        if fingerprint(imagery.extraction_identity()) != settings["imagery_recipe_sha256"]:
            raise ConfigurationError("Imagery recipe changed. Review the prediction configuration.")
        release = resolve_project_path(root, settings["model_release"])
        if hashlib.sha256(release.read_bytes()).hexdigest() != settings["model_release_sha256"]:
            raise ConfigurationError("Model release changed. Review the prediction configuration.")
        model = load_model(release)
        if model.model_version != settings["model_version"]:
            raise ConfigurationError("Prediction model version does not match the configuration.")
        if workers is not None:
            imagery = replace(imagery, max_workers=workers)
        return settings, context, imagery, model
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ConfigurationError(f"Cannot load prediction configuration: {exc}") from exc
