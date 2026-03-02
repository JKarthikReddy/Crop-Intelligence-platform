"""Weather Engine schemas — request/response models for weather intelligence."""

from pydantic import BaseModel, Field


class WeatherAnalysisRequest(BaseModel):
    """Request payload for weather analysis."""

    lat: float = Field(description="Latitude in decimal degrees (WGS84)")
    lon: float = Field(description="Longitude in decimal degrees (WGS84)")


class CurrentWeather(BaseModel):
    """Real-time weather observation from OpenWeather Current Weather API."""

    temperature: float = Field(description="Current temperature (°C)")
    feels_like: float = Field(description="Perceived temperature (°C)")
    temp_min: float = Field(description="Observed minimum temperature (°C)")
    temp_max: float = Field(description="Observed maximum temperature (°C)")
    pressure: int = Field(description="Atmospheric pressure at sea level (hPa)")
    humidity: int = Field(description="Humidity (%)")
    visibility: int = Field(description="Visibility (metres, max 10 000)")
    wind_speed: float = Field(description="Wind speed (m/s)")
    wind_deg: int = Field(description="Wind direction (degrees)")
    wind_gust: float | None = Field(default=None, description="Wind gust (m/s)")
    clouds: int = Field(description="Cloudiness (%)")
    weather_main: str = Field(description="Weather group (Rain, Clouds, Clear …)")
    weather_description: str = Field(description="Weather description")
    weather_icon: str = Field(description="OpenWeather icon code")
    rain_1h: float | None = Field(default=None, description="Rain volume last 1 h (mm)")
    snow_1h: float | None = Field(default=None, description="Snow volume last 1 h (mm)")
    sunrise: int = Field(description="Sunrise time (unix UTC)")
    sunset: int = Field(description="Sunset time (unix UTC)")
    city_name: str = Field(description="Nearest city / locality name")
    country: str = Field(description="ISO 3166 country code")
    dt: int = Field(description="Data calculation time (unix UTC)")


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

    current: CurrentWeather | None = None
    climate: ClimateSnapshot | None = None
    forecast: ForecastSummary | None = None
    water_model: WaterModel | None = None
    risk_assessment: WeatherRiskScore
    recommendations: list[str] = Field(description="Weather-based action items")
