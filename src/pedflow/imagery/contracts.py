"""Configuration and results for the imagery workflow."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from importlib.resources import files
from pathlib import Path

import pandas as pd

from pedflow.exceptions import ConfigurationError


def load_prompt() -> str:
    """Read the original notebook prompt verbatim, including its full schema."""
    return files("pedflow.imagery").joinpath("prompts/notebook_v1.txt").read_text("utf-8")


@dataclass(frozen=True)
class ImageryConfig:
    """Keep scientific recipe settings and execution limits in one validated value."""

    feature_set_version: str = "imagery_notebook_v1"
    model: str = "gemini-3.7-flash"
    max_workers: int = 50
    # None disables local pacing; provider cooldowns still apply after failures.
    maps_requests_per_minute: float | None = None
    llm_requests_per_minute: float | None = None
    request_timeout_seconds: float = 60
    llm_timeout_seconds: float = 120
    max_attempts: int = 4
    sampling_offset_m: float = 50

    def __post_init__(self):
        """Reject invalid limits and implicit model selection before any requests."""
        if (
            not isinstance(self.feature_set_version, str)
            or not self.feature_set_version.strip()
            or not isinstance(self.model, str)
            or not self.model.strip()
            or self.model == "auto"
        ):
            raise ConfigurationError(
                "Imagery feature version and explicit Gemini model are required."
            )
        for key, maximum in (("max_workers", 64), ("max_attempts", 8)):
            value = getattr(self, key)
            if type(value) is not int or not 1 <= value <= maximum:
                raise ConfigurationError(f"{key} must be an integer between 1 and {maximum}.")
        for key in (
            "maps_requests_per_minute",
            "llm_requests_per_minute",
            "request_timeout_seconds",
            "llm_timeout_seconds",
            "sampling_offset_m",
        ):
            value = getattr(self, key)
            if key in {"maps_requests_per_minute", "llm_requests_per_minute"} and value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ConfigurationError(f"{key} must be a positive finite number.")
            if not math.isfinite(value) or value <= 0:
                raise ConfigurationError(f"{key} must be a positive finite number.")

    def extraction_identity(self) -> dict:
        """Execution concurrency may change on resume; scientific settings may not."""
        return {
            "feature_set_version": self.feature_set_version,
            "model": self.model,
            "sampling_offset_m": self.sampling_offset_m,
            "image_profile": "google_notebook_web_mercator_v1",
            "prompt_sha256": hashlib.sha256(load_prompt().encode()).hexdigest(),
            "satellite": {"zoom": 19, "size": "640x640", "scale": 2},
            "street_view": {"size": "640x640", "heading": 0, "pitch": 0, "fov": 90},
        }


def load_imagery_config(path: str | Path) -> ImageryConfig:
    """Read the versioned recipe and reject unknown or malformed options."""
    try:
        payload = json.loads(Path(path).read_text("utf-8"))
        return ImageryConfig(**payload)
    except (OSError, ValueError, TypeError) as exc:
        raise ConfigurationError(f"Cannot load imagery configuration: {exc}") from exc


@dataclass
class ImageryResult:
    """Return feature rows together with extraction provenance and source status."""

    feature_set_version: str
    features: pd.DataFrame
    metadata: dict


def config_metadata(config: ImageryConfig) -> dict:
    """Record both execution settings and the exact image/prompt recipe."""
    return {**asdict(config), **config.extraction_identity()}


class ExtractionError(Exception):
    """Safe per-site error code; never include a URL, key or raw API response."""

    def __init__(self, code: str, *, retryable: bool = False, retry_after: float = 0):
        """Carry only a safe error code and retry hints across provider boundaries."""
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.retry_after = retry_after
