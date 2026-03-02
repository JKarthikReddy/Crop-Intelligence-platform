"""Intelligence engine schema -- unified geospatial response models."""

from pydantic import BaseModel, Field

from app.schemas.forecast import ForecastResponse
from app.schemas.satellite import NdviResponse
from app.schemas.soil import SoilResponse
from app.schemas.weather import WeatherResponse


class LocationInfo(BaseModel):
    """Spatial metadata extracted from the farm boundary."""

    centroid: list[float] = Field(description="[lat, lon] of farm centroid")
    bounds: list[float] = Field(description="[minx, miny, maxx, maxy] bounding box")
    area_hectares: float = Field(description="Farm area in hectares")


class IntelligenceResponse(BaseModel):
    """Unified intelligence payload aggregating all data sources."""

    location: LocationInfo
    soil: SoilResponse | None = Field(
        default=None, description="Soil chemistry (None if service unavailable)"
    )
    climate: WeatherResponse | None = Field(
        default=None, description="30-day climate history (None if service unavailable)"
    )
    forecast: ForecastResponse | None = Field(
        default=None, description="5-day forecast advisory (None if service unavailable)"
    )
    satellite: NdviResponse | None = Field(
        default=None, description="NDVI vegetation health (None if service unavailable)"
    )
