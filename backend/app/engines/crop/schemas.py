"""Crop Recommendation Engine schemas - request/response models.

Enterprise-grade crop recommendation based on soil conditions,
weather data, and location. Performs classification + ranking
to predict the most suitable crops for the farmer.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

# -- Enumerations ---------------------------------------------------------


class Season(StrEnum):
    """Indian agricultural seasons."""

    KHARIF = "Kharif"
    RABI = "Rabi"
    ZAID = "Zaid"


class ConfidenceLevel(StrEnum):
    """Prediction confidence band."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    VERY_HIGH = "Very High"


# -- Request Sub-Models ---------------------------------------------------


class SoilData(BaseModel):
    """Soil conditions (from Soil Engine or farmer input)."""

    nitrogen: float = Field(
        ge=0, le=500, description="Nitrogen (kg/ha)", json_schema_extra={"example": 45}
    )
    phosphorus: float = Field(
        ge=0, le=200, description="Phosphorus (kg/ha)", json_schema_extra={"example": 30}
    )
    potassium: float = Field(
        ge=0, le=500, description="Potassium (kg/ha)", json_schema_extra={"example": 40}
    )
    ph: float = Field(ge=0, le=14, description="Soil pH", json_schema_extra={"example": 6.5})
    soil_health: str = Field(
        default="Medium",
        description="Overall soil health label",
        json_schema_extra={"example": "Medium"},
    )


class WeatherData(BaseModel):
    """Weather conditions (from Weather Engine or farmer input)."""

    temperature: float = Field(
        ge=-10, le=60, description="Temperature (C)", json_schema_extra={"example": 32}
    )
    humidity: float = Field(
        ge=0, le=100, description="Relative humidity (%)", json_schema_extra={"example": 75}
    )
    rainfall: float = Field(
        ge=0, le=5000, description="Rainfall (mm)", json_schema_extra={"example": 120}
    )


# -- Main Request ---------------------------------------------------------


class CropRecommendationRequest(BaseModel):
    """Request payload for crop recommendation."""

    soil_data: SoilData = Field(description="Soil test parameters")
    weather_data: WeatherData = Field(description="Weather conditions")
    location: str = Field(
        min_length=2,
        description="Location (e.g. 'Guntur, Andhra Pradesh')",
        json_schema_extra={"example": "Guntur, Andhra Pradesh"},
    )
    season: Season | None = Field(
        default=None,
        description="Agricultural season (optional)",
        json_schema_extra={"example": "Kharif"},
    )

    @field_validator("location")
    @classmethod
    def normalise_location(cls, v: str) -> str:
        """Strip and title-case location."""
        return v.strip().title()


# -- Response Sub-Models --------------------------------------------------


class CropAlternative(BaseModel):
    """A ranked alternative crop."""

    crop: str = Field(description="Crop name")
    confidence: float = Field(description="Confidence score 0-100")
    suitability: str = Field(description="Brief suitability note")


class CropRecommendationResponse(BaseModel):
    """Complete crop recommendation output."""

    recommended_crop: str = Field(description="Best-suited crop")
    confidence: float = Field(description="Confidence score 0-100")
    confidence_level: ConfidenceLevel = Field(description="Confidence band label")
    top_alternatives: list[CropAlternative] = Field(description="Ranked alternative crops")
    reasoning: list[str] = Field(description="Why this crop was recommended")
    season: str = Field(description="Season used for analysis")
    location: str = Field(description="Location used for analysis")
    feature_vector: list[float] = Field(description="[N, P, K, pH, temp, humidity, rainfall]")

    # Backward-compat: advisory engine reads crop_health_score
    crop_health_score: float = Field(
        default=75.0,
        description="Mapped confidence as health score for advisory compat",
    )
