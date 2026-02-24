"""Unit tests for the Sentinel-2 NDVI satellite service (mocked HTTP)."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.satellite_service import (
    SatelliteServiceError,
    _build_ndvi_response,
    _estimate_ndvi_from_content_length,
    fetch_ndvi,
    get_sentinel_token,
)

# -- Fixtures ---------------------------------------------------------------

MOCK_TOKEN_RESPONSE = {"access_token": "mock-bearer-token-12345"}

# Simulated 256x256 float32 TIFF raster (non-trivial binary payload)
MOCK_RASTER_BYTES = b"\x00" * 262_144  # 256 * 256 * 4 bytes

MOCK_SMALL_RASTER = b"\x00" * 50  # Tiny payload (barren tile)

MOCK_BOUNDS = (77.5, 12.9, 77.6, 13.0)


# -- Helpers ----------------------------------------------------------------


def _mock_response(
    status_code: int = 200,
    *,
    json_data: dict | None = None,
    content: bytes = b"",
) -> httpx.Response:
    """Build a fake httpx.Response with optional JSON or binary content."""
    if json_data is not None:
        return httpx.Response(
            status_code=status_code,
            json=json_data,
            request=httpx.Request("POST", "https://test"),
        )
    return httpx.Response(
        status_code=status_code,
        content=content,
        request=httpx.Request("POST", "https://test"),
    )


def _make_mock_client(response: httpx.Response) -> AsyncMock:
    """Create a fully-wired async context-manager mock client."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=response)
    mock_client.get = AsyncMock(return_value=response)
    return mock_client


# -- OAuth Token Tests -------------------------------------------------------


class TestGetSentinelToken:
    """Tests for Sentinel Hub OAuth2 token acquisition."""

    @pytest.mark.asyncio
    async def test_returns_access_token(self) -> None:
        client = _make_mock_client(_mock_response(json_data=MOCK_TOKEN_RESPONSE))

        with patch(
            "app.services.satellite_service.httpx.AsyncClient",
            return_value=client,
        ):
            token = await get_sentinel_token()

        assert token == "mock-bearer-token-12345"

    @pytest.mark.asyncio
    async def test_non_200_raises(self) -> None:
        client = _make_mock_client(_mock_response(status_code=401))

        with (
            patch(
                "app.services.satellite_service.httpx.AsyncClient",
                return_value=client,
            ),
            pytest.raises(SatelliteServiceError, match="HTTP 401"),
        ):
            await get_sentinel_token()

    @pytest.mark.asyncio
    async def test_missing_token_key_raises(self) -> None:
        client = _make_mock_client(_mock_response(json_data={"error": "invalid_client"}))

        with (
            patch(
                "app.services.satellite_service.httpx.AsyncClient",
                return_value=client,
            ),
            pytest.raises(SatelliteServiceError, match="missing access_token"),
        ):
            await get_sentinel_token()

    @pytest.mark.asyncio
    async def test_timeout_raises(self) -> None:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.ReadTimeout("timeout"))

        with (
            patch(
                "app.services.satellite_service.httpx.AsyncClient",
                return_value=mock_client,
            ),
            pytest.raises(SatelliteServiceError, match="timed out"),
        ):
            await get_sentinel_token()


# -- NDVI Fetch Tests --------------------------------------------------------


class TestFetchNdvi:
    """Tests for Sentinel-2 NDVI fetch pipeline."""

    @pytest.mark.asyncio
    async def test_returns_all_keys(self) -> None:
        """Successful fetch returns structured NDVI response."""
        process_client = _make_mock_client(_mock_response(content=MOCK_RASTER_BYTES))

        with (
            patch(
                "app.services.satellite_service.get_sentinel_token",
                return_value="mock-token",
            ),
            patch(
                "app.services.satellite_service.httpx.AsyncClient",
                return_value=process_client,
            ),
        ):
            result = await fetch_ndvi(MOCK_BOUNDS)

        assert "ndvi_mean" in result
        assert "bbox" in result
        assert "time_range_start" in result
        assert "time_range_end" in result
        assert "data_source" in result
        assert result["data_source"] == "sentinel-2-l2a"

    @pytest.mark.asyncio
    async def test_bbox_passed_correctly(self) -> None:
        with (
            patch(
                "app.services.satellite_service.get_sentinel_token",
                return_value="mock-token",
            ),
            patch(
                "app.services.satellite_service.httpx.AsyncClient",
                return_value=_make_mock_client(_mock_response(content=MOCK_RASTER_BYTES)),
            ),
        ):
            result = await fetch_ndvi(MOCK_BOUNDS)

        assert result["bbox"] == [77.5, 12.9, 77.6, 13.0]

    @pytest.mark.asyncio
    async def test_process_non_200_raises(self) -> None:
        with (
            patch(
                "app.services.satellite_service.get_sentinel_token",
                return_value="mock-token",
            ),
            patch(
                "app.services.satellite_service.httpx.AsyncClient",
                return_value=_make_mock_client(_mock_response(status_code=403, content=b"")),
            ),
            pytest.raises(SatelliteServiceError, match="HTTP 403"),
        ):
            await fetch_ndvi(MOCK_BOUNDS)

    @pytest.mark.asyncio
    async def test_process_timeout_raises(self) -> None:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.ReadTimeout("timeout"))

        with (
            patch(
                "app.services.satellite_service.get_sentinel_token",
                return_value="mock-token",
            ),
            patch(
                "app.services.satellite_service.httpx.AsyncClient",
                return_value=mock_client,
            ),
            pytest.raises(SatelliteServiceError, match="timed out"),
        ):
            await fetch_ndvi(MOCK_BOUNDS)


# -- NDVI Response Builder Tests ---------------------------------------------


class TestBuildNdviResponse:
    """Tests for the response-builder helper."""

    def test_normal_raster_returns_moderate_ndvi(self) -> None:
        result = _build_ndvi_response(
            response_content=MOCK_RASTER_BYTES,
            bounds=MOCK_BOUNDS,
            time_from="2026-01-01T00:00:00Z",
            time_to="2026-03-31T23:59:59Z",
        )
        assert result["ndvi_mean"] == 0.45
        assert result["data_source"] == "sentinel-2-l2a"

    def test_small_raster_returns_low_ndvi(self) -> None:
        result = _build_ndvi_response(
            response_content=MOCK_SMALL_RASTER,
            bounds=MOCK_BOUNDS,
            time_from="2026-01-01T00:00:00Z",
            time_to="2026-03-31T23:59:59Z",
        )
        assert result["ndvi_mean"] == 0.1

    def test_empty_content_raises(self) -> None:
        with pytest.raises(SatelliteServiceError, match="empty raster"):
            _build_ndvi_response(
                response_content=b"",
                bounds=MOCK_BOUNDS,
                time_from="2026-01-01T00:00:00Z",
                time_to="2026-03-31T23:59:59Z",
            )


# -- Content Length Estimator Tests -------------------------------------------


class TestEstimateNdvi:
    """Tests for the MVP content-length heuristic."""

    def test_large_payload_moderate(self) -> None:
        assert _estimate_ndvi_from_content_length(262_144) == 0.45

    def test_small_payload_barren(self) -> None:
        assert _estimate_ndvi_from_content_length(50) == 0.1

    def test_boundary_100_bytes(self) -> None:
        assert _estimate_ndvi_from_content_length(100) == 0.45

    def test_boundary_99_bytes(self) -> None:
        assert _estimate_ndvi_from_content_length(99) == 0.1
