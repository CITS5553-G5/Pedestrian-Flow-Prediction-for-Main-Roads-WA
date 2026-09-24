"""Atomic, single-writer progress checkpoints containing features, never images."""

from __future__ import annotations

import json
import os
from pathlib import Path

from pedflow.exceptions import ConfigurationError

# Keep notebook imports compatible while sharing I/O across all workflows.
from pedflow.io import fingerprint, write_json_atomic

__all__ = ["Checkpoint", "fingerprint", "write_json_atomic"]


class Checkpoint:
    """Hold one writer lock and reuse records only for the same sites and recipe."""

    def __init__(self, path, identity, *, resume: bool):
        """Keep the checkpoint path optional for in-memory runs; defer I/O until entry."""
        self.path = Path(path) if path is not None else None
        self.identity = identity
        self.resume = resume
        self.records = {}
        self._lock = None

    def __enter__(self):
        """Reject an invalid resume before creating a directory or requesting imagery."""
        if self.resume and (self.path is None or not self.path.is_file()):
            raise ConfigurationError("Cannot resume without an existing checkpoint file.")
        if self.path is None:
            return self
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.path.with_name(self.path.name + ".lock")
        try:
            with lock.open("x", encoding="utf-8") as stream:
                stream.write(f"pid={os.getpid()}\n")
            self._lock = lock
        except FileExistsError as exc:
            raise ConfigurationError(
                f"Checkpoint is locked: {lock}. Use a different path; remove a stale lock "
                "only after confirming its process is no longer running."
            ) from exc
        try:
            if self.path.exists():
                if not self.resume:
                    raise ConfigurationError("Checkpoint exists. Use resume=True or a new path.")
                payload = json.loads(self.path.read_text("utf-8"))
                if payload.get("schema_version") != 1 or payload.get("identity") != self.identity:
                    raise ConfigurationError(
                        "Checkpoint inputs or extraction settings differ. Choose a new checkpoint."
                    )
                self.records = payload["records"]
                if not isinstance(self.records, dict):
                    raise ConfigurationError("Invalid checkpoint records.")
            return self
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            self.__exit__(None, None, None)
            raise ConfigurationError(f"Cannot read imagery checkpoint: {exc}") from exc
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def save(self, site_id, record):
        """Persist on the coordinator thread, once a site has completed."""
        self.records[site_id] = record
        if self.path is not None:
            write_json_atomic(
                self.path,
                {
                    "schema_version": 1,
                    "identity": self.identity,
                    "records": self.records,
                },
            )

    def __exit__(self, *args):
        """Release only the lock acquired by this checkpoint instance."""
        if self._lock is not None:
            self._lock.unlink(missing_ok=True)
        return False
