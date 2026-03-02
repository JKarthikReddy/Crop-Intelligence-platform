"""Weather Engine schemas — request/response models for weather intelligence."""

from pydantic import BaseModel, Field


class WeatherAnalysisRequest(BaseModel):
    """Request payload for weather analysis."""

    lat: float = Field(description="Latitude in decimal degrees (WGS84)")
    lon: float = Field(description="Longitude in decimal degrees (WGS84)")


class ClimateSnapshot(BaseModel):
    """30-day historical climate summary from NASA POWER."""

    temperature_avg_30d: float | None = Field(default=None, description="Mean temp at 2m (°C)")
    solar_radiation_avg_30d: float | None = Field(
        default=None, description="Mean solar (MJ/m²/day)"
    )
    wind_speed_avg_30d: float | None = Field(default=None, description="Mean wind at 2m (m/s)")


class ForecastSummary(BaseModel):
    """5-day forecast intelligence from OpenWeather."""

    avg_temp_next_5d: float = Field(description="Mean temperature next 5 days (°C)")
    max_temp_next_5d: float = Field(description="Maximum temperature next 5 days (°C)")
    total_rain_next_5d: float = Field(description="Total rainfall next 5 days (mm)")
    heat_risk_flag: bool = Field(description="True if max temp exceeds 35°C")
    heavy_rain_flag: bool = Field(description="True if rainfall exceeds 50mm")


class WaterModel(BaseModel):
    """Evapotranspiration and water stress assessment."""

    et0_estimate: float = Field(description="Reference ET0 (mm/day)")
    water_stress_risk: str = Field(description="Risk level: low/moderate/high")
    irrigation_recommendation: str = Field(description="Irrigation action guidance")


class WeatherRiskScore(BaseModel):
    """Composite agricultural weather risk assessment."""

    drought_risk: str = Field(description="Drought risk: low/moderate/high/critical")
    flood_risk: str = Field(description="Flood risk: low/moderate/high/critical")
    frost_risk: str = Field(description="Frost risk: none/low/moderate/high")
    overall_risk_score: float = Field(description="Composite risk score 0-100")


class WeatherAnalysisResponse(BaseModel):
    """Complete weather intelligence output."""

    climate: ClimateSnapshot | None = None
    forecast: ForecastSummary | None = None
    water_model: WaterModel | None = None
    risk_assessment: WeatherRiskScore
    recommendations: list[str] = Field(description="Weather-based action items")
