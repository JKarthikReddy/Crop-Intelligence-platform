"""Market Intelligence Engine — mandi prices, trend analysis & sell/hold advisory.

Pure service layer (no external I/O):
1. Crop-location mandi price database (30 Indian crops x key mandis)
2. 7-day price history simulation (deterministic, date-seeded)
3. Trend analysis (current vs 7-day avg)
4. Sell / Hold decision logic
5. Next-week price prediction (linear extrapolation)
"""

from __future__ import annotations

import hashlib
import math
from datetime import UTC, datetime, timedelta
from typing import Any

# ── Exception ────────────────────────────────────────────────────


class MarketEngineError(Exception):
    """Raised when market analysis fails."""


# ── Crop Mandi Price Database (₹ per quintal, base prices) ──────
# Aligned with CROP_DB names in the Crop Engine.
# Each crop stores: base_price, volatility (0-1 daily jitter),
# seasonal_peak_months, seasonal_low_months.

_CROP_PRICES: dict[str, dict[str, Any]] = {
    "Rice": {
        "base_price": 2200,
        "volatility": 0.04,
        "seasonal_peak_months": [3, 4, 5],
        "seasonal_low_months": [10, 11, 12],
    },
    "Wheat": {
        "base_price": 2400,
        "volatility": 0.03,
        "seasonal_peak_months": [8, 9, 10],
        "seasonal_low_months": [4, 5, 6],
    },
    "Maize": {
        "base_price": 2100,
        "volatility": 0.05,
        "seasonal_peak_months": [4, 5, 6],
        "seasonal_low_months": [9, 10, 11],
    },
    "Red Chilli": {
        "base_price": 14500,
        "volatility": 0.06,
        "seasonal_peak_months": [2, 3, 4],
        "seasonal_low_months": [8, 9, 10],
    },
    "Cotton": {
        "base_price": 6800,
        "volatility": 0.05,
        "seasonal_peak_months": [3, 4, 5],
        "seasonal_low_months": [10, 11, 12],
    },
    "Groundnut": {
        "base_price": 5500,
        "volatility": 0.04,
        "seasonal_peak_months": [5, 6, 7],
        "seasonal_low_months": [11, 12, 1],
    },
    "Soybean": {
        "base_price": 4600,
        "volatility": 0.05,
        "seasonal_peak_months": [6, 7, 8],
        "seasonal_low_months": [1, 2, 3],
    },
    "Sugarcane": {
        "base_price": 350,
        "volatility": 0.02,
        "seasonal_peak_months": [1, 2, 3],
        "seasonal_low_months": [7, 8, 9],
    },
    "Tobacco": {
        "base_price": 13000,
        "volatility": 0.05,
        "seasonal_peak_months": [4, 5, 6],
        "seasonal_low_months": [10, 11, 12],
    },
    "Turmeric": {
        "base_price": 8500,
        "volatility": 0.07,
        "seasonal_peak_months": [3, 4, 5],
        "seasonal_low_months": [9, 10, 11],
    },
    "Sunflower": {
        "base_price": 5800,
        "volatility": 0.04,
        "seasonal_peak_months": [5, 6, 7],
        "seasonal_low_months": [11, 12, 1],
    },
    "Sorghum": {
        "base_price": 3200,
        "volatility": 0.03,
        "seasonal_peak_months": [4, 5, 6],
        "seasonal_low_months": [10, 11, 12],
    },
    "Bajra": {
        "base_price": 2500,
        "volatility": 0.04,
        "seasonal_peak_months": [3, 4, 5],
        "seasonal_low_months": [9, 10, 11],
    },
    "Pulses (Moong)": {
        "base_price": 7500,
        "volatility": 0.05,
        "seasonal_peak_months": [5, 6, 7],
        "seasonal_low_months": [11, 12, 1],
    },
    "Pulses (Urad)": {
        "base_price": 6800,
        "volatility": 0.05,
        "seasonal_peak_months": [4, 5, 6],
        "seasonal_low_months": [10, 11, 12],
    },
    "Chickpea": {
        "base_price": 5200,
        "volatility": 0.04,
        "seasonal_peak_months": [6, 7, 8],
        "seasonal_low_months": [12, 1, 2],
    },
    "Lentil": {
        "base_price": 5800,
        "volatility": 0.04,
        "seasonal_peak_months": [7, 8, 9],
        "seasonal_low_months": [1, 2, 3],
    },
    "Mustard": {
        "base_price": 5500,
        "volatility": 0.04,
        "seasonal_peak_months": [8, 9, 10],
        "seasonal_low_months": [4, 5, 6],
    },
    "Potato": {
        "base_price": 1800,
        "volatility": 0.08,
        "seasonal_peak_months": [7, 8, 9],
        "seasonal_low_months": [1, 2, 3],
    },
    "Onion": {
        "base_price": 2200,
        "volatility": 0.10,
        "seasonal_peak_months": [8, 9, 10],
        "seasonal_low_months": [1, 2, 3],
    },
    "Tomato": {
        "base_price": 2500,
        "volatility": 0.12,
        "seasonal_peak_months": [5, 6, 7],
        "seasonal_low_months": [11, 12, 1],
    },
    "Banana": {
        "base_price": 1500,
        "volatility": 0.05,
        "seasonal_peak_months": [4, 5, 6],
        "seasonal_low_months": [10, 11, 12],
    },
    "Coconut": {
        "base_price": 2800,
        "volatility": 0.03,
        "seasonal_peak_months": [3, 4, 5],
        "seasonal_low_months": [9, 10, 11],
    },
    "Mango": {
        "base_price": 4000,
        "volatility": 0.08,
        "seasonal_peak_months": [4, 5, 6],
        "seasonal_low_months": [10, 11, 12],
    },
    "Tea": {
        "base_price": 18000,
        "volatility": 0.03,
        "seasonal_peak_months": [6, 7, 8],
        "seasonal_low_months": [12, 1, 2],
    },
    "Coffee": {
        "base_price": 42000,
        "volatility": 0.04,
        "seasonal_peak_months": [3, 4, 5],
        "seasonal_low_months": [9, 10, 11],
    },
    "Jute": {
        "base_price": 5000,
        "volatility": 0.04,
        "seasonal_peak_months": [7, 8, 9],
        "seasonal_low_months": [1, 2, 3],
    },
    "Sesame": {
        "base_price": 7200,
        "volatility": 0.05,
        "seasonal_peak_months": [4, 5, 6],
        "seasonal_low_months": [10, 11, 12],
    },
    "Castor": {
        "base_price": 6000,
        "volatility": 0.04,
        "seasonal_peak_months": [5, 6, 7],
        "seasonal_low_months": [11, 12, 1],
    },
}

_DEFAULT_CROP_PRICE: dict[str, Any] = {
    "base_price": 3000,
    "volatility": 0.05,
    "seasonal_peak_months": [4, 5, 6],
    "seasonal_low_months": [10, 11, 12],
}


# ── Location → Nearby Mandis Database ────────────────────────────
# Maps location (title-cased) → list of (mandi_name, distance_km, price_offset)
# price_offset: multiplier (1.0 = same as base, 0.95 = 5% cheaper, etc.)

_MANDI_MAP: dict[str, list[tuple[str, float, float]]] = {
    "Guntur": [
        ("Guntur Mirchi Yard", 0, 1.02),
        ("Chilakaluripet Mandi", 25, 0.97),
        ("Narasaraopet Mandi", 40, 0.95),
        ("Vijayawada Market", 70, 1.00),
    ],
    "Kurnool": [
        ("Kurnool Mandi", 0, 1.00),
        ("Nandyal Market", 55, 0.96),
        ("Adoni Mandi", 80, 0.94),
    ],
    "Hyderabad": [
        ("Begum Bazaar", 0, 1.05),
        ("Bowenpally Market", 10, 1.03),
        ("Gaddiannaram Mandi", 15, 1.01),
        ("Medchal Mandi", 30, 0.98),
    ],
    "Warangal": [
        ("Warangal Mandi", 0, 1.00),
        ("Hanamkonda Market", 5, 0.99),
        ("Karimnagar Mandi", 80, 0.96),
    ],
    "Vijayawada": [
        ("Vijayawada Market Yard", 0, 1.01),
        ("Guntur Mirchi Yard", 35, 1.02),
        ("Eluru Mandi", 60, 0.96),
    ],
    "Nashik": [
        ("Nashik APMC (Lasalgaon)", 0, 1.04),
        ("Pimpalgaon Mandi", 20, 1.00),
        ("Niphad Market", 30, 0.98),
    ],
    "Indore": [
        ("Indore Mandi", 0, 1.02),
        ("Dewas Market", 40, 0.97),
        ("Ujjain Mandi", 55, 0.96),
    ],
    "Ludhiana": [
        ("Ludhiana Grain Market", 0, 1.03),
        ("Jalandhar Mandi", 60, 1.00),
        ("Amritsar Mandi", 130, 1.01),
    ],
    "Jaipur": [
        ("Jaipur Mandi", 0, 1.01),
        ("Chomu Market", 35, 0.97),
        ("Sikar Mandi", 100, 0.95),
    ],
    "Kolhapur": [
        ("Kolhapur APMC", 0, 1.02),
        ("Sangli Mandi", 50, 1.00),
        ("Solapur Market", 120, 0.96),
    ],
}

# Default mandis for unknown locations
_DEFAULT_MANDIS: list[tuple[str, float, float]] = [
    ("Local Mandi", 0, 1.00),
    ("District Market Yard", 30, 0.97),
    ("Nearest APMC", 60, 0.95),
]


# =====================================================================
#  INTERNAL HELPERS
# =====================================================================


def _deterministic_jitter(seed_str: str, amplitude: float) -> float:
    """Produce a deterministic float in [-amplitude, +amplitude] from a seed string.

    Uses MD5 hash → stable across runs for the same date+crop+location.
    """
    h = hashlib.md5(seed_str.encode(), usedforsecurity=False).hexdigest()
    normalized = int(h[:8], 16) / 0xFFFFFFFF  # 0..1
    return (normalized * 2 - 1) * amplitude


def _simulate_price(
    base: float,
    volatility: float,
    peak_months: list[int],
    date: datetime,
    location: str = "",
) -> float:
    """Deterministic daily price for a crop at a date.

    Combines:
    - seasonal sine wave (peak at crop's peak months)
    - small daily jitter (hash-based for reproducibility)
    """
    # Seasonal component: peak at average of peak months
    avg_peak = sum(peak_months) / len(peak_months)
    seasonal = math.sin(2 * math.pi * (date.month - avg_peak) / 12) * volatility * base

    # Daily jitter (small, deterministic)
    seed = f"{date.isoformat()[:10]}:{location}:{base}"
    jitter = _deterministic_jitter(seed, volatility * base * 0.3)

    return round(max(base * 0.5, base + seasonal + jitter), 2)


def _get_price_history(
    crop_info: dict[str, Any],
    location: str,
    days: int = 7,
    ref_date: datetime | None = None,
) -> list[dict[str, object]]:
    """Build a list of {label, price} for the last *days* days."""
    now = ref_date or datetime.now(UTC)
    history: list[dict[str, object]] = []
    labels = [
        "Today",
        "Yesterday",
        "2 days ago",
        "3 days ago",
        "4 days ago",
        "5 days ago",
        "6 days ago",
    ]

    for i in range(days):
        d = now - timedelta(days=i)
        price = _simulate_price(
            crop_info["base_price"],
            crop_info["volatility"],
            crop_info["seasonal_peak_months"],
            d,
            location,
        )
        label = labels[i] if i < len(labels) else f"{i} days ago"
        history.append({"label": label, "price": price})

    return history


def _compute_trend(current: float, seven_day_avg: float) -> str:
    """Compare current price to 7-day average → trend label."""
    if seven_day_avg == 0:
        return "Stable"
    pct = ((current - seven_day_avg) / seven_day_avg) * 100
    if pct > 2:
        return "Increasing"
    if pct < -2:
        return "Decreasing"
    return "Stable"


def _predict_next_week(history: list[dict[str, object]]) -> float:
    """Simple linear extrapolation from the 7-day history.

    Fits a line through the daily prices and projects 7 days forward.
    """
    prices = [float(h["price"]) for h in history]
    n = len(prices)
    if n < 2:
        return prices[0] if prices else 0

    # prices[0] = today, prices[-1] = oldest → reverse for time order
    ordered = list(reversed(prices))
    x_mean = (n - 1) / 2
    y_mean = sum(ordered) / n

    num = sum((i - x_mean) * (ordered[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    slope = num / den if den != 0 else 0

    # Project 7 days ahead from the latest point
    predicted = ordered[-1] + slope * 7
    return round(max(0, predicted), 2)


def _decide_recommendation(
    current: float,
    seven_day_avg: float,
    trend: str,
    predicted: float,
) -> str:
    """Sell / Hold decision logic.

    - Price rising        → Hold for 3-5 days
    - Price peaked / flat → Sell now at current level
    - Falling rapidly     → Sell immediately
    """
    if trend == "Increasing" and predicted > current:
        return "Hold for 3\u20135 days \u2014 prices still rising"
    if trend == "Decreasing" and predicted < current * 0.97:
        return "Sell immediately \u2014 prices falling rapidly"
    if trend == "Decreasing":
        return "Sell now \u2014 prices are declining"
    # Stable or peaked
    if predicted <= current:
        return "Sell now \u2014 prices appear to have peaked"
    return "Monitor market \u2014 prices are stable"


def _build_nearby_mandis(
    location: str,
    crop_info: dict[str, Any],
    ref_date: datetime | None = None,
) -> list[dict[str, Any]]:
    """Look up nearby mandis and compute their current prices."""
    now = ref_date or datetime.now(UTC)
    mandis_raw = _MANDI_MAP.get(location, _DEFAULT_MANDIS)
    result: list[dict[str, Any]] = []

    for name, dist, offset in mandis_raw:
        price = (
            _simulate_price(
                crop_info["base_price"],
                crop_info["volatility"],
                crop_info["seasonal_peak_months"],
                now,
                name,
            )
            * offset
        )
        result.append(
            {
                "mandi": name,
                "price": round(price, 2),
                "distance_km": dist if dist > 0 else None,
            }
        )

    return result


def _generate_notes(
    crop: str,
    trend: str,
    recommendation: str,
    current: float,
    seven_day_avg: float,
    quantity: float | None,
) -> list[str]:
    """Generate advisory notes."""
    notes: list[str] = []

    if trend == "Increasing":
        notes.append(
            f"{crop} prices are trending upward \u2014 consider selling in batches "
            f"to capture gains over the next few days"
        )
    elif trend == "Decreasing":
        notes.append(
            f"{crop} prices are declining \u2014 explore storage options or "
            f"forward contracts to lock in prices"
        )
    else:
        notes.append(f"{crop} prices are stable \u2014 good time to sell at current levels")

    if quantity and quantity > 50:
        notes.append(
            f"Large quantity ({quantity} quintals) \u2014 consider splitting into "
            f"2\u20133 batches across different mandis for best average price"
        )

    notes.append("Compare prices across nearby mandis before finalizing the sale")
    notes.append(
        "Check government MSP (Minimum Support Price) to ensure you get "
        "at least the guaranteed price"
    )

    if "hold" in recommendation.lower():
        notes.append(
            "Ensure proper storage (moisture < 14%, pest protection) while " "holding stock"
        )

    return notes


# =====================================================================
#  MAIN ENTRY POINT
# =====================================================================


def analyze_market(
    crop: str = "Rice",
    location: str = "Guntur",
    quantity: float | None = None,
) -> dict[str, Any]:
    """Full market intelligence — prices, trend, prediction & sell/hold advice.

    Synchronous — no external I/O.

    Args:
        crop: Crop name (title-cased).
        location: Farmer's mandi / district.
        quantity: Quantity in quintals (optional).

    Returns:
        Dict matching ``MarketResponse`` schema.
    """
    crop = crop.strip().title()
    location = location.strip().title()

    crop_info = _CROP_PRICES.get(crop, _DEFAULT_CROP_PRICE)
    now = datetime.now(UTC)

    # 1. Price history (last 7 days)
    history = _get_price_history(crop_info, location, days=7, ref_date=now)

    current_price = history[0]["price"]
    prices = [float(h["price"]) for h in history]
    seven_day_avg = round(sum(prices) / len(prices), 2)

    # 2. Trend analysis
    trend = _compute_trend(float(current_price), seven_day_avg)

    # 3. Next-week prediction
    predicted = _predict_next_week(history)

    # 4. Sell / Hold
    recommendation = _decide_recommendation(float(current_price), seven_day_avg, trend, predicted)

    # 5. Nearby mandis
    nearby = _build_nearby_mandis(location, crop_info, ref_date=now)

    # 6. Advisory notes
    notes = _generate_notes(
        crop, trend, recommendation, float(current_price), seven_day_avg, quantity
    )

    return {
        "current_price": float(current_price),
        "unit": "\u20b9/quintal",
        "seven_day_avg": seven_day_avg,
        "trend": trend,
        "recommendation": recommendation,
        "expected_price_next_week": predicted,
        "nearby_mandis": nearby,
        "price_history": history,
        "notes": notes,
        # Backward compat for advisory engine
        "sell_recommendation": recommendation,
    }
