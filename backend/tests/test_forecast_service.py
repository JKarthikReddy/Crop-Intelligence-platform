"""Unit tests for the OpenWeather forecast service (mocked HTTP)."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.forecast_service import ForecastServiceError, fetch_forecast

# -- Fixtures ---------------------------------------------------------------

MOCK_FORECAST_RESPONSE = {
    "list": [
        {"main": {"temp": 30.0}, "rain": {"3h": 2.5}},
        {"main": {"temp": 32.0}, "rain": {"3h": 1.0}},
        {"main": {"temp": 28.0}},
        {"main": {"temp": 34.0}, "rain": {"3h": 5.0}},
        {"main": {"temp": 31.0}, "rain": {"3h": 0.5}},
    ]
}

MOCK_HEATWAVE_RESPONSE = {
    "list": [
        {"main": {"temp": 36.0}},
        {"main": {"temp": 38.5}},
        {"main": {"temp": 37.0}},
    ]
}

MOCK_HEAVY_RAIN_RESPONSE = {
    "list": [
        {"main": {"temp": 25.0}, "rain": {"3h": 20.0}},
        {"main": {"temp": 24.0}, "rain": {"3h": 18.0}},
        {"main": {"temp": 23.0}, "rain": {"3h": 15.0}},
    ]
}

MOCK_MALFORMED = {"unexpected": "structure"}


# -- Helpers ----------------------------------------------------------------


def _mock_response(json_data: dict, status_code: int = 200) -> httpx.Response:
    """Build a fake httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("GET", "https://test"),
    )


def _make_mock_client(response: httpx.Response) -> AsyncMock:
    """Create a fully-wired async context-manager mock client."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=response)
    return mock_client


# -- Happy path -------------------------------------------------------------


class TestFetchForecast:
    """Tests with mocked OpenWeather HTTP responses."""

    @pytest.mark.asyncio
    async def test_returns_all_keys(self) -> None:
        client = _make_mock_client(_mock_response(MOCK_FORECAST_RESPONSE))

        with patch(
            "app.services.forecast_service.httpx.AsyncClient",
            return_value=client,
        ):
            result = await fetch_forecast(12.0, 77.0)

        assert "avg_temp_next_5d" in result
        assert "max_temp_next_5d" in result
        assert "total_rain_next_5d" in result
        assert "heat_risk_flag" in result
        assert "heavy_rain_flag" in result

    @pytest.mark.asyncio
    async def test_averages_calculated_correctly(self) -> None:
        client = _make_mock_client(_mock_response(MOCK_FORECAST_RESPONSE))

        with patch(
            "app.services.forecast_service.httpx.AsyncClient",
            return_value=client,
        ):
            result = await fetch_forecast(12.0, 77.0)

        # (30 + 32 + 28 + 34 + 31) / 5 = 31.0
        assert result["avg_temp_next_5d"] == 31.0
        assert result["max_temp_next_5d"] == 34.0
        # 2.5 + 1.0 + 0 + 5.0 + 0.5 = 9.0
        assert result["total_rain_next_5d"] == 9.0
        # max 34 < 35 => no heat risk
        assert result["heat_risk_flag"] is False
        # total rain 9 < 50 => no heavy rain
        assert result["heavy_rain_flag"] is False

    @pytest.mark.asyncio
    async def test_heat_risk_flag_triggered(self) -> None:
        """Max temp > 35 C triggers heat_risk_flag."""
        client = _make_mock_client(_mock_response(MOCK_HEATWAVE_RESPONSE))

        with patch(
            "app.services.forecast_service.httpx.AsyncClient",
            return_value=client,
        ):
            result = await fetch_forecast(12.0, 77.0)

        assert result["max_temp_next_5d"] == 38.5
        assert result["heat_risk_flag"] is True

    @pytest.mark.asyncio
    async def test_heavy_rain_flag_triggered(self) -> None:
        """Total rainfall > 50 mm triggers heavy_rain_flag."""
        client = _make_mock_client(_mock_response(MOCK_HEAVY_RAIN_RESPONSE))

        with patch(
            "app.services.forecast_service.httpx.AsyncClient",
            return_value=client,
        ):
            result = await fetch_forecast(12.0, 77.0)

        # 20 + 18 + 15 = 53.0
        assert result["total_rain_next_5d"] == 53.0
        assert result["heavy_rain_flag"] is True


# -- Error handling ----------------------------------------------------------


class TestForecastServiceErrors:
    """API failure modes must raise ForecastServiceError."""

    @pytest.mark.asyncio
    async def test_non_200_raises(self) -> None:
        client = _make_mock_client(_mock_response({}, status_code=401))

        with (
            patch(
                "app.services.forecast_service.httpx.AsyncClient",
                return_value=client,
            ),
            pytest.raises(ForecastServiceError, match="HTTP 401"),
        ):
            await fetch_forecast(12.0, 77.0)

    @pytest.mark.asyncio
    async def test_malformed_response_raises(self) -> None:
        client = _make_mock_client(_mock_response(MOCK_MALFORMED))

        with (
            patch(
                "app.services.forecast_service.httpx.AsyncClient",
                return_value=client,
            ),
            pytest.raises(ForecastServiceError, match="Unexpected"),
        ):
            await fetch_forecast(12.0, 77.0)

    @pytest.mark.asyncio
    async def test_timeout_raises(self) -> None:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.ReadTimeout("timeout"))

        with (
            patch(
                "app.services.forecast_service.httpx.AsyncClient",
                return_value=mock_client,
            ),
            pytest.raises(ForecastServiceError, match="timed out"),
        ):
            await fetch_forecast(12.0, 77.0)
