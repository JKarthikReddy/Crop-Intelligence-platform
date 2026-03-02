"""Soil Engine — soil analysis, nutrient profiling, and health scoring.

Provides soil chemistry data from ISRIC SoilGrids, computes nutrient
adequacy ratings, pH interpretation, and soil health index scoring.
"""

from app.engines.soil.service import (
    SoilEngineError,
    analyze_soil,
    classify_ph,
    compute_soil_health_index,
)

__all__ = [
    "SoilEngineError",
    "analyze_soil",
    "classify_ph",
    "compute_soil_health_index",
]
