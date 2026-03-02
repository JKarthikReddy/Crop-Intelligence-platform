"""Soil Engine service — soil data fetching, analysis, and health scoring.

Pure service layer:
- Fetches soil chemistry from ISRIC SoilGrids API
- Computes pH classification, texture class, nutrient adequacy
- Generates soil health index (0-100) and improvement recommendations
- Async HTTP via httpx, Redis caching, graceful error handling
"""

from typing import Any

import httpx
from loguru import logger

from app.services.cache_service import SOIL_TTL, get_cache, make_cache_key, set_cache

SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"

_PROPERTIES = ["phh2o", "clay", "ocd", "nitrogen", "soc"]
_DEPTH = "0-5cm"
_VALUE = "mean"
_TIMEOUT = 15.0


class SoilEngineError(Exception):
    """Raised when soil analysis fails."""


# ── pH Classification ────────────────────────────────────────────


def classify_ph(ph: float | None) -> str:
    """Classify soil pH into agronomic categories."""
    if ph is None:
        return "unknown"
    if ph < 5.5:
        return "strongly_acidic"
    if ph < 6.0:
        return "acidic"
    if ph < 6.8:
        return "slightly_acidic"
    if ph <= 7.2:
        return "neutral"
    if ph <= 7.8:
        return "slightly_alkaline"
    if ph <= 8.5:
        return "alkaline"
    return "strongly_alkaline"


# ── Texture Classification ───────────────────────────────────────


def classify_texture(clay_percent: int | None) -> str:
    """Classify soil texture from clay content (g/kg)."""
    if clay_percent is None:
        return "unknown"
    if clay_percent < 150:
        return "sandy"
    if clay_percent < 350:
        return "loamy"
    return "clayey"


# ── Nutrient Adequacy ────────────────────────────────────────────


def assess_nutrients(soil_data: dict[str, Any]) -> dict[str, str]:
    """Assess nutrient adequacy from soil properties."""
    oc = soil_data.get("organic_carbon", 0) or 0

    # Organic carbon rating (g/dm³)
    if oc < 20:
        oc_rating = "poor"
    elif oc < 40:
        oc_rating = "fair"
    elif oc < 60:
        oc_rating = "good"
    else:
        oc_rating = "excellent"

    # Estimate N/P/K from organic carbon (simplified model)
    nitrogen = "low" if oc < 25 else ("adequate" if oc < 50 else "high")
    phosphorus = "low" if oc < 20 else ("adequate" if oc < 45 else "high")
    potassium = "adequate"  # Default; requires specific K data

    return {
        "nitrogen": nitrogen,
        "phosphorus": phosphorus,
        "potassium": potassium,
        "organic_carbon_rating": oc_rating,
    }


# ── Soil Health Index ────────────────────────────────────────────


def compute_soil_health_index(soil_data: dict[str, Any]) -> float:
    """Compute composite soil health index (0-100).

    Weights: pH optimalness (30%), organic carbon (35%),
    texture suitability (20%), overall nutrient status (15%).
    """
    score = 0.0

    # pH score (optimal range 6.0-7.0 = 100%)
    ph = soil_data.get("ph")
    if ph is not None:
        if 6.0 <= ph <= 7.0:
            ph_score = 100.0
        elif 5.5 <= ph <= 7.5:
            ph_score = 75.0
        elif 5.0 <= ph <= 8.0:
            ph_score = 50.0
        else:
            ph_score = 25.0
        score += 0.30 * ph_score
    else:
        score += 0.30 * 50.0  # Unknown = neutral assumption

    # Organic carbon score
    oc = soil_data.get("organic_carbon", 0) or 0
    oc_score = min(100.0, (oc / 60) * 100)
    score += 0.35 * oc_score

    # Texture score (loamy is ideal)
    clay = soil_data.get("clay_percent", 0) or 0
    texture = classify_texture(clay)
    texture_scores = {"sandy": 50.0, "loamy": 100.0, "clayey": 70.0, "unknown": 50.0}
    score += 0.20 * texture_scores.get(texture, 50.0)

    # Nutrient score
    nutrients = assess_nutrients(soil_data)
    nutrient_map = {"low": 30.0, "adequate": 80.0, "high": 60.0}
    n_score = nutrient_map.get(nutrients["nitrogen"], 50.0)
    p_score = nutrient_map.get(nutrients["phosphorus"], 50.0)
    score += 0.15 * ((n_score + p_score) / 2)

    return round(score, 1)


# ── Recommendations ──────────────────────────────────────────────


def generate_soil_recommendations(soil_data: dict[str, Any]) -> list[str]:
    """Generate actionable soil improvement recommendations."""
    recs: list[str] = []
    ph = soil_data.get("ph")
    oc = soil_data.get("organic_carbon", 0) or 0
    clay = soil_data.get("clay_percent", 0) or 0

    if ph is not None:
        if ph < 5.5:
            recs.append("Apply agricultural lime (2-4 t/ha) to raise pH")
        elif ph > 8.0:
            recs.append("Apply sulfur or gypsum (1-2 t/ha) to lower pH")

    if oc < 20:
        recs.append("Increase organic matter: add compost (5-10 t/ha) or green manure")
    elif oc < 40:
        recs.append("Maintain organic carbon with crop residue retention")

    if clay > 400:
        recs.append("Improve drainage; consider raised beds for heavy clay soils")
    elif clay < 100:
        recs.append("Add organic matter to improve water retention in sandy soil")

    nutrients = assess_nutrients(soil_data)
    if nutrients["nitrogen"] == "low":
        recs.append("Apply nitrogen fertilizer or plant leguminous cover crops")
    if nutrients["phosphorus"] == "low":
        recs.append("Apply phosphate fertilizer (DAP or SSP)")

    if not recs:
        recs.append("Soil conditions are good. Maintain current management practices")

    return recs


# ── Main Entry Point ─────────────────────────────────────────────


async def analyze_soil(lat: float, lon: float) -> dict[str, Any]:
    """Full soil analysis — fetch data, analyze, score, and recommend.

    Args:
        lat: Latitude (WGS84).
        lon: Longitude (WGS84).

    Returns:
        Complete soil intelligence dict with raw data, classifications,
        health index, and recommendations.
    """
    cache_key = make_cache_key("soil_engine", lat, lon)
    cached = await get_cache(cache_key)
    if cached is not None:
        logger.debug("Soil Engine cache HIT for {}", cache_key)
        return cached

    raw = await _fetch_soil_raw(lat, lon)

    result = {
        "ph": raw.get("ph"),
        "ph_classification": classify_ph(raw.get("ph")),
        "clay_percent": raw.get("clay_percent"),
        "organic_carbon": raw.get("organic_carbon"),
        "texture_class": classify_texture(raw.get("clay_percent")),
        "nutrient_profile": assess_nutrients(raw),
        "soil_health_index": compute_soil_health_index(raw),
        "recommendations": generate_soil_recommendations(raw),
    }

    await set_cache(cache_key, result, ttl=SOIL_TTL)
    return result


async def _fetch_soil_raw(lat: float, lon: float) -> dict[str, Any]:
    """Fetch raw soil properties from ISRIC SoilGrids."""
    params: dict[str, Any] = {
        "lat": lat,
        "lon": lon,
        "property": _PROPERTIES,
        "depth": [_DEPTH],
        "value": [_VALUE],
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(SOILGRIDS_URL, params=params)
    except httpx.TimeoutException as exc:
        raise SoilEngineError(f"SoilGrids API timed out after {_TIMEOUT}s") from exc
    except httpx.HTTPError as exc:
        raise SoilEngineError(f"SoilGrids API request failed: {exc}") from exc

    if response.status_code != 200:
        raise SoilEngineError(f"SoilGrids API returned HTTP {response.status_code}")

    return _parse_soil_response(response.json())


def _parse_soil_response(data: dict[str, Any]) -> dict[str, Any]:
    """Parse raw SoilGrids JSON into normalized soil dict."""
    try:
        layers = data["properties"]["layers"]
    except (KeyError, TypeError) as exc:
        raise SoilEngineError("Unexpected SoilGrids response structure") from exc

    soil: dict[str, Any] = {}
    layer_map = {"phh2o": "ph", "clay": "clay_percent", "ocd": "organic_carbon"}

    for layer in layers:
        name = layer.get("name")
        if name not in layer_map:
            continue
        try:
            raw_value = layer["depths"][0]["values"][_VALUE]
        except (KeyError, IndexError, TypeError) as exc:
            raise SoilEngineError(f"Missing data for layer '{name}'") from exc

        if raw_value is None:
            soil[layer_map[name]] = None
            continue

        soil[layer_map[name]] = round(raw_value / 10, 1) if name == "phh2o" else raw_value

    for key in layer_map.values():
        soil.setdefault(key, None)

    return soil
