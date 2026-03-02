"""Crop Engine — yield prediction, NDVI monitoring, and growth analysis.

Provides satellite vegetation health (NDVI/SAR), ML-based yield
forecasting (XGBoost + LSTM ensemble), crop growth stage tracking,
and harvest timing recommendations.
"""

from app.engines.crop.service import CropEngineError, analyze_crop

__all__ = ["CropEngineError", "analyze_crop"]
