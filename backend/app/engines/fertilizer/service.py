"""Fertilizer Optimization Engine — deficiency-driven recommendation service.

Pure service layer (no I/O):
1. Crop nutrient requirement lookup (30 Indian crops)
2. Match soil deficiencies with crop nutrient needs → severity
3. Map deficiency + severity → fertilizer products + quantities
4. Build application schedule & advisory notes
"""

from __future__ import annotations

from typing import Any

# ── Exception ────────────────────────────────────────────────────


class FertilizerEngineError(Exception):
    """Raised when fertilizer recommendation fails."""


# ── Hectare / Acre Conversion ────────────────────────────────────

_HA_PER_ACRE = 0.404686
_ACRES_PER_HA = 2.47105


# ── Crop Nutrient Requirement Table ──────────────────────────────
# Need level: "High" / "Medium" / "Low" for each of N, P, K.
# Aligned with CROP_DB names in the Crop Engine.

_CROP_NUTRIENTS: dict[str, dict[str, str]] = {
    "Rice": {"N": "High", "P": "Medium", "K": "Medium"},
    "Wheat": {"N": "High", "P": "Medium", "K": "Medium"},
    "Maize": {"N": "High", "P": "Medium", "K": "Medium"},
    "Red Chilli": {"N": "High", "P": "Medium", "K": "High"},
    "Cotton": {"N": "High", "P": "Medium", "K": "High"},
    "Groundnut": {"N": "Low", "P": "Medium", "K": "Medium"},
    "Soybean": {"N": "Low", "P": "Medium", "K": "Medium"},
    "Sugarcane": {"N": "High", "P": "Medium", "K": "High"},
    "Tobacco": {"N": "Medium", "P": "Medium", "K": "Medium"},
    "Turmeric": {"N": "High", "P": "Medium", "K": "High"},
    "Sunflower": {"N": "Medium", "P": "Medium", "K": "Medium"},
    "Sorghum": {"N": "Medium", "P": "Low", "K": "Low"},
    "Bajra": {"N": "Medium", "P": "Low", "K": "Low"},
    "Pulses (Moong)": {"N": "Low", "P": "Medium", "K": "Low"},
    "Pulses (Urad)": {"N": "Low", "P": "Medium", "K": "Low"},
    "Chickpea": {"N": "Low", "P": "Medium", "K": "Medium"},
    "Lentil": {"N": "Low", "P": "Medium", "K": "Low"},
    "Mustard": {"N": "Medium", "P": "Medium", "K": "Low"},
    "Potato": {"N": "High", "P": "High", "K": "High"},
    "Onion": {"N": "High", "P": "Medium", "K": "High"},
    "Tomato": {"N": "High", "P": "High", "K": "High"},
    "Banana": {"N": "High", "P": "Medium", "K": "High"},
    "Coconut": {"N": "Medium", "P": "Low", "K": "High"},
    "Mango": {"N": "Medium", "P": "Medium", "K": "Medium"},
    "Tea": {"N": "High", "P": "Low", "K": "Medium"},
    "Coffee": {"N": "Medium", "P": "Low", "K": "Medium"},
    "Jute": {"N": "Medium", "P": "Low", "K": "Low"},
    "Sesame": {"N": "Low", "P": "Low", "K": "Low"},
    "Castor": {"N": "Low", "P": "Low", "K": "Low"},
}

# Fallback for crops not in the table
_DEFAULT_CROP_NEED: dict[str, str] = {"N": "Medium", "P": "Medium", "K": "Medium"}


# ── Deficiency → Nutrient Key Mapping ────────────────────────────
# Maps soil deficiency labels (from Soil Engine) to canonical nutrient keys.

_DEFICIENCY_NUTRIENT: dict[str, str] = {
    "nitrogen": "N",
    "phosphorus": "P",
    "potassium": "K",
}


# ── Fertilizer Product Mapping ───────────────────────────────────
# Maps nutrient key → primary product(s).

_NUTRIENT_PRODUCTS: dict[str, list[str]] = {
    "N": ["Urea"],
    "P": ["DAP", "SSP"],
    "K": ["MOP"],
}

# When multiple nutrient deficiencies exist, add a blended mix
_BLEND_PRODUCT = "NPK 10-26-26"


# ── Severity-Based Quantity (kg per acre) ────────────────────────
# The combination of deficiency presence + crop requirement level
# determines a severity and base dosage.

_SEVERITY_QUANTITY: dict[str, float] = {
    "High": 60.0,
    "Medium": 50.0,
    "Low": 30.0,
}


# ── Application Schedule Templates ──────────────────────────────

_SCHEDULES: dict[str, list[dict[str, Any]]] = {
    "Rice": [
        {
            "stage": "Basal (at transplanting)",
            "timing": "Day 0",
            "products": ["DAP", "MOP"],
            "notes": "Apply 50% P and 50% K as basal; incorporate before transplanting",
        },
        {
            "stage": "Tillering",
            "timing": "21-25 days after transplanting",
            "products": ["Urea"],
            "notes": "Apply 50% Urea; broadcast in standing water",
        },
        {
            "stage": "Panicle initiation",
            "timing": "45-50 days after transplanting",
            "products": ["Urea", "MOP"],
            "notes": "Apply remaining Urea and 50% MOP; keep field moist",
        },
    ],
    "Wheat": [
        {
            "stage": "Sowing",
            "timing": "Day 0",
            "products": ["DAP", "MOP"],
            "notes": "Apply full P and K with seed drill at sowing",
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
    "Maize": [
        {
            "stage": "Sowing",
            "timing": "Day 0",
            "products": ["DAP", "MOP"],
            "notes": "Band-place DAP and MOP 5 cm from seed row",
        },
        {
            "stage": "Knee-high (V6)",
            "timing": "30-35 days after sowing",
            "products": ["Urea"],
            "notes": "Side-dress 60% Urea along rows",
        },
        {
            "stage": "Tasseling",
            "timing": "55-60 days after sowing",
            "products": ["Urea"],
            "notes": "Apply remaining Urea; fertigate if possible",
        },
    ],
    "Red Chilli": [
        {
            "stage": "Transplanting",
            "timing": "Day 0",
            "products": ["DAP", "MOP"],
            "notes": "Apply full P and 50% K as basal before transplanting",
        },
        {
            "stage": "Vegetative growth",
            "timing": "30 days after transplanting",
            "products": ["Urea"],
            "notes": "Apply 50% Urea as side-dress along rows",
        },
        {
            "stage": "Flowering & fruiting",
            "timing": "60 days after transplanting",
            "products": ["Urea", "MOP"],
            "notes": "Apply remaining Urea and 50% MOP; fertigate if possible",
        },
    ],
    "Cotton": [
        {
            "stage": "Sowing",
            "timing": "Day 0",
            "products": ["DAP", "MOP"],
            "notes": "Apply full P and 50% K as basal at sowing",
        },
        {
            "stage": "Square formation",
            "timing": "35-40 days after sowing",
            "products": ["Urea"],
            "notes": "Apply 50% Urea as side-dress",
        },
        {
            "stage": "Boll development",
            "timing": "70-80 days after sowing",
            "products": ["Urea", "MOP"],
            "notes": "Apply remaining Urea and 50% MOP",
        },
    ],
    "Sugarcane": [
        {
            "stage": "Planting",
            "timing": "Day 0",
            "products": ["DAP", "MOP"],
            "notes": "Apply full P and 33% K in furrows at planting",
        },
        {
            "stage": "Tillering",
            "timing": "45-60 days after planting",
            "products": ["Urea", "MOP"],
            "notes": "Apply 50% Urea and 33% MOP; earth up after application",
        },
        {
            "stage": "Grand growth",
            "timing": "90-120 days after planting",
            "products": ["Urea", "MOP"],
            "notes": "Apply remaining Urea and 34% MOP",
        },
    ],
    "Potato": [
        {
            "stage": "Planting",
            "timing": "Day 0",
            "products": ["DAP", "MOP"],
            "notes": "Apply full P and 50% K in rows before planting tubers",
        },
        {
            "stage": "Stolon initiation",
            "timing": "25-30 days after planting",
            "products": ["Urea"],
            "notes": "Apply 50% Urea and earth up",
        },
        {
            "stage": "Tuber bulking",
            "timing": "45-50 days after planting",
            "products": ["Urea", "MOP"],
            "notes": "Apply remaining Urea and 50% MOP; ensure irrigation",
        },
    ],
    "Tomato": [
        {
            "stage": "Transplanting",
            "timing": "Day 0",
            "products": ["DAP", "MOP"],
            "notes": "Apply full P and 50% K as basal",
        },
        {
            "stage": "Vegetative growth",
            "timing": "21-25 days after transplanting",
            "products": ["Urea"],
            "notes": "Apply 50% Urea; side-dress along rows",
        },
        {
            "stage": "Fruiting",
            "timing": "45-50 days after transplanting",
            "products": ["Urea", "MOP"],
            "notes": "Apply remaining Urea and 50% MOP through drip or side-dress",
        },
    ],
    "Banana": [
        {
            "stage": "Planting",
            "timing": "Day 0",
            "products": ["DAP", "MOP"],
            "notes": "Apply full P and 25% K in pit at planting",
        },
        {
            "stage": "Vegetative (3 months)",
            "timing": "90 days after planting",
            "products": ["Urea", "MOP"],
            "notes": "Apply 33% Urea and 25% MOP as ring application",
        },
        {
            "stage": "Shooting (5 months)",
            "timing": "150 days after planting",
            "products": ["Urea", "MOP"],
            "notes": "Apply 33% Urea and 25% MOP",
        },
        {
            "stage": "Bunch development",
            "timing": "210 days after planting",
            "products": ["Urea", "MOP"],
            "notes": "Apply remaining Urea and 25% MOP",
        },
    ],
    "Soybean": [
        {
            "stage": "Sowing",
            "timing": "Day 0",
            "products": ["DAP", "MOP"],
            "notes": "Apply full P and K as basal. Inoculate seed with Rhizobium",
        },
        {
            "stage": "Flowering (R1)",
            "timing": "35-40 days after sowing",
            "products": ["Urea"],
            "notes": "Light N top-dress only if plants show N deficiency",
        },
    ],
    "Onion": [
        {
            "stage": "Transplanting",
            "timing": "Day 0",
            "products": ["DAP", "MOP"],
            "notes": "Apply full P and 50% K as basal before transplanting",
        },
        {
            "stage": "Vegetative growth",
            "timing": "30 days after transplanting",
            "products": ["Urea"],
            "notes": "Apply 50% Urea; top-dress along rows",
        },
        {
            "stage": "Bulb formation",
            "timing": "50-55 days after transplanting",
            "products": ["Urea", "MOP"],
            "notes": "Apply remaining Urea and 50% MOP",
        },
    ],
}

# Default 3-stage schedule for crops without a specific template
_DEFAULT_SCHEDULE: list[dict[str, Any]] = [
    {
        "stage": "Basal (at sowing/planting)",
        "timing": "Day 0",
        "products": ["DAP", "MOP"],
        "notes": "Apply full P and 50% K as basal dose before sowing",
    },
    {
        "stage": "Top-dress 1",
        "timing": "30 days after sowing",
        "products": ["Urea"],
        "notes": "Apply 50% Urea as side-dress or top-dress",
    },
    {
        "stage": "Top-dress 2",
        "timing": "55-60 days after sowing",
        "products": ["Urea", "MOP"],
        "notes": "Apply remaining Urea and 50% MOP",
    },
]


# =====================================================================
#  INTERNAL HELPERS
# =====================================================================


def _resolve_crop_needs(crop: str) -> dict[str, str]:
    """Look up N/P/K need levels for a crop (title-cased)."""
    return _CROP_NUTRIENTS.get(crop, _DEFAULT_CROP_NEED)


def _parse_deficiency(label: str) -> str | None:
    """Extract canonical nutrient key from a deficiency label.

    Handles labels like "Nitrogen", "Phosphorus", "Potassium",
    "pH (too acidic)", "pH (too alkaline)", etc.
    Returns 'N', 'P', 'K', or *None* for non-nutrient deficiencies.
    """
    low = label.strip().lower()
    for keyword, key in _DEFICIENCY_NUTRIENT.items():
        if keyword in low:
            return key
    return None


def _determine_severity(
    deficiencies: list[str],
    crop_needs: dict[str, str],
) -> dict[str, str]:
    """Cross-reference soil deficiencies with crop requirements.

    Returns ``{nutrient_key: severity_level}`` where severity is
    "High" (crop needs High + soil deficient),
    "Medium" (crop needs Medium + soil deficient), or
    "Low" (crop needs Low + soil deficient).
    """
    severity: dict[str, str] = {}
    for label in deficiencies:
        nutrient = _parse_deficiency(label)
        if nutrient is None:
            continue  # pH or unknown — handled in notes
        need = crop_needs.get(nutrient, "Medium")
        severity[nutrient] = need  # severity = crop need level
    return severity


def _select_fertilizers(severity: dict[str, str]) -> list[str]:
    """Map nutrient deficiencies → fertilizer product names."""
    products: list[str] = []
    seen: set[str] = set()

    for nutrient in severity:
        for product in _NUTRIENT_PRODUCTS.get(nutrient, []):
            if product not in seen:
                products.append(product)
                seen.add(product)

    # If multiple nutrient deficiencies, add blended NPK mix
    if len(severity) >= 2 and _BLEND_PRODUCT not in seen:
        products.append(_BLEND_PRODUCT)

    return products


def _calculate_quantities(
    severity: dict[str, str],
    fertilizers: list[str],
    land_area_acres: float,
) -> tuple[dict[str, str], dict[str, str]]:
    """Calculate per-acre and total quantities for each fertilizer.

    Uses severity-based dosage: High → 60 kg/acre, Medium → 50 kg/acre,
    Low → 30 kg/acre.
    """
    # Compute average severity for blended products
    if severity:
        avg_qty = round(
            sum(_SEVERITY_QUANTITY[s] for s in severity.values()) / len(severity),
            1,
        )
    else:
        avg_qty = _SEVERITY_QUANTITY["Medium"]

    per_acre: dict[str, str] = {}
    total: dict[str, str] = {}

    for product in fertilizers:
        # Determine which nutrient this product primarily serves
        qty_per_acre: float | None = None
        for nutrient, prods in _NUTRIENT_PRODUCTS.items():
            if product in prods and nutrient in severity:
                qty_per_acre = _SEVERITY_QUANTITY[severity[nutrient]]
                break

        # Blended product or unmatched → use average
        if qty_per_acre is None:
            qty_per_acre = avg_qty

        total_qty = round(qty_per_acre * land_area_acres, 1)
        per_acre[product] = f"{qty_per_acre} kg"
        total[product] = f"{total_qty} kg"

    return per_acre, total


def _build_schedule(crop: str, fertilizers: list[str]) -> list[dict[str, Any]]:
    """Select the application schedule template for the crop.

    Filters schedule steps to only include products that were recommended.
    """
    template = _SCHEDULES.get(crop, _DEFAULT_SCHEDULE)

    # Filter each step's products to those actually recommended
    fert_set = set(fertilizers)
    schedule: list[dict[str, Any]] = []
    for step in template:
        relevant = [p for p in step["products"] if p in fert_set]
        if not relevant:
            # If none of the step's products are needed, keep step but
            # note "No application required at this stage"
            schedule.append(
                {
                    "stage": step["stage"],
                    "timing": step["timing"],
                    "products": [],
                    "notes": "No application required at this stage",
                }
            )
        else:
            schedule.append(
                {
                    "stage": step["stage"],
                    "timing": step["timing"],
                    "products": relevant,
                    "notes": step["notes"],
                }
            )
    return schedule


def _generate_notes(
    deficiencies: list[str],
    soil_health: str,
    ph_status: str,
    crop: str,
    severity: dict[str, str],
) -> list[str]:
    """Generate advisory notes based on soil conditions and crop."""
    notes: list[str] = []

    # pH-based tips
    ph_low = ph_status.lower()
    if "acidic" in ph_low:
        notes.append(
            "Apply agricultural lime (2-3 t/ha) 2-3 weeks before fertilizer "
            "to raise pH and improve nutrient availability"
        )
    elif "alkaline" in ph_low:
        notes.append(
            "Use ammonium-based fertilizers (e.g., Ammonium Sulfate) instead "
            "of Urea; consider gypsum application to lower pH"
        )

    # Soil health tips
    health_low = soil_health.lower()
    if health_low in ("poor", "low"):
        notes.append(
            "Soil health is low — supplement with organic manure (FYM: 5-10 t/ha) "
            "and consider green manuring to improve soil structure"
        )
    elif health_low == "medium":
        notes.append(
            "Maintain soil health with crop rotation and periodic organic " "matter additions"
        )

    # Severity-specific tips
    for nutrient, sev in severity.items():
        label = {"N": "Nitrogen", "P": "Phosphorus", "K": "Potassium"}.get(nutrient, nutrient)
        if sev == "High":
            notes.append(
                f"Strong {label} supplementation required — split application "
                f"across growth stages for maximum uptake"
            )

    # General best practices
    notes.append(
        f"Split nitrogen application reduces losses and increases " f"{crop} uptake efficiency"
    )
    notes.append("Avoid fertilizer application before heavy rain to prevent leaching")

    # Crop-specific
    if crop in ("Soybean", "Groundnut", "Chickpea", "Lentil", "Pulses (Moong)", "Pulses (Urad)"):
        notes.append(
            "Legume crop — use Rhizobium inoculant for seed treatment to "
            "reduce N fertilizer requirement by 60-80%"
        )

    # No deficiencies
    if not deficiencies:
        notes.insert(
            0,
            "No nutrient deficiencies detected — apply a maintenance dose "
            "of NPK based on crop requirement",
        )

    return notes


# =====================================================================
#  MAIN ENTRY POINT
# =====================================================================


def recommend_fertilizer(
    deficiencies: list[str] | None = None,
    soil_health: str = "Medium",
    ph_status: str = "Neutral",
    selected_crop: str = "Rice",
    land_area: float = 1.0,
    unit: str = "acre",
) -> dict[str, Any]:
    """Deficiency-driven fertilizer recommendation.

    Synchronous — no I/O required.

    Args:
        deficiencies: Nutrient deficiency labels from Soil Engine
            (e.g. ``["Nitrogen", "Potassium"]``).
        soil_health: Overall soil health label (Poor/Low/Medium/Good/Excellent).
        ph_status: pH classification from Soil Engine.
        selected_crop: Crop name (title-cased).
        land_area: Farm area value.
        unit: ``"acre"`` or ``"hectare"``.

    Returns:
        Dict matching ``FertilizerResponse`` schema.
    """
    deficiencies = deficiencies or []
    crop = selected_crop.strip().title()

    # Convert land_area to acres for internal calculation
    land_area_acres = land_area * _ACRES_PER_HA if unit.lower() == "hectare" else land_area

    # 1. Crop nutrient requirement lookup
    crop_needs = _resolve_crop_needs(crop)

    # 2. Match deficiencies with crop requirements → severity
    severity = _determine_severity(deficiencies, crop_needs)

    # 3. Map deficiency + severity → fertilizer products
    fertilizers = _select_fertilizers(severity)

    # If no deficiencies but crop has needs, recommend maintenance NPK
    if not fertilizers:
        fertilizers = [_BLEND_PRODUCT]

    # 4. Quantity calculation
    per_acre, total = _calculate_quantities(severity, fertilizers, land_area_acres)

    # 5. Application schedule
    schedule = _build_schedule(crop, fertilizers)

    # 6. Advisory notes
    notes = _generate_notes(deficiencies, soil_health, ph_status, crop, severity)

    return {
        "fertilizers": fertilizers,
        "quantity_per_acre": per_acre,
        "total_required": total,
        "schedule": schedule,
        "notes": notes,
        # Backward compat for advisory engine
        "application_schedule": schedule,
    }
