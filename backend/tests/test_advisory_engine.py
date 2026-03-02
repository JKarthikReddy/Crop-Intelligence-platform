"""Tests for Advisory Aggregator service."""

import pytest

from app.engines.advisory.service import (
    _build_summary,
    _compute_farm_health,
    _generate_priority_actions,
    generate_advisory,
)


class TestFarmHealth:
    """Composite farm health score tests."""

    def test_all_good(self) -> None:
        score = _compute_farm_health(
            soil={"soil_health_index": 80},
            weather={"risk_assessment": {"overall_risk_score": 20}},
            crop={"crop_health_score": 85},
            disease={"overall_risk_score": 15},
            market={"profitability": {"profit_margin_pct": 30}},
        )
        assert score > 70

    def test_all_poor(self) -> None:
        score = _compute_farm_health(
            soil={"soil_health_index": 20},
            weather={"risk_assessment": {"overall_risk_score": 80}},
            crop={"crop_health_score": 25},
            disease={"overall_risk_score": 80},
            market={"profitability": {"profit_margin_pct": 5}},
        )
        assert score < 40

    def test_missing_engines(self) -> None:
        """Should still compute with partial data."""
        score = _compute_farm_health(
            soil={"soil_health_index": 70},
            weather=None,
            crop=None,
            disease=None,
            market=None,
        )
        assert 0 <= score <= 100

    def test_no_data_returns_50(self) -> None:
        score = _compute_farm_health(None, None, None, None, None)
        assert score == 50.0


class TestPriorityActions:
    """Priority action generation tests."""

    def test_disease_critical_goes_first(self) -> None:
        actions = _generate_priority_actions(
            soil=None,
            weather=None,
            crop=None,
            fertilizer=None,
            disease={"risk_level": "Critical", "disease_risks": [{"disease_name": "Blast"}]},
            market=None,
        )
        assert len(actions) > 0
        assert actions[0]["category"] == "Disease"
        assert actions[0]["urgency"] == "Immediate"

    def test_fertilizer_scheduled(self) -> None:
        actions = _generate_priority_actions(
            soil=None,
            weather=None,
            crop=None,
            fertilizer={"application_schedule": [{"stage": "Basal", "products": ["DAP", "MOP"]}]},
            disease={"risk_level": "Low", "disease_risks": []},
            market=None,
        )
        fert_actions = [a for a in actions if a["category"] == "Fertilizer"]
        assert len(fert_actions) > 0

    def test_no_data_empty_actions(self) -> None:
        actions = _generate_priority_actions(None, None, None, None, None, None)
        assert actions == []


class TestBuildSummary:
    """Summary generation tests."""

    def test_healthy_farm(self) -> None:
        summary = _build_summary(80.0, [], 6, 6)
        assert "good" in summary.lower()
        assert "6/6" in summary

    def test_unhealthy_farm(self) -> None:
        summary = _build_summary(35.0, [{"urgency": "Immediate"}], 4, 6)
        assert "urgent" in summary.lower() or "below" in summary.lower()
        assert "4/6" in summary


@pytest.mark.asyncio
async def test_generate_advisory_end_to_end() -> None:
    """End-to-end advisory aggregation test.

    This calls all 6 engines — some may fail if external APIs are
    unreachable, but the aggregator should gracefully degrade.
    """
    result = await generate_advisory(
        lat=17.385,
        lon=78.487,
        crop_type="rice",
        target_yield=5.0,
        area_hectares=2.0,
        region="south_asia",
    )
    assert "farm_health_score" in result
    assert "advisory_summary" in result
    assert "priority_actions" in result
    assert "engine_statuses" in result
    assert "engines_total" in result
    assert result["engines_total"] == 6
    # At least the local engines (Fertilizer, Disease, Market) should succeed
    assert result["engines_succeeded"] >= 3
