"""Tests for Crop Engine service."""

import pytest

from app.engines.crop.service import (
    analyze_crop,
    classify_moisture,
    classify_ndvi,
    compute_crop_health,
    estimate_growth_stage,
    estimate_yield,
    generate_crop_recommendations,
)


class TestClassifyNDVI:
    """NDVI classification tests."""

    def test_poor(self) -> None:
        assert classify_ndvi(0.1) == "poor"

    def test_fair(self) -> None:
        assert classify_ndvi(0.35) == "fair"

    def test_good(self) -> None:
        assert classify_ndvi(0.55) == "good"

    def test_excellent(self) -> None:
        assert classify_ndvi(0.8) == "excellent"

    def test_none(self) -> None:
        assert classify_ndvi(None) == "unknown"


class TestClassifyMoisture:
    """SAR moisture classification tests."""

    def test_dry(self) -> None:
        assert classify_moisture(-20.0) == "dry"

    def test_moderate(self) -> None:
        assert classify_moisture(-16.0) == "moderate"

    def test_wet(self) -> None:
        assert classify_moisture(-12.0) == "wet"

    def test_saturated(self) -> None:
        assert classify_moisture(-5.0) == "saturated"

    def test_none(self) -> None:
        assert classify_moisture(None) == "unknown"


class TestGrowthStage:
    """Growth stage estimation tests."""

    def test_from_ndvi_high(self) -> None:
        stage = estimate_growth_stage(crop_type="rice", planting_date=None, ndvi=0.75)
        assert stage == "maturity_or_senescence"

    def test_from_ndvi_low(self) -> None:
        stage = estimate_growth_stage(crop_type="rice", planting_date=None, ndvi=0.1)
        assert stage == "bare_soil_or_germination"

    def test_from_planting_date(self) -> None:
        stage = estimate_growth_stage(crop_type="rice", planting_date="2025-01-01", ndvi=0.5)
        assert isinstance(stage, str)

    def test_unknown_when_no_data(self) -> None:
        stage = estimate_growth_stage(crop_type="rice", planting_date=None, ndvi=None)
        assert stage == "unknown"


class TestYieldEstimate:
    """Yield estimation tests."""

    def test_returns_dict(self) -> None:
        y = estimate_yield(crop_type="rice", ndvi=0.6, soil_health=70, weather_risk=20)
        assert "predicted_yield" in y
        assert "confidence" in y
        assert y["predicted_yield"] > 0

    def test_high_confidence_with_all_data(self) -> None:
        y = estimate_yield(crop_type="rice", ndvi=0.7, soil_health=80, weather_risk=15)
        assert y["confidence"] == "high"

    def test_low_inputs_lower_yield(self) -> None:
        y_low = estimate_yield(crop_type="rice", ndvi=0.2, soil_health=30, weather_risk=80)
        y_high = estimate_yield(crop_type="rice", ndvi=0.8, soil_health=80, weather_risk=10)
        assert y_low["predicted_yield"] < y_high["predicted_yield"]


class TestCropHealth:
    """Crop health score tests."""

    def test_health_score_range(self) -> None:
        score = compute_crop_health(ndvi=0.6, moisture="moderate", growth_stage="tillering")
        assert 0 <= score <= 100

    def test_dry_lowers_score(self) -> None:
        score_dry = compute_crop_health(ndvi=0.5, moisture="dry", growth_stage="tillering")
        score_mod = compute_crop_health(ndvi=0.5, moisture="moderate", growth_stage="tillering")
        assert score_dry < score_mod


class TestCropRecommendations:
    """Crop recommendation tests."""

    def test_returns_list(self) -> None:
        recs = generate_crop_recommendations("poor", "dry", "rice", "vegetative")
        assert isinstance(recs, list)
        assert len(recs) > 0


@pytest.mark.asyncio
async def test_analyze_crop_returns_expected_keys() -> None:
    """End-to-end crop analysis test."""
    bounds = {"north": 17.4, "south": 17.37, "east": 78.5, "west": 78.47}
    result = await analyze_crop(
        lat=17.385,
        lon=78.487,
        bounds=bounds,
        crop_type="rice",
        planting_date=None,
    )
    assert "vegetation" in result
    assert "yield_forecast" in result
    assert "crop_health_score" in result
    assert "recommendations" in result
