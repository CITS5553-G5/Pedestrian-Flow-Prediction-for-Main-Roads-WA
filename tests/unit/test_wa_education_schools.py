"""Unit tests for the WA education source adapter."""

import hashlib
import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd

from pedflow.context.contracts import SourceConfig
from pedflow.context.sources.wa_education_schools import (
    acquire_or_load_source,
    build_features,
    prepare_source,
    validate_source_specific,
)
from pedflow.exceptions import SourceExecutionError


def school_source_fixture() -> pd.DataFrame:
    """Return a small fixed source table with two WA schools and one external record."""

    return pd.DataFrame(
        {
            "Code": ["100", "200", "300"],
            "SchoolName": ["Alpha Primary", "Beta College", "Island School"],
            "PhysicalTown": ["ALPHA", "BETA", "ISLAND"],
            "Latitude": [-32.0000, -32.1000, -12.1880],
            "Longitude": [115.8000, 115.9000, 96.8288],
            "EducationRegionName": ["METRO", "REGIONAL", "EXTERNAL"],
            "Sector": ["GOVERNMENT", "NON-GOVERNMENT", "GOVERNMENT"],
            "RemCode": [0, 1, 4],
            "RemoteArea": [
                "Major Cities of Australia",
                "Inner Regional Australia",
                "Very Remote Australia",
            ],
            "LowYear": ["KIN", "PKG", "KIN"],
            "HighYear": ["Y06", "Y12", "Y12"],
            "TotalPrimaryK_6": [200, 100, 20],
            "TotalSecondary7_12": [0, 150, 10],
            "TotalSchool": [200, 250, 0],
        }
    )


class FakeHttpResponse:
    """Minimal context-managed HTTP response used by the download test."""

    def __init__(self, content: bytes) -> None:
        self.stream = BytesIO(content)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self, size: int = -1) -> bytes:
        return self.stream.read(size)


class WaEducationSourceTests(unittest.TestCase):
    def test_prepare_source_validates_and_filters_configured_bounds(self) -> None:
        prepared = prepare_source(
            school_source_fixture(),
            SourceConfig(name="wa_education_schools", enabled=False),
        )

        self.assertEqual(prepared.source_row_count, 3)
        self.assertEqual(prepared.schools["school_code"].tolist(), ["100", "200"])
        self.assertEqual(prepared.outside_scope_schools["school_code"].tolist(), ["300"])
        self.assertEqual(prepared.zero_total_school_count, 1)

    def test_build_features_accepts_arbitrary_sites_and_preserves_order(self) -> None:
        config = SourceConfig(name="wa_education_schools", enabled=False)
        prepared = prepare_source(school_source_fixture(), config)
        sites = pd.DataFrame(
            {
                "site_id": ["site-beta", "site-alpha"],
                "latitude": [-32.1000, -32.0000],
                "longitude": [115.9000, 115.8000],
                "coordinate_crs": ["EPSG:4326", "EPSG:4326"],
            }
        )

        features = build_features(sites, prepared, config)
        validate_source_specific(features, prepared, config)

        self.assertEqual(features["site_id"].tolist(), ["site-beta", "site-alpha"])
        self.assertEqual(
            features["education_nearest_school_code"].tolist(),
            ["200", "100"],
        )
        self.assertTrue(
            features["education_nearest_active_school_distance_m"].le(0.001).all()
        )
        self.assertTrue(features["education_data_status"].eq("matched").all())

    def test_unknown_source_category_fails_closed(self) -> None:
        raw_source = school_source_fixture()
        raw_source.loc[0, "Sector"] = "UNREVIEWED SECTOR"

        with self.assertRaisesRegex(SourceExecutionError, "Unexpected WA education sectors"):
            prepare_source(
                raw_source,
                SourceConfig(name="wa_education_schools", enabled=False),
            )

    def test_existing_snapshot_must_match_configured_hash(self) -> None:
        with TemporaryDirectory() as directory:
            project_root = Path(directory)
            source_path = project_root / "schools.xlsx"
            source_path.write_bytes(b"fixed local snapshot")
            config = SourceConfig(
                name="wa_education_schools",
                enabled=False,
                options={"source_path": "schools.xlsx", "source_sha256": "0" * 64},
            )

            with self.assertRaisesRegex(SourceExecutionError, "hash mismatch"):
                acquire_or_load_source(config, project_root)

    def test_missing_snapshot_uses_mocked_http_and_atomic_replacement(self) -> None:
        content = b"fixed mocked workbook bytes"
        expected_hash = hashlib.sha256(content).hexdigest()
        with TemporaryDirectory() as directory:
            project_root = Path(directory)
            config = SourceConfig(
                name="wa_education_schools",
                enabled=False,
                options={
                    "source_path": "cache/schools.xlsx",
                    "source_url": "https://example.invalid/schools.xlsx",
                    "source_sha256": expected_hash,
                    "minimum_source_bytes": 1,
                },
            )

            with patch(
                "pedflow.context.sources.wa_education_schools.urlopen",
                return_value=FakeHttpResponse(content),
            ) as mocked_urlopen:
                snapshot = acquire_or_load_source(config, project_root)

            self.assertEqual(snapshot.retrieval_method, "downloaded_snapshot")
            self.assertEqual(snapshot.sha256, expected_hash)
            self.assertEqual(snapshot.path.read_bytes(), content)
            self.assertEqual(mocked_urlopen.call_count, 1)
            self.assertEqual(list(snapshot.path.parent.glob(".*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
