"""Unit tests for deterministic Overture Places logic and cache-backed acquisition."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import geopandas as gpd
import pandas as pd

from pedflow.context.contracts import SourceConfig
from pedflow.context.sources import overture_places

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "context" / "overture_places_small.geojson"


class OverturePlacesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sites = pd.DataFrame(
            {
                "site_id": pd.Series(["site-a", "site-b"], dtype="string"),
                "latitude": [-32.0, -33.0],
                "longitude": [115.0, 116.0],
                "coordinate_crs": ["EPSG:4326", "EPSG:4326"],
            }
        )
        self.fixture = gpd.read_file(FIXTURE_PATH)

    def settings(self, directory: Path) -> overture_places.SourceSettings:
        return overture_places.SourceSettings(
            release="fixture-v1",
            buffer_radius_m=500.0,
            cache_directory=directory,
            allow_download=True,
            connect_timeout_s=1,
            request_timeout_s=1,
            max_workers=2,
        )

    def test_geodesic_bbox_encloses_a_500_m_radius(self) -> None:
        west, south, east, north = overture_places.geodesic_query_bbox(
            -32.0, 115.0, 500.0
        )

        self.assertLess(west, 115.0)
        self.assertGreater(east, 115.0)
        self.assertLess(south, -32.0)
        self.assertGreater(north, -32.0)

    def test_deterministic_features_use_distance_taxonomy_and_status(self) -> None:
        with TemporaryDirectory() as directory:
            settings = self.settings(Path(directory))
            requests = overture_places.build_site_requests(self.sites, settings)
            acquired = overture_places.AcquiredSource(
                sites={
                    request.site_id: overture_places.AcquiredSitePlaces(
                        request=request,
                        places=self.fixture.copy(),
                        cache_hit=True,
                        sha256="fixture",
                    )
                    for request in requests
                },
                cache_hits=2,
                downloads=0,
                cache_set_sha256="fixture-set",
            )

            built = overture_places.build_features(self.sites, acquired)
            overture_places.validate_source_specific(built.features, self.sites)

        first = built.features.iloc[0]
        self.assertEqual(first["overture_food_drink_count_500m"], 1)
        self.assertEqual(
            first["overture_grocery_convenience_pharmacy_count_500m"], 1
        )
        self.assertTrue(first["overture_shopping_mall_present_500m"])
        self.assertEqual(first["overture_other_shopping_count_500m"], 1)
        self.assertEqual(built.features.iloc[1]["overture_places_data_status"], "complete_no_eligible_places")
        self.assertEqual(built.excluded_closed_count, 1)
        self.assertEqual(built.unknown_operating_status_count, 1)

    def test_mocked_download_is_cached_and_reused(self) -> None:
        with TemporaryDirectory() as directory:
            settings = self.settings(Path(directory))
            calls: list[tuple[float, float, float, float]] = []

            def query(bbox, source_settings):
                self.assertEqual(source_settings.release, "fixture-v1")
                calls.append(bbox)
                return self.fixture.copy()

            first = overture_places.acquire_or_load_source(
                self.sites, settings, query=query
            )
            second = overture_places.acquire_or_load_source(
                self.sites,
                settings,
                query=lambda bbox, source_settings: self.fail(
                    "cache hit must not call the external query"
                ),
            )

        self.assertEqual(len(calls), 2)
        self.assertEqual(first.downloads, 2)
        self.assertEqual(first.cache_hits, 0)
        self.assertEqual(second.downloads, 0)
        self.assertEqual(second.cache_hits, 2)
        self.assertEqual(first.cache_set_sha256, second.cache_set_sha256)

    def test_empty_site_batch_does_not_start_a_worker_pool(self) -> None:
        with TemporaryDirectory() as directory:
            acquired = overture_places.acquire_or_load_source(
                self.sites.iloc[0:0],
                self.settings(Path(directory)),
                query=lambda bbox, settings: self.fail("empty batch must not query"),
            )

        self.assertEqual(acquired.sites, {})
        self.assertEqual(acquired.downloads, 0)
        self.assertEqual(acquired.cache_hits, 0)

    def test_config_requires_the_approved_500_m_contract(self) -> None:
        config = SourceConfig(
            name=overture_places.SOURCE_NAME,
            enabled=True,
            options={"buffer_radius_m": 250},
        )

        with self.assertRaisesRegex(Exception, "500 m"):
            overture_places.settings_from_config(config, PROJECT_ROOT)


if __name__ == "__main__":
    unittest.main()
