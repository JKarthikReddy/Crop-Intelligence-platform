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
from app.services.et0_service import build_water_model
from app.services.forecast_service import ForecastServiceError, fetch_forecast
from app.services.geometry_service import GeometryValidationError, extract_geometry_info
from app.services.ml_ensemble_service import ensemble_service
from app.services.satellite_service import SatelliteServiceError, fetch_ndvi, fetch_sar
from app.services.soil_service import SoilServiceError, fetch_soil_data
from app.services.weather_service import WeatherServiceError, fetch_nasa_weather


class IntelligenceEngineError(Exception):
    """Raised when the orchestrator encounters an unrecoverable error."""


async def generate_intelligence(geojson: dict[str, Any]) -> dict[str, Any]:
    """Generate unified intelligence for a farm boundary.

    Accepts a GeoJSON Feature, extracts spatial metadata, then
    concurrently fetches soil, climate, forecast, NDVI, and SAR data.
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
            - ``satellite``: Dict with ``ndvi`` and ``sar`` sub-keys
                (each None on individual failure)
            - ``water_model``: ET0 estimate and water stress risk
                (None if climate data unavailable)

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
    soil_result, climate_result, forecast_result, ndvi_result, sar_result = await asyncio.gather(
        fetch_soil_data(lat, lon),
        fetch_nasa_weather(lat, lon),
        fetch_forecast(lat, lon),
        fetch_ndvi(bounds),
        fetch_sar(bounds),
        return_exceptions=True,
    )

    # ── Sanitize results (exceptions become None + log) ──────────
    soil = _sanitize_result(soil_result, "soil", SoilServiceError)
    climate = _sanitize_result(climate_result, "climate", WeatherServiceError)
    forecast = _sanitize_result(forecast_result, "forecast", ForecastServiceError)
    ndvi = _sanitize_result(ndvi_result, "ndvi", SatelliteServiceError)
    sar = _sanitize_result(sar_result, "sar", SatelliteServiceError)

    # ── Derived models (pure computation, no API calls) ───────────
    water_model = build_water_model(climate)

    # ── ML yield forecast (ensemble: XGBoost + LSTM) ──────────────
    yield_forecast = _compute_yield_forecast(soil, climate, ndvi)

    payload = {
        "location": {
            "centroid": list(geom["centroid"]),
            "bounds": list(geom["bounds"]),
            "area_hectares": geom["area_hectares"],
        },
        "soil": soil,
        "climate": climate,
        "forecast": forecast,
        "satellite": {
            "ndvi": ndvi,
            "sar": sar,
        },
        "water_model": water_model,
        "yield_forecast": yield_forecast,
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


def _compute_yield_forecast(
    soil: dict[str, Any] | None,
    climate: dict[str, Any] | None,
    ndvi: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Build tabular features from intelligence data and run ensemble.

    Extracts the required feature values from the soil, climate, and
    NDVI service results, then calls the ensemble service for a
    yield prediction.  Returns ``None`` if insufficient data is
    available.

    Args:
        soil: Soil service result or None.
        climate: Climate service result or None.
        ndvi: NDVI service result or None.

    Returns:
        Ensemble prediction dict, or None on failure.
    """
    try:
        # Build tabular feature vector from available intelligence
        tabular = _extract_tabular_features(soil, climate, ndvi)
        if tabular is None:
            logger.warning("Yield forecast skipped — insufficient tabular data")
            return None

        # Weather sequence for LSTM (None if climate unavailable)
        weather_seq = _extract_weather_sequence(climate)

        result = ensemble_service.predict(
            tabular_features=tabular,
            weather_sequence=weather_seq,
        )
        return result
    except Exception as exc:
        logger.error("Yield forecast failed: {}", exc)
        return None


def _extract_tabular_features(
    soil: dict[str, Any] | None,
    climate: dict[str, Any] | None,
    ndvi: dict[str, Any] | None,
) -> dict[str, float] | None:
    """Extract tabular features from service results.

    Maps intelligence payload fields to the feature names expected
    by the XGBoost model.  Returns None if critical data (soil) is
    missing.

    Args:
        soil: Soil service result.
        climate: Climate service result.
        ndvi: NDVI service result.

    Returns:
        Dict of feature name → value, or None.
    """
    if soil is None:
        return None

    features = {
        "ph": soil.get("phh2o", 6.5),
        "clay_percent": soil.get("clay", 250),
        "organic_carbon": soil.get("soc", 50),
        "ndvi_mean": ndvi.get("ndvi_mean", 0.5) if ndvi else 0.5,
        "temp_avg_30d": 25.0,
        "rainfall_last_30d": 100.0,
        "historical_yield": 4.0,  # Default: mid-range assumption
        "target_yield": 0.0,  # Placeholder (prediction target)
    }

    # Override with actual climate data if available
    if climate is not None:
        features["temp_avg_30d"] = climate.get("temperature_avg", 25.0)
        features["rainfall_last_30d"] = climate.get("precipitation_sum", 100.0)

    return features


def _extract_weather_sequence(
    climate: dict[str, Any] | None,
) -> list[list[float]] | None:
    """Build a 12-month weather sequence for LSTM prediction.

    In production, this would pull from historical weather storage.
    For now, generates a synthetic 12-month sequence based on the
    current climate snapshot to demonstrate the LSTM pathway.

    Args:
        climate: Climate service result or None.

    Returns:
        List of 12 x [temperature, rainfall, radiation] or None.
    """
    if climate is None:
        return None

    temp = climate.get("temperature_avg", 25.0)
    rain = climate.get("precipitation_sum", 100.0) / 30.0  # daily → monthly approx
    rad = climate.get("solar_radiation_avg", 18.0)

    import math

    # Generate seasonal variation over 12 months
    sequence = []
    for month in range(12):
        seasonal = math.sin(2 * math.pi * (month - 3) / 12)
        sequence.append(
            [
                round(temp + 5 * seasonal, 1),
                round(max(0, rain * 30 + 50 * seasonal), 1),
                round(max(0, rad + 3 * seasonal), 1),
            ]
        )

    return sequence
