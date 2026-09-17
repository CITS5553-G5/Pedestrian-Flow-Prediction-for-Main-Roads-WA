"""Contract tests that run in the supported project environment with pandas."""

import unittest

import pandas as pd

from pedflow.context.validation import (
    merge_source_features,
    validate_and_normalise_sites,
    validate_source_features,
)
from pedflow.exceptions import ContractError


class ContextValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sites = pd.DataFrame(
            {
                "site_id": ["site-1", "site-2"],
                "latitude": [-31.95, -32.05],
                "longitude": [115.86, 115.76],
                "coordinate_crs": ["EPSG:4326", "EPSG:4326"],
            }
        )

    def test_site_contract_normalises_types(self) -> None:
        checked = validate_and_normalise_sites(self.sites)

        self.assertEqual(checked["site_id"].tolist(), ["site-1", "site-2"])
        self.assertEqual(
            checked["coordinate_crs"].tolist(),
            ["EPSG:4326", "EPSG:4326"],
        )

    def test_duplicate_site_id_fails(self) -> None:
        self.sites.loc[1, "site_id"] = "site-1"

        with self.assertRaisesRegex(ContractError, "unique"):
            validate_and_normalise_sites(self.sites)

    def test_source_contract_requires_exact_coverage(self) -> None:
        features = pd.DataFrame({"site_id": ["site-1"], "pta_count": [2]})

        with self.assertRaisesRegex(ContractError, "coverage"):
            validate_source_features(
                "pta_stops",
                features,
                self.sites["site_id"],
                ("pta_",),
            )

    def test_source_contract_rejects_target_columns(self) -> None:
        features = pd.DataFrame(
            {
                "site_id": ["site-1", "site-2"],
                "pta_obs_peak_cross": [1.0, 2.0],
            }
        )

        with self.assertRaisesRegex(ContractError, "target-derived"):
            validate_source_features(
                "pta_stops",
                features,
                self.sites["site_id"],
                ("pta_",),
            )

    def test_merge_preserves_site_order(self) -> None:
        pta = pd.DataFrame(
            {"site_id": ["site-2", "site-1"], "pta_stop_count": [3, 1]}
        )
        health = pd.DataFrame(
            {
                "site_id": ["site-1", "site-2"],
                "health_distance_m": [100.0, 200.0],
            }
        )

        combined = merge_source_features(self.sites, [pta, health])

        self.assertEqual(combined["site_id"].tolist(), ["site-1", "site-2"])
        self.assertEqual(combined["pta_stop_count"].tolist(), [1, 3])

    def test_merge_rejects_overlapping_columns(self) -> None:
        first = pd.DataFrame(
            {"site_id": ["site-1", "site-2"], "pta_stop_count": [1, 3]}
        )
        second = pd.DataFrame(
            {"site_id": ["site-1", "site-2"], "pta_stop_count": [2, 4]}
        )

        with self.assertRaisesRegex(ContractError, "overlapping"):
            merge_source_features(self.sites, [first, second])


if __name__ == "__main__":
    unittest.main()
