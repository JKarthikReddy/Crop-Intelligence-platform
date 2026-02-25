"""Unit tests for the farm CRUD service layer.

Mocks the async SQLAlchemy session to validate service logic
without requiring a live database connection.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.farm_service import (
    create_farm,
    delete_farm,
    get_farm,
    list_farms,
    update_farm,
)

# ── Constants ────────────────────────────────────────────────────

VALID_GEOJSON = {
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


def _make_farm(farm_id: int = 1, name: str = "Test Farm") -> MagicMock:
    """Create a fake Farm ORM instance."""
    farm = MagicMock()
    farm.id = farm_id
    farm.name = name
    return farm


# ── create_farm ──────────────────────────────────────────────────


class TestCreateFarm:
    """Tests for create_farm service."""

    @pytest.mark.asyncio
    @patch("app.services.farm_service.extract_geometry_info")
    @patch("app.services.farm_service.from_shape")
    async def test_create_farm_returns_dict(self, mock_from_shape, mock_extract):
        """create_farm should validate, persist, and return farm data."""
        mock_extract.return_value = {
            "geometry": MagicMock(),
            "centroid": {"lat": 12.005, "lon": 77.005},
            "bounds": [77.0, 12.0, 77.01, 12.01],
            "area_hectares": 1.11,
        }
        mock_from_shape.return_value = "FAKE_WKB"

        session = AsyncMock()
        # After flush+refresh, farm has .id and .name
        farm_obj = MagicMock()
        farm_obj.id = 42
        farm_obj.name = "My Farm"

        def side_effect_add(obj):
            obj.id = 42
            obj.name = "My Farm"

        session.add = MagicMock(side_effect=side_effect_add)
        session.flush = AsyncMock()

        async def fake_refresh(obj):
            obj.id = 42
            obj.name = "My Farm"

        session.refresh = fake_refresh

        result = await create_farm(session, "My Farm", VALID_GEOJSON)

        assert result["id"] == 42
        assert result["name"] == "My Farm"
        assert result["centroid"] == {"lat": 12.005, "lon": 77.005}
        assert result["area_hectares"] == 1.11
        mock_extract.assert_called_once_with(VALID_GEOJSON)


# ── list_farms ───────────────────────────────────────────────────


class TestListFarms:
    """Tests for list_farms service."""

    @pytest.mark.asyncio
    async def test_list_farms_returns_all(self):
        """list_farms returns a list of dicts with id and name."""
        rows = [
            SimpleNamespace(id=1, name="Farm A"),
            SimpleNamespace(id=2, name="Farm B"),
        ]
        mock_result = MagicMock()
        mock_result.all.return_value = rows

        session = AsyncMock()
        session.execute.return_value = mock_result

        result = await list_farms(session)

        assert len(result) == 2
        assert result[0] == {"id": 1, "name": "Farm A"}
        assert result[1] == {"id": 2, "name": "Farm B"}

    @pytest.mark.asyncio
    async def test_list_farms_empty(self):
        """list_farms returns empty list when no farms exist."""
        mock_result = MagicMock()
        mock_result.all.return_value = []

        session = AsyncMock()
        session.execute.return_value = mock_result

        result = await list_farms(session)
        assert result == []


# ── get_farm ─────────────────────────────────────────────────────


class TestGetFarm:
    """Tests for get_farm service."""

    @pytest.mark.asyncio
    async def test_get_farm_found(self):
        """get_farm returns farm dict when found."""
        farm = _make_farm(farm_id=7, name="Found Farm")
        session = AsyncMock()
        session.get.return_value = farm

        result = await get_farm(session, 7)

        assert result == {"id": 7, "name": "Found Farm"}
        session.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_farm_not_found(self):
        """get_farm returns None when farm does not exist."""
        session = AsyncMock()
        session.get.return_value = None

        result = await get_farm(session, 999)
        assert result is None


# ── update_farm ──────────────────────────────────────────────────


class TestUpdateFarm:
    """Tests for update_farm service."""

    @pytest.mark.asyncio
    async def test_update_farm_name_only(self):
        """update_farm can change just the name."""
        farm = _make_farm(farm_id=1, name="Old Name")
        session = AsyncMock()
        session.get.return_value = farm

        async def fake_refresh(obj):
            pass  # name was already set

        session.refresh = fake_refresh

        result = await update_farm(session, 1, name="New Name")

        assert farm.name == "New Name"
        assert result is not None
        assert result["name"] == "New Name"

    @pytest.mark.asyncio
    async def test_update_farm_not_found(self):
        """update_farm returns None for non-existent farm."""
        session = AsyncMock()
        session.get.return_value = None

        result = await update_farm(session, 999, name="X")
        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.farm_service.extract_geometry_info")
    @patch("app.services.farm_service.from_shape")
    async def test_update_farm_with_geojson(self, mock_from_shape, mock_extract):
        """update_farm can change the boundary."""
        mock_extract.return_value = {
            "geometry": MagicMock(),
            "centroid": {"lat": 12.0, "lon": 77.0},
            "bounds": [77.0, 12.0, 77.01, 12.01],
            "area_hectares": 1.0,
        }
        mock_from_shape.return_value = "FAKE_WKB"

        farm = _make_farm(farm_id=1, name="Same")
        session = AsyncMock()
        session.get.return_value = farm

        async def fake_refresh(obj):
            pass

        session.refresh = fake_refresh

        result = await update_farm(session, 1, geojson=VALID_GEOJSON)

        assert result is not None
        mock_extract.assert_called_once_with(VALID_GEOJSON)


# ── delete_farm ──────────────────────────────────────────────────


class TestDeleteFarm:
    """Tests for delete_farm service."""

    @pytest.mark.asyncio
    async def test_delete_farm_found(self):
        """delete_farm returns True on success."""
        farm = _make_farm(farm_id=3)
        session = AsyncMock()
        session.get.return_value = farm

        result = await delete_farm(session, 3)

        assert result is True
        session.delete.assert_called_once_with(farm)

    @pytest.mark.asyncio
    async def test_delete_farm_not_found(self):
        """delete_farm returns False when farm does not exist."""
        session = AsyncMock()
        session.get.return_value = None

        result = await delete_farm(session, 999)
        assert result is False
