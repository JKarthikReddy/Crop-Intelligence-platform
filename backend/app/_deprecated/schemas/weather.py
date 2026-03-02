"""Weather intelligence schema -- structured response models."""

from pydantic import BaseModel, Field


class WeatherResponse(BaseModel):
    """Normalized 30-day weather averages from NASA POWER."""

    temperature_avg_30d: float | None = Field(description="Mean temperature at 2m (Celsius)")
    solar_radiation_avg_30d: float | None = Field(
        description="Mean surface shortwave radiation (MJ/m2/day)"
    )
    wind_speed_avg_30d: float | None = Field(description="Mean wind speed at 2m (m/s)")


class WeatherTestResponse(BaseModel):
    """Response for the weather-test diagnostic endpoint."""

    centroid: tuple[float, float] = Field(description="(lat, lon) used for query")
    weather: WeatherResponse
