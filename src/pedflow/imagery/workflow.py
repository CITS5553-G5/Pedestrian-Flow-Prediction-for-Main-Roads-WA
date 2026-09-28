"""Bounded site-level concurrency, stable joins, progress and resumable extraction."""

from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from pedflow.exceptions import ConfigurationError
from pedflow.imagery.checkpoint import Checkpoint
from pedflow.imagery.contracts import ExtractionError, ImageryConfig, ImageryResult, config_metadata
from pedflow.imagery.providers import GoogleGeminiExtractor, validate_features
from pedflow.io import fingerprint
from pedflow.validation import validate_and_normalise_sites

REUSABLE = {"complete", "needs_review"}


def _extract_one(site, extractor):
    """Convert one provider result into a safe, nullable per-site record."""
    record = {
        "site_id": site["site_id"],
        "commercial_buildings": None,
        "footpath_both_sides": None,
        "imagery_status": "failed",
        "imagery_error": "",
        "imagery_warnings": "",
        "image_count": 0,
        "processed_at_utc": "",
        "provenance": {},
    }
    try:
        values, metadata = extractor(site)
        values = validate_features(values)
        record.update(values)
        record["imagery_status"] = (
            "complete" if all(value is not None for value in values.values()) else "needs_review"
        )
        record["provenance"] = metadata
        record["image_count"] = metadata.get("image_count", 0)
        record["imagery_warnings"] = "; ".join(metadata.get("warnings", []))
    except ExtractionError as exc:
        record["commercial_buildings"] = record["footpath_both_sides"] = None
        record["imagery_error"] = exc.code
        if exc.code == "imagery_http_404":
            record["imagery_status"] = "no_imagery"
    except Exception as exc:  # noqa: BLE001 - retain a safe failure row for each requested site
        # A failed site remains in the result, without leaking provider messages/keys.
        record["commercial_buildings"] = record["footpath_both_sides"] = None
        record["imagery_error"] = f"unexpected_{type(exc).__name__}"
    record["processed_at_utc"] = datetime.now(UTC).isoformat()
    return record


def _validate_saved(records, sites):
    """Reject malformed cached records before scheduling or trusting saved features."""
    if not set(records).issubset({site["site_id"] for site in sites}):
        raise ConfigurationError("Checkpoint contains unexpected site IDs.")
    for key, record in records.items():
        try:
            if record["site_id"] != key or record["imagery_status"] not in {
                *REUSABLE,
                "failed",
                "no_imagery",
            }:
                raise ValueError("Invalid identity or status")
            values = validate_features(record)
            if record["imagery_status"] == "complete" and any(v is None for v in values.values()):
                raise ValueError("Incomplete saved success")
            for field in ("processed_at_utc", "imagery_warnings", "imagery_error"):
                if not isinstance(record[field], str):
                    raise TypeError("Invalid metadata")
            if type(record["image_count"]) is not int or record["image_count"] < 0:
                raise ValueError("Invalid image count")
            if not isinstance(record["provenance"], dict):
                raise TypeError("Invalid provenance")
        except (KeyError, ValueError, TypeError, ExtractionError) as exc:
            raise ConfigurationError(f"Invalid checkpoint record for site {key}.") from exc


def build_imagery_features(
    sites: pd.DataFrame,
    config: ImageryConfig,
    *,
    checkpoint_path: str | Path | None = None,
    resume: bool = False,
    extractor=None,
    progress=None,
) -> ImageryResult:
    """Extract each site once with up to max_workers active sites.

    Input uses the common site_id/WGS84 contract. Injected extractors are useful
    for offline tests and must return (two_features, provenance). Progress receives
    (completed, total, site_id, status) on the coordinator thread after saving.
    A changed site set, coordinates, model or prompt rejects checkpoint reuse.
    """
    normalised = validate_and_normalise_sites(sites)
    rows = normalised.to_dict("records")
    identity = {
        "input_sha256": fingerprint(sorted(rows, key=lambda site: site["site_id"])),
        "extraction_sha256": fingerprint(config.extraction_identity()),
    }
    started_at = datetime.now(UTC).isoformat()
    with Checkpoint(checkpoint_path, identity, resume=resume) as checkpoint:
        _validate_saved(checkpoint.records, rows)
        completed = sum(
            record["imagery_status"] in REUSABLE for record in checkpoint.records.values()
        )
        reused = completed
        pending_sites = [
            site
            for site in rows
            if checkpoint.records.get(site["site_id"], {}).get("imagery_status") not in REUSABLE
        ]
        if pending_sites:
            active_extractor = extractor if extractor is not None else GoogleGeminiExtractor(config)
            iterator = iter(pending_sites)
            pool = ThreadPoolExecutor(max_workers=config.max_workers, thread_name_prefix="imagery")
            active = {}

            def submit_next():
                """Keep at most max_workers requests in flight without a fixed slow batch barrier."""
                site = next(iterator, None)
                if site is not None:
                    active[pool.submit(_extract_one, site, active_extractor)] = site["site_id"]

            try:
                for _ in range(min(config.max_workers, len(pending_sites))):
                    submit_next()
                while active:
                    finished, _ = wait(active, return_when=FIRST_COMPLETED)
                    for future in finished:
                        site_id = active.pop(future)
                        record = future.result()
                        checkpoint.save(site_id, record)
                        completed += 1
                        if progress is not None:
                            progress(completed, len(rows), site_id, record["imagery_status"])
                        submit_next()
            finally:
                pool.shutdown(wait=True, cancel_futures=True)
        elif progress is not None:
            progress(completed, len(rows), "", "resumed")
        ordered = [checkpoint.records[site["site_id"]] for site in rows]

    table = pd.DataFrame(
        [{k: v for k, v in record.items() if k != "provenance"} for record in ordered]
    )
    table["site_id"] = table["site_id"].astype("string")
    table["commercial_buildings"] = table["commercial_buildings"].astype("Int64")
    table["footpath_both_sides"] = table["footpath_both_sides"].astype("boolean")
    return ImageryResult(
        feature_set_version=config.feature_set_version,
        features=table,
        metadata={
            "started_at_utc": started_at,
            "finished_at_utc": datetime.now(UTC).isoformat(),
            "configuration": config_metadata(config),
            "identity": identity,
            "row_count": len(table),
            "reused_sites": reused,
            "status_counts": table["imagery_status"].value_counts().to_dict(),
            "sites": {record["site_id"]: record["provenance"] for record in ordered},
            "training_imagery_provenance": "Historical run recipe not fully documented; requires comparison",
        },
    )
