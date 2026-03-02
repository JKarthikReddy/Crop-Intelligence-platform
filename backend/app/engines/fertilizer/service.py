"""Fertilizer Engine service — NPK calculation, product selection, and scheduling.

Pure service layer:
- Crop-specific NPK requirement tables
- Soil-adjusted fertilizer dosage calculation
- Product mapping (Urea, DAP, MOP, etc.)
- Application schedule by growth stage
- Cost estimation
"""

from typing import Any

# ── Crop NPK Requirements (kg/ha per ton of yield) ──────────────
_CROP_NPK: dict[str, dict[str, float]] = {
    "rice": {"N": 22, "P2O5": 10, "K2O": 24},
    "wheat": {"N": 25, "P2O5": 12, "K2O": 20},
    "maize": {"N": 28, "P2O5": 14, "K2O": 22},
    "soybean": {"N": 8, "P2O5": 16, "K2O": 20},  # Soybean fixes N
}

# ── Soil Adjustment Factors ──────────────────────────────────────
# pH-based nutrient efficiency multipliers
_PH_N_EFFICIENCY: dict[str, float] = {
    "acidic": 0.85,
    "neutral": 1.0,
    "alkaline": 0.90,
}

# ── Fertilizer Products Database ─────────────────────────────────
_PRODUCTS: dict[str, dict[str, Any]] = {
    "Urea": {"npk": "46-0-0", "N": 0.46, "P": 0.0, "K": 0.0, "price_per_kg": 0.35},
    "DAP": {"npk": "18-46-0", "N": 0.18, "P": 0.46, "K": 0.0, "price_per_kg": 0.55},
    "MOP": {"npk": "0-0-60", "N": 0.0, "P": 0.0, "K": 0.60, "price_per_kg": 0.40},
    "NPK 10-26-26": {"npk": "10-26-26", "N": 0.10, "P": 0.26, "K": 0.26, "price_per_kg": 0.48},
    "Ammonium Sulfate": {"npk": "21-0-0", "N": 0.21, "P": 0.0, "K": 0.0, "price_per_kg": 0.28},
    "SSP": {"npk": "0-16-0", "N": 0.0, "P": 0.16, "K": 0.0, "price_per_kg": 0.22},
}


class FertilizerEngineError(Exception):
    """Raised when fertilizer calculation fails."""


def _ph_category(ph: float | None) -> str:
    """Classify pH into broad category for adjustment."""
    if ph is None:
        return "neutral"
    if ph < 6.0:
        return "acidic"
    if ph > 7.5:
        return "alkaline"
    return "neutral"


def calculate_npk(
    crop_type: str,
    target_yield: float,
    soil_ph: float | None,
    organic_carbon: int | None,
    area_hectares: float,
) -> dict[str, Any]:
    """Calculate NPK requirements adjusted for soil conditions."""
    crop_req = _CROP_NPK.get(crop_type, _CROP_NPK["rice"])

    # Base NPK from crop requirement x target yield
    base_n = crop_req["N"] * target_yield
    base_p = crop_req["P2O5"] * target_yield
    base_k = crop_req["K2O"] * target_yield

    # pH adjustment for N efficiency
    ph_cat = _ph_category(soil_ph)
    n_efficiency = _PH_N_EFFICIENCY.get(ph_cat, 1.0)
    adjusted_n = base_n / n_efficiency

    # Organic carbon adjustment (high OC reduces N need)
    oc = organic_carbon or 30
    if oc > 50:
        adjusted_n *= 0.85  # OC supplies some N
    elif oc < 20:
        adjusted_n *= 1.10  # Low OC = need more N

    # Round all values
    n_per_ha = round(adjusted_n, 1)
    p_per_ha = round(base_p, 1)
    k_per_ha = round(base_k, 1)

    return {
        "nitrogen_kg_per_ha": n_per_ha,
        "phosphorus_kg_per_ha": p_per_ha,
        "potassium_kg_per_ha": k_per_ha,
        "total_nitrogen_kg": round(n_per_ha * area_hectares, 1),
        "total_phosphorus_kg": round(p_per_ha * area_hectares, 1),
        "total_potassium_kg": round(k_per_ha * area_hectares, 1),
    }


def select_products(npk: dict[str, Any], area_hectares: float) -> list[dict[str, Any]]:
    """Select optimal fertilizer products to meet NPK targets."""
    products: list[dict[str, Any]] = []

    n_need = npk["nitrogen_kg_per_ha"]
    p_need = npk["phosphorus_kg_per_ha"]
    k_need = npk["potassium_kg_per_ha"]

    # DAP first (provides P + some N)
    if p_need > 0:
        dap_info = _PRODUCTS["DAP"]
        dap_qty = round(p_need / dap_info["P"], 1)
        n_from_dap = dap_qty * dap_info["N"]
        products.append(
            {
                "name": "DAP",
                "composition": dap_info["npk"],
                "quantity_kg_per_ha": dap_qty,
                "total_quantity_kg": round(dap_qty * area_hectares, 1),
                "estimated_cost_usd": round(dap_qty * area_hectares * dap_info["price_per_kg"], 2),
            }
        )
        n_need = max(0, n_need - n_from_dap)

    # Urea for remaining N
    if n_need > 0:
        urea_info = _PRODUCTS["Urea"]
        urea_qty = round(n_need / urea_info["N"], 1)
        products.append(
            {
                "name": "Urea",
                "composition": urea_info["npk"],
                "quantity_kg_per_ha": urea_qty,
                "total_quantity_kg": round(urea_qty * area_hectares, 1),
                "estimated_cost_usd": round(
                    urea_qty * area_hectares * urea_info["price_per_kg"], 2
                ),
            }
        )

    # MOP for K
    if k_need > 0:
        mop_info = _PRODUCTS["MOP"]
        mop_qty = round(k_need / mop_info["K"], 1)
        products.append(
            {
                "name": "MOP",
                "composition": mop_info["npk"],
                "quantity_kg_per_ha": mop_qty,
                "total_quantity_kg": round(mop_qty * area_hectares, 1),
                "estimated_cost_usd": round(mop_qty * area_hectares * mop_info["price_per_kg"], 2),
            }
        )

    return products


def build_schedule(crop_type: str) -> list[dict[str, Any]]:
    """Generate application schedule by crop growth stage."""
    schedules: dict[str, list[dict[str, Any]]] = {
        "rice": [
            {
                "stage": "Basal (at transplanting)",
                "timing": "Day 0",
                "products": ["DAP", "MOP"],
                "notes": "Apply 50% P and 50% K as basal; incorporate into soil before transplanting",
            },
            {
                "stage": "Tillering",
                "timing": "21-25 days after transplanting",
                "products": ["Urea"],
                "notes": "Apply 50% of Urea dose; broadcast in standing water",
            },
            {
                "stage": "Panicle initiation",
                "timing": "45-50 days after transplanting",
                "products": ["Urea", "MOP"],
                "notes": "Apply remaining Urea and 50% MOP; ensure field is moist",
            },
        ],
        "wheat": [
            {
                "stage": "Sowing",
                "timing": "Day 0",
                "products": ["DAP", "MOP"],
                "notes": "Apply full P and K dose with seed drill at sowing",
            },
            {
                "stage": "First irrigation (CRI)",
                "timing": "21 days after sowing",
                "products": ["Urea"],
                "notes": "Apply 50% N just before first irrigation",
            },
            {
                "stage": "Heading",
                "timing": "65-70 days after sowing",
                "products": ["Urea"],
                "notes": "Apply remaining 50% N; foliar spray if needed",
            },
        ],
        "maize": [
            {
                "stage": "Sowing",
                "timing": "Day 0",
                "products": ["DAP", "MOP"],
                "notes": "Band-place DAP and MOP 5cm from seed row",
            },
            {
                "stage": "Knee-high (V6)",
                "timing": "30-35 days after sowing",
                "products": ["Urea"],
                "notes": "Side-dress 60% of Urea dose along rows",
            },
            {
                "stage": "Tasseling",
                "timing": "55-60 days after sowing",
                "products": ["Urea"],
                "notes": "Apply remaining Urea; fertigate if possible",
            },
        ],
        "soybean": [
            {
                "stage": "Sowing",
                "timing": "Day 0",
                "products": ["DAP", "MOP"],
                "notes": "Apply full P and K as basal. Inoculate seed with Rhizobium for N fixation",
            },
            {
                "stage": "Flowering (R1)",
                "timing": "35-40 days after sowing",
                "products": ["Urea"],
                "notes": "Light N top-dress only if plants show N deficiency",
            },
        ],
    }
    return schedules.get(crop_type, schedules["rice"])


def generate_fertilizer_recommendations(
    crop_type: str,
    soil_ph: float | None,
    organic_carbon: int | None,
) -> list[str]:
    """Generate fertilizer management tips."""
    recs: list[str] = []

    if soil_ph is not None:
        if soil_ph < 5.5:
            recs.append("Apply lime 2-3 weeks before fertilizer to improve nutrient availability")
        elif soil_ph > 8.0:
            recs.append(
                "Use ammonium-based fertilizers (e.g., Ammonium Sulfate) instead of Urea in alkaline soils"
            )

    oc = organic_carbon or 30
    if oc < 20:
        recs.append("Low organic matter — supplement with organic manure (FYM: 5-10 t/ha)")

    recs.append(
        f"Split nitrogen application reduces losses and increases {crop_type} uptake efficiency"
    )
    recs.append("Avoid fertilizer application before heavy rain to prevent leaching")

    if crop_type == "soybean":
        recs.append(
            "Use Rhizobium inoculant for seed treatment — reduces N fertilizer need by 60-80%"
        )

    return recs


# ── Main Entry Point ─────────────────────────────────────────────


async def recommend_fertilizer(
    crop_type: str = "rice",
    target_yield: float = 5.0,
    soil_ph: float | None = None,
    organic_carbon: int | None = None,
    clay_percent: int | None = None,
    area_hectares: float = 1.0,
) -> dict[str, Any]:
    """Full fertilizer recommendation — NPK, products, schedule, and cost.

    Args:
        crop_type: Target crop.
        target_yield: Desired yield (t/ha).
        soil_ph: Soil pH (from Soil Engine).
        organic_carbon: SOC in g/dm³ (from Soil Engine).
        clay_percent: Clay in g/kg (from Soil Engine).
        area_hectares: Farm area for total quantity calculation.

    Returns:
        Complete fertilizer recommendation dict.
    """
    npk = calculate_npk(crop_type, target_yield, soil_ph, organic_carbon, area_hectares)
    products = select_products(npk, area_hectares)
    schedule = build_schedule(crop_type)
    recs = generate_fertilizer_recommendations(crop_type, soil_ph, organic_carbon)

    total_cost = sum(p["estimated_cost_usd"] for p in products)

    return {
        "npk_recommendation": npk,
        "products": products,
        "application_schedule": schedule,
        "cost_summary": {
            "total_fertilizer_cost_usd": round(total_cost, 2),
            "cost_per_hectare_usd": round(total_cost / max(area_hectares, 0.01), 2),
            "area_hectares": area_hectares,
        },
        "recommendations": recs,
    }
