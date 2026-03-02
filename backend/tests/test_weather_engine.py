"""Tests for Weather Engine service."""

import pytest

from app.engines.weather.service import (
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
    assert "climate" in result
    assert "forecast" in result
    assert "risk_assessment" in result
    assert "recommendations" in result
