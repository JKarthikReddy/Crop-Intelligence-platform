"""Unit tests for the soil intelligence service (mocked HTTP)."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.soil_service import SoilServiceError, fetch_soil_data

# ── Fixtures ─────────────────────────────────────────────────────

MOCK_SOILGRIDS_RESPONSE = {
    "type": "Feature",
    "properties": {
        "layers": [
            {
                "name": "phh2o",
                "depths": [{"values": {"mean": 64}}],
            },
            {
                "name": "clay",
                "depths": [{"values": {"mean": 280}}],
            },
            {
                "name": "ocd",
                "depths": [{"values": {"mean": 12}}],
            },
        ]
    },
}

MOCK_SOILGRIDS_PARTIAL = {
    "type": "Feature",
    "properties": {
        "layers": [
            {
                "name": "phh2o",
                "depths": [{"values": {"mean": 55}}],
            },
        ]
    },
}

MOCK_SOILGRIDS_NULL_VALUE = {
    "type": "Feature",
    "properties": {
        "layers": [
            {
                "name": "phh2o",
                "depths": [{"values": {"mean": None}}],
            },
            {
                "name": "clay",
                "depths": [{"values": {"mean": 200}}],
            },
            {
                "name": "ocd",
                "depths": [{"values": {"mean": 8}}],
            },
        ]
    },
}

MOCK_MALFORMED = {"unexpected": "structure"}


# ── Helpers ──────────────────────────────────────────────────────


def _mock_response(json_data: dict, status_code: int = 200) -> httpx.Response:
    """Build a fake httpx.Response."""
    response = httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("GET", "https://test"),
    )
    return response


# ── Happy path ───────────────────────────────────────────────────


class TestFetchSoilData:
    """Tests with mocked SoilGrids HTTP responses."""

    @pytest.mark.asyncio
    async def test_returns_all_keys(self):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(MOCK_SOILGRIDS_RESPONSE))

        with patch("app.services.soil_service.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_soil_data(12.0, 77.0)

        assert "ph" in result
        assert "clay_percent" in result
        assert "organic_carbon" in result

    @pytest.mark.asyncio
    async def test_ph_scale_correction(self):
        """SoilGrids returns pH x10; we must divide."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(MOCK_SOILGRIDS_RESPONSE))

        with patch("app.services.soil_service.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_soil_data(12.0, 77.0)

        assert result["ph"] == 6.4  # 64 / 10

    @pytest.mark.asyncio
    async def test_clay_and_ocd_raw(self):
        """Clay and OCD should pass through as-is."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(MOCK_SOILGRIDS_RESPONSE))

        with patch("app.services.soil_service.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_soil_data(12.0, 77.0)

        assert result["clay_percent"] == 280
        assert result["organic_carbon"] == 12

    @pytest.mark.asyncio
    async def test_null_value_handled(self):
        """None values from SoilGrids should pass through as None."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(MOCK_SOILGRIDS_NULL_VALUE))

        with patch("app.services.soil_service.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_soil_data(12.0, 77.0)

        assert result["ph"] is None
        assert result["clay_percent"] == 200

    @pytest.mark.asyncio
    async def test_partial_response_fills_defaults(self):
        """Missing layers should default to None."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(MOCK_SOILGRIDS_PARTIAL))

        with patch("app.services.soil_service.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_soil_data(12.0, 77.0)

        assert result["ph"] == 5.5
        assert result["clay_percent"] is None
        assert result["organic_carbon"] is None


# ── Error handling ───────────────────────────────────────────────


class TestSoilServiceErrors:
    """Tests for failure modes."""

    @pytest.mark.asyncio
    async def test_non_200_raises(self):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(
            return_value=_mock_response({"error": "not found"}, status_code=404)
        )

        with (
            patch("app.services.soil_service.httpx.AsyncClient", return_value=mock_client),
            pytest.raises(SoilServiceError, match="HTTP 404"),
        ):
            await fetch_soil_data(12.0, 77.0)

    @pytest.mark.asyncio
    async def test_malformed_response_raises(self):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(MOCK_MALFORMED))

        with (
            patch("app.services.soil_service.httpx.AsyncClient", return_value=mock_client),
            pytest.raises(SoilServiceError, match="Unexpected"),
        ):
            await fetch_soil_data(12.0, 77.0)

    @pytest.mark.asyncio
    async def test_timeout_raises(self):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

        with (
            patch("app.services.soil_service.httpx.AsyncClient", return_value=mock_client),
            pytest.raises(SoilServiceError, match="timed out"),
        ):
            await fetch_soil_data(12.0, 77.0)
