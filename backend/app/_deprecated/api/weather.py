"""Weather intelligence endpoints."""

from fastapi import APIRouter, HTTPException

from app.schemas.farm import FarmCreate
from app.schemas.weather import WeatherTestResponse
from app.services.geometry_service import GeometryValidationError, extract_geometry_info
from app.services.weather_service import WeatherServiceError, fetch_nasa_weather

router = APIRouter(prefix="/weather", tags=["weather"])


@router.post("/test", response_model=WeatherTestResponse, status_code=200)
async def weather_test(payload: FarmCreate) -> WeatherTestResponse:
    """Diagnostic endpoint: fetch 30-day weather for a farm boundary centroid.

    Accepts a GeoJSON farm payload, extracts the centroid, and queries
    NASA POWER for recent agro-meteorological data.
    """
    try:
        geom = extract_geometry_info(payload.geojson)
    except GeometryValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    lat, lon = geom["centroid"]

    try:
        weather = await fetch_nasa_weather(lat, lon)
    except WeatherServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return WeatherTestResponse(centroid=(lat, lon), weather=weather)
