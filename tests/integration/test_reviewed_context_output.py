"""Contract test for the single reviewed context-feature table."""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_DATASET = PROJECT_ROOT / "data" / "processed" / "model_dataset.xlsx"
REVIEWED_CONTEXT = (
    PROJECT_ROOT
    / "06_outputs"
    / "02_feature_extraction"
    / "02_00_haoqi_context_features.xlsx"
)


def test_reviewed_context_table_matches_training_sites() -> None:
    """The reviewed table is complete, keyed one-to-one and target-free."""

    model_sites = pd.read_excel(
        MODEL_DATASET,
        sheet_name="Model_Data",
        usecols=["site_id"],
        dtype={"site_id": "string"},
    )
    context = pd.read_excel(
        REVIEWED_CONTEXT,
        sheet_name="Context_Features",
        dtype={"site_id": "string"},
    )

    assert context["site_id"].is_unique
    assert context["site_id"].tolist() == model_sites["site_id"].tolist()
    assert len(context.columns) == 21
    for prefix in ("abs_", "pta_", "health_", "education_", "ms_"):
        assert any(column.startswith(prefix) for column in context.columns)
    assert not any(column.startswith("google_") for column in context.columns)
    assert not any("obs_peak_" in column for column in context.columns)
