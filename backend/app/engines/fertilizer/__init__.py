"""Fertilizer Engine — NPK recommendations and nutrient management.

Provides fertilizer dosage calculations, nutrient gap analysis,
cost optimization, and application scheduling.
"""

from app.engines.fertilizer.service import FertilizerEngineError, recommend_fertilizer

__all__ = ["FertilizerEngineError", "recommend_fertilizer"]
