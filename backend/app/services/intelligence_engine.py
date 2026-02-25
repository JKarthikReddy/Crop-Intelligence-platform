"""Unified geospatial intelligence orchestrator.

Coordinates all data-source services in parallel to produce a single,
structured intelligence payload for any farm boundary.

Pure service layer:
- No FastAPI imports
- No database logic
- No environment access
- Uses asyncio.gather for concurrent execution
- Handles partial failures gracefully (return None sections)
- Fully testable
"""

import asyncio
from typing import Any

from loguru import logger

from app.services.cache_service import INTELLIGENCE_TTL, get_cache, make_cache_key, set_cache
from app.services.forecast_service import ForecastServiceError, fetch_forecast
from app.services.geometry_service import GeometryValidationError, extract_geometry_info
from app.services.satellite_service import SatelliteServiceError, fetch_ndvi
from app.services.soil_service import SoilServiceError, fetch_soil_data
from app.services.weather_service import WeatherServiceError, fetch_nasa_weather


class IntelligenceEngineError(Exception):
    """Raised when the orchestrator encounters an unrecoverable error."""


async def generate_intelligence(geojson: dict[str, Any]) -> dict[str, Any]:
    """Generate unified intelligence for a farm boundary.

    Accepts a GeoJSON Feature, extracts spatial metadata, then
    concurrently fetches soil, climate, forecast, and satellite data.
    Individual service failures are logged and returned as ``None``
    sections rather than crashing the entire response.

    Args:
        geojson: A GeoJSON Feature dict with a ``geometry`` key.

    Returns:
        Structured intelligence dict with keys:
            - ``location``: Centroid, bounds, and area
            - ``soil``: Soil chemistry (or None on failure)
            - ``climate``: 30-day historical weather (or None on failure)
            - ``forecast``: 5-day forecast advisory (or None on failure)
            - ``satellite``: NDVI vegetation health (or None on failure)

    Raises:
        IntelligenceEngineError: If geometry extraction itself fails
            (no point running downstream services).
    """
    # ── Geometry extraction (must succeed) ───────────────────────
    try:
        geom = extract_geometry_info(geojson)
    except GeometryValidationError as exc:
        raise IntelligenceEngineError(f"Geometry error: {exc}") from exc

    lat, lon = geom["centroid"]
    bounds = geom["bounds"]

    # ── Intelligence-level cache check ────────────────────────────
    cache_key = make_cache_key("intelligence", lat, lon)
    cached = await get_cache(cache_key)
    if cached is not None:
        logger.info("Intelligence cache HIT for {}", cache_key)
        return cached

    # ── Parallel data fetch with graceful degradation ────────────
    soil_result, climate_result, forecast_result, satellite_result = await asyncio.gather(
        fetch_soil_data(lat, lon),
        fetch_nasa_weather(lat, lon),
        fetch_forecast(lat, lon),
        fetch_ndvi(bounds),
        return_exceptions=True,
    )

    # ── Sanitize results (exceptions become None + log) ──────────
    soil = _sanitize_result(soil_result, "soil", SoilServiceError)
    climate = _sanitize_result(climate_result, "climate", WeatherServiceError)
    forecast = _sanitize_result(forecast_result, "forecast", ForecastServiceError)
    satellite = _sanitize_result(satellite_result, "satellite", SatelliteServiceError)

    payload = {
        "location": {
            "centroid": list(geom["centroid"]),
            "bounds": list(geom["bounds"]),
            "area_hectares": geom["area_hectares"],
        },
        "soil": soil,
        "climate": climate,
        "forecast": forecast,
        "satellite": satellite,
    }

    await set_cache(cache_key, payload, ttl=INTELLIGENCE_TTL)
    return payload


def _sanitize_result(
    result: Any,
    section_name: str,
    expected_error: type,
) -> dict[str, Any] | None:
    """Convert a gather result into a clean value or None on failure.

    If ``result`` is an exception, logs a warning and returns None so
    the overall intelligence payload degrades gracefully instead of
    crashing.

    Args:
        result: The value or exception from asyncio.gather.
        section_name: Human-readable label for logging.
        expected_error: The expected service-level error class.

    Returns:
        The original dict result, or None if an exception occurred.
    """
    if isinstance(result, Exception):
        if isinstance(result, expected_error):
            logger.warning("Intelligence engine: {} service failed: {}", section_name, result)
        else:
            logger.error("Intelligence engine: unexpected {} error: {}", section_name, result)
        return None
    return result
