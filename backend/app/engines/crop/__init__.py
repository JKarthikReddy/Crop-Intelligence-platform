"""Crop Recommendation Engine — classification + ranking.

Diagnostic engine that recommends the best crops based on soil
conditions, weather data, and farmer location/season. Uses a
30-crop knowledge base with region-aware scoring.
"""

from app.engines.crop.service import CropEngineError, recommend_crops

__all__ = ["CropEngineError", "recommend_crops"]
