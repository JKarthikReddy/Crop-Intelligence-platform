"""Satellite NDVI intelligence endpoints."""

from fastapi import APIRouter, HTTPException

from app.schemas.farm import FarmCreate
from app.schemas.satellite import NdviTestResponse
from app.services.geometry_service import (
    GeometryValidationError,
    extract_geometry_info,
)
from app.services.satellite_service import SatelliteServiceError, fetch_ndvi

router = APIRouter(prefix="/satellite", tags=["satellite"])


@router.post("/ndvi-test", response_model=NdviTestResponse, status_code=200)
async def ndvi_test(payload: FarmCreate) -> NdviTestResponse:
    """Diagnostic endpoint: fetch Sentinel-2 NDVI for a farm boundary.

    Accepts a GeoJSON farm payload, extracts the bounding box, and
    queries Sentinel Hub for vegetation health intelligence.
    """
    try:
        geom = extract_geometry_info(payload.geojson)
    except GeometryValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    lat, lon = geom["centroid"]
    bounds = geom["bounds"]

    try:
        ndvi = await fetch_ndvi(bounds)
    except SatelliteServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return NdviTestResponse(centroid=(lat, lon), ndvi=ndvi)
