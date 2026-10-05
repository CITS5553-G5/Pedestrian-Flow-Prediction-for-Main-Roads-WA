"""Offline tests of notebook recipe, API error handling and shared pacing."""

import json
import threading
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from PIL import Image
from pyproj import Transformer

from pedflow.exceptions import ConfigurationError, ContractError
from pedflow.imagery import ImageryConfig, build_imagery_features, load_imagery_config
from pedflow.imagery.contracts import ExtractionError, load_prompt
from pedflow.imagery.providers import GoogleGeminiExtractor, parse_features, sampling_points
from pedflow.imagery.requests import RequestGate, request_with_retry


def sites(count=3):
    return pd.DataFrame(
        {
            "site_id": [f"site-{i}" for i in range(count)],
            "latitude": [-32.0] * count,
            "longitude": [116.0] * count,
            "coordinate_crs": ["EPSG:4326"] * count,
        }
    )


def extractor(site):
    return {
        "commercial_buildings": int(site["site_id"].split("-")[-1]),
        "footpath_both_sides": False,
    }, {"image_count": 2, "warnings": []}


def test_100_sites_are_bounded_to_fifty_workers_and_keep_identity():
    lock = threading.Lock()
    barrier = threading.Barrier(50, timeout=5)
    active = peak = 0
    seen = []

    def slow(site):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
            seen.append(site["site_id"])
        try:
            barrier.wait()
            return extractor(site)
        finally:
            with lock:
                active -= 1

    source = sites(100)
    result = build_imagery_features(source, ImageryConfig(), extractor=slow)
    assert peak == 50
    assert len(seen) == len(set(seen)) == 100
    assert result.features.site_id.tolist() == source.site_id.tolist()
    assert result.features.commercial_buildings.tolist() == list(range(100))
    assert result.features.imagery_status.eq("complete").all()


def test_sequential_and_parallel_results_match():
    one = build_imagery_features(sites(), ImageryConfig(max_workers=1), extractor=extractor)
    ten = build_imagery_features(sites(), ImageryConfig(max_workers=10), extractor=extractor)
    pd.testing.assert_frame_equal(
        one.features.drop(columns="processed_at_utc"), ten.features.drop(columns="processed_at_utc")
    )


def test_failure_and_unknown_features_never_become_zero():
    def mixed(site):
        if site["site_id"] == "site-0":
            raise RuntimeError("secret-key-in-URL")
        if site["site_id"] == "site-1":
            return {"commercial_buildings": None, "footpath_both_sides": None}, {}
        return {"commercial_buildings": 0, "footpath_both_sides": False}, {"image_count": 1}

    result = build_imagery_features(sites(), ImageryConfig(), extractor=mixed).features
    assert result.imagery_status.tolist() == ["failed", "needs_review", "complete"]
    assert result.commercial_buildings.iloc[:2].isna().all()
    assert result.loc[2, "commercial_buildings"] == 0
    assert not result.loc[2, "footpath_both_sides"]
    assert "secret" not in result.to_json()


def test_invalid_sites_fail_before_any_provider_call():
    provider = MagicMock()
    for frame in [
        sites(0),
        pd.concat([sites(), sites()]),
        sites().assign(coordinate_crs=None),
        sites().drop(columns="latitude"),
        sites().assign(latitude=100),
    ]:
        with pytest.raises(ContractError):
            build_imagery_features(frame, ImageryConfig(), extractor=provider)
    provider.assert_not_called()


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_workers", 0),
        ("max_workers", True),
        ("max_workers", 65),
        ("llm_requests_per_minute", 0),
        ("maps_requests_per_minute", False),
        ("maps_requests_per_minute", -1),
        ("maps_requests_per_minute", float("inf")),
        ("llm_requests_per_minute", "unlimited"),
        ("llm_requests_per_minute", float("nan")),
        ("max_attempts", -1),
        ("model", "auto"),
        ("sampling_offset_m", float("nan")),
        ("request_timeout_seconds", "60"),
    ],
)
def test_invalid_configuration(field, value):
    with pytest.raises(ConfigurationError):
        ImageryConfig(**{field: value})


def test_config_load_and_prompt_identity():
    root = Path(__file__).resolve().parents[2]
    config = load_imagery_config(root / "configs/prediction/imagery_v1.json")
    assert config.max_workers == 50
    assert ImageryConfig().max_workers == 50
    assert config.maps_requests_per_minute is None
    assert config.llm_requests_per_minute is None
    assert ImageryConfig().maps_requests_per_minute is None
    assert ImageryConfig().llm_requests_per_minute is None
    assert config.extraction_identity()["prompt_sha256"] == (
        "9c7a96a11250e0367227e7b1138f610fdfe05e6f2cba61fc4f087e84cb68d9c2"
    )
    assert '"parking_areas"' in load_prompt()  # Preserve the original full prompt.
    assert config.extraction_identity() == replace(config, max_workers=2).extraction_identity()
    assert (
        config.extraction_identity()
        == replace(
            config, maps_requests_per_minute=120, llm_requests_per_minute=30
        ).extraction_identity()
    )
    assert (
        config.extraction_identity() != replace(config, model="another-model").extraction_identity()
    )


def test_sampling_matches_original_notebook_offsets():
    lat, lon = -34.238746412, 116.14949095
    points = sampling_points(lat, lon, 50)
    forward = Transformer.from_crs(4326, 3857, always_xy=True)
    backward = Transformer.from_crs(3857, 4326, always_xy=True)
    x, y = forward.transform(lon, lat)
    expected = [(lat, lon)]
    for dx, dy in [(0, 50), (0, -50), (50, 0), (-50, 0)]:
        new_lon, new_lat = backward.transform(x + dx, y + dy)
        expected.append((new_lat, new_lon))
    assert points == expected


@pytest.mark.parametrize(
    "text",
    [
        "{}",
        '{"commercial_buildings":true,"footpath_both_sides":false}',
        '{"commercial_buildings":1.5,"footpath_both_sides":false}',
        '{"commercial_buildings":-1,"footpath_both_sides":false}',
        '{"commercial_buildings":1,"footpath_both_sides":"false"}',
        '{"commercial_buildings":1,"commercial_buildings":2,"footpath_both_sides":false}',
        "[]",
        "not JSON",
        None,
    ],
)
def test_rejects_malformed_llm_outputs(text):
    with pytest.raises(ExtractionError):
        parse_features(text)


def test_json_fences_and_null_are_supported():
    assert parse_features(
        '```json\n{"commercial_buildings":null,"footpath_both_sides":false}\n```'
    ) == {
        "commercial_buildings": None,
        "footpath_both_sides": False,
    }


def test_shared_gate_pacing_and_cooldown():
    now = [0.0]
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    gate = RequestGate(30, clock=lambda: now[0], sleep=sleep)
    gate.acquire()
    gate.acquire()
    assert sleeps == [2.0]
    gate.defer(10)
    gate.acquire()
    assert now[0] == 12


def test_unpaced_gate_does_not_sleep_between_requests_but_obeys_retry_after():
    now = [0.0]
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    gate = RequestGate(None, clock=lambda: now[0], sleep=sleep)
    for _ in range(1081):
        gate.acquire()
    assert sleeps == []  # The previous run's request volume adds no local delay.
    operation = MagicMock(side_effect=[ExtractionError("429", retryable=True, retry_after=9), 42])
    assert request_with_retry(operation, gate, 4) == 42
    assert sleeps == [9]
    gate.acquire()
    gate.acquire()
    assert sleeps == [9]  # Normal traffic immediately resumes without spacing.


def test_unpaced_gate_allows_overlapping_requests():
    from concurrent.futures import ThreadPoolExecutor

    sleeper = MagicMock(side_effect=AssertionError("Unexpected local pacing"))
    gate = RequestGate(None, clock=lambda: 0.0, sleep=sleeper)
    barrier = threading.Barrier(10, timeout=5)

    def request(_):
        gate.acquire()
        barrier.wait()  # All ten requests must start before any can finish.
        return True

    with ThreadPoolExecutor(max_workers=10) as pool:
        assert all(pool.map(request, range(10)))
    sleeper.assert_not_called()


def test_retry_is_bounded_and_respects_provider_delay():
    gate = MagicMock()
    operation = MagicMock(side_effect=[ExtractionError("429", retryable=True, retry_after=9), 42])
    assert request_with_retry(operation, gate, 4) == 42
    gate.defer.assert_called_once_with(9)
    operation = MagicMock(side_effect=ExtractionError("503", retryable=True))
    with pytest.raises(ExtractionError):
        request_with_retry(operation, gate, 3)
    assert operation.call_count == 3
    operation = MagicMock(side_effect=ExtractionError("403"))
    with pytest.raises(ExtractionError):
        request_with_retry(operation, gate, 4)
    assert operation.call_count == 1


def test_missing_credentials_fail_before_network():
    with patch.dict("os.environ", {}, clear=True), pytest.raises(ConfigurationError):
        GoogleGeminiExtractor(ImageryConfig())


def png_bytes():
    buffer = BytesIO()
    Image.new("RGB", (2, 2), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_aerial_only_is_flagged_and_original_prompt_uses_one_site():
    provider = GoogleGeminiExtractor(
        ImageryConfig(), maps_key="maps-test", gemini_key="gemini-test"
    )
    provider.maps_gate = MagicMock()
    image_response = MagicMock(status_code=200, content=png_bytes())
    metadata_response = MagicMock(status_code=200)
    metadata_response.json.return_value = {"status": "ZERO_RESULTS"}
    session = MagicMock()
    session.get.side_effect = [image_response] + [metadata_response] * 5
    with patch("requests.Session") as factory, patch.object(provider, "_analyse") as analyse:
        factory.return_value.__enter__.return_value = session
        analyse.return_value = {"commercial_buildings": 0, "footpath_both_sides": None}
        _, metadata = provider(sites(1).iloc[0].to_dict())
    assert session.get.call_count == 6
    assert metadata["image_count"] == 1
    assert "aerial_only" in metadata["warnings"]
    assert len(analyse.call_args.args[0]) == 1


def test_maps_throttling_and_metadata_throttling_retry():
    provider = GoogleGeminiExtractor(
        ImageryConfig(), maps_key="maps-test", gemini_key="gemini-test"
    )
    provider.maps_gate = MagicMock()
    response = MagicMock(status_code=429, headers={"Retry-After": "7"})
    limit = MagicMock(status_code=200)
    limit.json.return_value = {"status": "OVER_QUERY_LIMIT"}
    success = MagicMock(status_code=200)
    success.json.return_value = {"status": "ZERO_RESULTS"}
    session = MagicMock()
    session.get.side_effect = [response, limit, success]
    assert provider._get(session, "streetview/metadata", {})["status"] == "ZERO_RESULTS"
    assert session.get.call_count == 3
    assert provider.maps_gate.defer.call_args_list[0].args == (7,)


def test_gemini_sdk_uses_frozen_model_timeout_and_no_nested_retry():
    from google.genai import errors

    provider = GoogleGeminiExtractor(
        ImageryConfig(), maps_key="maps-test", gemini_key="gemini-test"
    )
    provider.llm_gate = MagicMock()
    response = SimpleNamespace(
        text=json.dumps({"commercial_buildings": 2, "footpath_both_sides": True})
    )
    error = errors.APIError(
        429,
        {"error": {"message": "do not expose"}},
        response=SimpleNamespace(headers={"Retry-After": "4"}),
    )
    with patch("google.genai.Client") as factory:
        client = factory.return_value.__enter__.return_value
        client.models.generate_content.side_effect = [error, response]
        assert provider._analyse(["image-for-one-site"])["commercial_buildings"] == 2
        options = factory.call_args.kwargs["http_options"]
        assert options.timeout == 120000
        assert options.retry_options.attempts == 1
        assert client.models.generate_content.call_count == 2
        assert client.models.generate_content.call_args.kwargs == {
            "model": "gemini-3.7-flash",
            "contents": [load_prompt(), "image-for-one-site"],
        }
    provider.llm_gate.defer.assert_called_once_with(4)
