"""Disease Engine — Crop disease and pest risk intelligence.

Provides disease risk scoring, pest prediction, outbreak probability,
and prevention recommendations based on weather and crop conditions.
"""

from app.engines.disease.service import DiseaseEngineError, assess_disease_risk

__all__ = ["DiseaseEngineError", "assess_disease_risk"]
