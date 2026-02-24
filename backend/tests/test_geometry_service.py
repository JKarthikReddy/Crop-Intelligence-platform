"""Unit tests for the geospatial core engine."""

import time

import pytest

from app.services.geometry_service import GeometryValidationError, extract_geometry_info

# ── Test fixtures ────────────────────────────────────────────────

VALID_POLYGON = {
    "type": "Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [
                [77.0, 12.0],
                [77.01, 12.0],
                [77.01, 12.01],
                [77.0, 12.01],
                [77.0, 12.0],
            ]
        ],
    },
}

VALID_MULTIPOLYGON = {
    "type": "Feature",
    "geometry": {
        "type": "MultiPolygon",
        "coordinates": [
            [
                [
                    [77.0, 12.0],
                    [77.01, 12.0],
                    [77.01, 12.01],
                    [77.0, 12.01],
                    [77.0, 12.0],
                ]
            ],
            [
                [
                    [78.0, 13.0],
                    [78.01, 13.0],
                    [78.01, 13.01],
                    [78.0, 13.01],
                    [78.0, 13.0],
                ]
            ],
        ],
    },
}


# ── Happy path tests ────────────────────────────────────────────


class TestValidGeometry:
    """Tests for valid Polygon and MultiPolygon inputs."""

    def test_polygon_returns_all_keys(self):
        result = extract_geometry_info(VALID_POLYGON)
        assert "geometry" in result
        assert "centroid" in result
        assert "bounds" in result
        assert "area_hectares" in result

    def test_polygon_centroid_is_lat_lon(self):
        result = extract_geometry_info(VALID_POLYGON)
        lat, lon = result["centroid"]
        assert 11.0 < lat < 13.0, f"Latitude {lat} out of expected range"
        assert 76.0 < lon < 78.0, f"Longitude {lon} out of expected range"

    def test_polygon_area_positive(self):
        result = extract_geometry_info(VALID_POLYGON)
        assert result["area_hectares"] > 0

    def test_polygon_bounds_tuple(self):
        result = extract_geometry_info(VALID_POLYGON)
        bounds = result["bounds"]
        assert len(bounds) == 4
        minx, miny, maxx, maxy = bounds
        assert minx < maxx
        assert miny < maxy

    def test_multipolygon_accepted(self):
        result = extract_geometry_info(VALID_MULTIPOLYGON)
        assert result["area_hectares"] > 0
        assert "centroid" in result
        assert "bounds" in result

    def test_multipolygon_area_larger_than_single(self):
        single = extract_geometry_info(VALID_POLYGON)
        multi = extract_geometry_info(VALID_MULTIPOLYGON)
        assert multi["area_hectares"] > single["area_hectares"]


# ── Validation / rejection tests ────────────────────────────────


class TestGeometryRejection:
    """Tests for invalid inputs that must raise GeometryValidationError."""

    def test_empty_payload(self):
        with pytest.raises(GeometryValidationError, match="empty"):
            extract_geometry_info({})

    def test_none_payload(self):
        with pytest.raises(GeometryValidationError, match="empty"):
            extract_geometry_info(None)  # type: ignore[arg-type]

    def test_missing_geometry_key(self):
        with pytest.raises(GeometryValidationError, match="missing 'geometry'"):
            extract_geometry_info({"type": "Feature", "properties": {}})

    def test_geometry_not_dict(self):
        with pytest.raises(GeometryValidationError, match="must be a dict"):
            extract_geometry_info({"geometry": "not-a-dict"})

    def test_geometry_missing_coordinates(self):
        with pytest.raises(GeometryValidationError, match="missing 'coordinates'"):
            extract_geometry_info({"geometry": {"type": "Polygon"}})

    def test_linestring_rejected(self):
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[77.0, 12.0], [77.01, 12.0]],
            },
        }
        with pytest.raises(GeometryValidationError, match="Only Polygon or MultiPolygon"):
            extract_geometry_info(geojson)

    def test_point_rejected(self):
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [77.0, 12.0],
            },
        }
        with pytest.raises(GeometryValidationError, match="Only Polygon or MultiPolygon"):
            extract_geometry_info(geojson)


# ── Performance test ─────────────────────────────────────────────


class TestPerformance:
    """Execution time must be < 50ms for a small polygon."""

    def test_sub_50ms(self):
        start = time.perf_counter()
        extract_geometry_info(VALID_POLYGON)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 50, f"Took {elapsed_ms:.1f}ms — exceeds 50ms threshold"
