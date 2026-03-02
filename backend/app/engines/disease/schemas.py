"""Disease Engine schemas — request/response models."""

from pydantic import BaseModel, Field


class DiseaseRequest(BaseModel):
    """Request payload for disease risk assessment."""

    crop_type: str = Field(default="rice", description="Crop type")
    growth_stage: str | None = Field(default=None, description="Current growth stage")
    avg_temperature: float | None = Field(
        default=None, description="Avg temp (°C) from Weather Engine"
    )
    avg_humidity: float | None = Field(default=None, description="Avg relative humidity (%)")
    recent_rainfall_mm: float | None = Field(default=None, description="Recent rainfall (mm)")
    ndvi_mean: float | None = Field(default=None, description="Mean NDVI from Crop Engine")
    soil_ph: float | None = Field(default=None, description="Soil pH from Soil Engine")


class DiseaseRisk(BaseModel):
    """Risk profile for a specific disease."""

    disease_name: str = Field(description="Disease or pest name")
    pathogen_type: str = Field(description="Fungal, bacterial, viral, or insect")
    risk_score: float = Field(description="Risk score 0-100")
    risk_level: str = Field(description="Low / Moderate / High / Critical")
    favorable_conditions: str = Field(description="What triggers this disease")
    symptoms: str = Field(description="Visual symptoms to watch for")


class PreventionPlan(BaseModel):
    """Prevention and treatment action plan."""

    action: str = Field(description="Preventive action")
    priority: str = Field(description="Immediate / Short-term / Long-term")
    method: str = Field(description="Chemical / Biological / Cultural")
    details: str = Field(description="Detailed instructions")


class DiseaseResponse(BaseModel):
    """Complete disease intelligence output."""

    overall_risk_score: float = Field(description="Composite disease risk 0-100")
    risk_level: str = Field(description="Overall risk level")
    disease_risks: list[DiseaseRisk] = Field(description="Individual disease risks")
    prevention_plan: list[PreventionPlan] = Field(description="Action plan")
    recommendations: list[str] = Field(description="General disease management tips")
