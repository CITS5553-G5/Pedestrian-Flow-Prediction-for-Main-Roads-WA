"""Google imagery and Gemini adapters preserving the notebook's extraction recipe."""

from __future__ import annotations

import json
import math
import os
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from io import BytesIO

import requests
from PIL import Image
from pyproj import Transformer

from pedflow.exceptions import ConfigurationError
from pedflow.imagery.contracts import ExtractionError, ImageryConfig, load_prompt
from pedflow.imagery.requests import RequestGate, request_with_retry

TRANSIENT_CODES = {408, 429, 500, 502, 503, 504}


def sampling_points(latitude: float, longitude: float, offset_m: float) -> list[tuple]:
    """Preserve notebook EPSG:3857 offsets; these are not geodesic ground metres."""
    forward = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    backward = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    x, y = forward.transform(longitude, latitude)
    if not math.isfinite(x) or not math.isfinite(y):
        raise ExtractionError("unsupported_imagery_coordinate")
    points = [(latitude, longitude)]
    for dx, dy in ((0, offset_m), (0, -offset_m), (offset_m, 0), (-offset_m, 0)):
        lon, lat = backward.transform(x + dx, y + dy)
        points.append((lat, lon))
    return points


def validate_features(payload: dict) -> dict:
    """Accept a nullable integer count and nullable boolean; never coerce LLM guesses."""
    if not isinstance(payload, dict) or not {
        "commercial_buildings",
        "footpath_both_sides",
    }.issubset(payload):
        raise ExtractionError("invalid_feature_schema")
    count = payload["commercial_buildings"]
    flag = payload["footpath_both_sides"]
    if count is not None and (type(count) is not int or not 0 <= count <= 2**63 - 1):
        raise ExtractionError("invalid_commercial_buildings")
    if flag is not None and type(flag) is not bool:
        raise ExtractionError("invalid_footpath_both_sides")
    return {"commercial_buildings": count, "footpath_both_sides": flag}


def parse_features(text: str) -> dict:
    """Read fenced or plain JSON and reject ambiguous duplicate fields."""
    if not isinstance(text, str):
        raise ExtractionError("empty_llm_response")
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)

    def unique_object(pairs):
        """Duplicate JSON keys would otherwise silently replace an earlier feature."""
        result = {}
        for key, value in pairs:
            if key in result:
                raise ExtractionError("duplicate_feature_key")
            result[key] = value
        return result

    try:
        payload = json.loads(cleaned, object_pairs_hook=unique_object)
    except (ValueError, TypeError) as exc:
        raise ExtractionError("invalid_llm_json") from exc
    return validate_features(payload)


def _retry_after(value) -> float:
    """Convert either HTTP delay form into a finite, non-negative cooldown."""
    try:
        seconds = float(value)
    except (ValueError, TypeError):
        try:
            seconds = (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds()
        except (ValueError, TypeError, OverflowError):
            return 0
    return max(0, seconds) if math.isfinite(seconds) else 0


class GoogleGeminiExtractor:
    """Each site owns its clients and images; only thread-safe pacing is shared."""

    def __init__(self, config: ImageryConfig, *, maps_key=None, gemini_key=None):
        """Freeze the recipe and create shared per-provider request gates."""
        self.config = config
        # Freeze prompt and image parameters once for the entire concurrent run.
        self.prompt = load_prompt()
        self.recipe = config.extraction_identity()
        self._maps_key = maps_key or os.environ.get("GOOGLE_MAPS_API_KEY")
        self._gemini_key = gemini_key or os.environ.get("GEMINI_API_KEY")
        if not self._maps_key or not self._gemini_key:
            raise ConfigurationError(
                "Set GOOGLE_MAPS_API_KEY and GEMINI_API_KEY for imagery extraction."
            )
        self.maps_gate = RequestGate(config.maps_requests_per_minute)
        self.llm_gate = RequestGate(config.llm_requests_per_minute)

    def _get(self, session, endpoint, params):
        """Fetch and close one Maps response, retrying only transient failures."""

        def operation():
            """Perform one Maps attempt; the outer retry gate owns pacing and retries."""
            try:
                response = session.get(
                    f"https://maps.googleapis.com/maps/api/{endpoint}",
                    params={**params, "key": self._maps_key},
                    timeout=self.config.request_timeout_seconds,
                )
            except (requests.Timeout, requests.ConnectionError) as exc:
                raise ExtractionError("imagery_connection_failed", retryable=True) from exc
            except requests.RequestException as exc:
                raise ExtractionError("imagery_request_failed") from exc
            if response.status_code != 200:
                status = response.status_code
                retry_after = _retry_after(response.headers.get("Retry-After"))
                response.close()
                raise ExtractionError(
                    f"imagery_http_{status}",
                    retryable=status in TRANSIENT_CODES,
                    retry_after=retry_after,
                )
            if endpoint.endswith("metadata"):
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise ExtractionError("invalid_imagery_metadata") from exc
                finally:
                    response.close()
                if not isinstance(payload, dict):
                    raise ExtractionError("invalid_imagery_metadata")
                status = payload.get("status")
                if status in {"OVER_QUERY_LIMIT", "UNKNOWN_ERROR"}:
                    raise ExtractionError(f"imagery_{status.lower()}", retryable=True)
                if status not in {"OK", "ZERO_RESULTS", "NOT_FOUND"}:
                    raise ExtractionError("imagery_metadata_rejected")
                return payload
            try:
                with Image.open(BytesIO(response.content)) as image:
                    image.load()
                    return image.copy()
            except (OSError, ValueError) as exc:
                raise ExtractionError("invalid_imagery_image") from exc
            finally:
                response.close()

        return request_with_retry(operation, self.maps_gate, self.config.max_attempts)

    def _analyse(self, images):
        # Lazy import: unit tests and command help do not need credentials or a client.
        """Send one site image set through the pinned Gemini model and validate its reply."""
        import httpx
        from google import genai
        from google.genai import errors, types

        with genai.Client(
            api_key=self._gemini_key,
            http_options=types.HttpOptions(
                timeout=round(self.config.llm_timeout_seconds * 1000),
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        ) as client:

            def operation():
                """Perform one Gemini attempt; return only schema-validated model features."""
                try:
                    response = client.models.generate_content(
                        model=self.config.model, contents=[self.prompt, *images]
                    )
                except errors.APIError as exc:
                    code = exc.code
                    headers = getattr(exc.response, "headers", {})
                    raise ExtractionError(
                        f"llm_http_{code}",
                        retryable=code in TRANSIENT_CODES,
                        retry_after=_retry_after(headers.get("Retry-After")),
                    ) from exc
                except httpx.TransportError as exc:
                    raise ExtractionError("llm_connection_failed", retryable=True) from exc
                return parse_features(response.text)

            return request_with_retry(operation, self.llm_gate, self.config.max_attempts)

    def __call__(self, site: dict) -> tuple[dict, dict]:
        """Collect satellite then centre/N/S/E/W views and release every image afterwards."""
        images = []
        views = []
        warnings = []
        try:
            with requests.Session() as session:
                images.append(
                    self._get(
                        session,
                        "staticmap",
                        {
                            **self.recipe["satellite"],
                            "center": f"{site['latitude']},{site['longitude']}",
                            "maptype": "satellite",
                        },
                    )
                )
                for lat, lon in sampling_points(
                    site["latitude"], site["longitude"], self.config.sampling_offset_m
                ):
                    location = f"{lat},{lon}"
                    metadata = self._get(session, "streetview/metadata", {"location": location})
                    if metadata["status"] != "OK":
                        warnings.append("street_view_unavailable")
                        continue
                    image = self._get(
                        session,
                        "streetview",
                        {
                            **self.recipe["street_view"],
                            "location": location,
                            "return_error_code": "true",
                        },
                    )
                    images.append(image)
                    views.append(
                        {
                            "pano_id": metadata.get("pano_id"),
                            "image_date": metadata.get("date"),
                            "copyright": metadata.get("copyright"),
                        }
                    )
            if len(images) == 1:
                warnings.append("aerial_only")
            features = self._analyse(images)
            return features, {
                "image_count": len(images),
                "street_views": views,
                "warnings": sorted(set(warnings)),
                "source": "Google Maps satellite + Street View",
            }
        finally:
            for image in images:
                image.close()
