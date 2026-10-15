"""Pairing, provenance and category errors must not create flattering comparisons."""

import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from pedflow.evaluation.irap import (
    MODEL_LABEL, MODEL_PATH, PROTOCOL, REFERENCE_LABEL,
    build_comparison, flow_category, load_comparison,
)
from pedflow.exceptions import ContractError


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.model = pd.DataFrame([
            dict(site_id="A", road_no="R1", slk_km=1.0, source_location_id="R1-1",
                 obs_peak_cross_ped_per_h=0., obs_peak_along_ped_per_h=10.),
            dict(site_id="250341-01", road_no="R2", slk_km=2.0, source_location_id="R2-2",
                 obs_peak_cross_ped_per_h=10., obs_peak_along_ped_per_h=20.),
            dict(site_id="C", road_no="R3", slk_km=3.0, source_location_id=None,
                 obs_peak_cross_ped_per_h=1000., obs_peak_along_ped_per_h=1000.),
        ])
        self.oof = pd.DataFrame([
            dict(site_id=row.site_id, road_no=row.road_no, Model="Linear regression", Target=target,
                 actual=getattr(row, f"obs_peak_{direction}_ped_per_h"), predicted=pred)
            for row, cross, along in zip(self.model.itertuples(), [2., 12., 0.], [13., 100., 0.])
            for direction, target, pred in [("cross", "Cross-road", cross),
                                             ("along", "Along-road", along)]
        ])
        self.client = pd.DataFrame([
            dict(ID="R1-1", ROAD_NO="R1", SLK=1., Ped_Peak_Cross=0., Ped_Peak_Along=18.),
            dict(ID="R2-2", ROAD_NO="R2", SLK=2., Ped_Peak_Cross=30., Ped_Peak_Along=30.),
        ])
        self.audit = dict(protocol_version=PROTOCOL, sites=[
            dict(site_id="A", source_location_id="R1-1", available=True,
                 cross_eligible=True, along_eligible=True, cross_codes=[1], cways=["S"],
                 cross_band_mean=[0., 0.], along_band_mean=[7., 30.]),
            dict(site_id="250341-01", source_location_id="R2-2", available=True,
                 cross_eligible=True, along_eligible=False, cross_codes=[3, 4], cways=["L", "R"],
                 cross_band_mean=[16., 37.5], along_band_mean=[12., 50.]),
            dict(site_id="C", available=False, cross_eligible=False, along_eligible=False),
        ])

    def build(self):
        return build_comparison(self.model, self.oof, self.client, self.audit)

    def test_identical_samples_per_direction_keep_excluded_details(self):
        result = self.build()
        metrics = result.metrics.set_index(["direction", "method"])
        self.assertEqual(len(result.sites), 3)
        self.assertEqual(metrics.loc[("Cross-road", MODEL_LABEL), "n"], 2)
        self.assertEqual(metrics.loc[("Cross-road", REFERENCE_LABEL), "n"], 2)
        self.assertEqual(metrics.loc[("Along-road", MODEL_LABEL), "n"], 1)
        self.assertEqual(metrics.loc[("Along-road", REFERENCE_LABEL), "n"], 1)
        self.assertEqual(metrics.loc[("Cross-road", MODEL_LABEL), "mae"], 2)
        self.assertEqual(metrics.loc[("Cross-road", REFERENCE_LABEL), "mae"], 10)
        self.assertAlmostEqual(metrics.loc[("Cross-road", REFERENCE_LABEL), "rmse"], math.sqrt(200))
        self.assertEqual(metrics.loc[("Along-road", MODEL_LABEL), "mae"], 3)
        self.assertEqual(metrics.loc[("Along-road", REFERENCE_LABEL), "mae"], 8)
        self.assertEqual(result.sites.iloc[1].pred_peak_along_ped_per_h, 100)
        self.assertIn("along_coverage_unconfirmed", result.sites.iloc[1].comparison_notes)

    def test_keyed_join_survives_reordered_sources_and_preserves_inputs(self):
        before = self.model.copy(deep=True)
        expected = self.build()
        self.oof = self.oof.iloc[::-1]
        self.client = self.client.iloc[::-1]
        self.audit["sites"].reverse()
        actual = self.build()
        pd.testing.assert_frame_equal(expected.sites, actual.sites)
        pd.testing.assert_frame_equal(self.model, before)

    def test_zero_missing_and_mixed_category_are_distinct(self):
        result = self.build().sites.set_index("site_id")
        self.assertEqual(result.loc["A", "existing_irap_cross_recoded_ped_per_h"], 0)
        self.assertEqual(result.loc["A", "existing_ausrap_cross_category"], 1)
        self.assertTrue(pd.isna(result.loc["C", "existing_irap_cross_recoded_ped_per_h"]))
        self.assertTrue(pd.isna(result.loc["250341-01", "existing_ausrap_cross_category"]))
        self.assertIn("Mixed crossing categories: 3, 4", result.loc["250341-01", "comparison_notes"])
        self.assertEqual(result.loc["250341-01", "existing_ausrap_cross_band"], "16–37.5")

    def test_duplicate_oof_or_client_rows_fail(self):
        self.oof = pd.concat([self.oof, self.oof.iloc[[0]]])
        with self.assertRaisesRegex(ContractError, "unique"):
            self.build()
        self.setUp()
        self.client = pd.concat([self.client, self.client.iloc[[0]]])
        with self.assertRaisesRegex(ContractError, "unique"):
            self.build()

    def test_stale_actual_road_or_eligibility_fail(self):
        self.oof.loc[0, "actual"] = 1
        with self.assertRaisesRegex(ContractError, "corrected target"):
            self.build()
        self.setUp()
        self.oof.loc[0, "road_no"] = "WRONG"
        with self.assertRaisesRegex(ContractError, "road grouping"):
            self.build()
        self.setUp()
        self.audit["sites"][1]["along_eligible"] = True
        with self.assertRaisesRegex(ContractError, "eligibility"):
            self.build()

    def test_missing_oof_or_nonfinite_prediction_cannot_silently_reduce_sample(self):
        self.oof = self.oof.iloc[1:]
        with self.assertRaisesRegex(ContractError, "site sets"):
            self.build()
        self.setUp()
        self.oof.loc[0, "predicted"] = float("inf")
        with self.assertRaisesRegex(ContractError, "finite"):
            self.build()

    def test_continuous_category_boundaries(self):
        for value, expected in [(0, 1), (0.00001, 2), (5, 2), (5.2, 3), (25, 3),
                                (25.2, 4), (900, 10), (900.01, 11)]:
            self.assertEqual(flow_category(value), expected)
        for invalid in [None, pd.NA, "bad", -1, float("inf"), float("nan"), True]:
            self.assertIsNone(flow_category(invalid))

    def test_no_valid_pairs_produces_unavailable_not_zero_error(self):
        self.client[["Ped_Peak_Cross", "Ped_Peak_Along"]] = float("nan")
        for row in self.audit["sites"]:
            row.update(available=False, cross_eligible=False, along_eligible=False)
        result = self.build()
        self.assertTrue(result.metrics.n.eq(0).all())
        self.assertTrue(result.metrics.mae.isna().all())
        self.assertTrue(result.metrics.rmse.isna().all())

    def test_changed_source_is_rejected_before_reading_workbooks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / MODEL_PATH
            model.parent.mkdir(parents=True)
            model.write_bytes(b"changed source")
            audit = root / "audit.json"
            audit.write_text(json.dumps({"source_files": [
                {"path": MODEL_PATH, "sha256": hashlib.sha256(b"old source").hexdigest()}
            ]}))
            with self.assertRaisesRegex(ContractError, "repeat preflight"):
                load_comparison(root, audit)


if __name__ == "__main__":
    unittest.main()
