"""Disease Engine service — disease/pest risk assessment and prevention.

Pure service layer:
- Crop-specific disease database with triggers
- Weather-based risk scoring (temperature x humidity x rainfall)
- Growth-stage vulnerability weighting
- Prevention plan generation
"""

from typing import Any

# ── Disease Database (crop → list of diseases) ───────────────────
_DISEASE_DB: dict[str, list[dict[str, Any]]] = {
    "rice": [
        {
            "name": "Blast (Magnaporthe oryzae)",
            "pathogen_type": "Fungal",
            "temp_range": (20, 30),
            "humidity_min": 80,
            "rainfall_boost": True,
            "vulnerable_stages": ["tillering", "heading"],
            "symptoms": "Diamond-shaped lesions on leaves; neck blast causes panicle breakage",
            "favorable": "Warm, humid conditions with heavy dew; excess nitrogen",
        },
        {
            "name": "Bacterial Leaf Blight (Xanthomonas oryzae)",
            "pathogen_type": "Bacterial",
            "temp_range": (25, 35),
            "humidity_min": 70,
            "rainfall_boost": True,
            "vulnerable_stages": ["tillering", "booting"],
            "symptoms": "Water-soaked lesions turning yellow-white; wilting leaf tips",
            "favorable": "High temperature, humidity, and wounds from storms",
        },
        {
            "name": "Brown Plant Hopper",
            "pathogen_type": "Insect",
            "temp_range": (22, 32),
            "humidity_min": 75,
            "rainfall_boost": False,
            "vulnerable_stages": ["tillering", "heading", "maturity"],
            "symptoms": "Hopper burn — circular patches of dried plants; honeydew on stems",
            "favorable": "Dense canopy, high humidity, excessive nitrogen",
        },
        {
            "name": "Sheath Blight (Rhizoctonia solani)",
            "pathogen_type": "Fungal",
            "temp_range": (25, 32),
            "humidity_min": 85,
            "rainfall_boost": True,
            "vulnerable_stages": ["booting", "heading"],
            "symptoms": "Oval greenish-grey lesions on leaf sheath near water line",
            "favorable": "Dense plantings, high N fertilizer, stagnant water",
        },
    ],
    "wheat": [
        {
            "name": "Stripe Rust (Puccinia striiformis)",
            "pathogen_type": "Fungal",
            "temp_range": (10, 20),
            "humidity_min": 70,
            "rainfall_boost": True,
            "vulnerable_stages": ["tillering", "heading"],
            "symptoms": "Yellow-orange stripes of pustules on leaves",
            "favorable": "Cool, moist weather; wind dispersal over long distances",
        },
        {
            "name": "Powdery Mildew (Blumeria graminis)",
            "pathogen_type": "Fungal",
            "temp_range": (15, 25),
            "humidity_min": 60,
            "rainfall_boost": False,
            "vulnerable_stages": ["tillering", "booting", "heading"],
            "symptoms": "White powdery patches on upper leaf surface",
            "favorable": "Moderate temperatures, dense stands, low light",
        },
        {
            "name": "Aphids",
            "pathogen_type": "Insect",
            "temp_range": (15, 28),
            "humidity_min": 50,
            "rainfall_boost": False,
            "vulnerable_stages": ["heading", "maturity"],
            "symptoms": "Yellowing, curling leaves; sticky honeydew deposits",
            "favorable": "Warm dry weather, delayed sowing",
        },
    ],
    "maize": [
        {
            "name": "Northern Leaf Blight (Exserohilum turcicum)",
            "pathogen_type": "Fungal",
            "temp_range": (18, 27),
            "humidity_min": 75,
            "rainfall_boost": True,
            "vulnerable_stages": ["vegetative", "tasseling"],
            "symptoms": "Long cigar-shaped grey-green lesions on leaves",
            "favorable": "Moderate temps, prolonged leaf wetness, continuous maize cropping",
        },
        {
            "name": "Fall Armyworm (Spodoptera frugiperda)",
            "pathogen_type": "Insect",
            "temp_range": (20, 35),
            "humidity_min": 50,
            "rainfall_boost": False,
            "vulnerable_stages": ["vegetative", "tasseling"],
            "symptoms": "Ragged feeding damage in whorl; frass in leaf axils",
            "favorable": "Warm seasons; migrates long distances; multiple generations per year",
        },
    ],
    "soybean": [
        {
            "name": "Soybean Rust (Phakopsora pachyrhizi)",
            "pathogen_type": "Fungal",
            "temp_range": (18, 28),
            "humidity_min": 80,
            "rainfall_boost": True,
            "vulnerable_stages": ["flowering", "pod_fill"],
            "symptoms": "Tan to reddish-brown lesions on lower leaves; premature defoliation",
            "favorable": "Warm, wet conditions with prolonged leaf wetness",
        },
        {
            "name": "Pod Borer (Helicoverpa armigera)",
            "pathogen_type": "Insect",
            "temp_range": (20, 32),
            "humidity_min": 50,
            "rainfall_boost": False,
            "vulnerable_stages": ["flowering", "pod_fill"],
            "symptoms": "Bored pods; frass near entry holes; larvae inside pods",
            "favorable": "Warm weather, previous crop residues, late planting",
        },
    ],
}


class DiseaseEngineError(Exception):
    """Raised when disease assessment fails."""


def _score_disease(
    disease: dict[str, Any],
    temp: float | None,
    humidity: float | None,
    rainfall: float | None,
    growth_stage: str | None,
    ndvi: float | None,
    soil_ph: float | None,
) -> float:
    """Score a single disease based on environmental conditions."""
    score = 0.0

    # Temperature factor (40% weight)
    if temp is not None:
        lo, hi = disease["temp_range"]
        if lo <= temp <= hi:
            # Peak risk at midpoint
            mid = (lo + hi) / 2
            temp_factor = 1.0 - abs(temp - mid) / (hi - lo)
            score += temp_factor * 40
        elif temp < lo:
            score += max(0, (1 - (lo - temp) / 10)) * 20
        else:
            score += max(0, (1 - (temp - hi) / 10)) * 20

    # Humidity factor (30% weight)
    if humidity is not None:
        hum_min = disease["humidity_min"]
        if humidity >= hum_min:
            hum_factor = min(1.0, (humidity - hum_min) / 20)
            score += (0.5 + 0.5 * hum_factor) * 30
        else:
            score += max(0, humidity / hum_min) * 15

    # Rainfall factor (15% weight)
    if rainfall is not None and disease.get("rainfall_boost"):
        if rainfall > 50:
            score += 15
        elif rainfall > 20:
            score += 10
        elif rainfall > 5:
            score += 5

    # Growth stage vulnerability (15% weight)
    if growth_stage and growth_stage.lower() in [
        s.lower() for s in disease.get("vulnerable_stages", [])
    ]:
        score += 15

    # NDVI stress boost — low NDVI = weakened crop, higher disease risk
    if ndvi is not None and ndvi < 0.3:
        score = min(100, score * 1.15)

    return round(min(100, max(0, score)), 1)


def _risk_level(score: float) -> str:
    """Classify risk score to level."""
    if score >= 75:
        return "Critical"
    if score >= 50:
        return "High"
    if score >= 30:
        return "Moderate"
    return "Low"


def _build_prevention_plan(
    diseases: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Generate prevention/treatment actions for top risks."""
    plan: list[dict[str, Any]] = []

    critical = [d for d in diseases if d["risk_score"] >= 75]
    high = [d for d in diseases if 50 <= d["risk_score"] < 75]
    moderate = [d for d in diseases if 30 <= d["risk_score"] < 50]

    for d in critical:
        if d["pathogen_type"] == "Fungal":
            plan.append(
                {
                    "action": f"Apply fungicide for {d['disease_name']}",
                    "priority": "Immediate",
                    "method": "Chemical",
                    "details": "Use registered fungicide (e.g., Propiconazole/Tricyclazole). Spray at first symptom appearance. Repeat after 10-14 days.",
                }
            )
        elif d["pathogen_type"] == "Insect":
            plan.append(
                {
                    "action": f"Apply insecticide for {d['disease_name']}",
                    "priority": "Immediate",
                    "method": "Chemical",
                    "details": "Use recommended insecticide. Scout fields for pest density (ETL: economic threshold level) before spraying.",
                }
            )
        else:
            plan.append(
                {
                    "action": f"Implement control measures for {d['disease_name']}",
                    "priority": "Immediate",
                    "method": "Chemical",
                    "details": "Apply registered bactericide/antibiotic. Remove infected plants. Improve drainage.",
                }
            )

    for d in high:
        if d["pathogen_type"] in ("Fungal", "Bacterial"):
            plan.append(
                {
                    "action": f"Preventive spray for {d['disease_name']}",
                    "priority": "Short-term",
                    "method": "Chemical",
                    "details": "Apply preventive fungicide/bactericide within 3-5 days.",
                }
            )
        elif d["pathogen_type"] == "Insect":
            plan.append(
                {
                    "action": f"Biological control for {d['disease_name']}",
                    "priority": "Short-term",
                    "method": "Biological",
                    "details": "Release natural enemies (e.g., Trichogramma cards for borers). Install pheromone traps for monitoring.",
                }
            )

    for d in moderate:
        plan.append(
            {
                "action": f"Monitor {d['disease_name']}",
                "priority": "Long-term",
                "method": "Cultural",
                "details": "Increase field scouting frequency. Maintain balanced fertilization. Ensure proper drainage.",
            }
        )

    if not plan:
        plan.append(
            {
                "action": "Routine field monitoring",
                "priority": "Long-term",
                "method": "Cultural",
                "details": "Continue regular scouting. Disease risk is currently low.",
            }
        )

    return plan


def _generate_recommendations(
    crop_type: str,
    overall_score: float,
    soil_ph: float | None,
) -> list[str]:
    """General disease management recommendations."""
    recs: list[str] = []

    if overall_score >= 50:
        recs.append("HIGH RISK: Increase field scouting to every 3-5 days")
    else:
        recs.append("Maintain weekly field scouting for early disease/pest detection")

    recs.append("Use certified disease-free seeds and resistant varieties")
    recs.append("Rotate crops to break disease cycles — avoid continuous monocropping")
    recs.append(
        "Maintain balanced NPK fertilization — excess nitrogen increases fungal susceptibility"
    )

    if soil_ph is not None and soil_ph < 5.5:
        recs.append("Low soil pH favors certain soil-borne pathogens — consider liming")

    if crop_type == "rice":
        recs.append("Maintain 2-3 cm water level to reduce sheath blight; drain periodically")
    elif crop_type == "maize":
        recs.append("Destroy crop residues after harvest to reduce inoculum for next season")

    return recs


# ── Main Entry Point ─────────────────────────────────────────────


async def assess_disease_risk(
    crop_type: str = "rice",
    growth_stage: str | None = None,
    avg_temperature: float | None = None,
    avg_humidity: float | None = None,
    recent_rainfall_mm: float | None = None,
    ndvi_mean: float | None = None,
    soil_ph: float | None = None,
) -> dict[str, Any]:
    """Full disease/pest risk assessment for given crop and conditions.

    Args:
        crop_type: Crop to assess diseases for.
        growth_stage: Current growth stage (e.g., tillering, heading).
        avg_temperature: Average air temp (°C).
        avg_humidity: Average relative humidity (%).
        recent_rainfall_mm: Recent cumulative rainfall (mm).
        ndvi_mean: Vegetation index (lower = stressed = more vulnerable).
        soil_ph: Soil pH.

    Returns:
        Complete disease risk assessment dict.
    """
    diseases = _DISEASE_DB.get(crop_type, _DISEASE_DB["rice"])

    scored: list[dict[str, Any]] = []
    for d in diseases:
        score = _score_disease(
            d, avg_temperature, avg_humidity, recent_rainfall_mm, growth_stage, ndvi_mean, soil_ph
        )
        scored.append(
            {
                "disease_name": d["name"],
                "pathogen_type": d["pathogen_type"],
                "risk_score": score,
                "risk_level": _risk_level(score),
                "favorable_conditions": d["favorable"],
                "symptoms": d["symptoms"],
            }
        )

    # Sort by risk score descending
    scored.sort(key=lambda x: x["risk_score"], reverse=True)

    # Overall risk = weighted average (top risk counts more)
    if scored:
        weights = [1.0 / (i + 1) for i in range(len(scored))]
        overall = sum(s["risk_score"] * w for s, w in zip(scored, weights, strict=False)) / sum(
            weights
        )
    else:
        overall = 0.0

    overall = round(overall, 1)
    plan = _build_prevention_plan(scored)
    recs = _generate_recommendations(crop_type, overall, soil_ph)

    return {
        "overall_risk_score": overall,
        "risk_level": _risk_level(overall),
        "disease_risks": scored,
        "prevention_plan": plan,
        "recommendations": recs,
    }
