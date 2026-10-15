"""Reference matching must preserve units, source rows, missing values and model output."""

import json

import pandas as pd
import pytest

from pedflow.exceptions import ContractError
from pedflow.prediction.ausrap import (
    SOURCE_COLUMNS,
    AusRAPIndex,
    attach_reference,
    match_site,
)
from pedflow.prediction.location import resolve_locations


def make_index(tmp_path, rows):
    source = tmp_path / "ausrap.xlsx"
    pd.DataFrame(rows, columns=SOURCE_COLUMNS).to_excel(source, index=False)
    return AusRAPIndex(source, tmp_path / "cache")


@pytest.fixture
def index(tmp_path):
    return make_index(tmp_path, [
        ["R1", 1.0, 1.1, "L", "None", "1 pedestrian", "2 to 3 pedestrians"],
        ["R1", 1.2, 1.1, "R", "2 to 3 pedestrians", "None", "None"],
        ["R2", 1.0, 1.1, "S", "None", "None", "None"],
    ])


def site(**values):
    return {"site_id": "new-1", "road_no": "R1", "slk_km": 1.1,
            "location_status": "matched", **values}


def test_client_mean_preserves_reversed_rows_carriageways_and_mixed_categories(index):
    result, audit = match_site(site(cway="L"), index)
    assert result["existing_irap_cross_recoded_ped_per_h"] == 7.5
    assert result["existing_irap_along_recoded_ped_per_h"] == 9
    assert result["existing_ausrap_cross_band"] == "3–12.5"
    assert result["existing_ausrap_along_combined_band"] == "3.5–15"
    assert result["existing_ausrap_cross_category"] is None
    assert "Mixed crossing categories: 1, 3" in result["comparison_notes"]
    assert audit["matched_source_rows"] == [2, 3]
    assert audit["carriageways"] == ["L", "R"]
    assert index.metadata["reversed_bounds_rows"] == 1


def test_zero_is_a_real_reference_and_no_match_is_not_zero(index):
    zero, _ = match_site(site(road_no="R2"), index)
    assert zero["comparison_status"] == "matched"
    assert zero["existing_irap_cross_recoded_ped_per_h"] == 0
    assert zero["existing_ausrap_cross_band"] == "0"
    missing, audit = match_site(site(road_no="MISSING"), index)
    assert missing["comparison_status"] == "no_ausrap_match"
    assert missing["existing_irap_cross_recoded_ped_per_h"] is None
    assert audit["matched_source_rows"] == []


def test_partial_source_missing_never_changes_the_mean_denominator(tmp_path):
    index = make_index(tmp_path, [
        ["R1", 1, 1.1, "S", "1 pedestrian", "1 pedestrian", "None"],
        ["R1", 1.1, 1.2, "S", None, "1 pedestrian", None],
    ])
    result, audit = match_site(site(), index)
    assert result["comparison_status"] == "matched_no_flow"
    assert result["existing_irap_cross_recoded_ped_per_h"] is None
    assert result["existing_ausrap_cross_category"] is None
    assert result["existing_ausrap_along_combined_band"] is None
    assert len(audit["matched_source_rows"]) == 2


def test_unknown_label_only_blocks_affected_direction(tmp_path):
    index = make_index(tmp_path, [["R1", 1, 1.2, "S", "unrecognized", "None", "None"]])
    result, _ = match_site(site(), index)
    assert result["comparison_status"] == "matched_partial"
    assert result["existing_irap_cross_recoded_ped_per_h"] is None
    assert result["existing_irap_along_recoded_ped_per_h"] == 0
    assert index.metadata["unrecognized_flow_cells"] == 1


def test_open_band_has_no_invented_recoded_count(tmp_path):
    index = make_index(tmp_path, [["R1", 1, 1.2, "S", 11, 10, 2]])
    result, audit = match_site(site(), index)
    assert result["comparison_status"] == "matched_bands_only"
    assert result["existing_ausrap_cross_category"] == 11
    assert result["existing_ausrap_cross_band"] == "900+"
    assert result["existing_ausrap_along_combined_band"] == "502–905"
    assert result["existing_irap_cross_recoded_ped_per_h"] is None
    assert result["existing_irap_along_recoded_ped_per_h"] is None
    assert audit["cross_band"] == (900, None)
    json.dumps(audit, allow_nan=False)


def test_duplicate_source_rows_remain_equal_weighted(tmp_path):
    record = ["R1", 1, 1.2, "S", 3, 1, 1]
    index = make_index(tmp_path, [record, record, ["R1", 1, 1.2, "S", 1, 1, 1]])
    result, audit = match_site(site(), index)
    assert result["existing_irap_cross_recoded_ped_per_h"] == 10
    assert audit["matched_source_rows"] == [2, 3, 4]


def test_source_record_id_selects_exactly_one_row(index):
    record_id = f"ausrap:{index.sha256}:2"
    result, audit = match_site(site(ausrap_record_id=record_id, cway="L"), index)
    assert result["existing_irap_cross_recoded_ped_per_h"] == 0
    assert result["existing_irap_along_recoded_ped_per_h"] == 18
    assert audit["matched_source_rows"] == [2]
    assert audit["method"] == "source_record_id"


@pytest.mark.parametrize("record_id", ["invalid", "ausrap:" + "0" * 64 + ":2", "absent_row", "oversized_row"])
def test_bad_record_id_cannot_fall_back_to_window(index, record_id):
    if record_id == "absent_row":
        record_id = f"ausrap:{index.sha256}:999"
    elif record_id == "oversized_row":
        record_id = f"ausrap:{index.sha256}:9999999999999999999999"
    result, _ = match_site(site(ausrap_record_id=record_id), index)
    assert result["comparison_status"] == "invalid_record_id"
    assert result["existing_irap_cross_recoded_ped_per_h"] is None


@pytest.mark.parametrize("override", [{"road_no": "R2"}, {"slk_km": 5}, {"cway": "R"}])
def test_record_location_conflicts_are_explicit(index, override):
    result, _ = match_site(site(ausrap_record_id=f"ausrap:{index.sha256}:2", **override), index)
    assert result["comparison_status"] == "record_location_conflict"


def test_coordinate_matching_uses_unrounded_slk(tmp_path):
    index = make_index(tmp_path, [["R1", 1.2234, 1.3, "S", 3, 1, 1]])
    location = site(road_no=None, slk_km=None, matched_road_no="R1", matched_slk_km=1.123,
                    _matched_slk_km_exact=1.12349)
    result, audit = match_site(location, index)
    assert result["comparison_status"] == "matched"
    assert audit["slk_km"] == 1.12349


def test_segment_without_record_id_uses_prediction_midpoint(index):
    result, audit = match_site(site(slk_km=None, start_slk=0.9, end_slk=1.3), index)
    assert result["comparison_status"] == "matched"
    assert audit["slk_km"] == 1.1
    assert audit["method"] == "point_window_equal_mean"


def test_ambiguous_coordinates_are_not_guessed_but_explicit_roads_can_have_a_reference(index):
    missing, _ = match_site(site(road_no=None, location_status="ambiguous_road"), index)
    assert missing["comparison_status"] == "location_unresolved"
    reference, _ = match_site(site(location_status="road_reference_not_found"), index)
    assert reference["comparison_status"] == "matched"
    assert "supplied road/SLK" in reference["comparison_notes"]
    conflict, _ = match_site(site(location_status="road_coordinate_conflict"), index)
    assert conflict["comparison_status"] == "location_conflict"


def test_attach_preserves_predictions_input_order_and_optional_observations(index, tmp_path):
    locations = pd.DataFrame([site(site_id="B"), site(site_id="A", obs_peak_cross_ped_per_h=5.2)])
    predictions = pd.DataFrame({"site_id": ["A", "B"], "pred_peak_cross_ped_per_h": [0., 5.2],
                                "pred_peak_along_ped_per_h": [10., None], "status": ["predicted", "not_predicted"]})
    before = predictions.copy(deep=True)
    result, metadata = attach_reference(predictions, locations, tmp_path, index=index)
    pd.testing.assert_frame_equal(result[before.columns], before)
    pd.testing.assert_frame_equal(predictions, before)
    assert result.predicted_cross_category.tolist() == [1, 3]
    assert result.observed_cross_category.iloc[0] == 3
    assert pd.isna(result.observed_cross_category.iloc[1])
    assert metadata["prediction_basis"] == "released_model_inference"
    assert metadata["accuracy_metrics_computed"] is False


def test_missing_source_does_not_erase_model_results(tmp_path):
    locations = pd.DataFrame([site()])
    predictions = pd.DataFrame({"site_id": ["new-1"], "pred_peak_cross_ped_per_h": [0.],
                                "pred_peak_along_ped_per_h": [12.], "status": ["predicted"]})
    result, metadata = attach_reference(predictions, locations, tmp_path)
    assert result.status.tolist() == ["predicted"]
    assert result.pred_peak_cross_ped_per_h.tolist() == [0.]
    assert result.pred_peak_along_ped_per_h.tolist() == [12.]
    assert result.comparison_status.tolist() == ["source_unavailable"]
    assert result.existing_irap_cross_recoded_ped_per_h.isna().all()
    json.dumps(metadata, allow_nan=False)


def test_index_reuses_identical_source_and_rebuilds_changed_source(index, tmp_path):
    old_time = index.path.stat().st_mtime_ns
    again = AusRAPIndex(index.source, tmp_path / "cache")
    assert again.path == index.path and again.path.stat().st_mtime_ns == old_time
    changed = make_index(tmp_path, [["R1", 1, 1.2, "S", 3, 1, 1]])
    assert changed.sha256 != index.sha256 and changed.path != index.path
    with pytest.raises(ContractError, match="different source"):
        changed.record(f"ausrap:{index.sha256}:2")


@pytest.mark.parametrize("bad", [-1, float("inf"), "invalid", True])
def test_invalid_optional_observation_rejected_before_location_lookup(bad):
    with pytest.raises(ContractError, match="finite and non-negative"):
        resolve_locations(pd.DataFrame([site(obs_peak_cross_ped_per_h=bad)]))


def test_missing_source_headers_fail_clearly(tmp_path):
    source = tmp_path / "bad.xlsx"
    pd.DataFrame({"wrong": [1]}).to_excel(source, index=False)
    with pytest.raises(ContractError, match="required road/flow headers"):
        AusRAPIndex(source, tmp_path / "cache")
