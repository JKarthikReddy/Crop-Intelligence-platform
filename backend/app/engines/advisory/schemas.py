"""Advisory Aggregator schemas — request/response models."""

from typing import Any

from pydantic import BaseModel, Field


class AdvisoryRequest(BaseModel):
    """Request payload for full farm advisory."""

    lat: float = Field(default=17.385, description="Latitude (WGS-84)")
    lon: float = Field(default=78.4867, description="Longitude (WGS-84)")
    crop_type: str = Field(default="rice", description="Crop type")
    planting_date: str | None = Field(default=None, description="ISO date of planting (YYYY-MM-DD)")
    target_yield: float = Field(default=5.0, description="Target yield (t/ha)")
    area_hectares: float = Field(default=1.0, description="Farm area in hectares")
    region: str = Field(default="south_asia", description="Market region")
    bounds: dict[str, float] | None = Field(
        default=None,
        description="Bounding box {north, south, east, west} for satellite analysis",
    )


class EngineStatus(BaseModel):
    """Status of each engine execution."""

    engine: str = Field(description="Engine name")
    status: str = Field(description="success / degraded / failed")
    latency_ms: float = Field(description="Execution time in ms")
    error: str | None = Field(default=None, description="Error message if failed")


class AdvisoryPriority(BaseModel):
    """Prioritized action item from aggregated intelligence."""

    priority: int = Field(description="Priority rank (1 = highest)")
    category: str = Field(description="Engine category")
    action: str = Field(description="Recommended action")
    urgency: str = Field(description="Immediate / This Week / This Month / Seasonal")
    impact: str = Field(description="High / Medium / Low")


class AdvisoryResponse(BaseModel):
    """Complete farm advisory — unified output from all 6 engines."""

    farm_health_score: float = Field(description="Composite farm health 0-100")
    advisory_summary: str = Field(description="Executive summary (2-3 sentences)")
    priority_actions: list[AdvisoryPriority] = Field(description="Ranked action items")

    soil_intelligence: dict[str, Any] | None = Field(default=None, description="Soil Engine output")
    weather_intelligence: dict[str, Any] | None = Field(
        default=None, description="Weather Engine output"
    )
    crop_intelligence: dict[str, Any] | None = Field(default=None, description="Crop Engine output")
    fertilizer_intelligence: dict[str, Any] | None = Field(
        default=None, description="Fertilizer Engine output"
    )
    disease_intelligence: dict[str, Any] | None = Field(
        default=None, description="Disease Engine output"
    )
    market_intelligence: dict[str, Any] | None = Field(
        default=None, description="Market Engine output"
    )

    engine_statuses: list[EngineStatus] = Field(description="Per-engine execution status")
    engines_succeeded: int = Field(description="Number of engines that succeeded")
    engines_total: int = Field(default=6, description="Total engines")
