"""Tests for Market Engine — Indian mandi price intelligence."""

from app.engines.market.service import (
    _compute_trend,
    _decide_recommendation,
    _deterministic_jitter,
    _predict_next_week,
    _simulate_price,
    analyze_market,
)

# ── Unit helpers ──────────────────────────────────────────────────


class TestDeterministicJitter:
    """Hash-based jitter tests."""

    def test_same_seed_same_result(self) -> None:
        a = _deterministic_jitter("2025-01-15:Guntur:14500", 100)
        b = _deterministic_jitter("2025-01-15:Guntur:14500", 100)
        assert a == b

    def test_within_amplitude(self) -> None:
        for seed in ("a", "b", "crop:loc:123"):
            j = _deterministic_jitter(seed, 50)
            assert -50 <= j <= 50


class TestSimulatePrice:
    """Daily price simulation tests."""

    def test_positive_price(self) -> None:
        from datetime import UTC, datetime

        price = _simulate_price(14500, 0.06, [2, 3, 4], datetime(2025, 3, 15, tzinfo=UTC), "Guntur")
        assert price > 0

    def test_deterministic(self) -> None:
        from datetime import UTC, datetime

        d = datetime(2025, 6, 1, tzinfo=UTC)
        p1 = _simulate_price(2200, 0.04, [3, 4, 5], d, "Warangal")
        p2 = _simulate_price(2200, 0.04, [3, 4, 5], d, "Warangal")
        assert p1 == p2


class TestTrend:
    """Trend analysis tests."""

    def test_increasing(self) -> None:
        assert _compute_trend(1050, 1000) == "Increasing"

    def test_decreasing(self) -> None:
        assert _compute_trend(950, 1000) == "Decreasing"

    def test_stable(self) -> None:
        assert _compute_trend(1010, 1000) == "Stable"

    def test_zero_avg(self) -> None:
        assert _compute_trend(100, 0) == "Stable"


class TestPrediction:
    """Next-week price prediction tests."""

    def test_upward_trend(self) -> None:
        history = [
            {"label": "Today", "price": 110},
            {"label": "Yesterday", "price": 105},
            {"label": "2 days ago", "price": 100},
        ]
        predicted = _predict_next_week(history)
        assert predicted > 110  # extrapolates upward

    def test_single_point(self) -> None:
        history = [{"label": "Today", "price": 500}]
        assert _predict_next_week(history) == 500


class TestDecision:
    """Sell/hold decision logic tests."""

    def test_rising_hold(self) -> None:
        rec = _decide_recommendation(1050, 1000, "Increasing", 1100)
        assert "hold" in rec.lower()

    def test_falling_sell(self) -> None:
        rec = _decide_recommendation(950, 1000, "Decreasing", 900)
        assert "sell immediately" in rec.lower()

    def test_stable_peaked(self) -> None:
        rec = _decide_recommendation(1000, 1000, "Stable", 990)
        assert "sell" in rec.lower()

    def test_stable_rising(self) -> None:
        rec = _decide_recommendation(1000, 1000, "Stable", 1020)
        assert "monitor" in rec.lower()


# ── End-to-end ────────────────────────────────────────────────────


class TestAnalyzeMarket:
    """Full pipeline tests."""

    def test_default_inputs(self) -> None:
        r = analyze_market()
        assert r["current_price"] > 0
        assert r["unit"] == "₹/quintal"
        assert r["trend"] in ("Increasing", "Stable", "Decreasing")
        assert len(r["nearby_mandis"]) > 0
        assert len(r["price_history"]) == 7
        assert len(r["notes"]) > 0
        assert "sell_recommendation" in r  # backward compat

    def test_known_crop_and_location(self) -> None:
        r = analyze_market(crop="Red Chilli", location="Guntur", quantity=100)
        assert r["current_price"] > 5000  # chilli is expensive
        assert any("Guntur" in m["mandi"] for m in r["nearby_mandis"])

    def test_unknown_crop_gets_default(self) -> None:
        r = analyze_market(crop="Dragonfruit", location="Hyderabad")
        assert r["current_price"] > 0  # uses default price DB

    def test_unknown_location_gets_default_mandis(self) -> None:
        r = analyze_market(crop="Rice", location="Timbuktu")
        assert len(r["nearby_mandis"]) > 0
        assert r["nearby_mandis"][0]["mandi"] == "Local Mandi"

    def test_title_case_normalization(self) -> None:
        r = analyze_market(crop="red chilli", location="guntur")
        assert r["current_price"] > 5000  # recognized correctly

    def test_quantity_in_notes(self) -> None:
        r = analyze_market(crop="Cotton", location="Kurnool", quantity=80)
        assert any("batch" in n.lower() for n in r["notes"])

    def test_all_known_crops_produce_results(self) -> None:
        from app.engines.market.service import _CROP_PRICES

        for crop_name in _CROP_PRICES:
            r = analyze_market(crop=crop_name, location="Hyderabad")
            assert r["current_price"] > 0, f"Failed for {crop_name}"
