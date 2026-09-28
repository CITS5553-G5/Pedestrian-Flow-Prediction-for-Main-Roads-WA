"""Input, output, and manifest handling for integrated context features."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from pedflow.context.contracts import ContextBuildResult, ContextPipelineConfig
from pedflow.io import atomic_path, read_sites, write_json_atomic
from pedflow.paths import resolve_project_path


def read_batch_input(
    project_root: Path,
    config: ContextPipelineConfig,
) -> pd.DataFrame:
    """Read a batch table and add its documented WGS84 CRS when omitted."""

    return read_sites(
        resolve_project_path(project_root, config.input_path), sheet=config.input_sheet
    )


def _site_id_hash(frame: pd.DataFrame) -> str:
    """Record the exact output population and order in the Context manifest."""
    serialised = "\n".join(frame["site_id"].astype(str)).encode("utf-8")
    return hashlib.sha256(serialised).hexdigest()


def build_manifest(result: ContextBuildResult) -> dict:
    """Build a serialisable run manifest from validated results."""

    return {
        "feature_set_version": result.feature_set_version,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "row_count": len(result.features),
        "site_id_sha256": _site_id_hash(result.features),
        "columns": list(result.features.columns),
        "sources": [
            {
                "name": source.source_name,
                "version": source.source_version,
                "metadata": source.metadata,
                "warnings": list(source.warnings),
                "columns": list(source.features.columns),
            }
            for source in result.source_results
        ],
    }


def write_context_outputs(
    project_root: Path,
    config: ContextPipelineConfig,
    result: ContextBuildResult,
) -> dict[str, Path]:
    """Write requested table formats and an always-present JSON manifest."""

    output_directory = resolve_project_path(project_root, config.output_directory)
    written: dict[str, Path] = {}

    if "xlsx" in config.output_formats:
        xlsx_path = output_directory / f"{config.output_stem}.xlsx"
        with atomic_path(xlsx_path) as temporary:
            result.features.to_excel(temporary, sheet_name="Context_Features", index=False)
        written["xlsx"] = xlsx_path

    if "parquet" in config.output_formats:
        parquet_path = output_directory / f"{config.output_stem}.parquet"
        with atomic_path(parquet_path) as temporary:
            result.features.to_parquet(temporary, index=False)
        written["parquet"] = parquet_path

    manifest_path = output_directory / f"{config.output_stem}.manifest.json"
    manifest = build_manifest(result)
    write_json_atomic(manifest_path, manifest)
    written["manifest"] = manifest_path
    return written
