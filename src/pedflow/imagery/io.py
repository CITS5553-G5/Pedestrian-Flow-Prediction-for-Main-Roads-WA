"""Thin batch-file adapters for the shared imagery workflow."""

from __future__ import annotations

from pathlib import Path

from pedflow.imagery.contracts import ImageryResult
from pedflow.io import atomic_path, read_sites, write_json_atomic

__all__ = ["read_sites", "write_imagery_outputs"]


def write_imagery_outputs(result: ImageryResult, directory: str | Path) -> dict[str, Path]:
    """Export features and provenance; partial CSV writes never replace prior results."""
    folder = Path(directory)
    target = folder / "imagery_features.csv"
    with atomic_path(target) as temporary:
        result.features.to_csv(temporary, index=False)
    manifest = folder / "imagery_features.manifest.json"
    write_json_atomic(
        manifest, {"feature_set_version": result.feature_set_version, **result.metadata}
    )
    return {"csv": target, "manifest": manifest}
