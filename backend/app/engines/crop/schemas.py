"""Crop Engine schemas — request/response models for crop intelligence."""

from pydantic import BaseModel, Field


class CropAnalysisRequest(BaseModel):
    """Request payload for crop analysis."""

    lat: float = Field(description="Latitude (WGS84)")
    lon: float = Field(description="Longitude (WGS84)")
    bounds: list[float] = Field(description="Bounding box [minx, miny, maxx, maxy]")
    crop_type: str = Field(default="rice", description="Crop type: rice/wheat/maize/soybean")
    planting_date: str | None = Field(default=None, description="Planting date (ISO format)")


class VegetationHealth(BaseModel):
    """NDVI and SAR-based vegetation assessment."""

    ndvi_mean: float | None = Field(default=None, description="Mean NDVI (-1 to 1)")
    ndvi_classification: str = Field(description="Health: poor/fair/good/excellent")
    moisture_status: str = Field(description="Soil surface moisture: dry/moderate/wet/saturated")
    growth_stage: str = Field(description="Estimated crop growth stage")


class YieldForecast(BaseModel):
    """ML-based yield prediction."""

    predicted_yield: float | None = Field(default=None, description="Yield estimate (t/ha)")
    confidence: str = Field(description="Prediction confidence: low/medium/high")
    model_version: str = Field(description="Model version used")
    yield_trend: str = Field(description="Compared to historical: below/average/above")


class CropAnalysisResponse(BaseModel):
    """Complete crop intelligence output."""

    vegetation: VegetationHealth
    yield_forecast: YieldForecast | None = None
    optimal_harvest_window: str = Field(description="Recommended harvest period")
    crop_health_score: float = Field(description="Overall crop health 0-100")
    recommendations: list[str] = Field(description="Crop management action items")
