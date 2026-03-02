"""Soil Engine schemas — request/response models for soil diagnostics.

Enterprise-grade soil health analysis based on farmer-supplied soil test data.
Evaluates NPK levels, pH balance, deficiencies, and generates a composite
soil health score with actionable amendment recommendations.
"""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# ── Enumerations ─────────────────────────────────────────────────


class SoilType(StrEnum):
    """Supported soil type classifications."""

    ALLUVIAL = "Alluvial"
    BLACK = "Black"
    RED = "Red"
    LATERITE = "Laterite"
    SANDY = "Sandy"
    CLAYEY = "Clayey"
    LOAMY = "Loamy"
    PEATY = "Peaty"
    SALINE = "Saline"
    OTHER = "Other"


class NutrientStatus(StrEnum):
    """Nutrient adequacy classification."""

    DEFICIENT = "Deficient"
    LOW = "Low"
    ADEQUATE = "Adequate"
    HIGH = "High"
    EXCESS = "Excess"


class PhStatus(StrEnum):
    """Soil pH classification."""

    STRONGLY_ACIDIC = "Strongly Acidic"
    ACIDIC = "Acidic"
    SLIGHTLY_ACIDIC = "Slightly Acidic"
    NEUTRAL = "Neutral"
    SLIGHTLY_ALKALINE = "Slightly Alkaline"
    ALKALINE = "Alkaline"
    STRONGLY_ALKALINE = "Strongly Alkaline"


class HealthLevel(StrEnum):
    """Soil health classification."""

    POOR = "Poor"
    LOW = "Low"
    MEDIUM = "Medium"
    GOOD = "Good"
    EXCELLENT = "Excellent"


# ── Request ──────────────────────────────────────────────────────


class SoilAnalysisRequest(BaseModel):
    """Request payload for soil analysis.

    Farmer provides core soil test parameters; the engine diagnoses
    health, detects deficiencies, and prescribes amendments.
    """

    nitrogen: float = Field(
        ge=0,
        le=500,
        description="Nitrogen level in kg/ha",
        json_schema_extra={"example": 45},
    )
    phosphorus: float = Field(
        ge=0,
        le=200,
        description="Phosphorus level in kg/ha",
        json_schema_extra={"example": 30},
    )
    potassium: float = Field(
        ge=0,
        le=500,
        description="Potassium level in kg/ha",
        json_schema_extra={"example": 40},
    )
    ph: float = Field(
        ge=0,
        le=14,
        description="Soil pH value (0-14 scale)",
        json_schema_extra={"example": 6.5},
    )
    soil_type: SoilType = Field(
        default=SoilType.LOAMY,
        description="Soil category classification",
        json_schema_extra={"example": "Black"},
    )

    @model_validator(mode="before")
    @classmethod
    def _reject_nan_inf(cls, data: Any) -> Any:
        """Reject NaN / Infinity before field validators run."""
        if isinstance(data, dict):
            for field in ("nitrogen", "phosphorus", "potassium", "ph"):
                v = data.get(field)
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    msg = f"{field} must be a finite number"
                    raise ValueError(msg)
        return data

    @field_validator("ph")
    @classmethod
    def validate_ph_range(cls, v: float) -> float:
        """Ensure pH is within physically meaningful range."""
        if not 0 <= v <= 14:
            msg = "pH must be between 0 and 14"
            raise ValueError(msg)
        return round(v, 2)


# ── Response Sub-Models ──────────────────────────────────────────


class NutrientDetail(BaseModel):
    """Individual nutrient assessment."""

    value: float = Field(description="Measured value (kg/ha)")
    status: NutrientStatus = Field(description="Adequacy classification")
    ideal_range: str = Field(description="Ideal range for healthy crops")
    deviation_pct: float = Field(
        description="Percentage deviation from ideal midpoint (negative = below)"
    )


class NutrientProfile(BaseModel):
    """Complete NPK nutrient analysis."""

    nitrogen: NutrientDetail = Field(description="Nitrogen (N) assessment")
    phosphorus: NutrientDetail = Field(description="Phosphorus (P) assessment")
    potassium: NutrientDetail = Field(description="Potassium (K) assessment")


class PhAnalysis(BaseModel):
    """pH diagnostic result."""

    value: float = Field(description="Measured pH")
    status: PhStatus = Field(description="pH classification")
    optimal_range: str = Field(default="6.0 - 7.5", description="Optimal pH range for most crops")
    deviation: float = Field(description="Distance from optimal midpoint (6.75)")


class SoilTypeInsight(BaseModel):
    """Characteristics for the given soil type."""

    soil_type: SoilType = Field(description="Classified soil type")
    water_retention: str = Field(description="Water retention capacity")
    drainage: str = Field(description="Natural drainage quality")
    fertility: str = Field(description="Inherent fertility level")
    best_crops: list[str] = Field(description="Crops best suited for this soil")
    management_notes: str = Field(description="Key management consideration")


class ScoreBreakdown(BaseModel):
    """Detailed scoring breakdown showing how health score was computed."""

    nitrogen_score: float = Field(description="N contribution (0-25)")
    phosphorus_score: float = Field(description="P contribution (0-20)")
    potassium_score: float = Field(description="K contribution (0-20)")
    ph_score: float = Field(description="pH contribution (0-25)")
    soil_type_score: float = Field(description="Soil-type bonus (0-10)")
    total: float = Field(description="Composite score (0-100)")


class Recommendation(BaseModel):
    """Structured improvement recommendation."""

    category: str = Field(description="Category: NPK / pH / Organic / General")
    priority: str = Field(description="Priority: Critical / High / Medium / Low")
    action: str = Field(description="Specific corrective action")
    product: str | None = Field(default=None, description="Recommended product/input")
    dosage: str | None = Field(default=None, description="Application rate if applicable")


# ── Main Response ────────────────────────────────────────────────


class SoilAnalysisResponse(BaseModel):
    """Complete enterprise soil diagnostic report.

    Contains nutrient profiles, pH diagnostics, soil-type insights,
    composite health scoring with breakdown, detected deficiencies,
    and prioritised amendment recommendations.
    """

    soil_health: HealthLevel = Field(description="Overall health classification")
    score: float = Field(description="Composite soil health score (0-100)")
    score_breakdown: ScoreBreakdown = Field(description="Per-factor scoring detail")
    deficiencies: list[str] = Field(description="Nutrients below ideal threshold")
    ph_status: PhStatus = Field(description="pH classification label")
    ph_analysis: PhAnalysis = Field(description="Detailed pH diagnostic")
    nutrient_profile: NutrientProfile = Field(description="NPK nutrient detail")
    soil_insight: SoilTypeInsight = Field(description="Soil-type characteristics")
    recommendations: list[Recommendation] = Field(description="Prioritised actions")

    # Keep backward-compatible key for advisory engine
    @property
    def soil_health_index(self) -> float:
        """Alias so advisory engine can read soil_health_index."""
        return self.score

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Override to inject soil_health_index for advisory engine compat."""
        d = super().model_dump(**kwargs)
        d["soil_health_index"] = d["score"]
        return d
