"""Fertilizer Engine schemas — request/response models."""

from pydantic import BaseModel, Field


class FertilizerRequest(BaseModel):
    """Request payload for fertilizer recommendation."""

    crop_type: str = Field(default="rice", description="Crop type")
    target_yield: float = Field(default=5.0, description="Target yield (t/ha)")
    soil_ph: float | None = Field(default=None, description="Soil pH from Soil Engine")
    organic_carbon: int | None = Field(default=None, description="Organic carbon (g/dm³)")
    clay_percent: int | None = Field(default=None, description="Clay content (g/kg)")
    area_hectares: float = Field(default=1.0, description="Farm area in hectares")


class NPKRecommendation(BaseModel):
    """Nitrogen, Phosphorus, Potassium recommendation."""

    nitrogen_kg_per_ha: float = Field(description="Nitrogen dose (kg/ha)")
    phosphorus_kg_per_ha: float = Field(description="Phosphorus (P₂O₅) dose (kg/ha)")
    potassium_kg_per_ha: float = Field(description="Potassium (K₂O) dose (kg/ha)")
    total_nitrogen_kg: float = Field(description="Total N for entire area")
    total_phosphorus_kg: float = Field(description="Total P₂O₅ for entire area")
    total_potassium_kg: float = Field(description="Total K₂O for entire area")


class FertilizerProduct(BaseModel):
    """Recommended fertilizer product."""

    name: str = Field(description="Product name (e.g., Urea, DAP, MOP)")
    composition: str = Field(description="NPK composition ratio")
    quantity_kg_per_ha: float = Field(description="Recommended quantity (kg/ha)")
    total_quantity_kg: float = Field(description="Total for entire area")
    estimated_cost_usd: float = Field(description="Estimated cost")


class ApplicationSchedule(BaseModel):
    """Fertilizer application timing."""

    stage: str = Field(description="Growth stage for application")
    timing: str = Field(description="When to apply")
    products: list[str] = Field(description="Which products to apply")
    notes: str = Field(description="Application method and tips")


class FertilizerResponse(BaseModel):
    """Complete fertilizer intelligence output."""

    npk_recommendation: NPKRecommendation
    products: list[FertilizerProduct]
    application_schedule: list[ApplicationSchedule]
    cost_summary: dict[str, float] = Field(description="Cost breakdown")
    recommendations: list[str] = Field(description="Fertilizer management tips")
