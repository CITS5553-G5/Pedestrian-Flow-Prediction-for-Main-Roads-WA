"""Regression checks for shared file, site and recovery boundaries."""

import json
from pathlib import Path

import pandas as pd
import pytest

from pedflow.context.contracts import SourceConfig
from pedflow.context.sources.abs_meshblock_sa1 import query_meshblock_codes
from pedflow.exceptions import ConfigurationError, ContractError
from pedflow.imagery.checkpoint import Checkpoint
from pedflow.io import read_sites, write_json_atomic
from pedflow.validation import validate_and_normalise_sites


@pytest.mark.parametrize("suffix", ["csv", "xlsx"])
def test_file_readers_preserve_na_and_leading_zero_ids(tmp_path, suffix):
    """Default pandas NA recognition must not discard legitimate location IDs."""
    sites = pd.DataFrame(
        {"site_id": ["NA", "001"], "latitude": [-32, -31], "longitude": [116, 116]}
    )
    path = tmp_path / f"sites.{suffix}"
    if suffix == "csv":
        sites.to_csv(path, index=False)
    else:
        sites.to_excel(path, sheet_name="Batch_Input", index=False)
    checked = validate_and_normalise_sites(read_sites(path))
    assert checked.site_id.tolist() == ["NA", "001"]


def test_atomic_json_failure_preserves_previous_record(tmp_path):
    """A bad new record must not corrupt the last usable checkpoint."""
    path = tmp_path / "checkpoint.json"
    write_json_atomic(path, {"complete": 1})
    with pytest.raises(ValueError):
        write_json_atomic(path, {"complete": float("nan")})
    assert json.loads(path.read_text()) == {"complete": 1}
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("use_path", [True, False])
def test_resume_requires_existing_checkpoint(tmp_path, use_path):
    """A requested recovery must not silently start new paid source requests."""
    path = tmp_path / "new/checkpoint.json" if use_path else None
    with (
        pytest.raises(ConfigurationError, match="existing checkpoint"),
        Checkpoint(path, {}, resume=True),
    ):
        pytest.fail("Must not enter a fresh run")
    assert not list(tmp_path.iterdir())


def test_boolean_coordinates_are_rejected():
    sites = pd.DataFrame(
        {"site_id": ["x"], "latitude": [True], "longitude": [116], "coordinate_crs": ["EPSG:4326"]}
    )
    with pytest.raises(ContractError, match="booleans"):
        validate_and_normalise_sites(sites)


def test_abs_closes_responses_and_owned_session(monkeypatch):
    """Malformed responses are failures, not valid no-match evidence."""
    from unittest.mock import MagicMock

    response = MagicMock()
    response.json.return_value = {}
    factory = MagicMock()
    session = factory.return_value.__enter__.return_value
    session.get.return_value = response
    monkeypatch.setattr("requests.Session", factory)
    sites = pd.DataFrame({"site_id": ["x"], "latitude": [-32], "longitude": [116]})
    result = query_meshblock_codes(sites, SourceConfig("abs_meshblock_sa1", True))
    assert result.abs_match_status.tolist() == ["request_failed"]
    response.close.assert_called_once()
    factory.return_value.__exit__.assert_called_once()


def test_workflow_rejects_unrecognised_setting_before_extraction(tmp_path):
    from pedflow.prediction.config import load_settings

    root = Path(__file__).resolve().parents[2]
    settings = json.loads((root / "configs/prediction/workflow_v1.json").read_text())
    settings["misspelled_setting"] = "ignored before this fix"
    path = tmp_path / "config.json"
    path.write_text(json.dumps(settings))
    with pytest.raises(ConfigurationError, match="exactly"):
        load_settings(root, path)
