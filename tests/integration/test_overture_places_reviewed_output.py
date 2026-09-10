"""Regression checks for the reviewed Overture Places feature workbook."""

from pathlib import Path

import pandas as pd
import pytest

from pedflow.context.contracts import ContextPipelineConfig, SourceConfig
from pedflow.context.sources import overture_places
from pedflow.context.validation import validate_and_normalise_sites
from pedflow.context.workflow import build_context_features

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_DATASET = PROJECT_ROOT / "data" / "processed" / "model_dataset.xlsx"
REVIEWED_OUTPUT = (
    PROJECT_ROOT
    / "06_outputs"
    / "02_feature_extraction"
    / "02_09_haoqi_overture_places_features.xlsx"
)
CACHE_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "external_raw"
    / "overture_places"
    / overture_places.DEFAULT_RELEASE
)


def _sites() -> pd.DataFrame:
    source = pd.read_excel(
        MODEL_DATASET,
        sheet_name="Model_Data",
        usecols=["site_id", "latitude", "longitude"],
        dtype={"site_id": "string"},
    )
    source["coordinate_crs"] = "EPSG:4326"
    return validate_and_normalise_sites(source)


def _reviewed() -> pd.DataFrame:
    return pd.read_excel(
        REVIEWED_OUTPUT,
        sheet_name="Overture_Places_Features",
        dtype={"site_id": "string", "overture_places_data_status": "string"},
    )


def test_reviewed_overture_workbook_matches_the_site_and_feature_contract() -> None:
    sites = _sites()
    reviewed = _reviewed()

    assert tuple(reviewed.columns) == overture_places.FEATURE_COLUMNS
    assert reviewed["site_id"].tolist() == sites["site_id"].tolist()
    assert reviewed["site_id"].is_unique
    overture_places.validate_source_specific(reviewed, sites)


def test_cache_backed_module_output_matches_the_reviewed_workbook_exactly() -> None:
    sites = _sites()
    settings = overture_places.SourceSettings(
        release=overture_places.DEFAULT_RELEASE,
        buffer_radius_m=500.0,
        cache_directory=CACHE_DIRECTORY,
        allow_download=False,
        connect_timeout_s=1,
        request_timeout_s=1,
        max_workers=4,
    )
    requests = overture_places.build_site_requests(sites, settings)
    if not all(request.cache_path.is_file() for request in requests):
        pytest.skip(
            "Local Overture cache is intentionally not versioned; run the notebook "
            "once to enable this cache-backed regression check."
        )

    acquired = overture_places.acquire_or_load_source(sites, settings)
    actual = overture_places.build_features(sites, acquired).features
    reviewed = _reviewed()

    pd.testing.assert_frame_equal(
        actual.reset_index(drop=True),
        reviewed.reset_index(drop=True),
        check_dtype=False,
        check_exact=True,
    )


def test_overture_source_runs_through_the_integrated_context_workflow() -> None:
    sites = _sites()
    settings = overture_places.SourceSettings(
        release=overture_places.DEFAULT_RELEASE,
        buffer_radius_m=500.0,
        cache_directory=CACHE_DIRECTORY,
        allow_download=False,
        connect_timeout_s=1,
        request_timeout_s=1,
        max_workers=4,
    )
    requests = overture_places.build_site_requests(sites, settings)
    if not all(request.cache_path.is_file() for request in requests):
        pytest.skip(
            "Local Overture cache is intentionally not versioned; run the notebook "
            "once to enable this integrated regression check."
        )

    config = ContextPipelineConfig(
        feature_set_version="overture-reviewed-2026-08-19.0",
        input_path="unused-by-in-memory-test.xlsx",
        input_sheet="Model_Data",
        output_directory="unused-by-in-memory-test",
        output_stem="unused-by-in-memory-test",
        output_formats=("xlsx",),
        sources=(
            SourceConfig(
                name="overture_places",
                enabled=True,
                options={
                    "release": overture_places.DEFAULT_RELEASE,
                    "buffer_radius_m": 500,
                    "cache_directory": "data/external_raw/overture_places/{release}",
                    "allow_download": False,
                    "max_workers": 4,
                },
            ),
        ),
    )
    result = build_context_features(sites, config, PROJECT_ROOT)

    assert len(result.source_results) == 1
    pd.testing.assert_frame_equal(
        result.features.reset_index(drop=True),
        _reviewed().reset_index(drop=True),
        check_dtype=False,
        check_exact=True,
    )
