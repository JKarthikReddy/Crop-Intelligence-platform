"""Soil intelligence schema — structured response models."""

from pydantic import BaseModel, Field


class SoilResponse(BaseModel):
    """Normalized soil properties returned from SoilGrids."""

    ph: float | None = Field(description="Soil pH (H₂O), scale-corrected")
    clay_percent: int | None = Field(description="Clay content in g/kg")
    organic_carbon: int | None = Field(description="Organic carbon density in g/dm³")


class SoilTestResponse(BaseModel):
    """Response for the soil-test diagnostic endpoint."""

    centroid: tuple[float, float] = Field(description="(lat, lon) used for query")
    soil: SoilResponse
