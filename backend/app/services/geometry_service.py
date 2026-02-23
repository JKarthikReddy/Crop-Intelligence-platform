"""Geometry processing service — validates, normalizes, and extracts spatial data."""

from typing import Any

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform


def validate_and_extract_geometry(geojson: dict[str, Any]) -> dict[str, Any]:
    """Validate GeoJSON and extract geometry, centroid, and area.

    Args:
        geojson: A GeoJSON Feature dict with a geometry key.

    Returns:
        Dictionary with 'geometry' (Shapely), 'centroid' (lat, lon), and 'area_hectares'.

    Raises:
        ValueError: If GeoJSON structure is invalid or geometry type is unsupported.
    """
    if "geometry" not in geojson:
        raise ValueError("Invalid GeoJSON: missing 'geometry' key")

    raw_geometry = geojson["geometry"]

    if not isinstance(raw_geometry, dict) or "type" not in raw_geometry:
        raise ValueError("Invalid GeoJSON: 'geometry' must be a dict with 'type'")

    if "coordinates" not in raw_geometry:
        raise ValueError("Invalid GeoJSON: 'geometry' missing 'coordinates'")

    try:
        geom = shape(raw_geometry)
    except Exception as exc:
        raise ValueError(f"Cannot parse geometry: {exc}") from exc

    if not geom.is_valid:
        raise ValueError(f"Invalid geometry: {geom.is_valid}")

    if geom.geom_type not in ("Polygon", "MultiPolygon"):
        raise ValueError(
            f"Unsupported geometry type '{geom.geom_type}'. "
            "Only Polygon or MultiPolygon accepted."
        )

    # ── CRS normalization (enforce WGS84 / EPSG:4326) ───────────
    wgs84_transformer = Transformer.from_crs("EPSG:4326", "EPSG:4326", always_xy=True)
    geom = transform(wgs84_transformer.transform, geom)

    # ── Centroid extraction ──────────────────────────────────────
    centroid = geom.centroid

    # ── Area calculation (project to Web Mercator for meters) ────
    area_transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    projected_geom = transform(area_transformer.transform, geom)
    area_hectares = round(projected_geom.area / 10_000, 2)

    return {
        "geometry": geom,
        "centroid": (centroid.y, centroid.x),  # (lat, lon)
        "area_hectares": area_hectares,
    }
