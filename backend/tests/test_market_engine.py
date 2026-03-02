"""Tests for Market Engine service."""

import pytest

from app.engines.market.service import (
    analyze_market,
    determine_sell_recommendation,
    estimate_profitability,
    generate_market_recommendations,
    get_price_snapshot,
    get_seasonal_pattern,
)


class TestPriceSnapshot:
    """Market price retrieval tests."""

    def test_rice_price_positive(self) -> None:
        snap = get_price_snapshot("rice", "south_asia")
        assert snap["current_price_usd_per_ton"] > 0
        assert snap["price_30d_ago"] > 0
        assert snap["price_trend"] in ("Rising", "Stable", "Declining")

    def test_region_multiplier_applied(self) -> None:
        global_snap = get_price_snapshot("rice", "global")
        asia_snap = get_price_snapshot("rice", "south_asia")
        # South Asia prices should be less than global
        assert asia_snap["current_price_usd_per_ton"] <= global_snap["current_price_usd_per_ton"]


class TestSeasonalPattern:
    """Seasonal pattern analysis tests."""

    def test_rice_seasonal_months(self) -> None:
        pattern = get_seasonal_pattern("rice")
        assert len(pattern["best_sell_months"]) > 0
        assert len(pattern["worst_sell_months"]) > 0
        assert pattern["seasonality_strength"] in ("Strong", "Moderate", "Weak")

    def test_all_crops_have_patterns(self) -> None:
        for crop in ("rice", "wheat", "maize", "soybean"):
            pattern = get_seasonal_pattern(crop)
            assert len(pattern["best_sell_months"]) > 0


class TestProfitability:
    """Profitability estimation tests."""

    def test_positive_profit(self) -> None:
        prof = estimate_profitability("rice", "south_asia", 10.0, 2.0, 500.0)
        assert prof["gross_revenue_usd"] > 0
        assert prof["break_even_price_usd"] > 0

    def test_default_values(self) -> None:
        prof = estimate_profitability("rice", "south_asia", None, 1.0, None)
        assert prof["production_cost_usd"] > 0
        assert prof["gross_revenue_usd"] > 0


class TestSellRecommendation:
    """Sell recommendation tests."""

    def test_returns_valid_recommendation(self) -> None:
        price = get_price_snapshot("rice", "south_asia")
        seasonal = get_seasonal_pattern("rice")
        prof = estimate_profitability("rice", "south_asia", None, 1.0, None)
        rec, conf = determine_sell_recommendation(price, seasonal, prof)
        assert isinstance(rec, str)
        assert 0 <= conf <= 1


class TestMarketRecommendations:
    """Market recommendation tests."""

    def test_returns_recommendations(self) -> None:
        price = get_price_snapshot("rice", "south_asia")
        prof = estimate_profitability("rice", "south_asia", None, 1.0, None)
        recs = generate_market_recommendations("rice", price, prof)
        assert len(recs) > 0


@pytest.mark.asyncio
async def test_analyze_market_end_to_end() -> None:
    """End-to-end market analysis test."""
    result = await analyze_market(
        crop_type="rice",
        region="south_asia",
        estimated_yield_tons=5.0,
        area_hectares=2.0,
    )
    assert "price_snapshot" in result
    assert "seasonal_pattern" in result
    assert "profitability" in result
    assert "sell_recommendation" in result
    assert "confidence" in result
    assert "recommendations" in result
