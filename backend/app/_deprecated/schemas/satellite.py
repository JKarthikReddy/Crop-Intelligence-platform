"""Satellite NDVI intelligence schema -- structured response models."""

from pydantic import BaseModel, Field


class NdviResponse(BaseModel):
    """Normalized NDVI vegetation health summary from Sentinel-2."""

    ndvi_mean: float = Field(description="Mean NDVI score (-1 to 1)")
    bbox: list[float] = Field(description="Bounding box used [minx, miny, maxx, maxy]")
    time_range_start: str = Field(description="ISO start date of imagery window")
    time_range_end: str = Field(description="ISO end date of imagery window")
    data_source: str = Field(description="Satellite data source identifier")


class NdviTestResponse(BaseModel):
    """Response for the NDVI diagnostic test endpoint."""

    centroid: tuple[float, float] = Field(description="(lat, lon) of farm centroid")
    ndvi: NdviResponse
