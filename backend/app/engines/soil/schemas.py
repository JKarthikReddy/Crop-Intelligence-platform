"""Soil Engine schemas — request/response models for soil intelligence."""

from pydantic import BaseModel, Field


class SoilAnalysisRequest(BaseModel):
    """Request payload for soil analysis."""

    lat: float = Field(description="Latitude in decimal degrees (WGS84)")
    lon: float = Field(description="Longitude in decimal degrees (WGS84)")


class NutrientProfile(BaseModel):
    """Nutrient adequacy assessment."""

    nitrogen: str = Field(description="N adequacy: low/adequate/high")
    phosphorus: str = Field(description="P adequacy: low/adequate/high")
    potassium: str = Field(description="K adequacy: low/adequate/high")
    organic_carbon_rating: str = Field(description="SOC rating: poor/fair/good/excellent")


class SoilAnalysisResponse(BaseModel):
    """Complete soil intelligence output."""

    ph: float | None = Field(default=None, description="Soil pH (0-14 scale)")
    ph_classification: str = Field(description="pH class: acidic/neutral/alkaline")
    clay_percent: int | None = Field(default=None, description="Clay content (g/kg)")
    organic_carbon: int | None = Field(default=None, description="Organic carbon density (g/dm³)")
    texture_class: str = Field(description="Soil texture: sandy/loamy/clayey")
    nutrient_profile: NutrientProfile
    soil_health_index: float = Field(description="Composite health score 0-100")
    recommendations: list[str] = Field(description="Actionable soil improvement tips")
