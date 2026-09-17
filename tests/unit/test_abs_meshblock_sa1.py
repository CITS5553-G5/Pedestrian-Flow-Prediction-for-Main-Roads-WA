"""Unit tests for deterministic ABS Mesh Block/SA1 source logic."""

import json
import unittest

import pandas as pd

from pedflow.context.contracts import SourceConfig
from pedflow.context.sources.abs_meshblock_sa1 import (
    FEATURE_COLUMNS,
    MeshBlockCountSnapshot,
    build_features,
    prepare_source,
    query_meshblock_codes,
    validate_source_specific,
)
from pedflow.exceptions import SourceExecutionError


class FakeResponse:
    def __init__(self, payload, error=None):
        self.payload = payload
        self.error = error

    def raise_for_status(self):
        if self.error is not None:
            raise self.error

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        return next(self.responses)


class AbsMeshblockSa1Tests(unittest.TestCase):
    def setUp(self):
        self.config = SourceConfig(name="abs_meshblock_sa1", enabled=False, options={})
        self.sites = pd.DataFrame(
            {
                "site_id": ["site-1", "site-2"],
                "latitude": [-31.95, -32.05],
                "longitude": [115.86, 115.76],
                "coordinate_crs": ["EPSG:4326", "EPSG:4326"],
            }
        )
        self.raw_counts = pd.DataFrame(
            {
                "MB_CODE_2021": ["50000000001", "50000000002", "40000000001"],
                "MB_CATEGORY_NAME_2021": ["Residential", "Transport", "Residential"],
                "AREA_ALBERS_SQKM": [0.25, 0.5, 0.1],
                "Dwelling": [10, 0, 3],
                "Person": [20, 0, 6],
                "State": [5, 5, 4],
            }
        )

    def snapshot(self, frame=None):
        return MeshBlockCountSnapshot(
            frame=self.raw_counts if frame is None else frame,
            configured_path="fixture.xlsx",
            sha256="a" * 64,
            sheet_name="Table 5",
            header_row=6,
        )

    def test_prepare_source_filters_state_and_preserves_integer_counts(self):
        prepared = prepare_source(self.snapshot(), self.config)

        self.assertEqual(
            prepared["abs_mb_code_2021"].tolist(),
            ["50000000001", "50000000002"],
        )
        self.assertEqual(prepared["abs_mb_dwellings_2021"].tolist(), [10, 0])
        self.assertEqual(prepared["abs_mb_persons_usual_resident_2021"].tolist(), [20, 0])

    def test_prepare_source_rejects_duplicate_meshblock_codes(self):
        duplicate = pd.concat([self.raw_counts.iloc[[0]], self.raw_counts.iloc[[0]]])

        with self.assertRaisesRegex(SourceExecutionError, "duplicate"):
            prepare_source(self.snapshot(duplicate), self.config)

    def test_query_uses_expected_arcgis_parameters_and_retains_statuses(self):
        session = FakeSession(
            [
                FakeResponse(
                    {
                        "features": [
                            {
                                "attributes": {
                                    "mb_code_2021": "50000000001",
                                    "sa1_code_2021": "50100000001",
                                }
                            }
                        ]
                    }
                ),
                FakeResponse({"features": []}),
            ]
        )

        matches = query_meshblock_codes(self.sites, self.config, session=session)

        self.assertEqual(matches["abs_match_status"].tolist(), ["matched", "no_match"])
        self.assertEqual(matches.loc[0, "abs_mb_code_2021"], "50000000001")
        self.assertEqual(len(session.calls), 2)
        first_call = session.calls[0]
        self.assertEqual(first_call["params"]["outFields"], "mb_code_2021,sa1_code_2021")
        self.assertEqual(first_call["params"]["returnGeometry"], "false")
        geometry = json.loads(first_call["params"]["geometry"])
        self.assertEqual(geometry["spatialReference"], {"wkid": 4326})

    def test_query_converts_http_failure_to_safe_source_status(self):
        session = FakeSession(
            [FakeResponse({}, error=RuntimeError("token=do-not-copy raw server details"))]
        )

        match = query_meshblock_codes(self.sites.iloc[[0]], self.config, session=session).iloc[0]

        self.assertEqual(match["abs_match_status"], "request_failed")
        self.assertEqual(
            match["abs_error_message"],
            "RuntimeError: ABS Mesh Block request failed.",
        )
        self.assertNotIn("token", match["abs_error_message"])

    def test_build_features_calculates_densities_and_preserves_site_order(self):
        prepared = prepare_source(self.snapshot(), self.config)
        matches = pd.DataFrame(
            {
                "site_id": ["site-2", "site-1"],
                "abs_match_status": ["matched", "matched"],
                "abs_error_message": [pd.NA, pd.NA],
                "abs_mb_code_2021": ["50000000002", "50000000001"],
                "abs_sa1_code_2021": ["50100000002", "50100000001"],
            }
        )

        features = build_features(self.sites, matches, prepared)
        validate_source_specific(features, self.sites["site_id"])

        self.assertEqual(tuple(features.columns), FEATURE_COLUMNS)
        self.assertEqual(features["site_id"].tolist(), ["site-1", "site-2"])
        self.assertEqual(features["abs_mb_dwellings_per_sqkm_2021"].tolist(), [40.0, 0.0])
        self.assertEqual(features["abs_mb_persons_per_sqkm_2021"].tolist(), [80.0, 0.0])

    def test_build_features_marks_a_code_missing_from_local_counts(self):
        prepared = prepare_source(self.snapshot(), self.config)
        matches = pd.DataFrame(
            {
                "site_id": ["site-1", "site-2"],
                "abs_match_status": ["matched", "matched"],
                "abs_error_message": [pd.NA, pd.NA],
                "abs_mb_code_2021": ["50000000001", "59999999999"],
                "abs_sa1_code_2021": ["50100000001", "59999999999"],
            }
        )

        features = build_features(self.sites, matches, prepared)

        self.assertEqual(features.loc[1, "abs_match_status"], "matched_no_local_counts")
        self.assertTrue(pd.isna(features.loc[1, "abs_mb_area_sqkm_2021"]))


if __name__ == "__main__":
    unittest.main()
