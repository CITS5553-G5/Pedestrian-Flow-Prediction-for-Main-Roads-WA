"""Unit tests for deterministic WA Health source logic and controlled I/O."""

import copy
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from pedflow.context.contracts import SourceConfig
from pedflow.context.sources import wa_health_establishments as source
from pedflow.exceptions import SourceExecutionError

FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "fixtures"
    / "context"
    / "wa_health_establishments_fixture.geojson"
)


class FakeResponse:
    def __init__(self, payload):
        self.encoded = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.encoded


class FakeOpener:
    def __init__(self, payloads):
        self.payloads = iter(payloads)
        self.calls = []

    def __call__(self, request, timeout):
        self.calls.append((request.full_url, timeout))
        return FakeResponse(next(self.payloads))


class WaHealthEstablishmentTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        self.config = SourceConfig(
            name=source.SOURCE_NAME,
            enabled=False,
            options={"allow_download": False},
        )
        self.sites = pd.DataFrame(
            {
                "site_id": ["fixture-a", "fixture-b"],
                "latitude": [-31.95, -32.05],
                "longitude": [115.86, 115.76],
                "coordinate_crs": ["EPSG:4326", "EPSG:4326"],
            }
        )

    def test_prepare_source_validates_domains_and_filters_closed_records(self):
        prepared = source.prepare_source(self.payload, self.config)

        self.assertEqual(prepared.source_record_count, 3)
        self.assertEqual(prepared.eligible_record_count, 2)
        self.assertEqual(prepared.eligible_records["estab_id"].tolist(), ["100", "200"])
        self.assertEqual(prepared.maximum_coordinate_difference_deg, 0.0)

    def test_prepare_source_rejects_unapproved_category(self):
        payload = copy.deepcopy(self.payload)
        payload["features"][0]["properties"]["category"] = "Unapproved Facility"

        with self.assertRaisesRegex(SourceExecutionError, "unexpected category"):
            source.prepare_source(payload, self.config)

    def test_build_features_ignores_closed_record_and_accepts_two_sites(self):
        prepared = source.prepare_source(self.payload, self.config)
        features = source.build_features(self.sites, prepared, self.config)
        source.validate_source_specific(features, self.sites, prepared, self.config)

        self.assertEqual(tuple(features.columns), source.FEATURE_COLUMNS)
        self.assertEqual(features["site_id"].tolist(), ["fixture-a", "fixture-b"])
        self.assertEqual(
            features["health_nearest_establishment_id"].tolist(), ["100", "200"]
        )
        self.assertEqual(
            features["health_nearest_establishment_category"].tolist(),
            ["Acute Hospital", "Nursing Post"],
        )
        self.assertEqual(
            features["health_nearest_establishment_distance_m"].tolist(), [0.0, 0.0]
        )
        self.assertTrue(features["health_data_status"].eq("matched").all())

    def test_controlled_retrieval_is_mocked_cached_atomically_then_reused(self):
        opener = FakeOpener([{"type": "Feature Layer"}, self.payload])
        with TemporaryDirectory() as directory:
            project_root = Path(directory)
            config = SourceConfig(
                name=source.SOURCE_NAME,
                enabled=False,
                options={
                    "snapshot_path": "fixtures/health.geojson",
                    "snapshot_date": "2099-01-01",
                    "allow_download": True,
                },
            )
            acquired = source.acquire_or_load_source(config, project_root, opener=opener)
            snapshot_path = project_root / "fixtures" / "health.geojson"
            self.assertTrue(snapshot_path.is_file())
            self.assertEqual(len(opener.calls), 2)
            self.assertIn("controlled ArcGIS", acquired.retrieval_method)

            cached = source.acquire_or_load_source(
                config,
                project_root,
                opener=lambda *_args, **_kwargs: self.fail("cache should avoid HTTP"),
            )
            self.assertEqual(cached.sha256, acquired.sha256)
            self.assertEqual(cached.retrieval_method, "cached dated GeoJSON snapshot")

    def test_extract_returns_safe_feature_result_without_enabling_source(self):
        with TemporaryDirectory() as directory:
            project_root = Path(directory)
            snapshot_path = project_root / "fixtures" / "health.geojson"
            snapshot_path.parent.mkdir(parents=True)
            snapshot_path.write_text(json.dumps(self.payload), encoding="utf-8")
            config = SourceConfig(
                name=source.SOURCE_NAME,
                enabled=False,
                options={
                    "snapshot_path": "fixtures/health.geojson",
                    "allow_download": False,
                },
            )
            result = source.extract(self.sites, config, project_root)

        self.assertEqual(result.source_name, source.SOURCE_NAME)
        self.assertEqual(len(result.features), 2)
        self.assertIn(source.DATASET_ID, result.source_version)
        serialised_metadata = json.dumps(result.metadata).lower()
        self.assertNotIn("token", serialised_metadata)
        self.assertNotIn("api_key", serialised_metadata)
        self.assertTrue(result.warnings)
        self.assertEqual(source.DEFINITION.name, "wa_health_establishments")

    def test_layer_url_cannot_embed_credentials_or_query_tokens(self):
        with TemporaryDirectory() as directory:
            config = SourceConfig(
                name=source.SOURCE_NAME,
                enabled=False,
                options={
                    "snapshot_path": "missing.geojson",
                    "layer_url": "https://example.test/layer?token=do-not-store",
                    "allow_download": True,
                },
            )
            with self.assertRaisesRegex(SourceExecutionError, "public HTTPS URL") as error:
                source.acquire_or_load_source(config, Path(directory))

        self.assertNotIn("do-not-store", str(error.exception))


if __name__ == "__main__":
    unittest.main()
