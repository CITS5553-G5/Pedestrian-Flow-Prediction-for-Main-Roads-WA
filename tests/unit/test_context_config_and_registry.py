"""Configuration and source-list tests."""

import json
import tempfile
import unittest
from pathlib import Path

from pedflow.context.config import load_context_config, select_sources
from pedflow.context.sources.registry import build_default_registry
from pedflow.exceptions import ConfigurationError


class ContextConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = {
            "feature_set_version": "test_v1",
            "input": {"path": "sites.xlsx", "sheet": "Model_Data"},
            "output": {
                "directory": "outputs",
                "stem": "context_test",
                "formats": ["xlsx"],
            },
            "sources": {
                "abs_meshblock_sa1": {"enabled": False, "options": {}},
                "pta_stops": {"enabled": True, "options": {"buffer_radius_m": 500}},
            },
        }

    def write_config(self, payload: dict) -> Path:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        path = Path(temporary_directory.name) / "config.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_loads_source_order_and_enabled_state(self) -> None:
        config = load_context_config(self.write_config(self.payload))

        self.assertEqual(config.feature_set_version, "test_v1")
        self.assertEqual(
            tuple(source.name for source in config.sources),
            ("abs_meshblock_sa1", "pta_stops"),
        )
        self.assertEqual(
            tuple(source.name for source in config.enabled_sources()),
            ("pta_stops",),
        )

    def test_source_override_is_explicit(self) -> None:
        config = load_context_config(self.write_config(self.payload))
        selected = select_sources(config, ["abs_meshblock_sa1"])

        self.assertEqual(
            tuple(source.name for source in selected.enabled_sources()),
            ("abs_meshblock_sa1",),
        )

    def test_unknown_source_override_fails(self) -> None:
        config = load_context_config(self.write_config(self.payload))

        with self.assertRaises(ConfigurationError):
            select_sources(config, ["not_registered_in_config"])

    def test_research_config_keeps_google_experiment_disabled(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        config = load_context_config(
            project_root / "configs" / "research" / "context_features_v1.json"
        )
        google = next(
            source for source in config.sources if source.name == "google_places_aggregate_poi"
        )

        self.assertFalse(google.enabled)
        self.assertEqual(
            google.options["governance_status"],
            "excluded_from_modeling_by_uwa_project_decision",
        )
        self.assertEqual(
            set(google.options),
            {"governance_status", "decision_archive"},
        )

    def test_formal_config_contains_only_abs(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        config = load_context_config(project_root / "configs" / "context_features_v1.json")
        self.assertEqual(config.feature_set_version, "context_abs_v1")
        self.assertEqual(tuple(source.name for source in config.sources), ("abs_meshblock_sa1",))
        self.assertEqual(config.enabled_sources(), config.sources)
        self.assertEqual(config.output_stem, "batch_abs_context_features")
        for source in ("pta_stops", "overture_places", "google_places_aggregate_poi"):
            with self.subTest(source=source), self.assertRaises(ConfigurationError):
                select_sources(config, [source])


class ContextRegistryTests(unittest.TestCase):
    def test_default_registry_has_unique_expected_sources(self) -> None:
        registry = build_default_registry()

        self.assertEqual(
            tuple(registry),
            ("abs_meshblock_sa1",),
        )
        self.assertEqual(registry["abs_meshblock_sa1"].column_prefixes, ("abs_",))


if __name__ == "__main__":
    unittest.main()
