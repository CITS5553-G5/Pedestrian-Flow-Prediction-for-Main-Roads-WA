"""Tracer bullet: real CLI → source adapters → saved model → files → recovery.

Only HTTP/SDK responses are simulated. Synthetic images/counts are test inputs,
never scientific evidence of imagery accuracy or a live provider speed test.
"""

import hashlib
import json
from collections import Counter
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pandas as pd
import pytest
import requests
from PIL import Image

from pedflow.prediction.__main__ import main

ROOT = Path(__file__).resolve().parents[2]


def test_tracer_cli_to_r_reference_and_resume(tmp_path, monkeypatch):
    """One failed site must recover without repeating the two completed image jobs."""
    from google.genai import errors, models

    # Keep actual workbook parsing, ABS calculations and recipe/release validation.
    config_dir = tmp_path / "configs/prediction"
    config_dir.mkdir(parents=True)
    settings = json.loads((ROOT / "configs/prediction/workflow_v1.json").read_text())
    settings["model_release"] = str(ROOT / settings["model_release"])
    context = json.loads((ROOT / settings["context_config"]).read_text())
    context["sources"]["abs_meshblock_sa1"]["options"]["counts_path"] = "counts.xlsx"
    imagery = json.loads((ROOT / settings["imagery_config"]).read_text())
    # Only execution limits differ; the scientific recipe/hash remains unchanged.
    imagery.update(max_workers=3, maps_requests_per_minute=10**9, llm_requests_per_minute=10**9)
    for name, data in [
        ("workflow_v1", settings),
        ("context_abs_v1", context),
        ("imagery_v1", imagery),
    ]:
        (config_dir / f"{name}.json").write_text(json.dumps(data))

    counts = pd.DataFrame(
        {
            "MB_CODE_2021": ["50000000001", "50000000002", "50000000003"],
            "MB_CATEGORY_NAME_2021": ["Residential", "Commercial", "Transport"],
            "AREA_ALBERS_SQKM": [0.25, 0.5, 1.0],
            "Dwelling": [10, 20, 0],
            "Person": [20, 40, 0],
            "State": [5, 5, 5],
        }
    )
    counts.to_excel(tmp_path / "counts.xlsx", sheet_name="Table 5", startrow=6, index=False)
    sites = pd.DataFrame(
        {
            "site_id": ["003", "NA", "001"],
            "latitude": [-31.1, -31.2, -31.3],
            "longitude": [116.0] * 3,
        }
    )
    sites.to_csv(tmp_path / "sites.csv", index=False)
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "tracer-maps-key")
    monkeypatch.setenv("GEMINI_API_KEY", "tracer-gemini-key")

    calls = Counter()
    recovery = False

    def remote_http(_session, request, **kwargs):
        """Emulate transport responses while exercising the real request construction."""
        url = urlparse(request.url)
        query = parse_qs(url.query)
        response = requests.Response()
        response.status_code = 200
        response.request = request
        response.url = request.url
        if url.hostname == "geo.abs.gov.au":
            latitude = json.loads(query["geometry"][0])["y"]
            site_number = round((-latitude - 31) * 10)
            calls["abs"] += 1
            payload = {
                "features": [
                    {
                        "attributes": {
                            "mb_code_2021": f"5000000000{site_number}",
                            "sa1_code_2021": f"5010000000{site_number}",
                        }
                    }
                ]
            }
            response._content = json.dumps(payload).encode()
        elif url.hostname == "maps.googleapis.com":
            calls["maps"] += 1
            if url.path.endswith("metadata"):
                response._content = b'{"status":"ZERO_RESULTS"}'
            elif url.path.endswith("staticmap"):
                latitude = float(query["center"][0].split(",")[0])
                site_number = round((-latitude - 31) * 10)
                image = Image.new("RGB", (2, 2), (site_number, 0, 0))
                buffer = BytesIO()
                image.save(buffer, format="PNG")
                image.close()
                response._content = buffer.getvalue()
            else:
                pytest.fail(f"Unexpected image request: {url.path}")
        else:
            pytest.fail(f"Unstubbed HTTP host: {url.hostname}")
        return response

    def remote_gemini(_models, *, model, contents):
        """Identify the synthetic site through its image, not through injected features."""
        assert model == imagery["model"]
        assert isinstance(contents[0], str) and len(contents) == 2
        site_number = contents[1].getpixel((0, 0))[0]
        calls[f"gemini-{site_number}"] += 1
        if site_number == 3 and not recovery:
            raise errors.APIError(400, {"error": {"message": "synthetic rejection"}})
        return SimpleNamespace(text='{"commercial_buildings":2,"footpath_both_sides":true}')

    monkeypatch.setattr(requests.Session, "send", remote_http)
    monkeypatch.setattr(models.Models, "generate_content", remote_gemini)
    argv = [
        "pedflow-predict",
        "--project-root",
        str(tmp_path),
        "--input",
        "sites.csv",
        "--output-directory",
        "output",
    ]
    monkeypatch.setattr("sys.argv", argv)
    assert main() == 2
    workbook = tmp_path / "output/predictions.xlsx"
    first = pd.read_excel(
        workbook, sheet_name="Predictions", keep_default_na=False, dtype={"site_id": "string"}
    )
    assert first.site_id.tolist() == ["003", "NA", "001"]
    assert first.status.tolist() == [
        "predicted_with_warning",
        "predicted_with_warning",
        "not_predicted",
    ]
    assert first.pred_peak_cross_ped_per_h.iloc[2] == ""
    first_manifest = json.loads((tmp_path / "output/predictions.manifest.json").read_text())

    # Resume refreshes ABS and retries only the failed imagery job.
    recovery = True
    monkeypatch.setattr("sys.argv", argv + ["--resume"])
    assert main() == 0
    assert calls == {"abs": 6, "maps": 24, "gemini-1": 1, "gemini-2": 1, "gemini-3": 2}
    result = pd.read_excel(
        workbook, sheet_name="Predictions", keep_default_na=False, dtype={"site_id": "string"}
    )
    features = pd.read_excel(
        workbook, sheet_name="Features", keep_default_na=False, dtype={"site_id": "string"}
    )
    assert features.abs_mb_category_simple.tolist() == ["Residential", "Commercial", "Other"]
    assert features.abs_mb_category_2021.tolist() == ["Residential", "Commercial", "Transport"]
    assert "abs_mb_persons_per_sqkm_2021" not in features  # Not a deployed model input.
    assert result.status.eq("predicted_with_warning").all()
    assert result.message.str.contains("aerial_only").all()

    # R predict.lm references are independent of the Python coefficient calculation.
    reference = json.loads((ROOT / "tests/fixtures/modeling/r_linear_reference.json").read_text())
    for index, category in enumerate(features.abs_mb_category_simple):
        case = next(
            case
            for case in reference["cases"]
            if case["commercial_buildings"] == 2
            and case["footpath_both_sides"] == "TRUE"
            and case["abs_mb_category_simple"] == category
        )
        for target in ("pred_peak_cross_ped_per_h", "pred_peak_along_ped_per_h"):
            assert result[target].iloc[index] == pytest.approx(case[target], rel=1e-12)
    manifest = json.loads((tmp_path / "output/predictions.manifest.json").read_text())
    assert manifest["run_id"] != first_manifest["run_id"]
    assert manifest["imagery"]["reused_sites"] == 2
    assert "workbook_sha256" not in manifest
    assert (
        manifest["context"]["sources"][0]["metadata"]["source_file_sha256"]
        == hashlib.sha256((tmp_path / "counts.xlsx").read_bytes()).hexdigest()
    )
    assert not list((tmp_path / "output").glob("*.lock"))
