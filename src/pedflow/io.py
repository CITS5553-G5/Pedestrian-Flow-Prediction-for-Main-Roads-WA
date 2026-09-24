"""Shared location input, stable fingerprints and atomic local file writes."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import pandas as pd

from pedflow.exceptions import ConfigurationError


def read_sites(path: str | Path, *, sheet: str = "Batch_Input") -> pd.DataFrame:
    """Preserve text IDs and add WGS84 only when the CRS column is absent."""
    source = Path(path)
    try:
        if source.suffix.lower() in {".xlsx", ".xls"}:
            table = pd.read_excel(
                source, sheet_name=sheet, dtype={"site_id": "string"}, keep_default_na=False
            )
        elif source.suffix.lower() == ".csv":
            table = pd.read_csv(source, dtype={"site_id": "string"}, keep_default_na=False)
        elif source.suffix.lower() == ".parquet":
            table = pd.read_parquet(source)
        else:
            raise ConfigurationError("Input must be an Excel, CSV or Parquet location table.")
    except (OSError, ValueError) as exc:
        raise ConfigurationError(f"Cannot read location input: {exc}") from exc
    # Strings such as 'NA' are legitimate IDs; coordinate blanks fail validation later.
    if "coordinate_crs" not in table:
        table.insert(min(3, len(table.columns)), "coordinate_crs", "EPSG:4326")
    return table


def fingerprint(value) -> str:
    """Hash JSON content independently of dictionary key order; reject nonfinite values."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


@contextmanager
def atomic_path(target: str | Path):
    """Publish a completed file by replacement; clean up failed temporary writes."""
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.stem}.{uuid4().hex}.tmp{target.suffix}")
    try:
        yield temporary
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def write_json_atomic(path: str | Path, data: dict) -> None:
    """Flush a strict JSON record before replacing the previous checkpoint/manifest."""
    with atomic_path(path) as temporary, temporary.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
