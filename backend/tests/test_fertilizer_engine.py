"""Tests for Fertilizer Engine service."""

import pytest

from app.engines.fertilizer.service import (
    build_schedule,
    calculate_npk,
    generate_fertilizer_recommendations,
    recommend_fertilizer,
    select_products,
)


class TestCalculateNPK:
    """NPK calculation tests."""

    def test_rice_default(self) -> None:
        npk = calculate_npk("rice", 5.0, None, None, 1.0)
        assert npk["nitrogen_kg_per_ha"] > 0
        assert npk["phosphorus_kg_per_ha"] > 0
        assert npk["potassium_kg_per_ha"] > 0

    def test_area_scaling(self) -> None:
        npk = calculate_npk("rice", 5.0, None, None, 2.0)
        assert npk["total_nitrogen_kg"] == pytest.approx(npk["nitrogen_kg_per_ha"] * 2.0, 0.1)

    def test_acidic_ph_increases_n(self) -> None:
        npk_neutral = calculate_npk("rice", 5.0, 6.5, None, 1.0)
        npk_acidic = calculate_npk("rice", 5.0, 5.0, None, 1.0)
        assert npk_acidic["nitrogen_kg_per_ha"] >= npk_neutral["nitrogen_kg_per_ha"]

    def test_high_oc_reduces_n(self) -> None:
        npk_low_oc = calculate_npk("rice", 5.0, 6.5, 15, 1.0)
        npk_high_oc = calculate_npk("rice", 5.0, 6.5, 55, 1.0)
        assert npk_high_oc["nitrogen_kg_per_ha"] < npk_low_oc["nitrogen_kg_per_ha"]


class TestSelectProducts:
    """Product selection tests."""

    def test_returns_dap_urea_mop(self) -> None:
        npk = {"nitrogen_kg_per_ha": 110, "phosphorus_kg_per_ha": 50, "potassium_kg_per_ha": 120}
        products = select_products(npk, 1.0)
        names = [p["name"] for p in products]
        assert "DAP" in names
        assert "Urea" in names
        assert "MOP" in names

    def test_cost_is_positive(self) -> None:
        npk = {"nitrogen_kg_per_ha": 100, "phosphorus_kg_per_ha": 50, "potassium_kg_per_ha": 100}
        products = select_products(npk, 1.0)
        total_cost = sum(p["estimated_cost_usd"] for p in products)
        assert total_cost > 0


class TestBuildSchedule:
    """Application schedule tests."""

    def test_rice_schedule(self) -> None:
        schedule = build_schedule("rice")
        assert len(schedule) >= 2
        stages = [s["stage"] for s in schedule]
        assert any("basal" in s.lower() for s in stages)

    def test_wheat_schedule(self) -> None:
        schedule = build_schedule("wheat")
        assert len(schedule) >= 2

    def test_unknown_crop_defaults_to_rice(self) -> None:
        schedule = build_schedule("quinoa")
        assert len(schedule) >= 2


class TestRecommendations:
    """Fertilizer recommendation tests."""

    def test_acidic_soil_gets_lime_tip(self) -> None:
        recs = generate_fertilizer_recommendations("rice", 5.0, 30)
        assert any("lime" in r.lower() for r in recs)

    def test_soybean_gets_rhizobium(self) -> None:
        recs = generate_fertilizer_recommendations("soybean", 6.5, 30)
        assert any("rhizobium" in r.lower() for r in recs)


@pytest.mark.asyncio
async def test_recommend_fertilizer_end_to_end() -> None:
    """End-to-end fertilizer recommendation test."""
    result = await recommend_fertilizer(
        crop_type="rice",
        target_yield=5.0,
        soil_ph=6.5,
        organic_carbon=30,
        area_hectares=2.0,
    )
    assert "npk_recommendation" in result
    assert "products" in result
    assert "application_schedule" in result
    assert "cost_summary" in result
    assert result["cost_summary"]["total_fertilizer_cost_usd"] > 0
