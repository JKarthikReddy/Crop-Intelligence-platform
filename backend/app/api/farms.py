"""Farm boundary ingestion and intelligence endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.farm import FarmCreate, FarmResponse
from app.schemas.intelligence import IntelligenceResponse
from app.services.farm_service import create_farm
from app.services.geometry_service import GeometryValidationError
from app.services.intelligence_engine import (
    IntelligenceEngineError,
    generate_intelligence,
)

router = APIRouter(prefix="/farms", tags=["farms"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/", response_model=FarmResponse, status_code=201)
async def create_farm_endpoint(
    payload: FarmCreate,
    session: DbSession,
) -> FarmResponse:
    """Ingest a farm boundary from GeoJSON.

    Validates geometry, normalizes CRS to WGS84, computes area and centroid,
    persists to PostGIS, and returns a structured response.
    """
    try:
        result = await create_farm(
            session=session,
            name=payload.name,
            geojson=payload.geojson,
        )
        return FarmResponse(**result)
    except GeometryValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}") from exc


@router.post("/analyze", response_model=IntelligenceResponse, status_code=200)
async def analyze_farm(payload: FarmCreate) -> IntelligenceResponse:
    """Generate unified intelligence for a farm boundary.

    Accepts a GeoJSON farm payload, extracts spatial metadata, and
    concurrently fetches soil, climate, forecast, and satellite data.
    Individual service failures degrade gracefully (null sections).
    """
    try:
        result = await generate_intelligence(payload.geojson)
    except IntelligenceEngineError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return IntelligenceResponse(**result)
