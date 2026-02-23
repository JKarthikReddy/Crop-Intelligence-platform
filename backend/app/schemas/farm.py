"""Farm request/response schemas for boundary ingestion."""

from typing import Any

from pydantic import BaseModel, Field


class FarmCreate(BaseModel):
    """Schema for creating a farm with GeoJSON boundary."""

    name: str = Field(..., min_length=2, max_length=100)
    geojson: dict[str, Any] = Field(
        ...,
        description="GeoJSON Feature with Polygon or MultiPolygon geometry",
    )


class FarmResponse(BaseModel):
    """Structured response after farm creation."""

    id: int
    name: str
    centroid: tuple[float, float] = Field(
        description="(latitude, longitude) of boundary centroid",
    )
    area_hectares: float = Field(description="Farm area in hectares")
