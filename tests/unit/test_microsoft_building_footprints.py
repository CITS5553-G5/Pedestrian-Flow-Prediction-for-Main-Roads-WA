"""Source-specific unit tests for Microsoft building-footprint promotion."""

import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

from pedflow.context.contracts import SourceConfig
from pedflow.context.sources.microsoft_building_footprints import (
    FEATURE_COLUMNS,
    build_features,
    build_site_contexts,
    download_file,
    load_release_index,
    quadkeys_for_bounds,
    settings_from_config,
    validate_source_specific,
)
from pedflow.exceptions import SourceExecutionError


def fixture_sites() -> pd.DataFrame:
    """Return a deliberately small site table; adapters must not assume 49 rows."""

    return pd.DataFrame(
        {
            "site_id": ["fixture-1"],
            "latitude": [-31.9505],
            "longitude": [115.8605],
            "coordinate_crs": ["EPSG:4326"],
        }
    )


def footprint_at_site(context, half_width_m: float = 10.0):
    centre = context.buffer_metric.centroid
    footprint_metric = gpd.GeoSeries(
        [
            box(
                centre.x - half_width_m,
                centre.y - half_width_m,
                centre.x + half_width_m,
                centre.y + half_width_m,
            )
        ],
        crs=context.metric_crs,
    )
    return footprint_metric.to_crs("EPSG:4326").iloc[0]


def tile_fixture(context, geometries) -> dict[str, gpd.GeoDataFrame]:
    frames = {
        key: gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
        for key in context.quadkeys
    }
    first_key = min(context.quadkeys)
    frames[first_key] = gpd.GeoDataFrame(geometry=list(geometries), crs="EPSG:4326")
    return frames


class FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int):
        del chunk_size
        yield self.payload[:3]
        yield self.payload[3:]


class FakeSession:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.calls: list[tuple[str, bool, tuple[float, float]]] = []

    def get(self, url: str, stream: bool, timeout: tuple[float, float]):
        self.calls.append((url, stream, timeout))
        return FakeResponse(self.payload)


class MicrosoftBuildingFootprintsUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sites = fixture_sites()
        self.contexts = build_site_contexts(self.sites, 500.0, 9)
        self.context = self.contexts["fixture-1"]

    def test_duplicate_geometry_is_counted_once_and_area_is_not_doubled(self) -> None:
        footprint = footprint_at_site(self.context)
        tiles = tile_fixture(self.context, [footprint, footprint])

        built = build_features(self.sites, self.contexts, tiles)

        self.assertEqual(built.duplicate_geometry_count, 1)
        self.assertEqual(int(built.features.loc[0, "ms_building_count_500m"]), 1)
        self.assertAlmostEqual(
            built.features.loc[0, "ms_building_footprint_area_m2_500m"],
            400.0,
            delta=0.01,
        )
        validate_source_specific(built.features, self.sites, 500.0)

    def test_empty_source_tile_returns_completed_zero_features(self) -> None:
        built = build_features(self.sites, self.contexts, tile_fixture(self.context, []))

        self.assertEqual(
            built.features.loc[0, "ms_building_data_status"],
            "complete_no_detected_buildings",
        )
        self.assertEqual(int(built.features.loc[0, "ms_building_count_500m"]), 0)
        self.assertEqual(built.features.loc[0, "ms_building_coverage_ratio_500m"], 0.0)

    def test_missing_required_partition_is_not_converted_to_zero(self) -> None:
        built = build_features(self.sites, self.contexts, {})

        self.assertEqual(
            built.features.loc[0, "ms_building_data_status"],
            "source_tile_not_listed",
        )
        self.assertTrue(pd.isna(built.features.loc[0, "ms_building_count_500m"]))

    def test_quadkey_selection_includes_both_sides_of_tile_boundary(self) -> None:
        zoom = 9
        longitude_boundary = (420 / (1 << zoom)) * 360 - 180
        keys = quadkeys_for_bounds(
            (longitude_boundary - 0.001, -32.0, longitude_boundary + 0.001, -31.99),
            zoom,
        )

        self.assertGreaterEqual(len(keys), 2)

    def test_download_uses_atomic_file_and_mocked_http(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "fixture.bin"
            session = FakeSession(b"fixture-payload")

            downloaded = download_file(
                "https://example.test/fixture.bin",
                destination,
                session=session,
                timeout=(1.0, 2.0),
            )

            self.assertTrue(downloaded)
            self.assertEqual(destination.read_bytes(), b"fixture-payload")
            self.assertFalse(destination.with_name(".fixture.bin.part").exists())
            self.assertEqual(len(session.calls), 1)

    def test_release_index_rejects_duplicate_quadkeys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dataset-links.csv"
            pd.DataFrame(
                {
                    "Location": ["Australia", "Australia"],
                    "QuadKey": ["123", "123"],
                    "Url": ["https://example.test/a", "https://example.test/b"],
                    "Size": ["1KB", "1KB"],
                    "UploadDate": ["2026-07-24", "2026-07-24"],
                }
            ).to_csv(path, index=False)

            with self.assertRaisesRegex(SourceExecutionError, "duplicate QuadKey"):
                load_release_index(path, "Australia")

    def test_settings_are_configurable_and_do_not_require_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = settings_from_config(
                SourceConfig(
                    name="microsoft_building_footprints",
                    enabled=False,
                    options={
                        "source_release": "fixture-v1",
                        "buffer_radius_m": 250,
                        "quadkey_zoom": 8,
                        "allow_download": False,
                    },
                ),
                Path(directory),
            )

        self.assertEqual(settings.release, "fixture-v1")
        self.assertEqual(settings.buffer_radius_m, 250.0)
        self.assertEqual(settings.quadkey_zoom, 8)
        self.assertFalse(settings.allow_download)
        self.assertEqual(next(iter(FEATURE_COLUMNS)), "site_id")


if __name__ == "__main__":
    unittest.main()
