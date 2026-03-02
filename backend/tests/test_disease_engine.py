"""Tests for Disease Engine service."""

import pytest

from app.engines.disease.service import (
    _build_prevention_plan,
    _generate_recommendations,
    _risk_level,
    _score_disease,
    assess_disease_risk,
)


class TestRiskLevel:
    """Risk level classification tests."""

    def test_critical(self) -> None:
        assert _risk_level(80) == "Critical"

    def test_high(self) -> None:
        assert _risk_level(60) == "High"

    def test_moderate(self) -> None:
        assert _risk_level(40) == "Moderate"

    def test_low(self) -> None:
        assert _risk_level(20) == "Low"


class TestScoreDisease:
    """Individual disease scoring tests."""

    def test_optimal_conditions_high_score(self) -> None:
        disease = {
            "name": "Blast",
            "pathogen_type": "Fungal",
            "temp_range": (20, 30),
            "humidity_min": 80,
            "rainfall_boost": True,
            "vulnerable_stages": ["tillering"],
            "symptoms": "test",
            "favorable": "test",
        }
        score = _score_disease(
            disease,
            temp=25,
            humidity=90,
            rainfall=60,
            growth_stage="tillering",
            ndvi=0.3,
            soil_ph=6.5,
        )
        assert score > 50

    def test_unfavorable_conditions_low_score(self) -> None:
        disease = {
            "name": "Blast",
            "pathogen_type": "Fungal",
            "temp_range": (20, 30),
            "humidity_min": 80,
            "rainfall_boost": True,
            "vulnerable_stages": ["tillering"],
            "symptoms": "test",
            "favorable": "test",
        }
        score = _score_disease(
            disease, temp=5, humidity=30, rainfall=0, growth_stage="maturity", ndvi=0.7, soil_ph=6.5
        )
        assert score < 30

    def test_none_values_handled(self) -> None:
        disease = {
            "name": "Test",
            "pathogen_type": "Fungal",
            "temp_range": (20, 30),
            "humidity_min": 80,
            "rainfall_boost": False,
            "vulnerable_stages": [],
            "symptoms": "test",
            "favorable": "test",
        }
        score = _score_disease(disease, None, None, None, None, None, None)
        assert score == 0.0


class TestPreventionPlan:
    """Prevention plan generation tests."""

    def test_critical_disease_gets_immediate_action(self) -> None:
        diseases = [
            {
                "disease_name": "Blast",
                "pathogen_type": "Fungal",
                "risk_score": 80,
                "risk_level": "Critical",
            }
        ]
        plan = _build_prevention_plan(diseases)
        assert any(p["priority"] == "Immediate" for p in plan)

    def test_low_risk_gets_monitoring(self) -> None:
        diseases = [
            {
                "disease_name": "Test",
                "pathogen_type": "Fungal",
                "risk_score": 10,
                "risk_level": "Low",
            }
        ]
        plan = _build_prevention_plan(diseases)
        assert any(
            "monitor" in p["action"].lower() or "routine" in p["action"].lower() for p in plan
        )


class TestRecommendations:
    """Disease recommendation tests."""

    def test_high_risk_increases_scouting(self) -> None:
        recs = _generate_recommendations("rice", 60.0, 6.5)
        assert any("scouting" in r.lower() for r in recs)

    def test_low_ph_warns_pathogens(self) -> None:
        recs = _generate_recommendations("rice", 30.0, 5.0)
        assert any("ph" in r.lower() or "lim" in r.lower() for r in recs)


@pytest.mark.asyncio
async def test_assess_disease_risk_end_to_end() -> None:
    """End-to-end disease assessment test."""
    result = await assess_disease_risk(
        crop_type="rice",
        avg_temperature=27.0,
        avg_humidity=85.0,
        recent_rainfall_mm=40.0,
        growth_stage="tillering",
    )
    assert "overall_risk_score" in result
    assert "risk_level" in result
    assert "disease_risks" in result
    assert "prevention_plan" in result
    assert len(result["disease_risks"]) > 0


@pytest.mark.asyncio
async def test_assess_disease_risk_all_crops() -> None:
    """Test disease assessment works for all supported crops."""
    for crop in ("rice", "wheat", "maize", "soybean"):
        result = await assess_disease_risk(crop_type=crop)
        assert result["overall_risk_score"] >= 0
        assert len(result["disease_risks"]) > 0
