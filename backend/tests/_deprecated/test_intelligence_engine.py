"""Unit tests for the unified intelligence engine (all services mocked)."""

from unittest.mock import patch

import pytest

from app.services.forecast_service import ForecastServiceError
from app.services.intelligence_engine import (
    IntelligenceEngineError,
    generate_intelligence,
)
from app.services.satellite_service import SatelliteServiceError
from app.services.soil_service import SoilServiceError
from app.services.weather_service import WeatherServiceError

# -- Fixtures ---------------------------------------------------------------

VALID_GEOJSON = {
    "type": "Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [
                [77.5, 12.9],
                [77.6, 12.9],
                [77.6, 13.0],
                [77.5, 13.0],
                [77.5, 12.9],
            ]
        ],
    },
    "properties": {},
}

MOCK_SOIL = {"ph": 6.4, "clay_percent": 280, "organic_carbon": 110}

MOCK_CLIMATE = {
    "temperature_avg_30d": 29.2,
    "solar_radiation_avg_30d": 18.5,
    "wind_speed_avg_30d": 3.1,
}

MOCK_FORECAST = {
    "avg_temp_next_5d": 31.5,
    "max_temp_next_5d": 38.2,
    "total_rain_next_5d": 22.1,
    "heat_risk_flag": True,
    "heavy_rain_flag": False,
}

MOCK_NDVI = {
    "ndvi_mean": 0.45,
    "bbox": [77.5, 12.9, 77.6, 13.0],
    "time_range_start": "2025-11-26T00:00:00Z",
    "time_range_end": "2026-02-24T23:59:59Z",
    "data_source": "sentinel-2-l2a",
}

MOCK_SAR = {
    "sar_vv_mean": -14.2,
    "sar_vh_mean": -18.7,
    "moisture_indicator": "moderate",
    "bbox": [77.5, 12.9, 77.6, 13.0],
    "time_range_start": "2025-11-26T00:00:00Z",
    "time_range_end": "2026-02-24T23:59:59Z",
    "data_source": "sentinel-1-grd",
}


# -- Helpers ----------------------------------------------------------------

_SOIL_PATCH = "app.services.intelligence_engine.fetch_soil_data"
_WEATHER_PATCH = "app.services.intelligence_engine.fetch_nasa_weather"
_FORECAST_PATCH = "app.services.intelligence_engine.fetch_forecast"
_NDVI_PATCH = "app.services.intelligence_engine.fetch_ndvi"
_SAR_PATCH = "app.services.intelligence_engine.fetch_sar"


def _patch_all_services(
    soil=MOCK_SOIL,
    climate=MOCK_CLIMATE,
    forecast=MOCK_FORECAST,
    ndvi=MOCK_NDVI,
    sar=MOCK_SAR,
):
    """Return a combined context manager patching all five services."""
    from unittest.mock import AsyncMock

    return (
        patch(_SOIL_PATCH, new_callable=AsyncMock, return_value=soil),
        patch(_WEATHER_PATCH, new_callable=AsyncMock, return_value=climate),
        patch(_FORECAST_PATCH, new_callable=AsyncMock, return_value=forecast),
        patch(_NDVI_PATCH, new_callable=AsyncMock, return_value=ndvi),
        patch(_SAR_PATCH, new_callable=AsyncMock, return_value=sar),
    )


# -- Happy Path --------------------------------------------------------------


class TestGenerateIntelligence:
    """Tests with all services mocked to succeed."""

    @pytest.mark.asyncio
    async def test_returns_all_top_level_keys(self) -> None:
        p_soil, p_weather, p_forecast, p_ndvi, p_sar = _patch_all_services()
        with p_soil, p_weather, p_forecast, p_ndvi, p_sar:
            result = await generate_intelligence(VALID_GEOJSON)

        assert "location" in result
        assert "soil" in result
        assert "climate" in result
        assert "forecast" in result
        assert "satellite" in result
        assert "water_model" in result

    @pytest.mark.asyncio
    async def test_location_has_centroid_and_area(self) -> None:
        p_soil, p_weather, p_forecast, p_ndvi, p_sar = _patch_all_services()
        with p_soil, p_weather, p_forecast, p_ndvi, p_sar:
            result = await generate_intelligence(VALID_GEOJSON)

        loc = result["location"]
        assert "centroid" in loc
        assert "bounds" in loc
        assert "area_hectares" in loc
        assert len(loc["centroid"]) == 2
        assert len(loc["bounds"]) == 4
        assert loc["area_hectares"] > 0

    @pytest.mark.asyncio
    async def test_soil_data_passed_through(self) -> None:
        p_soil, p_weather, p_forecast, p_ndvi, p_sar = _patch_all_services()
        with p_soil, p_weather, p_forecast, p_ndvi, p_sar:
            result = await generate_intelligence(VALID_GEOJSON)

        assert result["soil"] == MOCK_SOIL

    @pytest.mark.asyncio
    async def test_climate_data_passed_through(self) -> None:
        p_soil, p_weather, p_forecast, p_ndvi, p_sar = _patch_all_services()
        with p_soil, p_weather, p_forecast, p_ndvi, p_sar:
            result = await generate_intelligence(VALID_GEOJSON)

        assert result["climate"] == MOCK_CLIMATE

    @pytest.mark.asyncio
    async def test_forecast_data_passed_through(self) -> None:
        p_soil, p_weather, p_forecast, p_ndvi, p_sar = _patch_all_services()
        with p_soil, p_weather, p_forecast, p_ndvi, p_sar:
            result = await generate_intelligence(VALID_GEOJSON)

        assert result["forecast"] == MOCK_FORECAST

    @pytest.mark.asyncio
    async def test_satellite_contains_ndvi_and_sar(self) -> None:
        p_soil, p_weather, p_forecast, p_ndvi, p_sar = _patch_all_services()
        with p_soil, p_weather, p_forecast, p_ndvi, p_sar:
            result = await generate_intelligence(VALID_GEOJSON)

        assert result["satellite"]["ndvi"] == MOCK_NDVI
        assert result["satellite"]["sar"] == MOCK_SAR


# -- Graceful Degradation ---------------------------------------------------


class TestPartialFailure:
    """Verify that individual service failures degrade gracefully."""

    @pytest.mark.asyncio
    async def test_soil_failure_returns_none(self) -> None:
        from unittest.mock import AsyncMock

        with (
            patch(
                _SOIL_PATCH,
                new_callable=AsyncMock,
                side_effect=SoilServiceError("SoilGrids down"),
            ),
            patch(_WEATHER_PATCH, new_callable=AsyncMock, return_value=MOCK_CLIMATE),
            patch(_FORECAST_PATCH, new_callable=AsyncMock, return_value=MOCK_FORECAST),
            patch(_NDVI_PATCH, new_callable=AsyncMock, return_value=MOCK_NDVI),
            patch(_SAR_PATCH, new_callable=AsyncMock, return_value=MOCK_SAR),
        ):
            result = await generate_intelligence(VALID_GEOJSON)

        assert result["soil"] is None
        assert result["climate"] == MOCK_CLIMATE
        assert result["forecast"] == MOCK_FORECAST
        assert result["satellite"]["ndvi"] == MOCK_NDVI
        assert result["satellite"]["sar"] == MOCK_SAR

    @pytest.mark.asyncio
    async def test_weather_failure_returns_none(self) -> None:
        from unittest.mock import AsyncMock

        with (
            patch(_SOIL_PATCH, new_callable=AsyncMock, return_value=MOCK_SOIL),
            patch(
                _WEATHER_PATCH,
                new_callable=AsyncMock,
                side_effect=WeatherServiceError("NASA POWER down"),
            ),
            patch(_FORECAST_PATCH, new_callable=AsyncMock, return_value=MOCK_FORECAST),
            patch(_NDVI_PATCH, new_callable=AsyncMock, return_value=MOCK_NDVI),
            patch(_SAR_PATCH, new_callable=AsyncMock, return_value=MOCK_SAR),
        ):
            result = await generate_intelligence(VALID_GEOJSON)

        assert result["soil"] == MOCK_SOIL
        assert result["climate"] is None

    @pytest.mark.asyncio
    async def test_weather_failure_water_model_none(self) -> None:
        """When climate fails, water_model degrades to None."""
        from unittest.mock import AsyncMock

        with (
            patch(_SOIL_PATCH, new_callable=AsyncMock, return_value=MOCK_SOIL),
            patch(
                _WEATHER_PATCH,
                new_callable=AsyncMock,
                side_effect=WeatherServiceError("NASA POWER down"),
            ),
            patch(_FORECAST_PATCH, new_callable=AsyncMock, return_value=MOCK_FORECAST),
            patch(_NDVI_PATCH, new_callable=AsyncMock, return_value=MOCK_NDVI),
            patch(_SAR_PATCH, new_callable=AsyncMock, return_value=MOCK_SAR),
        ):
            result = await generate_intelligence(VALID_GEOJSON)

        assert result["water_model"] is None

    @pytest.mark.asyncio
    async def test_forecast_failure_returns_none(self) -> None:
        from unittest.mock import AsyncMock

        with (
            patch(_SOIL_PATCH, new_callable=AsyncMock, return_value=MOCK_SOIL),
            patch(_WEATHER_PATCH, new_callable=AsyncMock, return_value=MOCK_CLIMATE),
            patch(
                _FORECAST_PATCH,
                new_callable=AsyncMock,
                side_effect=ForecastServiceError("OpenWeather down"),
            ),
            patch(_NDVI_PATCH, new_callable=AsyncMock, return_value=MOCK_NDVI),
            patch(_SAR_PATCH, new_callable=AsyncMock, return_value=MOCK_SAR),
        ):
            result = await generate_intelligence(VALID_GEOJSON)

        assert result["forecast"] is None
        assert result["satellite"]["ndvi"] == MOCK_NDVI
        assert result["satellite"]["sar"] == MOCK_SAR

    @pytest.mark.asyncio
    async def test_ndvi_failure_sar_still_works(self) -> None:
        from unittest.mock import AsyncMock

        with (
            patch(_SOIL_PATCH, new_callable=AsyncMock, return_value=MOCK_SOIL),
            patch(_WEATHER_PATCH, new_callable=AsyncMock, return_value=MOCK_CLIMATE),
            patch(_FORECAST_PATCH, new_callable=AsyncMock, return_value=MOCK_FORECAST),
            patch(
                _NDVI_PATCH,
                new_callable=AsyncMock,
                side_effect=SatelliteServiceError("Sentinel-2 clouded out"),
            ),
            patch(_SAR_PATCH, new_callable=AsyncMock, return_value=MOCK_SAR),
        ):
            result = await generate_intelligence(VALID_GEOJSON)

        assert result["satellite"]["ndvi"] is None
        assert result["satellite"]["sar"] == MOCK_SAR
        assert result["soil"] == MOCK_SOIL

    @pytest.mark.asyncio
    async def test_sar_failure_ndvi_still_works(self) -> None:
        from unittest.mock import AsyncMock

        with (
            patch(_SOIL_PATCH, new_callable=AsyncMock, return_value=MOCK_SOIL),
            patch(_WEATHER_PATCH, new_callable=AsyncMock, return_value=MOCK_CLIMATE),
            patch(_FORECAST_PATCH, new_callable=AsyncMock, return_value=MOCK_FORECAST),
            patch(_NDVI_PATCH, new_callable=AsyncMock, return_value=MOCK_NDVI),
            patch(
                _SAR_PATCH,
                new_callable=AsyncMock,
                side_effect=SatelliteServiceError("Sentinel-1 down"),
            ),
        ):
            result = await generate_intelligence(VALID_GEOJSON)

        assert result["satellite"]["ndvi"] == MOCK_NDVI
        assert result["satellite"]["sar"] is None

    @pytest.mark.asyncio
    async def test_all_services_fail_returns_all_none(self) -> None:
        from unittest.mock import AsyncMock

        with (
            patch(
                _SOIL_PATCH,
                new_callable=AsyncMock,
                side_effect=SoilServiceError("down"),
            ),
            patch(
                _WEATHER_PATCH,
                new_callable=AsyncMock,
                side_effect=WeatherServiceError("down"),
            ),
            patch(
                _FORECAST_PATCH,
                new_callable=AsyncMock,
                side_effect=ForecastServiceError("down"),
            ),
            patch(
                _NDVI_PATCH,
                new_callable=AsyncMock,
                side_effect=SatelliteServiceError("down"),
            ),
            patch(
                _SAR_PATCH,
                new_callable=AsyncMock,
                side_effect=SatelliteServiceError("down"),
            ),
        ):
            result = await generate_intelligence(VALID_GEOJSON)

        assert result["soil"] is None
        assert result["climate"] is None
        assert result["forecast"] is None
        assert result["satellite"]["ndvi"] is None
        assert result["satellite"]["sar"] is None
        # Location must still be present
        assert result["location"]["area_hectares"] > 0
        # Water model also None when climate fails
        assert result["water_model"] is None


# -- Geometry Failure --------------------------------------------------------


class TestGeometryFailure:
    """Invalid geometry must raise IntelligenceEngineError immediately."""

    @pytest.mark.asyncio
    async def test_empty_geojson_raises(self) -> None:
        with pytest.raises(IntelligenceEngineError, match="Geometry error"):
            await generate_intelligence({})

    @pytest.mark.asyncio
    async def test_missing_geometry_key_raises(self) -> None:
        with pytest.raises(IntelligenceEngineError, match="Geometry error"):
            await generate_intelligence({"type": "Feature", "properties": {}})

    @pytest.mark.asyncio
    async def test_point_geometry_raises(self) -> None:
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [77.5, 12.9],
            },
            "properties": {},
        }
        with pytest.raises(IntelligenceEngineError, match="Geometry error"):
            await generate_intelligence(geojson)
