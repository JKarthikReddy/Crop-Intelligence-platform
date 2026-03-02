"""Unit tests for the NASA POWER weather service (mocked HTTP)."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.weather_service import WeatherServiceError, fetch_nasa_weather

# -- Fixtures ---------------------------------------------------------------

MOCK_NASA_RESPONSE = {
    "properties": {
        "parameter": {
            "T2M": {
                "20260101": 28.5,
                "20260102": 29.0,
                "20260103": 27.8,
            },
            "ALLSKY_SFC_SW_DWN": {
                "20260101": 18.2,
                "20260102": 19.1,
                "20260103": 17.5,
            },
            "WS2M": {
                "20260101": 3.1,
                "20260102": 3.5,
                "20260103": 2.9,
            },
        }
    }
}

MOCK_NASA_WITH_FILL = {
    "properties": {
        "parameter": {
            "T2M": {
                "20260101": 28.0,
                "20260102": -999,
                "20260103": 30.0,
            },
            "ALLSKY_SFC_SW_DWN": {
                "20260101": -999,
                "20260102": -999,
                "20260103": -999,
            },
            "WS2M": {
                "20260101": 4.0,
                "20260102": 4.0,
                "20260103": 4.0,
            },
        }
    }
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


class TestFetchNasaWeather:
    """Tests with mocked NASA POWER HTTP responses."""

    @pytest.mark.asyncio
    async def test_returns_all_keys(self):
        client = _make_mock_client(_mock_response(MOCK_NASA_RESPONSE))

        with patch(
            "app.services.weather_service.httpx.AsyncClient",
            return_value=client,
        ):
            result = await fetch_nasa_weather(12.0, 77.0)

        assert "temperature_avg_30d" in result
        assert "solar_radiation_avg_30d" in result
        assert "wind_speed_avg_30d" in result

    @pytest.mark.asyncio
    async def test_averages_calculated_correctly(self):
        client = _make_mock_client(_mock_response(MOCK_NASA_RESPONSE))

        with patch(
            "app.services.weather_service.httpx.AsyncClient",
            return_value=client,
        ):
            result = await fetch_nasa_weather(12.0, 77.0)

        # (28.5 + 29.0 + 27.8) / 3 = 28.43
        assert result["temperature_avg_30d"] == 28.43
        # (18.2 + 19.1 + 17.5) / 3 = 18.27
        assert result["solar_radiation_avg_30d"] == 18.27
        # (3.1 + 3.5 + 2.9) / 3 = 3.17
        assert result["wind_speed_avg_30d"] == 3.17

    @pytest.mark.asyncio
    async def test_fill_values_filtered(self):
        """NASA uses -999 for missing data; these must be excluded."""
        client = _make_mock_client(_mock_response(MOCK_NASA_WITH_FILL))

        with patch(
            "app.services.weather_service.httpx.AsyncClient",
            return_value=client,
        ):
            result = await fetch_nasa_weather(12.0, 77.0)

        # T2M: (28.0 + 30.0) / 2 = 29.0  (one -999 filtered)
        assert result["temperature_avg_30d"] == 29.0
        # ALLSKY: all -999 -> None
        assert result["solar_radiation_avg_30d"] is None
        # WS2M: (4+4+4)/3 = 4.0
        assert result["wind_speed_avg_30d"] == 4.0


# -- Error handling ---------------------------------------------------------


class TestWeatherServiceErrors:
    """Tests for failure modes."""

    @pytest.mark.asyncio
    async def test_non_200_raises(self):
        client = _make_mock_client(_mock_response({"error": "bad request"}, status_code=400))

        with (
            patch(
                "app.services.weather_service.httpx.AsyncClient",
                return_value=client,
            ),
            pytest.raises(WeatherServiceError, match="HTTP 400"),
        ):
            await fetch_nasa_weather(12.0, 77.0)

    @pytest.mark.asyncio
    async def test_malformed_response_raises(self):
        client = _make_mock_client(_mock_response(MOCK_MALFORMED))

        with (
            patch(
                "app.services.weather_service.httpx.AsyncClient",
                return_value=client,
            ),
            pytest.raises(WeatherServiceError, match="Unexpected"),
        ):
            await fetch_nasa_weather(12.0, 77.0)

    @pytest.mark.asyncio
    async def test_timeout_raises(self):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

        with (
            patch(
                "app.services.weather_service.httpx.AsyncClient",
                return_value=mock_client,
            ),
            pytest.raises(WeatherServiceError, match="timed out"),
        ):
            await fetch_nasa_weather(12.0, 77.0)
