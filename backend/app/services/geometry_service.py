"""Geospatial core engine — validates, normalizes, and extracts spatial data.

Pure service layer:
- No FastAPI imports
- No database logic
- No environment access
- No side effects
- Fully deterministic and testable
"""

from typing import Any

from pyproj import Transformer
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.ops import transform


class GeometryValidationError(Exception):
    """Raised when GeoJSON input fails structural or spatial validation."""


def extract_geometry_info(geojson: dict[str, Any]) -> dict[str, Any]:
    """Validate and process a GeoJSON Feature.

    Accepts a GeoJSON Feature dict, validates its structure, enforces
    Polygon/MultiPolygon type, normalizes CRS to WGS84, and computes
    centroid, bounding box, and area.

    Args:
        geojson: A GeoJSON Feature dict with a ``geometry`` key.

    Returns:
        Dictionary with keys:
            - ``geometry``: Shapely geometry object (WGS84)
            - ``centroid``: ``(lat, lon)`` tuple
            - ``bounds``: ``(minx, miny, maxx, maxy)`` tuple
            - ``area_hectares``: Area in hectares (float)

    Raises:
        GeometryValidationError: If input is empty, missing keys,
            has unsupported geometry type, or is spatially invalid.
    """
    # ── Payload-level validation ─────────────────────────────────
    if not geojson:
        raise GeometryValidationError("GeoJSON payload is empty.")

    if "geometry" not in geojson:
        raise GeometryValidationError("Invalid GeoJSON: missing 'geometry' key.")

    raw_geometry = geojson["geometry"]

    if not isinstance(raw_geometry, dict) or "type" not in raw_geometry:
        raise GeometryValidationError("Invalid GeoJSON: 'geometry' must be a dict with 'type'.")

    if "coordinates" not in raw_geometry:
        raise GeometryValidationError("Invalid GeoJSON: 'geometry' missing 'coordinates'.")

    # ── Shape construction ───────────────────────────────────────
    try:
        geom = shape(raw_geometry)
    except Exception as exc:
        raise GeometryValidationError(f"Cannot parse geometry: {exc}") from exc

    # ── Type enforcement ─────────────────────────────────────────
    if not isinstance(geom, Polygon | MultiPolygon):
        raise GeometryValidationError(
            f"Only Polygon or MultiPolygon geometries are supported. " f"Got '{geom.geom_type}'."
        )

    # ── Spatial validity ─────────────────────────────────────────
    if not geom.is_valid:
        raise GeometryValidationError("Invalid geometry shape.")

    if geom.is_empty:
        raise GeometryValidationError("Geometry is empty.")

    # ── CRS normalization (enforce WGS84 / EPSG:4326) ───────────
    wgs84_transformer = Transformer.from_crs("EPSG:4326", "EPSG:4326", always_xy=True)
    geom = transform(wgs84_transformer.transform, geom)

    # ── Centroid extraction ──────────────────────────────────────
    centroid = geom.centroid
    centroid_latlon: tuple[float, float] = (centroid.y, centroid.x)

    # ── Bounding box ─────────────────────────────────────────────
    bounds: tuple[float, float, float, float] = geom.bounds  # (minx, miny, maxx, maxy)

    # ── Area calculation (project to Web Mercator for meters) ────
    metric_transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    projected_geom = transform(metric_transformer.transform, geom)
    area_hectares = round(projected_geom.area / 10_000, 2)

    return {
        "geometry": geom,
        "centroid": centroid_latlon,
        "bounds": bounds,
        "area_hectares": area_hectares,
    }
