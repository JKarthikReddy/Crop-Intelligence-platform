"""NASA POWER agro-meteorological intelligence service.

Pure service layer:
- No FastAPI imports
- No database logic
- No environment access
- Async HTTP via httpx
- Structured, normalized output only
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from loguru import logger

NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

# Parameters requested from NASA POWER
_PARAMETERS = "T2M,ALLSKY_SFC_SW_DWN,WS2M"
_COMMUNITY = "AG"
_FORMAT = "JSON"
_LOOKBACK_DAYS = 30
_TIMEOUT = 20.0


class WeatherServiceError(Exception):
    """Raised when the NASA POWER API call or response parsing fails."""


async def fetch_nasa_weather(
    lat: float,
    lon: float,
    *,
    lookback_days: int = _LOOKBACK_DAYS,
    timeout: float = _TIMEOUT,
) -> dict[str, Any]:
    """Fetch recent daily weather data from NASA POWER for a coordinate.

    Requests temperature (T2M), solar radiation (ALLSKY_SFC_SW_DWN), and
    wind speed (WS2M) for the last ``lookback_days`` days.  Returns 30-day
    averages in a clean, normalized structure.

    Args:
        lat: Latitude in decimal degrees (WGS84).
        lon: Longitude in decimal degrees (WGS84).
        lookback_days: Number of past days to fetch (default 30).
        timeout: HTTP request timeout in seconds.

    Returns:
        Normalized dict with keys:
            - ``temperature_avg_30d``: Mean temperature at 2 m (C)
            - ``solar_radiation_avg_30d``: Mean surface shortwave downward (MJ/m2/day)
            - ``wind_speed_avg_30d``: Mean wind speed at 2 m (m/s)

    Raises:
        WeatherServiceError: On HTTP failure or malformed response.
    """
    end_date = datetime.now(tz=UTC).date()
    start_date = end_date - timedelta(days=lookback_days)

    params: dict[str, Any] = {
        "latitude": lat,
        "longitude": lon,
        "start": start_date.strftime("%Y%m%d"),
        "end": end_date.strftime("%Y%m%d"),
        "parameters": _PARAMETERS,
        "community": _COMMUNITY,
        "format": _FORMAT,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(NASA_POWER_URL, params=params)
    except httpx.TimeoutException as exc:
        logger.error("NASA POWER timeout for ({}, {}): {}", lat, lon, exc)
        raise WeatherServiceError(f"NASA POWER API timed out after {timeout}s") from exc
    except httpx.HTTPError as exc:
        logger.error("NASA POWER HTTP error for ({}, {}): {}", lat, lon, exc)
        raise WeatherServiceError(f"NASA POWER API request failed: {exc}") from exc

    if response.status_code != 200:
        logger.error(
            "NASA POWER returned {} for ({}, {})",
            response.status_code,
            lat,
            lon,
        )
        raise WeatherServiceError(f"NASA POWER API returned HTTP {response.status_code}")

    return _parse_weather_response(response.json())


def _parse_weather_response(data: dict[str, Any]) -> dict[str, Any]:
    """Parse and normalize raw NASA POWER JSON into a stable schema.

    Filters out fill-value entries (-999) that NASA uses for missing data,
    then computes averages across valid days.

    Args:
        data: Raw JSON dict from NASA POWER API.

    Returns:
        Normalized weather averages dict.

    Raises:
        WeatherServiceError: If required parameters or structure is missing.
    """
    try:
        parameters = data["properties"]["parameter"]
    except (KeyError, TypeError) as exc:
        raise WeatherServiceError(
            "Unexpected NASA POWER response: missing 'properties.parameter'"
        ) from exc

    param_map: dict[str, str] = {
        "T2M": "temperature_avg_30d",
        "ALLSKY_SFC_SW_DWN": "solar_radiation_avg_30d",
        "WS2M": "wind_speed_avg_30d",
    }

    result: dict[str, Any] = {}

    for nasa_key, output_key in param_map.items():
        raw = parameters.get(nasa_key)
        if not raw:
            result[output_key] = None
            continue

        # Filter out NASA fill values (-999)
        valid_values = [v for v in raw.values() if v != -999]

        if not valid_values:
            result[output_key] = None
            continue

        result[output_key] = round(sum(valid_values) / len(valid_values), 2)

    return result
