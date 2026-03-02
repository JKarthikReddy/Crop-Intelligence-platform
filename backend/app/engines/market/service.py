"""Market Engine service — market intelligence, price trends, and sell advisory.

Pure service layer:
- Simulated crop market price data (deterministic for demo)
- Seasonal pattern analysis
- Profitability estimation
- Sell-timing recommendation
"""

import math
from datetime import UTC, datetime
from typing import Any

# ── Crop Price Database (USD per metric ton, base prices) ────────
_BASE_PRICES: dict[str, dict[str, Any]] = {
    "rice": {
        "base_price": 380,
        "volatility": 0.08,
        "seasonal_peak_months": [3, 4, 5],  # Mar-May (before new harvest)
        "seasonal_low_months": [10, 11, 12],  # Oct-Dec (harvest season)
        "annual_trend": 0.03,  # 3% annual increase
    },
    "wheat": {
        "base_price": 310,
        "volatility": 0.10,
        "seasonal_peak_months": [8, 9, 10],  # Aug-Oct
        "seasonal_low_months": [4, 5, 6],  # Apr-Jun (harvest)
        "annual_trend": 0.025,
    },
    "maize": {
        "base_price": 260,
        "volatility": 0.12,
        "seasonal_peak_months": [4, 5, 6],  # Apr-Jun
        "seasonal_low_months": [9, 10, 11],  # Sep-Nov (harvest)
        "annual_trend": 0.02,
    },
    "soybean": {
        "base_price": 520,
        "volatility": 0.09,
        "seasonal_peak_months": [6, 7, 8],  # Jun-Aug
        "seasonal_low_months": [1, 2, 3],  # Jan-Mar (post-harvest)
        "annual_trend": 0.035,
    },
}

# ── Region Multipliers ───────────────────────────────────────────
_REGION_MULTIPLIER: dict[str, float] = {
    "south_asia": 0.85,
    "southeast_asia": 0.90,
    "east_africa": 0.80,
    "west_africa": 0.78,
    "latin_america": 0.95,
    "global": 1.0,
}

_MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


class MarketEngineError(Exception):
    """Raised when market analysis fails."""


def _simulate_price(base: float, volatility: float, month: int, year: int) -> float:
    """Deterministic price simulation using sine wave + trend."""
    # Seasonal component (sine wave peaking at different months per crop)
    seasonal = math.sin(2 * math.pi * month / 12) * volatility * base
    # Annual trend
    years_from_2024 = year - 2024
    trend = base * (1 + 0.03 * years_from_2024)
    return round(trend + seasonal, 2)


def get_price_snapshot(crop_type: str, region: str) -> dict[str, Any]:
    """Get current and historical prices."""
    crop_data = _BASE_PRICES.get(crop_type, _BASE_PRICES["rice"])
    multiplier = _REGION_MULTIPLIER.get(region, 1.0)
    now = datetime.now(UTC)

    current = (
        _simulate_price(crop_data["base_price"], crop_data["volatility"], now.month, now.year)
        * multiplier
    )
    m1 = now.month - 1 if now.month > 1 else 12
    y1 = now.year if now.month > 1 else now.year - 1
    price_30d = (
        _simulate_price(crop_data["base_price"], crop_data["volatility"], m1, y1) * multiplier
    )

    m3 = now.month - 3 if now.month > 3 else now.month + 9
    y3 = now.year if now.month > 3 else now.year - 1
    price_90d = (
        _simulate_price(crop_data["base_price"], crop_data["volatility"], m3, y3) * multiplier
    )

    price_365d = (
        _simulate_price(crop_data["base_price"], crop_data["volatility"], now.month, now.year - 1)
        * multiplier
    )

    change_30d = ((current - price_30d) / price_30d) * 100 if price_30d else 0

    if change_30d > 2:
        trend = "Rising"
    elif change_30d < -2:
        trend = "Declining"
    else:
        trend = "Stable"

    return {
        "current_price_usd_per_ton": round(current, 2),
        "price_30d_ago": round(price_30d, 2),
        "price_90d_ago": round(price_90d, 2),
        "price_365d_ago": round(price_365d, 2),
        "price_trend": trend,
        "price_change_30d_pct": round(change_30d, 1),
    }


def get_seasonal_pattern(crop_type: str) -> dict[str, Any]:
    """Analyze seasonal price patterns."""
    crop_data = _BASE_PRICES.get(crop_type, _BASE_PRICES["rice"])
    now = datetime.now(UTC)

    peak_months = [_MONTH_NAMES[m - 1] for m in crop_data["seasonal_peak_months"]]
    low_months = [_MONTH_NAMES[m - 1] for m in crop_data["seasonal_low_months"]]

    if now.month in crop_data["seasonal_peak_months"]:
        outlook = "Currently in peak price season — favorable for selling"
    elif now.month in crop_data["seasonal_low_months"]:
        outlook = "Currently in low price season — consider storage if possible"
    else:
        months_to_peak = min((m - now.month) % 12 for m in crop_data["seasonal_peak_months"])
        outlook = (
            f"Prices expected to improve in {months_to_peak} month(s) — hold if storage available"
        )

    strength = "Strong" if crop_data["volatility"] >= 0.10 else "Moderate"

    return {
        "best_sell_months": peak_months,
        "worst_sell_months": low_months,
        "current_season_outlook": outlook,
        "seasonality_strength": strength,
    }


def estimate_profitability(
    crop_type: str,
    region: str,
    estimated_yield_tons: float | None,
    area_hectares: float,
    production_cost_usd: float | None,
) -> dict[str, Any]:
    """Estimate farm profitability."""
    price = get_price_snapshot(crop_type, region)
    current_price = price["current_price_usd_per_ton"]

    # Default production costs per hectare by crop
    default_costs: dict[str, float] = {
        "rice": 650,
        "wheat": 480,
        "maize": 520,
        "soybean": 400,
    }

    # Default yield (t/ha)
    default_yields: dict[str, float] = {
        "rice": 4.5,
        "wheat": 3.5,
        "maize": 5.5,
        "soybean": 2.5,
    }

    yield_tons = estimated_yield_tons or (default_yields.get(crop_type, 4.0) * area_hectares)
    cost = production_cost_usd or (default_costs.get(crop_type, 500) * area_hectares)

    revenue = yield_tons * current_price
    profit = revenue - cost
    margin = (profit / revenue * 100) if revenue > 0 else 0
    break_even = cost / yield_tons if yield_tons > 0 else 0

    return {
        "gross_revenue_usd": round(revenue, 2),
        "production_cost_usd": round(cost, 2),
        "net_profit_usd": round(profit, 2),
        "profit_margin_pct": round(margin, 1),
        "break_even_price_usd": round(break_even, 2),
    }


def determine_sell_recommendation(
    price_snapshot: dict[str, Any],
    seasonal: dict[str, Any],
    profitability: dict[str, Any],
) -> tuple[str, float]:
    """Determine sell recommendation and confidence."""
    score = 0.5  # neutral

    # Price trend factor
    if price_snapshot["price_trend"] == "Rising":
        score += 0.15
    elif price_snapshot["price_trend"] == "Declining":
        score -= 0.15

    # Seasonal factor
    if "peak" in seasonal["current_season_outlook"].lower():
        score += 0.20
    elif "low" in seasonal["current_season_outlook"].lower():
        score -= 0.20

    # Profitability factor
    if profitability["profit_margin_pct"] > 30:
        score += 0.10
    elif profitability["profit_margin_pct"] < 10:
        score -= 0.10

    confidence = min(1.0, max(0.3, abs(score - 0.5) * 2 + 0.4))

    if score >= 0.65:
        return "Sell now — prices are favorable", round(confidence, 2)
    elif score <= 0.35:
        return "Hold — wait for better prices", round(confidence, 2)
    else:
        return "Monitor market — prices are neutral", round(confidence, 2)


def generate_market_recommendations(
    crop_type: str,
    price_snapshot: dict[str, Any],
    profitability: dict[str, Any],
) -> list[str]:
    """Generate market advice."""
    recs: list[str] = []

    if price_snapshot["price_trend"] == "Rising":
        recs.append(
            f"{crop_type.title()} prices trending upward — consider selling in batches to capture gains"
        )
    elif price_snapshot["price_trend"] == "Declining":
        recs.append(
            f"{crop_type.title()} prices declining — explore storage options or forward contracts to lock prices"
        )

    if profitability["profit_margin_pct"] < 15:
        recs.append(
            "Thin margins detected — review input costs and explore bulk purchasing for fertilizers"
        )

    recs.append(
        "Diversify market channels: explore local mandis, government procurement, and online platforms"
    )
    recs.append("Consider contract farming agreements for price stability in future seasons")

    if profitability["break_even_price_usd"] > price_snapshot["current_price_usd_per_ton"] * 0.8:
        recs.append(
            "Break-even price is close to market price — optimize production costs urgently"
        )

    return recs


# ── Main Entry Point ─────────────────────────────────────────────


async def analyze_market(
    crop_type: str = "rice",
    region: str = "south_asia",
    estimated_yield_tons: float | None = None,
    area_hectares: float = 1.0,
    production_cost_usd: float | None = None,
) -> dict[str, Any]:
    """Full market intelligence — prices, seasonality, profitability, and sell advice.

    Args:
        crop_type: Crop being marketed.
        region: Market region for price context.
        estimated_yield_tons: Expected production (optional).
        area_hectares: Farm area.
        production_cost_usd: Total production cost (optional).

    Returns:
        Complete market intelligence dict.
    """
    price_snapshot = get_price_snapshot(crop_type, region)
    seasonal = get_seasonal_pattern(crop_type)
    profitability = estimate_profitability(
        crop_type,
        region,
        estimated_yield_tons,
        area_hectares,
        production_cost_usd,
    )
    sell_rec, confidence = determine_sell_recommendation(price_snapshot, seasonal, profitability)
    recs = generate_market_recommendations(crop_type, price_snapshot, profitability)

    return {
        "price_snapshot": price_snapshot,
        "seasonal_pattern": seasonal,
        "profitability": profitability,
        "sell_recommendation": sell_rec,
        "confidence": confidence,
        "recommendations": recs,
    }
