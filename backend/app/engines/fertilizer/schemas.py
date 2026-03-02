"""Fertilizer Optimization Engine schemas — request/response models.

Takes processed outputs from Soil Engine + Crop Engine + optional farmer
land area to recommend the right fertilizer type, quantity, and schedule.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

# -- Enumerations ---------------------------------------------------------


class AreaUnit(StrEnum):
    """Land area measurement units."""

    ACRE = "acre"
    HECTARE = "hectare"


# -- Request Sub-Models ---------------------------------------------------


class SoilReport(BaseModel):
    """Soil diagnostics (from Soil Engine output)."""

    deficiencies: list[str] = Field(
        default_factory=list,
        description="Nutrient deficiencies detected",
        json_schema_extra={"example": ["Nitrogen"]},
    )
    soil_health: str = Field(
        default="Medium",
        description="Overall soil health label",
        json_schema_extra={"example": "Medium"},
    )
    ph_status: str = Field(
        default="Neutral",
        description="pH classification",
        json_schema_extra={"example": "Neutral"},
    )


# -- Main Request ---------------------------------------------------------


class FertilizerRequest(BaseModel):
    """Request payload for fertilizer recommendation."""

    soil_report: SoilReport = Field(
        default_factory=SoilReport,
        description="Soil diagnostics from Soil Engine",
    )
    selected_crop: str = Field(
        default="Rice",
        min_length=2,
        description="Crop selected (from Crop Engine or farmer)",
        json_schema_extra={"example": "Red Chilli"},
    )
    land_area: float = Field(
        default=1.0,
        gt=0,
        le=10000,
        description="Farm area",
        json_schema_extra={"example": 2.0},
    )
    unit: AreaUnit = Field(
        default=AreaUnit.ACRE,
        description="Area unit (acre or hectare)",
        json_schema_extra={"example": "acre"},
    )

    @field_validator("selected_crop")
    @classmethod
    def normalise_crop(cls, v: str) -> str:
        """Strip and title-case crop name."""
        return v.strip().title()


# -- Response Sub-Models --------------------------------------------------


class ScheduleStep(BaseModel):
    """A single step in the application schedule."""

    stage: str = Field(description="Application stage label")
    timing: str = Field(description="When to apply")
    products: list[str] = Field(description="Which products to apply")
    notes: str = Field(description="Method and tips")


# -- Main Response --------------------------------------------------------


class FertilizerResponse(BaseModel):
    """Complete fertilizer recommendation output."""

    fertilizers: list[str] = Field(description="Recommended fertilizer names")
    quantity_per_acre: dict[str, str] = Field(
        description="Dosage per acre for each fertilizer",
    )
    total_required: dict[str, str] = Field(
        description="Total quantity for entire farm area",
    )
    schedule: list[ScheduleStep] = Field(
        description="Application schedule with timing",
    )
    notes: list[str] = Field(description="Advisory messages and tips")

    # Backward-compat: advisory engine reads application_schedule
    application_schedule: list[ScheduleStep] = Field(
        default_factory=list,
        description="Alias for schedule (advisory compat)",
    )
