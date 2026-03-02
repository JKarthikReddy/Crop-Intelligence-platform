"""Weather Engine service — climate data, forecasting, and risk scoring.

Pure service layer:
- NASA POWER API for 30-day climate history
- OpenWeather API for 5-day forecast
- FAO-56 ET0 evapotranspiration calculation
- Agricultural weather risk scoring
- Irrigation recommendations
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from loguru import logger

from app.core.config import get_settings
from app.services.cache_service import (
    FORECAST_TTL,
    WEATHER_TTL,
    get_cache,
    make_cache_key,
    set_cache,
)

# ── API Endpoints ────────────────────────────────────────────────
NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
OPENWEATHER_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/forecast"

_NASA_PARAMS = "T2M,ALLSKY_SFC_SW_DWN,WS2M,PRECTOTCORR"
_LOOKBACK_DAYS = 30
_TIMEOUT = 20.0

_HEAT_THRESHOLD_C = 35.0
_HEAVY_RAIN_THRESHOLD_MM = 50.0


class WeatherEngineError(Exception):
    """Raised when weather analysis fails."""


# ── ET0 Calculation (FAO-56 Simplified) ──────────────────────────


def calculate_et0(temperature: float, solar_radiation: float, wind_speed: float) -> float:
    """Estimate daily reference ET0 using simplified FAO-56."""
    et0 = 0.408 * solar_radiation + 0.0023 * (temperature + 17.8) * (wind_speed + 1)
    return round(max(0.0, et0), 2)


def water_stress_indicator(et0: float) -> str:
    """Classify water stress risk from ET0."""
    if et0 > 6:
        return "high"
    if et0 > 4:
        return "moderate"
    return "low"


def irrigation_recommendation(et0: float, rain_forecast: float) -> str:
    """Generate irrigation guidance from ET0 and forecast rainfall."""
    daily_deficit = et0 - (rain_forecast / 5)  # mm/day balance
    if daily_deficit > 4:
        return "Irrigate immediately — significant water deficit expected"
    if daily_deficit > 2:
        return "Schedule irrigation within 2 days"
    if daily_deficit > 0:
        return "Monitor soil moisture; light irrigation may be needed"
    return "Adequate rainfall expected; no irrigation needed"


# ── Risk Assessment ──────────────────────────────────────────────


def assess_weather_risks(
    climate: dict[str, Any] | None,
    forecast: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compute composite weather risk scores."""
    score = 0.0
    drought_risk = "low"
    flood_risk = "low"
    frost_risk = "none"

    if climate:
        temp = climate.get("temperature_avg_30d", 25)
        rain_30d = climate.get("precipitation_sum_30d", 60)

        # Drought risk
        if rain_30d is not None:
            if rain_30d < 10:
                drought_risk = "critical"
                score += 40
            elif rain_30d < 30:
                drought_risk = "high"
                score += 25
            elif rain_30d < 60:
                drought_risk = "moderate"
                score += 10

        # Frost risk
        if temp is not None and temp < 5:
            frost_risk = "high"
            score += 20
        elif temp is not None and temp < 10:
            frost_risk = "moderate"
            score += 10
        elif temp is not None and temp < 15:
            frost_risk = "low"
            score += 5

    if forecast:
        total_rain = forecast.get("total_rain_next_5d", 0.0)
        max_temp = forecast.get("max_temp_next_5d", 25.0)

        if total_rain > 100:
            flood_risk = "critical"
            score += 30
        elif total_rain > 50:
            flood_risk = "high"
            score += 20
        elif total_rain > 25:
            flood_risk = "moderate"
            score += 10

        if max_temp > 40:
            score += 15  # Extreme heat penalty

    return {
        "drought_risk": drought_risk,
        "flood_risk": flood_risk,
        "frost_risk": frost_risk,
        "overall_risk_score": min(100.0, round(score, 1)),
    }


def generate_weather_recommendations(
    climate: dict[str, Any] | None,
    forecast: dict[str, Any] | None,
    risks: dict[str, Any],
) -> list[str]:
    """Generate actionable weather-based recommendations."""
    recs: list[str] = []

    if risks["drought_risk"] in ("high", "critical"):
        recs.append("Drought alert: increase irrigation frequency and apply mulch")
    if risks["flood_risk"] in ("high", "critical"):
        recs.append("Flood risk: ensure field drainage is clear; avoid planting low-lying areas")
    if risks["frost_risk"] in ("moderate", "high"):
        recs.append("Frost warning: protect sensitive crops with covers or delay planting")

    if forecast:
        if forecast.get("heat_risk_flag"):
            recs.append(
                "Heat stress expected: irrigate early morning and provide shade for nurseries"
            )
        if forecast.get("heavy_rain_flag"):
            recs.append("Heavy rain expected: harvest mature crops early and secure stored produce")

    if not recs:
        recs.append("Weather conditions are favorable for farming operations")

    return recs


# ── Data Fetching ────────────────────────────────────────────────


async def _fetch_current_weather(lat: float, lon: float) -> dict[str, Any]:
    """Fetch real-time current weather from OpenWeather Current Weather API."""
    cache_key = make_cache_key("current_weather", lat, lon)
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    settings = get_settings()
    params = {
        "lat": lat,
        "lon": lon,
        "appid": settings.OPENWEATHER_API_KEY,
        "units": "metric",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(OPENWEATHER_CURRENT_URL, params=params)
    except httpx.HTTPError as exc:
        raise WeatherEngineError(f"OpenWeather current request failed: {exc}") from exc

    if response.status_code != 200:
        body = response.text
        raise WeatherEngineError(
            f"OpenWeather current returned HTTP {response.status_code}: {body}"
        )

    result = _parse_current_weather(response.json())
    await set_cache(cache_key, result, ttl=600)  # 10 min TTL — current data
    return result


def _parse_current_weather(data: dict[str, Any]) -> dict[str, Any]:
    """Parse OpenWeather /weather JSON into CurrentWeather dict."""
    try:
        main = data["main"]
        wind = data.get("wind", {})
        clouds = data.get("clouds", {})
        sys_info = data.get("sys", {})
        weather_block = data.get("weather", [{}])[0]

        return {
            "temperature": main["temp"],
            "feels_like": main["feels_like"],
            "temp_min": main["temp_min"],
            "temp_max": main["temp_max"],
            "pressure": main["pressure"],
            "humidity": main["humidity"],
            "visibility": data.get("visibility", 0),
            "wind_speed": wind.get("speed", 0.0),
            "wind_deg": wind.get("deg", 0),
            "wind_gust": wind.get("gust"),
            "clouds": clouds.get("all", 0),
            "weather_main": weather_block.get("main", "Unknown"),
            "weather_description": weather_block.get("description", ""),
            "weather_icon": weather_block.get("icon", "01d"),
            "rain_1h": data.get("rain", {}).get("1h"),
            "snow_1h": data.get("snow", {}).get("1h"),
            "sunrise": sys_info.get("sunrise", 0),
            "sunset": sys_info.get("sunset", 0),
            "city_name": data.get("name", "Unknown"),
            "country": sys_info.get("country", ""),
            "dt": data.get("dt", 0),
        }
    except (KeyError, TypeError, IndexError) as exc:
        raise WeatherEngineError(f"Failed to parse current weather: {exc}") from exc


async def _fetch_climate(lat: float, lon: float) -> dict[str, Any]:
    """Fetch 30-day climate from NASA POWER."""
    cache_key = make_cache_key("climate", lat, lon)
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    end_date = datetime.now(tz=UTC).date()
    start_date = end_date - timedelta(days=_LOOKBACK_DAYS)

    params = {
        "latitude": lat,
        "longitude": lon,
        "start": start_date.strftime("%Y%m%d"),
        "end": end_date.strftime("%Y%m%d"),
        "parameters": _NASA_PARAMS,
        "community": "AG",
        "format": "JSON",
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(NASA_POWER_URL, params=params)
    except httpx.HTTPError as exc:
        raise WeatherEngineError(f"NASA POWER request failed: {exc}") from exc

    if response.status_code != 200:
        raise WeatherEngineError(f"NASA POWER returned HTTP {response.status_code}")

    result = _parse_climate(response.json())
    await set_cache(cache_key, result, ttl=WEATHER_TTL)
    return result


def _parse_climate(data: dict[str, Any]) -> dict[str, Any]:
    """Parse NASA POWER JSON into climate snapshot."""
    try:
        parameters = data["properties"]["parameter"]
    except (KeyError, TypeError) as exc:
        raise WeatherEngineError("Unexpected NASA POWER response") from exc

    def _avg(key: str) -> float | None:
        raw = parameters.get(key, {})
        vals = [v for v in raw.values() if v != -999]
        return round(sum(vals) / len(vals), 2) if vals else None

    def _sum(key: str) -> float | None:
        raw = parameters.get(key, {})
        vals = [v for v in raw.values() if v != -999]
        return round(sum(vals), 2) if vals else None

    return {
        "temperature_avg_30d": _avg("T2M"),
        "solar_radiation_avg_30d": _avg("ALLSKY_SFC_SW_DWN"),
        "wind_speed_avg_30d": _avg("WS2M"),
        "precipitation_sum_30d": _sum("PRECTOTCORR"),
    }


async def _fetch_forecast(lat: float, lon: float) -> dict[str, Any]:
    """Fetch 5-day forecast from OpenWeather."""
    cache_key = make_cache_key("forecast", lat, lon)
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    settings = get_settings()
    params = {
        "lat": lat,
        "lon": lon,
        "appid": settings.OPENWEATHER_API_KEY,
        "units": "metric",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(OPENWEATHER_URL, params=params)
    except httpx.HTTPError as exc:
        raise WeatherEngineError(f"OpenWeather request failed: {exc}") from exc

    if response.status_code != 200:
        raise WeatherEngineError(f"OpenWeather returned HTTP {response.status_code}")

    result = _parse_forecast(response.json())
    await set_cache(cache_key, result, ttl=FORECAST_TTL)
    return result


def _parse_forecast(data: dict[str, Any]) -> dict[str, Any]:
    """Parse OpenWeather 5-day JSON into structured forecast."""
    try:
        temps = [item["main"]["temp"] for item in data["list"]]
        rainfall = [item.get("rain", {}).get("3h", 0.0) for item in data["list"]]
    except (KeyError, TypeError) as exc:
        raise WeatherEngineError("Unexpected OpenWeather response") from exc

    if not temps:
        raise WeatherEngineError("No forecast intervals found")

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


# ── Main Entry Point ─────────────────────────────────────────────


async def analyze_weather(lat: float, lon: float) -> dict[str, Any]:
    """Full weather analysis — climate, forecast, ET0, and risk scoring.

    Args:
        lat: Latitude (WGS84).
        lon: Longitude (WGS84).

    Returns:
        Complete weather intelligence dict.
    """
    import asyncio

    current, climate, forecast = None, None, None

    results = await asyncio.gather(
        _fetch_current_weather(lat, lon),
        _fetch_climate(lat, lon),
        _fetch_forecast(lat, lon),
        return_exceptions=True,
    )

    if not isinstance(results[0], Exception):
        current = results[0]
    else:
        logger.warning("Current weather fetch failed: {}", results[0])

    if not isinstance(results[1], Exception):
        climate = results[1]
    else:
        logger.warning("Climate fetch failed: {}", results[1])

    if not isinstance(results[2], Exception):
        forecast = results[2]
    else:
        logger.warning("Forecast fetch failed: {}", results[2])

    # Water model
    water_model = None
    if climate:
        temp = climate.get("temperature_avg_30d")
        solar = climate.get("solar_radiation_avg_30d")
        wind = climate.get("wind_speed_avg_30d")
        rain_f = forecast.get("total_rain_next_5d", 0) if forecast else 0

        if temp is not None and solar is not None and wind is not None:
            et0 = calculate_et0(temp, solar, wind)
            water_model = {
                "et0_estimate": et0,
                "water_stress_risk": water_stress_indicator(et0),
                "irrigation_recommendation": irrigation_recommendation(et0, rain_f),
            }

    risks = assess_weather_risks(climate, forecast)
    recs = generate_weather_recommendations(climate, forecast, risks)

    return {
        "current": current,
        "climate": climate,
        "forecast": forecast,
        "water_model": water_model,
        "risk_assessment": risks,
        "recommendations": recs,
    }
