"""Excel and manifest integration tests for the source-independent output layer."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from pedflow.context.contracts import (
    ContextPipelineConfig,
    FeatureResult,
    SourceConfig,
    SourceDefinition,
)
from pedflow.context.io import read_batch_input, write_context_outputs
from pedflow.context.workflow import build_context_features


class ContextIoTests(unittest.TestCase):
    def test_reads_sites_and_writes_excel_with_manifest(self) -> None:
        with TemporaryDirectory() as directory:
            project_root = Path(directory)
            input_path = project_root / "data" / "batch_input.xlsx"
            input_path.parent.mkdir(parents=True)

            source_sites = pd.DataFrame(
                {
                    "site_id": ["site-1", "site-2"],
                    "latitude": [-31.95, -32.05],
                    "longitude": [115.86, 115.76],
                    "road_no": ["H001", "H002"],
                }
            )
            source_sites.to_excel(input_path, sheet_name="Batch_Input", index=False)

            config = ContextPipelineConfig(
                feature_set_version="test-v1",
                input_path="data/batch_input.xlsx",
                input_sheet="Batch_Input",
                output_directory="outputs",
                output_stem="context_test",
                output_formats=("xlsx",),
                sources=(SourceConfig(name="pta_stops", enabled=True),),
            )
            sites = read_batch_input(project_root, config)
            self.assertEqual(sites["coordinate_crs"].tolist(), ["EPSG:4326"] * 2)
            self.assertEqual(sites["road_no"].tolist(), ["H001", "H002"])

            def extract_pta(sites, source_config, root):
                features = pd.DataFrame(
                    {
                        "site_id": sites["site_id"],
                        "pta_active_stops_within_500m": [2, 4],
                    }
                )
                return FeatureResult(
                    source_name="pta_stops",
                    source_version="fixture-v1",
                    features=features,
                    metadata={"buffer_radius_m": 500},
                )

            definition = SourceDefinition(
                name="pta_stops",
                description="Test fixture",
                column_prefixes=("pta_",),
                extractor=extract_pta,
            )
            result = build_context_features(
                sites,
                config,
                project_root,
                registry={definition.name: definition},
            )

            written = write_context_outputs(project_root, config, result)

            self.assertEqual(set(written), {"xlsx", "manifest"})
            self.assertTrue(written["xlsx"].is_file())
            self.assertTrue(written["manifest"].is_file())

            roundtrip = pd.read_excel(
                written["xlsx"],
                sheet_name="Context_Features",
                dtype={"site_id": "string"},
            )
            self.assertEqual(roundtrip["site_id"].tolist(), ["site-1", "site-2"])
            self.assertEqual(
                roundtrip["pta_active_stops_within_500m"].tolist(),
                [2, 4],
            )

            manifest = json.loads(written["manifest"].read_text(encoding="utf-8"))
            self.assertEqual(manifest["feature_set_version"], "test-v1")
            self.assertEqual(manifest["row_count"], 2)
            self.assertEqual(manifest["sources"][0]["name"], "pta_stops")


if __name__ == "__main__":
    unittest.main()
