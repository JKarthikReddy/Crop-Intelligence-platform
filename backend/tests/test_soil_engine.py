"""Tests for Soil Engine service."""

import pytest

from app.engines.soil.service import (
    analyze_soil,
    assess_nutrients,
    classify_ph,
    classify_texture,
    compute_soil_health_index,
    generate_soil_recommendations,
)


class TestClassifyPh:
    """pH classification tests."""

    def test_strongly_acidic(self) -> None:
        assert classify_ph(3.0) == "strongly_acidic"

    def test_acidic(self) -> None:
        assert classify_ph(5.6) == "acidic"

    def test_slightly_acidic(self) -> None:
        assert classify_ph(6.5) == "slightly_acidic"

    def test_neutral(self) -> None:
        assert classify_ph(7.0) == "neutral"

    def test_slightly_alkaline(self) -> None:
        assert classify_ph(7.5) == "slightly_alkaline"

    def test_alkaline(self) -> None:
        assert classify_ph(8.0) == "alkaline"

    def test_strongly_alkaline(self) -> None:
        assert classify_ph(9.0) == "strongly_alkaline"

    def test_none_returns_unknown(self) -> None:
        assert classify_ph(None) == "unknown"


class TestClassifyTexture:
    """Soil texture classification tests."""

    def test_sandy(self) -> None:
        assert classify_texture(100) == "sandy"

    def test_loamy(self) -> None:
        assert classify_texture(250) == "loamy"

    def test_clayey(self) -> None:
        assert classify_texture(450) == "clayey"

    def test_none_returns_unknown(self) -> None:
        assert classify_texture(None) == "unknown"


class TestAssessNutrients:
    """Nutrient assessment tests."""

    def test_poor_oc(self) -> None:
        result = assess_nutrients({"organic_carbon": 10})
        assert result["organic_carbon_rating"] == "poor"
        assert result["nitrogen"] == "low"

    def test_excellent_oc(self) -> None:
        result = assess_nutrients({"organic_carbon": 65})
        assert result["organic_carbon_rating"] == "excellent"
        assert result["nitrogen"] == "high"

    def test_fair_oc(self) -> None:
        result = assess_nutrients({"organic_carbon": 30})
        assert result["organic_carbon_rating"] == "fair"


class TestSoilHealthIndex:
    """Soil health index computation tests."""

    def test_good_soil(self) -> None:
        data = {"ph": 6.5, "organic_carbon": 50, "clay_percent": 250}
        index = compute_soil_health_index(data)
        assert 60 <= index <= 100

    def test_poor_soil(self) -> None:
        data = {"ph": 4.0, "organic_carbon": 10, "clay_percent": 50}
        index = compute_soil_health_index(data)
        assert 0 <= index <= 55

    def test_unknown_data_gives_moderate(self) -> None:
        index = compute_soil_health_index({})
        assert 20 <= index <= 70


class TestRecommendations:
    """Soil recommendation tests."""

    def test_acidic_soil_gets_lime_rec(self) -> None:
        recs = generate_soil_recommendations({"ph": 4.5, "organic_carbon": 30, "clay_percent": 200})
        assert any("lime" in r.lower() for r in recs)

    def test_sandy_soil_gets_organic_rec(self) -> None:
        recs = generate_soil_recommendations({"ph": 6.5, "organic_carbon": 30, "clay_percent": 50})
        assert any("organic" in r.lower() or "water retention" in r.lower() for r in recs)

    def test_good_soil_gets_maintain(self) -> None:
        recs = generate_soil_recommendations({"ph": 6.5, "organic_carbon": 50, "clay_percent": 250})
        assert any("good" in r.lower() or "maintain" in r.lower() for r in recs)


@pytest.mark.asyncio
async def test_analyze_soil_returns_expected_keys() -> None:
    """End-to-end test for soil analysis."""
    result = await analyze_soil(lat=17.385, lon=78.487)
    assert "ph" in result
    assert "soil_health_index" in result
    assert "recommendations" in result
    assert isinstance(result["recommendations"], list)
    assert 0 <= result["soil_health_index"] <= 100
