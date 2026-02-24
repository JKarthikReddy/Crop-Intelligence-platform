"""Soil intelligence endpoints."""

from fastapi import APIRouter, HTTPException

from app.schemas.farm import FarmCreate
from app.schemas.soil import SoilTestResponse
from app.services.geometry_service import GeometryValidationError, extract_geometry_info
from app.services.soil_service import SoilServiceError, fetch_soil_data

router = APIRouter(prefix="/soil", tags=["soil"])


@router.post("/test", response_model=SoilTestResponse, status_code=200)
async def soil_test(payload: FarmCreate) -> SoilTestResponse:
    """Diagnostic endpoint: fetch soil data for a farm boundary's centroid.

    Accepts a GeoJSON farm payload, extracts the centroid, and queries
    ISRIC SoilGrids for soil properties at that location.
    """
    try:
        geom = extract_geometry_info(payload.geojson)
    except GeometryValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    lat, lon = geom["centroid"]

    try:
        soil = await fetch_soil_data(lat, lon)
    except SoilServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SoilTestResponse(centroid=(lat, lon), soil=soil)
