"""Forecast intelligence schema -- structured response models."""

from pydantic import BaseModel, Field


class ForecastResponse(BaseModel):
    """Normalized 5-day forecast advisory from OpenWeather."""

    avg_temp_next_5d: float = Field(description="Mean temperature across intervals (C)")
    max_temp_next_5d: float = Field(description="Maximum temperature across intervals (C)")
    total_rain_next_5d: float = Field(description="Cumulative rainfall (mm)")
    heat_risk_flag: bool = Field(description="True if max temp exceeds 35 C")
    heavy_rain_flag: bool = Field(description="True if total rainfall exceeds 50 mm")


class ForecastTestResponse(BaseModel):
    """Response for the forecast-test diagnostic endpoint."""

    centroid: tuple[float, float] = Field(description="(lat, lon) used for query")
    forecast: ForecastResponse
