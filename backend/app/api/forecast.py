"""Forecast intelligence endpoints."""

from fastapi import APIRouter, HTTPException

from app.schemas.farm import FarmCreate
from app.schemas.forecast import ForecastTestResponse
from app.services.forecast_service import ForecastServiceError, fetch_forecast
from app.services.geometry_service import (
    GeometryValidationError,
    extract_geometry_info,
)

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.post("/test", response_model=ForecastTestResponse, status_code=200)
async def forecast_test(payload: FarmCreate) -> ForecastTestResponse:
    """Diagnostic endpoint: fetch 5-day forecast for a farm boundary centroid.

    Accepts a GeoJSON farm payload, extracts the centroid, and queries
    OpenWeather for short-term forecast advisory data.
    """
    try:
        geom = extract_geometry_info(payload.geojson)
    except GeometryValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    lat, lon = geom["centroid"]

    try:
        forecast = await fetch_forecast(lat, lon)
    except ForecastServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ForecastTestResponse(centroid=(lat, lon), forecast=forecast)
