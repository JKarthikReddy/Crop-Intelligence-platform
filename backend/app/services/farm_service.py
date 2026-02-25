"""Farm service layer — orchestrates boundary ingestion and persistence."""

from typing import Any

from geoalchemy2.shape import from_shape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.farm import Farm
from app.services.geometry_service import extract_geometry_info


async def create_farm(
    session: AsyncSession,
    name: str,
    geojson: dict[str, Any],
) -> dict[str, Any]:
    """Validate geometry, persist farm, and return structured result.

    Args:
        session: Async SQLAlchemy session (injected via FastAPI dependency).
        name: Farm display name.
        geojson: GeoJSON Feature containing Polygon/MultiPolygon geometry.

    Returns:
        Dictionary with farm id, name, centroid, bounds, and area_hectares.
    """
    geom_data = extract_geometry_info(geojson)

    farm = Farm(
        name=name,
        boundary=from_shape(geom_data["geometry"], srid=4326),
    )

    session.add(farm)
    await session.flush()  # populate farm.id without committing
    await session.refresh(farm)

    return {
        "id": farm.id,
        "name": farm.name,
        "centroid": geom_data["centroid"],
        "bounds": geom_data["bounds"],
        "area_hectares": geom_data["area_hectares"],
    }


async def list_farms(session: AsyncSession) -> list[dict[str, Any]]:
    """Return all farms (id + name only).

    Args:
        session: Async SQLAlchemy session.

    Returns:
        List of dicts with id and name.
    """
    result = await session.execute(select(Farm.id, Farm.name).order_by(Farm.id))
    return [{"id": row.id, "name": row.name} for row in result.all()]


async def get_farm(session: AsyncSession, farm_id: int) -> dict[str, Any] | None:
    """Retrieve a single farm by ID.

    Args:
        session: Async SQLAlchemy session.
        farm_id: Primary key of the farm.

    Returns:
        Farm dict with id and name, or None if not found.
    """
    farm = await session.get(Farm, farm_id)
    if farm is None:
        return None
    return {"id": farm.id, "name": farm.name}


async def update_farm(
    session: AsyncSession,
    farm_id: int,
    name: str | None = None,
    geojson: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Update an existing farm's name and/or boundary.

    Args:
        session: Async SQLAlchemy session.
        farm_id: Primary key of the farm.
        name: New farm name (optional).
        geojson: New GeoJSON boundary (optional).

    Returns:
        Updated farm dict, or None if not found.
    """
    farm = await session.get(Farm, farm_id)
    if farm is None:
        return None

    if name is not None:
        farm.name = name

    if geojson is not None:
        geom_data = extract_geometry_info(geojson)
        farm.boundary = from_shape(geom_data["geometry"], srid=4326)

    await session.flush()
    await session.refresh(farm)

    return {"id": farm.id, "name": farm.name}


async def delete_farm(session: AsyncSession, farm_id: int) -> bool:
    """Delete a farm by ID.

    Args:
        session: Async SQLAlchemy session.
        farm_id: Primary key of the farm.

    Returns:
        True if deleted, False if not found.
    """
    farm = await session.get(Farm, farm_id)
    if farm is None:
        return False

    await session.delete(farm)
    await session.flush()
    return True
