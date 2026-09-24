"""Offline checkpoint, recovery and file-boundary integration tests."""

import json
from dataclasses import replace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from pedflow.exceptions import ConfigurationError
from pedflow.imagery import ImageryConfig, build_imagery_features
from pedflow.imagery.contracts import ExtractionError
from pedflow.imagery.io import read_sites, write_imagery_outputs
from pedflow.modeling import load_model


def sites():
    return pd.DataFrame(
        {
            "site_id": ["003", "001", "002"],
            "latitude": [-32.0] * 3,
            "longitude": [116.0] * 3,
            "coordinate_crs": ["EPSG:4326"] * 3,
        }
    )


def extract(site):
    return {"commercial_buildings": int(site["site_id"]), "footpath_both_sides": True}, {
        "image_count": 2,
        "warnings": [],
        "source": "offline fixture",
    }


def test_checkpoint_reuses_successes_and_retries_only_failed_sites(tmp_path):
    path = tmp_path / "checkpoint.json"
    config = ImageryConfig()

    def first(site):
        if site["site_id"] == "001":
            raise ExtractionError("llm_http_503", retryable=True)
        return extract(site)

    result = build_imagery_features(sites(), config, extractor=first, checkpoint_path=path)
    assert result.features.imagery_status.tolist() == ["complete", "failed", "complete"]
    resumed_provider = MagicMock(side_effect=extract)
    result = build_imagery_features(
        sites().iloc[::-1],
        replace(config, max_workers=1),
        extractor=resumed_provider,
        checkpoint_path=path,
        resume=True,
    )
    resumed_provider.assert_called_once()
    assert resumed_provider.call_args.args[0]["site_id"] == "001"
    assert result.features.site_id.tolist() == ["002", "001", "003"]
    assert result.metadata["reused_sites"] == 2
    assert result.features.imagery_status.eq("complete").all()
    assert not path.with_suffix(".json.lock").exists()


def test_compatible_completed_checkpoint_needs_no_keys_or_requests(tmp_path):
    path = tmp_path / "checkpoint.json"
    build_imagery_features(sites(), ImageryConfig(), extractor=extract, checkpoint_path=path)
    with patch.dict("os.environ", {}, clear=True), patch("requests.Session") as network:
        result = build_imagery_features(sites(), ImageryConfig(), checkpoint_path=path, resume=True)
    assert result.metadata["reused_sites"] == 3
    network.assert_not_called()


def test_changed_inputs_or_recipe_cannot_reuse_checkpoint(tmp_path):
    path = tmp_path / "checkpoint.json"
    config = ImageryConfig()
    build_imagery_features(sites(), config, extractor=extract, checkpoint_path=path)
    provider = MagicMock()
    for data, changed in [
        (sites().assign(latitude=-33), config),
        (sites().iloc[:2], config),
        (sites(), replace(config, model="different-model")),
        (sites(), replace(config, sampling_offset_m=100)),
    ]:
        with pytest.raises(ConfigurationError, match="differ"):
            build_imagery_features(
                data, changed, extractor=provider, checkpoint_path=path, resume=True
            )
    provider.assert_not_called()


def test_existing_checkpoint_requires_explicit_resume_and_lock_blocks_second_writer(tmp_path):
    path = tmp_path / "checkpoint.json"
    build_imagery_features(sites(), ImageryConfig(), extractor=extract, checkpoint_path=path)
    original = path.read_bytes()
    with pytest.raises(ConfigurationError, match="exists"):
        build_imagery_features(sites(), ImageryConfig(), extractor=extract, checkpoint_path=path)
    assert path.read_bytes() == original
    lock = path.with_name(path.name + ".lock")
    lock.write_text("another worker")
    with pytest.raises(ConfigurationError, match="locked"):
        build_imagery_features(
            sites(), ImageryConfig(), extractor=extract, checkpoint_path=path, resume=True
        )
    assert lock.read_text() == "another worker"


def test_progress_is_saved_before_interruption(tmp_path):
    path = tmp_path / "checkpoint.json"
    config = ImageryConfig(max_workers=1)

    def interrupt(*args):
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        build_imagery_features(
            sites(), config, extractor=extract, checkpoint_path=path, progress=interrupt
        )
    assert len(json.loads(path.read_text())["records"]) == 1
    assert not path.with_name(path.name + ".lock").exists()
    provider = MagicMock(side_effect=extract)
    resumed = build_imagery_features(
        sites(), config, extractor=provider, checkpoint_path=path, resume=True
    )
    assert provider.call_count == 2
    assert resumed.features.imagery_status.eq("complete").all()


def test_corrupt_checkpoint_does_not_silently_requery(tmp_path):
    path = tmp_path / "checkpoint.json"
    build_imagery_features(sites(), ImageryConfig(), extractor=extract, checkpoint_path=path)
    data = json.loads(path.read_text())
    data["records"]["001"]["site_id"] = "different-site"
    path.write_text(json.dumps(data))
    provider = MagicMock()
    with pytest.raises(ConfigurationError, match="Invalid checkpoint"):
        build_imagery_features(
            sites(), ImageryConfig(), extractor=provider, checkpoint_path=path, resume=True
        )
    provider.assert_not_called()


def test_input_output_round_trip_and_model_contract(tmp_path):
    source = sites().drop(columns="coordinate_crs")
    path = tmp_path / "sites.xlsx"
    source.to_excel(path, sheet_name="Batch_Input", index=False)
    prepared = read_sites(path)
    assert prepared.site_id.tolist() == ["003", "001", "002"]
    assert prepared.coordinate_crs.eq("EPSG:4326").all()
    result = build_imagery_features(prepared, ImageryConfig(), extractor=extract)
    paths = write_imagery_outputs(result, tmp_path / "output")
    persisted = pd.read_csv(paths["csv"], dtype={"site_id": "string"})
    assert persisted.site_id.tolist() == source.site_id.tolist()
    assert json.loads(paths["manifest"].read_text())["status_counts"] == {"complete": 3}
    assert list((tmp_path / "output").glob("*"))  # No image files are written.
    assert {p.suffix for p in (tmp_path / "output").iterdir()} == {".csv", ".json"}
    predictions = load_model().predict(result.features.assign(abs_mb_category_simple="Residential"))
    assert predictions.site_id.tolist() == source.site_id.tolist()
    assert predictions.pred_peak_cross_ped_per_h.gt(0).all()


def test_cli_calls_shared_workflow_and_exports(tmp_path, monkeypatch):
    from pedflow.imagery.__main__ import main

    config = tmp_path / "config.json"
    config.write_text('{"max_workers":2}')
    sites().to_csv(tmp_path / "sites.csv", index=False)
    monkeypatch.setattr(
        "sys.argv",
        [
            "pedflow-imagery",
            "--project-root",
            str(tmp_path),
            "--config",
            "config.json",
            "--input",
            "sites.csv",
            "--output-directory",
            "output",
            "--workers",
            "10",
        ],
    )
    with patch("pedflow.imagery.workflow.GoogleGeminiExtractor", return_value=extract) as factory:
        assert main() == 0
    assert factory.call_args.args[0].max_workers == 10
    assert (tmp_path / "output/imagery_features.csv").is_file()
