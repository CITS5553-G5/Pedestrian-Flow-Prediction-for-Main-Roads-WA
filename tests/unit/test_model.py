"""Verify the portable release against saved R predict.lm outputs and input contracts."""

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from pedflow.exceptions import ConfigurationError, ContractError
from pedflow.modeling import PedestrianFlowModel, load_model, simplify_abs_categories
from pedflow.modeling.model import FEATURES

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "src/pedflow/modeling/releases/pedestrian_linear_v1.json"
REFERENCES = ROOT / "tests/fixtures/modeling/r_linear_reference.json"
OUTPUTS = ["pred_peak_cross_ped_per_h", "pred_peak_along_ped_per_h"]


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = json.loads(RELEASE.read_text())
        cls.reference = json.loads(REFERENCES.read_text())
        cls.cases = pd.DataFrame(cls.reference["cases"])
        cls.model = load_model()

    def setUp(self):
        self.input = pd.DataFrame(
            {
                "site_id": ["example"],
                "commercial_buildings": [2.0],
                "footpath_both_sides": [True],
                "abs_mb_category_simple": ["Commercial"],
            }
        )

    def test_all_r_reference_predictions(self):
        self.assertEqual(len(self.cases), 79)
        self.assertEqual((self.cases.case_kind == "training").sum(), 49)
        self.assertEqual(self.reference["model_version"], self.model.model_version)
        self.assertEqual(
            self.reference["source_bundle_md5"],
            self.release["provenance"]["source_bundle_md5"],
        )
        prediction = self.model.predict(self.cases, allow_fallback=True)
        np.testing.assert_allclose(prediction[OUTPUTS], self.cases[OUTPUTS], rtol=1e-13, atol=1e-12)
        self.assertEqual(prediction.site_id.tolist(), self.cases.site_id.tolist())
        self.assertTrue(prediction.loc[self.cases.case_kind == "fallback", "warnings"].ne("").all())

    def test_complete_r_references_need_no_fallback(self):
        cases = self.cases.loc[self.cases.case_kind != "fallback"]
        result = self.model.predict(cases)
        np.testing.assert_allclose(result[OUTPUTS], cases[OUTPUTS], rtol=1e-13, atol=1e-12)

    def test_release_source_identity_when_bundle_available(self):
        source = ROOT / (
            "06_outputs/03_model_development/03_yashika_model_comparison/"
            "03_pedestrian_flow_final_model_bundle.rds"
        )
        if not source.exists():
            self.skipTest("Research bundle is not required for standalone inference tests.")
        self.assertEqual(
            hashlib.md5(source.read_bytes()).hexdigest(),
            self.release["provenance"]["source_bundle_md5"],
        )

    def test_input_order_and_index_are_preserved_without_mutation(self):
        data = self.cases.iloc[[12, 1, 20]].copy()
        data.index = [9, 2, 9]
        before = data.copy(deep=True)
        result = self.model.predict(data)
        pd.testing.assert_frame_equal(data, before)
        self.assertEqual(result.index.tolist(), [9, 2, 9])
        self.assertEqual(result.site_id.tolist(), data.site_id.tolist())

    def test_three_features_are_sufficient_and_extra_targets_are_ignored(self):
        expected = self.model.predict(self.input)
        extended = self.input.assign(bus_stops=999, obs_peak_cross_ped_per_h=999999)
        pd.testing.assert_frame_equal(expected, self.model.predict(extended))

    def test_native_boolean_and_r_string_agree(self):
        for value in [True, False]:
            self.input["footpath_both_sides"] = value
            expected = self.model.predict(self.input)
            self.input["footpath_both_sides"] = str(value).upper()
            pd.testing.assert_frame_equal(expected, self.model.predict(self.input))

    def test_missing_values_rejected_by_default_and_fallback_is_visible(self):
        for feature in FEATURES:
            with self.subTest(feature=feature):
                data = self.input.copy().astype(object)
                data.loc[0, feature] = pd.NA
                with self.assertRaisesRegex(ContractError, "missing"):
                    self.model.predict(data)
                result = self.model.predict(data, allow_fallback=True)
                self.assertEqual(result.loc[0, "status"], "warning")
                self.assertIn(feature, result.loc[0, "warnings"])
                self.assertFalse(pd.isna(result.loc[0, feature]))

    def test_unknown_category_uses_r_mode_only_when_explicit(self):
        self.input["abs_mb_category_simple"] = "Industrial"
        with self.assertRaisesRegex(ContractError, "unknown"):
            self.model.predict(self.input)
        result = self.model.predict(self.input, allow_fallback=True)
        self.assertEqual(result.loc[0, "abs_mb_category_simple"], "Residential")
        self.assertIn("unknown category", result.loc[0, "warnings"])

    def test_raw_abs_mapping_preserves_missing_source(self):
        raw = pd.Series(["Residential", "Commercial", "Industrial", "Other", None, ""])
        result = simplify_abs_categories(raw)
        self.assertEqual(result.iloc[:4].tolist(), ["Residential", "Commercial", "Other", "Other"])
        self.assertTrue(result.iloc[4:].isna().all())
        with self.assertRaises(ContractError):
            simplify_abs_categories(pd.Series([5]))

    def test_invalid_feature_values_fail_even_with_fallback(self):
        for feature, values in {
            "commercial_buildings": [-1, float("inf"), "nan", "invalid", True, [2]],
            "footpath_both_sides": ["yes", "unknown", 1, 0],
            "abs_mb_category_simple": [42, ["Residential"]],
        }.items():
            for value in values:
                with self.subTest(feature=feature, value=value):
                    data = self.input.astype(object)
                    data.at[0, feature] = value
                    with self.assertRaises(ContractError):
                        self.model.predict(data, allow_fallback=True)

    def test_outside_training_range_is_flagged(self):
        self.input["commercial_buildings"] = 13
        result = self.model.predict(self.input)
        self.assertEqual(result.loc[0, "status"], "warning")
        self.assertIn("outside training range", result.loc[0, "warnings"])

    def test_overflow_is_an_actionable_error(self):
        self.input["commercial_buildings"] = 1e300
        with self.assertRaisesRegex(ContractError, "overflow"):
            self.model.predict(self.input)

    def test_schema_rejection(self):
        for column in ["site_id", *FEATURES]:
            with self.subTest(column=column), self.assertRaises(ContractError):
                self.model.predict(self.input.drop(columns=column), allow_fallback=True)
        for invalid in [
            [],
            self.input.iloc[:0],
            pd.concat([self.input, self.input]),
            self.input.assign(site_id=" "),
            self.input.assign(site_id=None),
            pd.concat([self.input, self.input[["site_id"]]], axis=1),
        ]:
            with self.subTest(invalid=type(invalid)), self.assertRaises(ContractError):
                self.model.predict(invalid)

    def test_release_round_trip_and_explicit_path(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "release.json"
            path.write_text(json.dumps(self.release))
            reloaded = load_model(path)
            pd.testing.assert_frame_equal(
                self.model.predict(self.input), reloaded.predict(self.input)
            )
            path.write_text("not json")
            with self.assertRaises(ConfigurationError):
                load_model(path)
            with self.assertRaises(ConfigurationError):
                load_model(Path(folder) / "missing.json")

    def test_incompatible_and_malformed_releases_fail(self):
        mutations = [
            ("schema_version", 2),
            ("schema_version", True),
            ("features", []),
            ("model_type", "random_forest"),
            ("models", {}),
            ("model_version", ""),
            ("inverse_transform", "exp(eta)"),
            ("numeric_preprocessing", None),
        ]
        for field, value in mutations:
            invalid = copy.deepcopy(self.release)
            invalid[field] = value
            with self.subTest(field=field), self.assertRaises(ConfigurationError):
                PedestrianFlowModel(invalid)
        for value in [float("nan"), float("inf"), "1.2", True]:
            invalid = copy.deepcopy(self.release)
            invalid["models"]["cross"]["intercept"] = value
            with self.assertRaises(ConfigurationError):
                PedestrianFlowModel(invalid)
        for invalid in [None, [], {}, {"schema_version": 1}]:
            with self.assertRaises(ConfigurationError):
                PedestrianFlowModel(invalid)

    def test_negative_predictions_are_clipped(self):
        release = copy.deepcopy(self.release)
        for model in release["models"].values():
            model["intercept"] = -100
        result = PedestrianFlowModel(release).predict(self.input)
        self.assertTrue((result[OUTPUTS] == 0).all().all())


if __name__ == "__main__":
    unittest.main()
