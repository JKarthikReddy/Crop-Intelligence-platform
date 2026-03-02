"""Soil Engine — diagnostic soil health analysis.

Analyses farmer-provided NPK, pH, and soil type to produce health scores,
deficiency detection, nutrient profiles, and amendment recommendations.
No external API calls — purely algorithmic diagnostics.
"""

from app.engines.soil.service import (
    SoilEngineError,
    analyze_soil,
    classify_health,
    classify_ph,
    compute_soil_health_score,
)

__all__ = [
    "SoilEngineError",
    "analyze_soil",
    "classify_health",
    "classify_ph",
    "compute_soil_health_score",
]
