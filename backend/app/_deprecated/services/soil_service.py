"""Soil intelligence service — dynamic soil data from ISRIC SoilGrids.

Pure service layer:
- No FastAPI imports
- No database logic
- No environment access
- Async HTTP via httpx
- Structured, normalized output only
"""

from typing import Any

import httpx
from loguru import logger

from app.services.cache_service import SOIL_TTL, get_cache, make_cache_key, set_cache

SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"

# Properties requested from SoilGrids
_PROPERTIES = ["phh2o", "clay", "ocd"]
_DEPTH = "0-5cm"
_VALUE = "mean"

# Default timeout for external API calls (seconds)
_TIMEOUT = 15.0


class SoilServiceError(Exception):
    """Raised when the SoilGrids API call or response parsing fails."""


async def fetch_soil_data(
    lat: float,
    lon: float,
    *,
    timeout: float = _TIMEOUT,
) -> dict[str, Any]:
    """Fetch soil properties from ISRIC SoilGrids for a given coordinate.

    Requests pH (H2O), clay %, and organic carbon density at 0-5 cm depth.
    Normalizes the response into a clean, stable structure that never leaks
    raw upstream JSON.

    Args:
        lat: Latitude in decimal degrees (WGS84).
        lon: Longitude in decimal degrees (WGS84).
        timeout: HTTP request timeout in seconds.

    Returns:
        Normalized dict with keys:
            - ``ph``: Soil pH (float, scale-corrected by /10)
            - ``clay_percent``: Clay content in g/kg (int)
            - ``organic_carbon``: Organic carbon density in g/dm³ (int)

    Raises:
        SoilServiceError: If the API request fails or the response is
            malformed / missing expected data.
    """
    # ── Cache check ──────────────────────────────────────────────
    cache_key = make_cache_key("soil", lat, lon)
    cached = await get_cache(cache_key)
    if cached is not None:
        logger.debug("Cache HIT for {}", cache_key)
        return cached

    params: dict[str, Any] = {
        "lat": lat,
        "lon": lon,
        "property": _PROPERTIES,
        "depth": [_DEPTH],
        "value": [_VALUE],
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(SOILGRIDS_URL, params=params)
    except httpx.TimeoutException as exc:
        logger.error("SoilGrids timeout for ({}, {}): {}", lat, lon, exc)
        raise SoilServiceError(f"SoilGrids API timed out after {timeout}s") from exc
    except httpx.HTTPError as exc:
        logger.error("SoilGrids HTTP error for ({}, {}): {}", lat, lon, exc)
        raise SoilServiceError(f"SoilGrids API request failed: {exc}") from exc

    if response.status_code != 200:
        logger.error(
            "SoilGrids returned {} for ({}, {})",
            response.status_code,
            lat,
            lon,
        )
        raise SoilServiceError(f"SoilGrids API returned HTTP {response.status_code}")

    result = _parse_soil_response(response.json())
    await set_cache(cache_key, result, ttl=SOIL_TTL)
    return result


def _parse_soil_response(data: dict[str, Any]) -> dict[str, Any]:
    """Parse and normalize raw SoilGrids JSON into a stable schema.

    Args:
        data: Raw JSON dict from the SoilGrids API.

    Returns:
        Normalized soil data dict.

    Raises:
        SoilServiceError: If required layers or values are missing.
    """
    try:
        layers = data["properties"]["layers"]
    except (KeyError, TypeError) as exc:
        raise SoilServiceError(
            "Unexpected SoilGrids response structure: missing 'properties.layers'"
        ) from exc

    soil: dict[str, Any] = {}
    layer_map: dict[str, str] = {
        "phh2o": "ph",
        "clay": "clay_percent",
        "ocd": "organic_carbon",
    }

    for layer in layers:
        name = layer.get("name")
        if name not in layer_map:
            continue

        try:
            raw_value = layer["depths"][0]["values"][_VALUE]
        except (KeyError, IndexError, TypeError) as exc:
            raise SoilServiceError(f"Missing depth/value data for layer '{name}'") from exc

        if raw_value is None:
            soil[layer_map[name]] = None
            continue

        # SoilGrids returns pH x10 -- normalize
        if name == "phh2o":
            soil[layer_map[name]] = round(raw_value / 10, 1)
        else:
            soil[layer_map[name]] = raw_value

    # Ensure all expected keys are present even if absent from response
    for key in layer_map.values():
        soil.setdefault(key, None)

    return soil
