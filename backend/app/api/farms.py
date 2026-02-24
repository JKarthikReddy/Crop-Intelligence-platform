"""Farm boundary ingestion endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.farm import FarmCreate, FarmResponse
from app.services.farm_service import create_farm
from app.services.geometry_service import GeometryValidationError

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
