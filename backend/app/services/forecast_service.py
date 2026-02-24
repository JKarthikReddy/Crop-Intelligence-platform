"""OpenWeather 5-day forecast intelligence service.

Pure service layer:
- No FastAPI imports
- No database logic
- Reads API key via settings (never os.getenv)
- Async HTTP via httpx
- Structured, normalized output only
"""

from typing import Any

import httpx
from loguru import logger

from app.core.config import get_settings

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/forecast"

_TIMEOUT = 15.0

# ── Risk thresholds ──────────────────────────────────────────────
_HEAT_THRESHOLD_C = 35.0
_HEAVY_RAIN_THRESHOLD_MM = 50.0


class ForecastServiceError(Exception):
    """Raised when the OpenWeather API call or response parsing fails."""


async def fetch_forecast(
    lat: float,
    lon: float,
    *,
    timeout: float = _TIMEOUT,
) -> dict[str, Any]:
    """Fetch 5-day / 3-hour forecast and return summarized intelligence.

    Queries the OpenWeather forecast endpoint for the given coordinate,
    aggregates temperature and rainfall across all 3-hour intervals, and
    derives advisory flags for heat risk and heavy rain.

    Args:
        lat: Latitude in decimal degrees (WGS84).
        lon: Longitude in decimal degrees (WGS84).
        timeout: HTTP request timeout in seconds.

    Returns:
        Normalized dict with keys:
            - ``avg_temp_next_5d``: Mean temperature across intervals (C)
            - ``max_temp_next_5d``: Maximum temperature across intervals (C)
            - ``total_rain_next_5d``: Cumulative rainfall (mm)
            - ``heat_risk_flag``: True if max temp exceeds 35 C
            - ``heavy_rain_flag``: True if total rainfall exceeds 50 mm

    Raises:
        ForecastServiceError: On HTTP failure or malformed response.
    """
    settings = get_settings()

    params: dict[str, Any] = {
        "lat": lat,
        "lon": lon,
        "appid": settings.OPENWEATHER_API_KEY,
        "units": "metric",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(OPENWEATHER_URL, params=params)
    except httpx.TimeoutException as exc:
        logger.error("OpenWeather timeout for ({}, {}): {}", lat, lon, exc)
        raise ForecastServiceError(f"OpenWeather API timed out after {timeout}s") from exc
    except httpx.HTTPError as exc:
        logger.error("OpenWeather HTTP error for ({}, {}): {}", lat, lon, exc)
        raise ForecastServiceError(f"OpenWeather API request failed: {exc}") from exc

    if response.status_code != 200:
        logger.error(
            "OpenWeather returned {} for ({}, {})",
            response.status_code,
            lat,
            lon,
        )
        raise ForecastServiceError(f"OpenWeather API returned HTTP {response.status_code}")

    return _parse_forecast_response(response.json())


def _parse_forecast_response(data: dict[str, Any]) -> dict[str, Any]:
    """Parse raw OpenWeather 5-day JSON into structured advisory output.

    Iterates over every 3-hour interval in ``data["list"]``, extracts
    temperature and rainfall, then computes aggregates and risk flags.

    Args:
        data: Raw JSON dict from the OpenWeather forecast endpoint.

    Returns:
        Structured forecast intelligence dict.

    Raises:
        ForecastServiceError: If the response structure is unexpected.
    """
    try:
        temps: list[float] = []
        rainfall: list[float] = []

        for item in data["list"]:
            temps.append(item["main"]["temp"])
            rainfall.append(item.get("rain", {}).get("3h", 0.0))

        if not temps:
            raise ForecastServiceError("No forecast intervals found.")

        avg_temp = round(sum(temps) / len(temps), 2)
        max_temp = round(max(temps), 2)
        total_rain = round(sum(rainfall), 2)

        return {
            "avg_temp_next_5d": avg_temp,
            "max_temp_next_5d": max_temp,
            "total_rain_next_5d": total_rain,
            "heat_risk_flag": max_temp > _HEAT_THRESHOLD_C,
            "heavy_rain_flag": total_rain > _HEAVY_RAIN_THRESHOLD_MM,
        }
    except ForecastServiceError:
        raise
    except Exception as exc:
        logger.error("Failed to parse OpenWeather response: {}", exc)
        raise ForecastServiceError("Unexpected OpenWeather response format.") from exc
