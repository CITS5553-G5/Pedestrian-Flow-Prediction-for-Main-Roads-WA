"""Run against local private data when available; never fetch external services."""

import json
from pathlib import Path

import pandas as pd
import pytest

from pedflow.prediction.ausrap import DEFAULT_SOURCE, AusRAPIndex, match_site

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "04_prediction_pipeline/irap_comparison/evidence/preflight_audit.json"


@pytest.mark.skipif(not AUDIT.exists() or not (ROOT / DEFAULT_SOURCE).exists(), reason="Local client sources required")
def test_all_45_original_client_means_and_bands_are_reproduced():
    audit = json.loads(AUDIT.read_text())
    index = AusRAPIndex(ROOT / DEFAULT_SOURCE, ROOT / "data/cache/ausrap")
    client = pd.read_csv(ROOT / "data/raw/Ped_iRAP_merged.csv").set_index("ID")
    count = 0
    for checked in audit["sites"]:
        if not checked["available"]:
            continue
        baseline = client.loc[checked["source_location_id"]]
        result, matched = match_site({"site_id": checked["site_id"], "road_no": baseline.ROAD_NO,
                                      "slk_km": baseline.SLK, "location_status": "matched"}, index)
        assert result["existing_irap_cross_recoded_ped_per_h"] == pytest.approx(baseline.Ped_Peak_Cross, rel=0, abs=1e-9)
        assert result["existing_irap_along_recoded_ped_per_h"] == pytest.approx(baseline.Ped_Peak_Along, rel=0, abs=1e-9)
        assert matched["matched_source_rows"] == checked["matched_rows"]
        assert matched["cross_band"] == pytest.approx(checked["cross_band_mean"])
        assert matched["along_combined_band"] == pytest.approx(checked["along_band_mean"])
        if checked["site_id"] == "250303-13":
            assert result["existing_irap_along_recoded_ped_per_h"] == 126
            assert matched["matched_source_rows"] == [73747, 73748, 73749]
        count += 1
    assert count == 45
    assert index.metadata["source_rows"] == 189222
