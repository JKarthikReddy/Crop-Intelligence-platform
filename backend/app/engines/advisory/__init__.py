"""Advisory Aggregator — Unified intelligence combining all 6 engines.

Orchestrates Soil, Weather, Crop, Fertilizer, Disease, and Market engines
into a single comprehensive farm advisory.
"""

from app.engines.advisory.service import AdvisoryEngineError, generate_advisory

__all__ = ["AdvisoryEngineError", "generate_advisory"]
