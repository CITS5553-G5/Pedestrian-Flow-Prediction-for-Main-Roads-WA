"""ABS-only default execution and rejection of historical runtime configurations."""

import json
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import pandas as pd

from pedflow.context.config import load_context_config
from pedflow.context.contracts import FeatureResult
from pedflow.context.io import write_context_outputs
from pedflow.context.sources import abs_meshblock_sa1
from pedflow.context.workflow import build_context_features
from pedflow.exceptions import ConfigurationError

ROOT = Path(__file__).resolve().parents[2]


class AbsPredictionWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.config = load_context_config(ROOT / "configs/context_features_v1.json")
        self.sites = pd.DataFrame(
            {
                "site_id": ["site-2", "site-1"],
                "latitude": [-31.95, -32.05],
                "longitude": [115.86, 115.76],
                "coordinate_crs": ["EPSG:4326", "EPSG:4326"],
            }
        )
        self.extract = Mock(
            return_value=FeatureResult(
                source_name="abs_meshblock_sa1",
                source_version="ABS fixture",
                features=pd.DataFrame(
                    {
                        "site_id": ["site-2", "site-1"],
                        "abs_mb_category_2021": ["Residential", "Commercial"],
                        "abs_match_status": ["matched", "matched"],
                    }
                ),
                metadata={"fixture": True},
            )
        )
        definition = replace(abs_meshblock_sa1.DEFINITION, extractor=self.extract)
        replacement = patch.object(abs_meshblock_sa1, "DEFINITION", definition)
        replacement.start()
        self.addCleanup(replacement.stop)

    def test_default_workflow_outputs_only_abs_and_preserves_provenance(self):
        result = build_context_features(self.sites, self.config, ROOT)
        self.extract.assert_called_once()
        self.assertEqual(result.feature_set_version, "context_abs_v1")
        self.assertEqual(result.features.site_id.tolist(), ["site-2", "site-1"])
        self.assertTrue(
            all(name == "site_id" or name.startswith("abs_") for name in result.features.columns)
        )
        self.assertEqual(
            [source.source_name for source in result.source_results], ["abs_meshblock_sa1"]
        )
        with TemporaryDirectory() as directory:
            config = replace(self.config, output_formats=("xlsx",))
            written = write_context_outputs(Path(directory), config, result)
            table = pd.read_excel(
                written["xlsx"], sheet_name="Context_Features", dtype={"site_id": "string"}
            )
            pd.testing.assert_frame_equal(table, result.features)
            manifest = json.loads(written["manifest"].read_text())
            self.assertEqual(manifest["feature_set_version"], "context_abs_v1")
            self.assertEqual(
                [source["name"] for source in manifest["sources"]], ["abs_meshblock_sa1"]
            )

    def test_research_config_is_rejected_before_any_source_runs(self):
        config = load_context_config(ROOT / "configs/research/context_features_v1.json")
        with self.assertRaisesRegex(ConfigurationError, "ABS only"):
            build_context_features(self.sites, config, ROOT)
        self.extract.assert_not_called()

    def test_explicit_empty_registry_does_not_enable_default_sources(self):
        with self.assertRaisesRegex(ConfigurationError, "not available"):
            build_context_features(self.sites, self.config, ROOT, registry={})
        self.extract.assert_not_called()


if __name__ == "__main__":
    unittest.main()
