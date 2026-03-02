"""Tests for Weather Engine service."""

from typing import ClassVar

import pytest

from app.engines.weather.service import (
    _parse_current_weather,
    analyze_weather,
    assess_weather_risks,
    calculate_et0,
    generate_weather_recommendations,
    irrigation_recommendation,
    water_stress_indicator,
)


class TestET0:
    """ET0 evapotranspiration calculation tests."""

    def test_typical_conditions(self) -> None:
        et0 = calculate_et0(temperature=25.0, solar_radiation=18.0, wind_speed=2.0)
        assert et0 > 0

    def test_zero_radiation(self) -> None:
        et0 = calculate_et0(temperature=25.0, solar_radiation=0.0, wind_speed=1.0)
        assert et0 >= 0


class TestWaterStress:
    """Water stress indicator tests."""

    def test_high(self) -> None:
        assert water_stress_indicator(7.0) == "high"

    def test_moderate(self) -> None:
        assert water_stress_indicator(5.0) == "moderate"

    def test_low(self) -> None:
        assert water_stress_indicator(3.0) == "low"


class TestIrrigation:
    """Irrigation recommendation tests."""

    def test_deficit_recommends_irrigation(self) -> None:
        rec = irrigation_recommendation(et0=6.0, rain_forecast=5.0)
        assert "irrigat" in rec.lower()

    def test_adequate_rain_no_irrigation(self) -> None:
        rec = irrigation_recommendation(et0=3.0, rain_forecast=50.0)
        assert "no irrigation" in rec.lower() or "adequate" in rec.lower()


class TestWeatherRisks:
    """Weather risk assessment tests."""

    def test_drought_risk_low_rain(self) -> None:
        risk = assess_weather_risks(
            climate={"precipitation_sum_30d": 5, "temperature_avg_30d": 30},
            forecast=None,
        )
        assert risk["drought_risk"] == "critical"
        assert risk["overall_risk_score"] > 30

    def test_frost_risk(self) -> None:
        risk = assess_weather_risks(
            climate={"temperature_avg_30d": 3, "precipitation_sum_30d": 40},
            forecast=None,
        )
        assert risk["frost_risk"] == "high"

    def test_flood_risk(self) -> None:
        risk = assess_weather_risks(
            climate=None,
            forecast={"total_rain_next_5d": 120, "max_temp_next_5d": 28},
        )
        assert risk["flood_risk"] == "critical"

    def test_no_data_low_risk(self) -> None:
        risk = assess_weather_risks(climate=None, forecast=None)
        assert risk["overall_risk_score"] == 0.0


class TestWeatherRecommendations:
    """Weather recommendation tests."""

    def test_drought_gets_irrigation_rec(self) -> None:
        recs = generate_weather_recommendations(
            None, None, {"drought_risk": "critical", "flood_risk": "low", "frost_risk": "none"}
        )
        assert any("drought" in r.lower() or "irrigat" in r.lower() for r in recs)

    def test_good_weather(self) -> None:
        recs = generate_weather_recommendations(
            None, None, {"drought_risk": "low", "flood_risk": "low", "frost_risk": "none"}
        )
        assert any("favorable" in r.lower() for r in recs)


@pytest.mark.asyncio
async def test_analyze_weather_returns_expected_keys() -> None:
    """End-to-end weather analysis test."""
    result = await analyze_weather(lat=17.385, lon=78.487)
    assert "current" in result
    assert "climate" in result
    assert "forecast" in result
    assert "risk_assessment" in result
    assert "recommendations" in result


class TestParseCurrentWeather:
    """Tests for _parse_current_weather helper."""

    _SAMPLE_RESPONSE: ClassVar[dict] = {
        "coord": {"lon": 78.49, "lat": 17.39},
        "weather": [
            {"id": 802, "main": "Clouds", "description": "scattered clouds", "icon": "03d"}
        ],
        "base": "stations",
        "main": {
            "temp": 30.5,
            "feels_like": 29.8,
            "temp_min": 29.0,
            "temp_max": 31.5,
            "pressure": 1012,
            "humidity": 45,
            "sea_level": 1012,
            "grnd_level": 960,
        },
        "visibility": 10000,
        "wind": {"speed": 3.5, "deg": 180, "gust": 5.2},
        "clouds": {"all": 40},
        "dt": 1772475938,
        "sys": {
            "type": 2,
            "id": 9214,
            "country": "IN",
            "sunrise": 1772413449,
            "sunset": 1772455965,
        },
        "timezone": 19800,
        "id": 1269843,
        "name": "Hyderabad",
        "cod": 200,
    }

    def test_parses_temperature(self) -> None:
        result = _parse_current_weather(self._SAMPLE_RESPONSE)
        assert result["temperature"] == 30.5
        assert result["feels_like"] == 29.8
        assert result["temp_min"] == 29.0
        assert result["temp_max"] == 31.5

    def test_parses_wind(self) -> None:
        result = _parse_current_weather(self._SAMPLE_RESPONSE)
        assert result["wind_speed"] == 3.5
        assert result["wind_deg"] == 180
        assert result["wind_gust"] == 5.2

    def test_parses_weather_description(self) -> None:
        result = _parse_current_weather(self._SAMPLE_RESPONSE)
        assert result["weather_main"] == "Clouds"
        assert result["weather_description"] == "scattered clouds"
        assert result["weather_icon"] == "03d"

    def test_parses_location(self) -> None:
        result = _parse_current_weather(self._SAMPLE_RESPONSE)
        assert result["city_name"] == "Hyderabad"
        assert result["country"] == "IN"

    def test_parses_sys_times(self) -> None:
        result = _parse_current_weather(self._SAMPLE_RESPONSE)
        assert result["sunrise"] == 1772413449
        assert result["sunset"] == 1772455965
        assert result["dt"] == 1772475938

    def test_optional_rain_snow(self) -> None:
        result = _parse_current_weather(self._SAMPLE_RESPONSE)
        assert result["rain_1h"] is None
        assert result["snow_1h"] is None

    def test_rain_present(self) -> None:
        data = {**self._SAMPLE_RESPONSE, "rain": {"1h": 2.5}}
        result = _parse_current_weather(data)
        assert result["rain_1h"] == 2.5

    def test_missing_main_raises(self) -> None:
        from app.engines.weather.service import WeatherEngineError

        with pytest.raises(WeatherEngineError):
            _parse_current_weather({"weather": [], "wind": {}, "sys": {}})
