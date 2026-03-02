"""Soil Engine service  -  diagnostic soil health analysis.

Pure diagnostic engine (no external API calls):
- Analyses farmer-provided NPK values against agronomic thresholds
- Classifies pH into detailed categories
- Detects nutrient deficiencies
- Computes composite soil health score (0-100) with breakdown
- Generates prioritised amendment recommendations
- Provides soil-type-specific insights and crop suitability
"""

from __future__ import annotations

from typing import Any

from loguru import logger


class SoilEngineError(Exception):
    """Raised when soil analysis fails."""


# ── Ideal Thresholds (kg/ha) ────────────────────────────────────
# Source: ICAR / NBSS&LUP general guidelines for Indian soils

_N_THRESHOLDS = {"deficient": 20, "low": 50, "adequate": 120, "high": 200}
_P_THRESHOLDS = {"deficient": 10, "low": 25, "adequate": 60, "high": 100}
_K_THRESHOLDS = {"deficient": 15, "low": 40, "adequate": 110, "high": 180}

_N_IDEAL_RANGE = "50 - 120 kg/ha"
_P_IDEAL_RANGE = "25 - 60 kg/ha"
_K_IDEAL_RANGE = "40 - 110 kg/ha"

_N_IDEAL_MID = 85.0
_P_IDEAL_MID = 42.5
_K_IDEAL_MID = 75.0

# ── Soil Type Knowledge Base ────────────────────────────────────

SOIL_TYPE_DB: dict[str, dict[str, Any]] = {
    "Alluvial": {
        "water_retention": "Moderate to High",
        "drainage": "Good",
        "fertility": "High",
        "best_crops": ["Rice", "Wheat", "Sugarcane", "Maize", "Pulses"],
        "management_notes": "Maintain organic matter; rotate crops to avoid nutrient depletion",
    },
    "Black": {
        "water_retention": "Very High",
        "drainage": "Poor",
        "fertility": "High",
        "best_crops": ["Cotton", "Soybean", "Sorghum", "Wheat", "Sunflower"],
        "management_notes": "Avoid waterlogging; add gypsum if sodic; deep ploughing helps",
    },
    "Red": {
        "water_retention": "Low",
        "drainage": "Good to Excessive",
        "fertility": "Low to Medium",
        "best_crops": ["Groundnut", "Millets", "Pulses", "Potato", "Tobacco"],
        "management_notes": "Requires regular fertilisation; add organic matter for retention",
    },
    "Laterite": {
        "water_retention": "Low",
        "drainage": "Excessive",
        "fertility": "Low",
        "best_crops": ["Cashew", "Tea", "Coffee", "Coconut", "Rubber"],
        "management_notes": "Heavily leached; needs lime and phosphorus amendments",
    },
    "Sandy": {
        "water_retention": "Very Low",
        "drainage": "Excessive",
        "fertility": "Low",
        "best_crops": ["Millets", "Barley", "Groundnut", "Pulses", "Watermelon"],
        "management_notes": "Frequent light irrigation; add organic compost for binding",
    },
    "Clayey": {
        "water_retention": "Very High",
        "drainage": "Poor",
        "fertility": "Medium to High",
        "best_crops": ["Rice", "Wheat", "Lentils", "Sugarcane", "Jute"],
        "management_notes": "Improve drainage with raised beds; avoid compaction",
    },
    "Loamy": {
        "water_retention": "Moderate",
        "drainage": "Good",
        "fertility": "High",
        "best_crops": ["Vegetables", "Cereals", "Fruits", "Cotton", "Sugarcane"],
        "management_notes": "Ideal soil; maintain with balanced fertilisation and rotation",
    },
    "Peaty": {
        "water_retention": "Very High",
        "drainage": "Poor",
        "fertility": "High (organic)",
        "best_crops": ["Rice", "Vegetables", "Jute", "Banana", "Spices"],
        "management_notes": "Manage water table; may be acidic  -  lime if needed",
    },
    "Saline": {
        "water_retention": "Moderate",
        "drainage": "Variable",
        "fertility": "Low (salt-affected)",
        "best_crops": ["Barley", "Cotton", "Beet", "Date Palm", "Salt-tolerant Rice"],
        "management_notes": "Leach salts with good irrigation; apply gypsum for reclamation",
    },
    "Other": {
        "water_retention": "Variable",
        "drainage": "Variable",
        "fertility": "Variable",
        "best_crops": ["Consult local extension for recommendations"],
        "management_notes": "Conduct detailed soil survey for specific management",
    },
}


# ── pH Classification ────────────────────────────────────────────


def classify_ph(ph: float) -> str:
    """Classify soil pH into agronomic categories.

    Returns a PhStatus value string.
    """
    if ph < 4.5:
        return "Strongly Acidic"
    if ph < 5.5:
        return "Acidic"
    if ph < 6.0:
        return "Slightly Acidic"
    if ph <= 7.5:
        return "Neutral"
    if ph <= 8.0:
        return "Slightly Alkaline"
    if ph <= 8.5:
        return "Alkaline"
    return "Strongly Alkaline"


# ── Nutrient Assessment ──────────────────────────────────────────


def _classify_nutrient(
    value: float,
    thresholds: dict[str, float],
) -> str:
    """Classify a nutrient level against thresholds."""
    if value < thresholds["deficient"]:
        return "Deficient"
    if value < thresholds["low"]:
        return "Low"
    if value <= thresholds["adequate"]:
        return "Adequate"
    if value <= thresholds["high"]:
        return "High"
    return "Excess"


def _deviation_pct(value: float, ideal_mid: float) -> float:
    """Percent deviation from ideal midpoint."""
    if ideal_mid == 0:
        return 0.0
    return round(((value - ideal_mid) / ideal_mid) * 100, 1)


def assess_nutrient(
    value: float,
    thresholds: dict[str, float],
    ideal_range: str,
    ideal_mid: float,
) -> dict[str, Any]:
    """Assess a single nutrient and return detail dict."""
    return {
        "value": value,
        "status": _classify_nutrient(value, thresholds),
        "ideal_range": ideal_range,
        "deviation_pct": _deviation_pct(value, ideal_mid),
    }


def assess_nutrients(
    nitrogen: float,
    phosphorus: float,
    potassium: float,
) -> dict[str, Any]:
    """Assess all three NPK nutrients."""
    return {
        "nitrogen": assess_nutrient(nitrogen, _N_THRESHOLDS, _N_IDEAL_RANGE, _N_IDEAL_MID),
        "phosphorus": assess_nutrient(phosphorus, _P_THRESHOLDS, _P_IDEAL_RANGE, _P_IDEAL_MID),
        "potassium": assess_nutrient(potassium, _K_THRESHOLDS, _K_IDEAL_RANGE, _K_IDEAL_MID),
    }


# ── Deficiency Detection ────────────────────────────────────────


def detect_deficiencies(
    nitrogen: float,
    phosphorus: float,
    potassium: float,
    ph: float,
) -> list[str]:
    """Detect nutrients that fall below ideal thresholds."""
    deficiencies: list[str] = []
    if nitrogen < _N_THRESHOLDS["low"]:
        deficiencies.append("Nitrogen")
    if phosphorus < _P_THRESHOLDS["low"]:
        deficiencies.append("Phosphorus")
    if potassium < _K_THRESHOLDS["low"]:
        deficiencies.append("Potassium")
    if ph < 5.5:
        deficiencies.append("pH (too acidic)")
    elif ph > 8.5:
        deficiencies.append("pH (too alkaline)")
    return deficiencies


# ── Soil Health Score ────────────────────────────────────────────


def _score_nutrient(value: float, thresholds: dict[str, float], max_score: float) -> float:
    """Score a nutrient (0 to max_score).

    Peak score when value is in the adequate range.
    """
    low = thresholds["low"]
    adequate = thresholds["adequate"]
    high = thresholds["high"]

    if low <= value <= adequate:
        # In ideal range → full score
        return max_score
    if value < thresholds["deficient"]:
        # Severely deficient → minimal score
        return max_score * 0.1
    if value < low:
        # Below ideal → proportional
        return max_score * (0.3 + 0.7 * (value / low))
    if value <= high:
        # Slightly above adequate → small penalty
        return max_score * 0.8
    # Excess → moderate penalty
    return max_score * 0.5


def _score_ph(ph: float) -> float:
    """Score pH on a 0-25 scale (optimal: 6.0-7.5)."""
    if 6.0 <= ph <= 7.5:
        return 25.0
    if 5.5 <= ph < 6.0 or 7.5 < ph <= 8.0:
        return 20.0
    if 5.0 <= ph < 5.5 or 8.0 < ph <= 8.5:
        return 12.0
    if 4.5 <= ph < 5.0 or 8.5 < ph <= 9.0:
        return 6.0
    return 2.0


_SOIL_TYPE_BONUS: dict[str, float] = {
    "Alluvial": 10.0,
    "Loamy": 10.0,
    "Black": 8.0,
    "Clayey": 6.0,
    "Peaty": 6.0,
    "Red": 5.0,
    "Laterite": 4.0,
    "Sandy": 3.0,
    "Saline": 2.0,
    "Other": 5.0,
}


def compute_soil_health_score(
    nitrogen: float,
    phosphorus: float,
    potassium: float,
    ph: float,
    soil_type: str,
) -> dict[str, Any]:
    """Compute composite soil health score (0-100) with breakdown.

    Weights:
      Nitrogen  → 25 pts
      pH        → 25 pts
      Phosphorus→ 20 pts
      Potassium → 20 pts
      Soil type → 10 pts
    """
    n_sc = round(_score_nutrient(nitrogen, _N_THRESHOLDS, 25.0), 1)
    p_sc = round(_score_nutrient(phosphorus, _P_THRESHOLDS, 20.0), 1)
    k_sc = round(_score_nutrient(potassium, _K_THRESHOLDS, 20.0), 1)
    ph_sc = round(_score_ph(ph), 1)
    st_sc = _SOIL_TYPE_BONUS.get(soil_type, 5.0)

    total = round(min(100.0, n_sc + p_sc + k_sc + ph_sc + st_sc), 1)

    return {
        "nitrogen_score": n_sc,
        "phosphorus_score": p_sc,
        "potassium_score": k_sc,
        "ph_score": ph_sc,
        "soil_type_score": st_sc,
        "total": total,
    }


def classify_health(score: float) -> str:
    """Classify overall health from composite score."""
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Medium"
    if score >= 30:
        return "Low"
    return "Poor"


# ── Recommendations ──────────────────────────────────────────────


def generate_recommendations(
    nitrogen: float,
    phosphorus: float,
    potassium: float,
    ph: float,
    soil_type: str,
    deficiencies: list[str],
) -> list[dict[str, Any]]:
    """Generate prioritised soil amendment recommendations."""
    recs: list[dict[str, Any]] = []

    # ── Nitrogen ─────────────────────────────────────────────────
    if nitrogen < _N_THRESHOLDS["deficient"]:
        recs.append(
            {
                "category": "NPK",
                "priority": "Critical",
                "action": "Nitrogen is critically low  -  apply nitrogen fertiliser immediately",
                "product": "Urea (46-0-0)",
                "dosage": "80-120 kg/ha based on crop demand",
            }
        )
    elif nitrogen < _N_THRESHOLDS["low"]:
        recs.append(
            {
                "category": "NPK",
                "priority": "High",
                "action": "Nitrogen is below optimal  -  supplement with nitrogen source",
                "product": "Urea or Ammonium Sulphate",
                "dosage": "40-80 kg/ha",
            }
        )
    elif nitrogen > _N_THRESHOLDS["high"]:
        recs.append(
            {
                "category": "NPK",
                "priority": "Medium",
                "action": "Nitrogen is in excess  -  reduce N application to prevent burning",
                "product": None,
                "dosage": "Reduce by 30-50%",
            }
        )

    # ── Phosphorus ───────────────────────────────────────────────
    if phosphorus < _P_THRESHOLDS["deficient"]:
        recs.append(
            {
                "category": "NPK",
                "priority": "Critical",
                "action": "Phosphorus critically deficient  -  apply P fertiliser before sowing",
                "product": "DAP (18-46-0) or SSP",
                "dosage": "60-100 kg/ha",
            }
        )
    elif phosphorus < _P_THRESHOLDS["low"]:
        recs.append(
            {
                "category": "NPK",
                "priority": "High",
                "action": "Phosphorus is low  -  supplement to improve root development",
                "product": "Single Super Phosphate (SSP)",
                "dosage": "40-60 kg/ha",
            }
        )

    # ── Potassium ────────────────────────────────────────────────
    if potassium < _K_THRESHOLDS["deficient"]:
        recs.append(
            {
                "category": "NPK",
                "priority": "Critical",
                "action": "Potassium critically deficient  -  apply K fertiliser for plant vigour",
                "product": "Muriate of Potash (MOP, 0-0-60)",
                "dosage": "60-80 kg/ha",
            }
        )
    elif potassium < _K_THRESHOLDS["low"]:
        recs.append(
            {
                "category": "NPK",
                "priority": "High",
                "action": "Potassium is low  -  supplement to improve stress tolerance",
                "product": "MOP or Sulphate of Potash",
                "dosage": "30-60 kg/ha",
            }
        )

    # ── pH Correction ────────────────────────────────────────────
    if ph < 5.0:
        recs.append(
            {
                "category": "pH",
                "priority": "Critical",
                "action": "Soil is highly acidic  -  apply lime to raise pH above 5.5",
                "product": "Agricultural Lime (CaCO3)",
                "dosage": "3-5 t/ha depending on buffer capacity",
            }
        )
    elif ph < 5.5:
        recs.append(
            {
                "category": "pH",
                "priority": "High",
                "action": "Soil is acidic  -  apply dolomite lime to raise pH",
                "product": "Dolomite Lime",
                "dosage": "2-3 t/ha",
            }
        )
    elif ph > 8.5:
        recs.append(
            {
                "category": "pH",
                "priority": "Critical",
                "action": "Soil is very alkaline  -  apply gypsum or sulfur to lower pH",
                "product": "Gypsum (CaSO4) or Elemental Sulfur",
                "dosage": "2-4 t/ha gypsum or 0.5-1 t/ha sulfur",
            }
        )
    elif ph > 8.0:
        recs.append(
            {
                "category": "pH",
                "priority": "High",
                "action": "Soil is alkaline  -  incorporate organic matter and consider sulfur",
                "product": "Organic compost + Elemental Sulfur",
                "dosage": "5 t/ha compost + 0.3 t/ha sulfur",
            }
        )

    # ── Soil-Type-Specific ───────────────────────────────────────

    if soil_type == "Sandy":
        recs.append(
            {
                "category": "Organic",
                "priority": "High",
                "action": "Sandy soil has low retention  -  add organic compost for binding",
                "product": "Farmyard Manure (FYM) or Vermicompost",
                "dosage": "8-12 t/ha",
            }
        )
    elif soil_type == "Clayey":
        recs.append(
            {
                "category": "General",
                "priority": "Medium",
                "action": "Clayey soil can waterlog  -  improve drainage with raised beds",
                "product": None,
                "dosage": None,
            }
        )
    elif soil_type == "Saline":
        recs.append(
            {
                "category": "General",
                "priority": "High",
                "action": "Saline soil  -  leach salts with good irrigation and apply gypsum",
                "product": "Gypsum",
                "dosage": "3-5 t/ha",
            }
        )
    elif soil_type == "Laterite":
        recs.append(
            {
                "category": "General",
                "priority": "Medium",
                "action": "Laterite soil is leached  -  supplement with phosphorus and lime",
                "product": "Rock Phosphate + Lime",
                "dosage": "As per soil test recommendations",
            }
        )

    # ── Fallback ─────────────────────────────────────────────────
    if not recs:
        recs.append(
            {
                "category": "General",
                "priority": "Low",
                "action": (
                    "Soil conditions are within acceptable range. "
                    "Maintain current practices and re-test next season."
                ),
                "product": None,
                "dosage": None,
            }
        )

    return recs


# ── Main Entry Point ─────────────────────────────────────────────


def analyze_soil(
    nitrogen: float,
    phosphorus: float,
    potassium: float,
    ph: float,
    soil_type: str = "Loamy",
) -> dict[str, Any]:
    """Full diagnostic soil analysis.

    This is a **synchronous** function  -  no I/O calls.  It runs
    purely against the supplied test parameters.

    Args:
        nitrogen:  Nitrogen level (kg/ha).
        phosphorus: Phosphorus level (kg/ha).
        potassium: Potassium level (kg/ha).
        ph:        Soil pH (0-14).
        soil_type: Soil category string.

    Returns:
        Complete soil diagnostic dict matching SoilAnalysisResponse.
    """
    logger.debug(
        "Soil Engine: N={}, P={}, K={}, pH={}, type={}",
        nitrogen,
        phosphorus,
        potassium,
        ph,
        soil_type,
    )

    # Nutrient profile
    nutrient_profile = assess_nutrients(nitrogen, phosphorus, potassium)

    # Deficiencies
    deficiencies = detect_deficiencies(nitrogen, phosphorus, potassium, ph)

    # pH
    ph_status = classify_ph(ph)
    ph_analysis = {
        "value": ph,
        "status": ph_status,
        "optimal_range": "6.0 - 7.5",
        "deviation": round(ph - 6.75, 2),
    }

    # Score
    score_breakdown = compute_soil_health_score(nitrogen, phosphorus, potassium, ph, soil_type)
    score = score_breakdown["total"]
    soil_health = classify_health(score)

    # Soil insight
    soil_info = SOIL_TYPE_DB.get(soil_type, SOIL_TYPE_DB["Other"])
    soil_insight = {"soil_type": soil_type, **soil_info}

    # Recommendations
    recommendations = generate_recommendations(
        nitrogen, phosphorus, potassium, ph, soil_type, deficiencies
    )

    return {
        "soil_health": soil_health,
        "score": score,
        "score_breakdown": score_breakdown,
        "deficiencies": deficiencies,
        "ph_status": ph_status,
        "ph_analysis": ph_analysis,
        "nutrient_profile": nutrient_profile,
        "soil_insight": soil_insight,
        "recommendations": recommendations,
        # backward compat for advisory engine
        "soil_health_index": score,
    }
