"""Input, output, and manifest handling for integrated context features."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd

from pedflow.context.contracts import ContextBuildResult, ContextPipelineConfig
from pedflow.exceptions import ConfigurationError
from pedflow.paths import resolve_project_path


def read_batch_input(
    project_root: Path,
    config: ContextPipelineConfig,
) -> pd.DataFrame:
    """Read a batch table and add its documented WGS84 CRS when omitted."""

    path = resolve_project_path(project_root, config.input_path)
    if not path.is_file():
        raise ConfigurationError(f"Configured batch input does not exist: {path}")

    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        frame = pd.read_excel(
            path,
            sheet_name=config.input_sheet,
            dtype={"site_id": "string", "coordinate_crs": "string"},
        )
    elif suffix == ".csv":
        frame = pd.read_csv(
            path,
            dtype={"site_id": "string", "coordinate_crs": "string"},
        )
    elif suffix == ".parquet":
        frame = pd.read_parquet(path)
    else:
        raise ConfigurationError(f"Unsupported batch input format: {path.suffix}")

    if "coordinate_crs" not in frame.columns:
        frame.insert(min(3, len(frame.columns)), "coordinate_crs", "EPSG:4326")
    return frame


def _temporary_path(target: Path) -> Path:
    return target.with_name(f".{target.stem}.{uuid4().hex}.tmp{target.suffix}")


def _write_atomic(target: Path, writer) -> None:
    temporary = _temporary_path(target)
    try:
        writer(temporary)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def _site_id_hash(frame: pd.DataFrame) -> str:
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
    output_directory.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    if "xlsx" in config.output_formats:
        xlsx_path = output_directory / f"{config.output_stem}.xlsx"
        _write_atomic(
            xlsx_path,
            lambda path: result.features.to_excel(
                path,
                sheet_name="Context_Features",
                index=False,
            ),
        )
        written["xlsx"] = xlsx_path

    if "parquet" in config.output_formats:
        parquet_path = output_directory / f"{config.output_stem}.parquet"
        _write_atomic(
            parquet_path,
            lambda path: result.features.to_parquet(path, index=False),
        )
        written["parquet"] = parquet_path

    manifest_path = output_directory / f"{config.output_stem}.manifest.json"
    manifest = build_manifest(result)
    _write_atomic(
        manifest_path,
        lambda path: path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False, default=str) + "\n",
            encoding="utf-8",
        ),
    )
    written["manifest"] = manifest_path
    return written
