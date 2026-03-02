"""Fertilizer Optimization Engine — deficiency-driven nutrient management.

Takes soil diagnostics + crop selection → recommends fertilizer type,
quantity, application schedule, and advisory notes.
"""

from app.engines.fertilizer.service import FertilizerEngineError, recommend_fertilizer

__all__ = ["FertilizerEngineError", "recommend_fertilizer"]
