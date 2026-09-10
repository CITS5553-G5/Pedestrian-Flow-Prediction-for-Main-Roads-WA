"""Source-specific tests for the promoted PTA stop adapter."""

from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

import numpy as np
import pandas as pd

from pedflow.context.contracts import SourceConfig
from pedflow.context.sources.pta_stops import (
    APPROVED_FEATURE_COLUMNS,
    acquire_or_load_source,
    build_features,
    count_within_radius,
    download_arcgis_snapshot,
    extract,
    prepare_source,
)
from pedflow.exceptions import SourceExecutionError

FIXTURE_PATH = (
    Path(__file__).parents[1] / "fixtures" / "context" / "pta_stops_small.geojson"
)


def load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


class PTAStopsPreparationTests(unittest.TestCase):
    def test_preparation_removes_exact_duplicate_and_excludes_planned_stop(self) -> None:
        prepared = prepare_source(load_fixture())

        self.assertEqual(len(prepared.all_stops), 4)
        self.assertEqual(prepared.exact_duplicate_count, 1)
        self.assertEqual(len(prepared.active_stops), 2)
        self.assertEqual(prepared.status_counts, {"Active": 3, "Planned": 1})
        self.assertEqual(prepared.active_stops["stopid"].tolist(), ["1001", "1002"])

    def test_conflicting_rows_for_one_stop_id_fail(self) -> None:
        payload = load_fixture()
        conflicting = deepcopy(payload["features"][1])
        conflicting["properties"]["stopid"] = 1001
        payload["features"].append(conflicting)

        with self.assertRaisesRegex(SourceExecutionError, "conflicting source rows"):
            prepare_source(payload)

    def test_radius_boundary_is_inclusive(self) -> None:
        distances = np.array([499.999, 500.0, 500.001, np.nan])

        self.assertEqual(count_within_radius(distances, 500.0), 2)


class PTAStopsFeatureTests(unittest.TestCase):
    def test_build_features_handles_arbitrary_site_count_and_source_statuses(self) -> None:
        sites = pd.DataFrame(
            {
                "site_id": ["at-stop", "far-away", "outside-wa"],
                "latitude": [-31.95, -31.95, 0.0],
                "longitude": [115.86, 116.10, 0.0],
                "coordinate_crs": ["EPSG:4326", "EPSG:4326", "EPSG:4326"],
            }
        )

        features = build_features(sites, prepare_source(load_fixture()))

        self.assertEqual(tuple(features.columns), APPROVED_FEATURE_COLUMNS)
        self.assertEqual(features["site_id"].tolist(), sites["site_id"].tolist())
        self.assertEqual(
            features["pta_data_status"].tolist(),
            ["matched", "valid_no_stop_within_500m", "invalid_coordinate"],
        )
        self.assertEqual(features.loc[0, "pta_active_stops_within_500m"], 1)
        self.assertEqual(features.loc[0, "pta_nearest_stop_id"], "1001")
        self.assertGreater(features.loc[1, "pta_nearest_active_stop_distance_m"], 500)
        self.assertTrue(pd.isna(features.loc[2, "pta_nearest_stop_id"]))


class PTAStopsAcquisitionTests(unittest.TestCase):
    def test_download_uses_count_verified_paging_with_mocked_http(self) -> None:
        records = []
        for index in range(3):
            feature = deepcopy(load_fixture()["features"][0])
            feature["properties"]["gid"] = index + 1
            feature["properties"]["stopid"] = 2000 + index
            feature["geometry"] = {"x": 115.86 + index * 0.001, "y": -31.95}
            records.append(
                {
                    "attributes": feature["properties"],
                    "geometry": feature["geometry"],
                }
            )

        responses = [
            {"name": "PTA-001 fixture", "maxRecordCount": 2},
            {"count": 3},
            {"features": records[:2]},
            {"features": records[2:]},
        ]
        session = Mock()
        session.get.side_effect = [self._response(payload) for payload in responses]

        metadata, feature_collection = download_arcgis_snapshot(
            session, layer_url="https://example.test/MapServer/14", timeout_seconds=5
        )

        self.assertEqual(metadata["name"], "PTA-001 fixture")
        self.assertEqual(len(feature_collection["features"]), 3)
        self.assertEqual(session.get.call_count, 4)
        offsets = [
            call.kwargs["params"].get("resultOffset")
            for call in session.get.call_args_list[2:]
        ]
        self.assertEqual(offsets, [0, 2])

    def test_cached_extract_returns_safe_provenance_and_warning(self) -> None:
        with TemporaryDirectory() as directory:
            project_root = Path(directory)
            snapshot_directory = (
                project_root / "data" / "external_raw" / "pta_stops" / "2026-09-02"
            )
            snapshot_directory.mkdir(parents=True)
            (snapshot_directory / "pta_stops.geojson").write_text(
                json.dumps(load_fixture()), encoding="utf-8"
            )
            (snapshot_directory / "pta_layer_metadata.json").write_text(
                json.dumps({"name": "PTA-001 fixture", "maxRecordCount": 2000}),
                encoding="utf-8",
            )
            sites = pd.DataFrame(
                {
                    "site_id": ["fixture-site"],
                    "latitude": [-31.95],
                    "longitude": [115.86],
                    "coordinate_crs": ["EPSG:4326"],
                }
            )
            config = SourceConfig(
                name="pta_stops",
                enabled=True,
                options={"snapshot_date": "2026-09-02", "allow_download": False},
            )

            result = extract(sites, config, project_root)

        self.assertEqual(result.source_name, "pta_stops")
        self.assertTrue(result.source_version.startswith("PTA-001-2026-09-02-"))
        self.assertEqual(result.metadata["retrieval_method"], "cached")
        self.assertEqual(result.metadata["buffer_radius_m"], 500.0)
        self.assertEqual(len(result.warnings), 1)
        self.assertNotIn("token", json.dumps(result.metadata).lower())
        self.assertNotIn("password", json.dumps(result.metadata).lower())

    def test_incomplete_cache_fails_without_network_request(self) -> None:
        with TemporaryDirectory() as directory:
            project_root = Path(directory)
            snapshot_directory = (
                project_root / "data" / "external_raw" / "pta_stops" / "2026-09-02"
            )
            snapshot_directory.mkdir(parents=True)
            (snapshot_directory / "pta_stops.geojson").write_text(
                json.dumps(load_fixture()), encoding="utf-8"
            )
            config = SourceConfig(
                name="pta_stops",
                enabled=True,
                options={"snapshot_date": "2026-09-02", "allow_download": False},
            )

            with self.assertRaisesRegex(SourceExecutionError, "incomplete"):
                acquire_or_load_source(config, project_root)

    def test_layer_url_cannot_embed_credentials_or_query_tokens(self) -> None:
        with TemporaryDirectory() as directory:
            project_root = Path(directory)
            config = SourceConfig(
                name="pta_stops",
                enabled=True,
                options={
                    "snapshot_date": "2026-09-02",
                    "layer_url": "https://example.test/MapServer/14?token=secret",
                },
            )
            sites = pd.DataFrame(
                {
                    "site_id": ["fixture-site"],
                    "latitude": [-31.95],
                    "longitude": [115.86],
                    "coordinate_crs": ["EPSG:4326"],
                }
            )

            with self.assertRaisesRegex(SourceExecutionError, "credential-free"):
                extract(sites, config, project_root)

    @staticmethod
    def _response(payload: dict) -> Mock:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = payload
        return response


if __name__ == "__main__":
    unittest.main()
