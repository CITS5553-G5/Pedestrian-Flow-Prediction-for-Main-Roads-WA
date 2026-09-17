"""Tests for the governance guard on the excluded Google POI experiment."""

from __future__ import annotations

import unittest
from pathlib import Path

from pedflow.context.contracts import SourceConfig
from pedflow.context.sources import google_places_aggregate_poi as google_poi
from pedflow.exceptions import SourceExecutionError


class GooglePlacesGovernanceGuardTests(unittest.TestCase):
    def test_extraction_is_blocked_before_credentials_or_network_are_needed(self) -> None:
        config = SourceConfig(
            name=google_poi.SOURCE_NAME,
            enabled=True,
            options={},
        )

        with self.assertRaisesRegex(SourceExecutionError, "excluded"):
            google_poi.extract(object(), config, Path("unused"))

    def test_definition_records_the_excluded_source_contract(self) -> None:
        self.assertFalse(google_poi.MODEL_USE_APPROVED)
        self.assertEqual(google_poi.DEFINITION.name, google_poi.SOURCE_NAME)
        self.assertEqual(tuple(google_poi.DEFINITION.column_prefixes), ("google_",))
        self.assertIn("governance guard", google_poi.DEFINITION.description)


if __name__ == "__main__":
    unittest.main()
