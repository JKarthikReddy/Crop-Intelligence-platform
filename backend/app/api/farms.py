"""Farm boundary ingestion, CRUD, and intelligence endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.engines.advisory.schemas import AdvisoryResponse
from app.engines.advisory.service import (
    AdvisoryEngineError,
    generate_advisory,
)
from app.schemas.farm import FarmCreate, FarmListItem, FarmResponse, FarmUpdate
from app.services.farm_service import (
    create_farm,
    delete_farm,
    get_farm,
    list_farms,
    update_farm,
)
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


@router.get("/", response_model=list[FarmListItem])
async def list_farms_endpoint(session: DbSession) -> list[FarmListItem]:
    """List all registered farms (id + name)."""
    farms = await list_farms(session)
    return [FarmListItem(**f) for f in farms]


@router.get("/{farm_id}", response_model=FarmListItem)
async def get_farm_endpoint(farm_id: int, session: DbSession) -> FarmListItem:
    """Retrieve a single farm by ID."""
    farm = await get_farm(session, farm_id)
    if farm is None:
        raise HTTPException(status_code=404, detail=f"Farm {farm_id} not found")
    return FarmListItem(**farm)


@router.put("/{farm_id}", response_model=FarmListItem)
async def update_farm_endpoint(
    farm_id: int,
    payload: FarmUpdate,
    session: DbSession,
) -> FarmListItem:
    """Update a farm's name and/or boundary."""
    try:
        farm = await update_farm(
            session=session,
            farm_id=farm_id,
            name=payload.name,
            geojson=payload.geojson,
        )
    except GeometryValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if farm is None:
        raise HTTPException(status_code=404, detail=f"Farm {farm_id} not found")
    return FarmListItem(**farm)


@router.delete("/{farm_id}", status_code=204)
async def delete_farm_endpoint(farm_id: int, session: DbSession) -> None:
    """Delete a farm by ID."""
    deleted = await delete_farm(session, farm_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Farm {farm_id} not found")


@router.post("/analyze", response_model=AdvisoryResponse, status_code=200)
async def analyze_farm(payload: FarmCreate) -> AdvisoryResponse:
    """Generate unified intelligence for a farm boundary.

    Accepts a GeoJSON farm payload, extracts spatial metadata, and
    orchestrates all 6 domain engines via the Advisory Aggregator.
    Individual engine failures degrade gracefully (null sections).
    """
    try:
        # Extract centroid from GeoJSON for engine inputs
        from app.services.geometry_service import extract_geometry_info

        geo_info = extract_geometry_info(payload.geojson)
        lat, lon = geo_info["centroid"]
        minx, miny, maxx, maxy = geo_info["bounds"]
        bounds = {"north": maxy, "south": miny, "east": maxx, "west": minx}

        result = await generate_advisory(
            lat=lat,
            lon=lon,
            crop_type="rice",
            bounds=bounds,
        )
    except AdvisoryEngineError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return AdvisoryResponse(**result)
