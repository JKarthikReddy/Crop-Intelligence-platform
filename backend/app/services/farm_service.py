"""Farm service layer — orchestrates boundary ingestion and persistence."""

from typing import Any

from geoalchemy2.shape import from_shape
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.farm import Farm
from app.services.geometry_service import validate_and_extract_geometry


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
        Dictionary with farm id, name, centroid, and area_hectares.
    """
    geom_data = validate_and_extract_geometry(geojson)

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
        "area_hectares": geom_data["area_hectares"],
    }
