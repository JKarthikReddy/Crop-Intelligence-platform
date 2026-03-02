"""Advisory Aggregator service — orchestrates all 6 engines.

This is the core aggregator that:
1. Launches all 6 engines in parallel via asyncio.gather
2. Gracefully degrades if any engine fails
3. Cross-correlates engine outputs for unified intelligence
4. Generates prioritized action items
5. Computes composite farm health score
"""

import asyncio
import time
from typing import Any

from loguru import logger

from app.engines.crop.service import analyze_crop
from app.engines.disease.service import assess_disease_risk
from app.engines.fertilizer.service import recommend_fertilizer
from app.engines.market.service import analyze_market
from app.engines.soil.service import analyze_soil
from app.engines.weather.service import analyze_weather


class AdvisoryEngineError(Exception):
    """Raised when advisory aggregation fails."""


async def _run_engine(
    name: str,
    coro: Any,
) -> tuple[str, str, dict[str, Any] | None, float, str | None]:
    """Run a single engine with timing and error handling.

    Returns (name, status, result, latency_ms, error_msg).
    """
    t0 = time.perf_counter()
    try:
        result = await coro
        latency = round((time.perf_counter() - t0) * 1000, 1)
        return name, "success", result, latency, None
    except Exception as exc:
        latency = round((time.perf_counter() - t0) * 1000, 1)
        logger.warning(f"Engine {name} failed: {exc}")
        return name, "failed", None, latency, str(exc)


def _compute_farm_health(
    soil: dict[str, Any] | None,
    weather: dict[str, Any] | None,
    crop: dict[str, Any] | None,
    disease: dict[str, Any] | None,
    market: dict[str, Any] | None,
) -> float:
    """Compute composite farm health score (0-100).

    Weights:
      - Soil Health:      20%
      - Weather Safety:   20%
      - Crop Health:      25%
      - Disease Safety:   20% (inverted risk)
      - Market Outlook:   15%
    """
    scores: list[tuple[float, float]] = []  # (score, weight)

    if soil:
        scores.append((soil.get("soil_health_index", 50), 0.20))

    if weather:
        risk = weather.get("risk_assessment", {})
        weather_safety = 100 - risk.get("overall_risk_score", 50)
        scores.append((weather_safety, 0.20))

    if crop:
        scores.append((crop.get("crop_health_score", 50), 0.25))

    if disease:
        disease_safety = 100 - disease.get("overall_risk_score", 50)
        scores.append((disease_safety, 0.20))

    if market:
        prof = market.get("profitability", {})
        margin = prof.get("profit_margin_pct", 20)
        market_score = min(100, max(0, margin * 2.5))
        scores.append((market_score, 0.15))

    if not scores:
        return 50.0

    total_weight = sum(w for _, w in scores)
    weighted_sum = sum(s * w for s, w in scores)
    return round(weighted_sum / total_weight, 1)


def _generate_priority_actions(
    soil: dict[str, Any] | None,
    weather: dict[str, Any] | None,
    crop: dict[str, Any] | None,
    fertilizer: dict[str, Any] | None,
    disease: dict[str, Any] | None,
    market: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Generate prioritized action list from all engine outputs."""
    actions: list[dict[str, Any]] = []

    # Disease — highest priority if critical
    if disease:
        risk_level = disease.get("risk_level", "Low")
        if risk_level in ("Critical", "High"):
            top_disease = disease.get("disease_risks", [{}])[0]
            actions.append(
                {
                    "category": "Disease",
                    "action": f"Address {risk_level.lower()} disease risk: {top_disease.get('disease_name', 'Unknown')}",
                    "urgency": "Immediate",
                    "impact": "High",
                }
            )

    # Weather — urgent if risk is high
    if weather:
        risk = weather.get("risk_assessment", {})
        if risk.get("overall_risk_score", 0) > 60:
            actions.append(
                {
                    "category": "Weather",
                    "action": "Take protective measures against weather risks",
                    "urgency": "Immediate",
                    "impact": "High",
                }
            )
        water = weather.get("water_model", {})
        if water.get("irrigation_recommendation"):
            actions.append(
                {
                    "category": "Weather",
                    "action": water["irrigation_recommendation"],
                    "urgency": "This Week",
                    "impact": "Medium",
                }
            )

    # Fertilizer — scheduled applications
    if fertilizer:
        schedule = fertilizer.get("application_schedule", [])
        if schedule:
            next_app = schedule[0]
            actions.append(
                {
                    "category": "Fertilizer",
                    "action": f"Apply fertilizer: {next_app.get('stage', 'scheduled')} — {', '.join(next_app.get('products', []))}",
                    "urgency": "This Week",
                    "impact": "High",
                }
            )

    # Soil — amendments if health is low
    if soil and soil.get("soil_health_index", 100) < 50:
        actions.append(
            {
                "category": "Soil",
                "action": "Soil health is below optimal — follow soil amendment recommendations",
                "urgency": "This Month",
                "impact": "Medium",
            }
        )

    # Crop — yield optimization
    if crop and crop.get("crop_health_score", 100) < 60:
        actions.append(
            {
                "category": "Crop",
                "action": "Crop health suboptimal — review irrigation, nutrition, and pest management",
                "urgency": "This Week",
                "impact": "High",
            }
        )

    # Market — selling decisions
    if market:
        rec = market.get("sell_recommendation", "")
        if "sell now" in rec.lower():
            actions.append(
                {
                    "category": "Market",
                    "action": rec,
                    "urgency": "This Week",
                    "impact": "Medium",
                }
            )
        elif "hold" in rec.lower():
            actions.append(
                {
                    "category": "Market",
                    "action": rec,
                    "urgency": "This Month",
                    "impact": "Medium",
                }
            )

    # Assign priority ranks
    urgency_order = {"Immediate": 0, "This Week": 1, "This Month": 2, "Seasonal": 3}
    actions.sort(key=lambda a: (urgency_order.get(a["urgency"], 9), a["impact"] != "High"))
    for i, action in enumerate(actions, 1):
        action["priority"] = i

    return actions


def _build_summary(
    farm_health: float,
    actions: list[dict[str, Any]],
    succeeded: int,
    total: int,
) -> str:
    """Build executive summary."""
    if farm_health >= 75:
        health_text = "Farm is in good overall condition."
    elif farm_health >= 50:
        health_text = "Farm health is moderate — attention needed in some areas."
    else:
        health_text = "Farm health is below optimal — urgent actions required."

    immediate = [a for a in actions if a["urgency"] == "Immediate"]
    if immediate:
        action_text = f" {len(immediate)} immediate action(s) identified."
    else:
        action_text = " No immediate threats detected."

    engine_text = f" Analysis based on {succeeded}/{total} engines."

    return health_text + action_text + engine_text


# ── Main Entry Point ─────────────────────────────────────────────


async def generate_advisory(
    lat: float = 17.385,
    lon: float = 78.4867,
    crop_type: str = "rice",
    planting_date: str | None = None,
    target_yield: float = 5.0,
    area_hectares: float = 1.0,
    region: str = "south_asia",
    bounds: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Generate comprehensive farm advisory by orchestrating all 6 engines.

    Launches all engines concurrently, gracefully degrades on failures,
    and produces unified intelligence with prioritized actions.

    Args:
        lat: Farm latitude.
        lon: Farm longitude.
        crop_type: Target crop.
        planting_date: ISO planting date.
        target_yield: Target yield (t/ha).
        area_hectares: Farm area.
        region: Market region.
        bounds: Satellite analysis bounding box.

    Returns:
        Complete advisory dict with all engine outputs.
    """
    logger.info(f"Advisory: orchestrating 6 engines for ({lat}, {lon}) crop={crop_type}")

    # Build default bounds if not provided
    if bounds is None:
        offset = 0.02
        bounds = {
            "north": lat + offset,
            "south": lat - offset,
            "east": lon + offset,
            "west": lon - offset,
        }

    # ── Launch all 6 engines in parallel ─────────────────────────
    results = await asyncio.gather(
        _run_engine("Soil", analyze_soil(lat=lat, lon=lon)),
        _run_engine("Weather", analyze_weather(lat=lat, lon=lon)),
        _run_engine(
            "Crop",
            analyze_crop(
                lat=lat,
                lon=lon,
                bounds=bounds,
                crop_type=crop_type,
                planting_date=planting_date,
            ),
        ),
        _run_engine(
            "Fertilizer",
            recommend_fertilizer(
                crop_type=crop_type,
                target_yield=target_yield,
                area_hectares=area_hectares,
            ),
        ),
        _run_engine("Disease", assess_disease_risk(crop_type=crop_type)),
        _run_engine(
            "Market",
            analyze_market(
                crop_type=crop_type,
                region=region,
                area_hectares=area_hectares,
            ),
        ),
        return_exceptions=True,
    )

    # ── Collect results ──────────────────────────────────────────
    engine_map: dict[str, dict[str, Any] | None] = {}
    statuses: list[dict[str, Any]] = []

    for item in results:
        if isinstance(item, Exception):
            logger.error(f"Engine gather exception: {item}")
            continue
        name, status, data, latency, error = item
        engine_map[name] = data
        statuses.append(
            {
                "engine": name,
                "status": status,
                "latency_ms": latency,
                "error": error,
            }
        )

    # ── Cross-pollinate data between engines ─────────────────────
    # Feed soil data into fertilizer if soil succeeded
    soil_data = engine_map.get("Soil")
    weather_data = engine_map.get("Weather")
    crop_data = engine_map.get("Crop")
    fertilizer_data = engine_map.get("Fertilizer")
    disease_data = engine_map.get("Disease")
    market_data = engine_map.get("Market")

    # If soil data available, re-run fertilizer with actual soil values
    if soil_data and fertilizer_data:
        try:
            fertilizer_data = await recommend_fertilizer(
                crop_type=crop_type,
                target_yield=target_yield,
                soil_ph=soil_data.get("ph"),
                organic_carbon=soil_data.get("organic_carbon"),
                clay_percent=soil_data.get("clay_percent"),
                area_hectares=area_hectares,
            )
            engine_map["Fertilizer"] = fertilizer_data
        except Exception:
            pass  # Keep original fertilizer result

    # If weather + crop available, re-run disease with actual values
    if (weather_data or crop_data) and disease_data:
        try:
            climate = weather_data.get("climate", {}) if weather_data else {}
            veg = crop_data.get("vegetation_health", {}) if crop_data else {}
            disease_data = await assess_disease_risk(
                crop_type=crop_type,
                avg_temperature=climate.get("temperature_mean"),
                avg_humidity=climate.get("humidity_mean"),
                recent_rainfall_mm=climate.get("precipitation_total"),
                ndvi_mean=veg.get("ndvi_mean"),
                soil_ph=soil_data.get("ph") if soil_data else None,
            )
            engine_map["Disease"] = disease_data
        except Exception:
            pass

    # ── Compute composite intelligence ───────────────────────────
    succeeded = sum(1 for s in statuses if s["status"] == "success")
    farm_health = _compute_farm_health(
        soil_data, weather_data, crop_data, disease_data, market_data
    )
    priority_actions = _generate_priority_actions(
        soil_data,
        weather_data,
        crop_data,
        fertilizer_data,
        disease_data,
        market_data,
    )
    summary = _build_summary(farm_health, priority_actions, succeeded, 6)

    return {
        "farm_health_score": farm_health,
        "advisory_summary": summary,
        "priority_actions": priority_actions,
        "soil_intelligence": soil_data,
        "weather_intelligence": weather_data,
        "crop_intelligence": crop_data,
        "fertilizer_intelligence": fertilizer_data,
        "disease_intelligence": disease_data,
        "market_intelligence": market_data,
        "engine_statuses": statuses,
        "engines_succeeded": succeeded,
        "engines_total": 6,
    }
