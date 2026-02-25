"""Unit tests for the ET0 evapotranspiration and water stress service."""

from app.services.et0_service import (
    build_water_model,
    calculate_et0,
    water_stress_indicator,
)

# -- ET0 Calculation Tests ---------------------------------------------------


class TestCalculateEt0:
    """Tests for the simplified FAO ET0 model."""

    def test_positive_output(self) -> None:
        et0 = calculate_et0(30, 18, 3)
        assert et0 > 0

    def test_returns_float(self) -> None:
        et0 = calculate_et0(25, 15, 2)
        assert isinstance(et0, float)

    def test_rounded_to_two_decimals(self) -> None:
        et0 = calculate_et0(29.2, 18.5, 3.1)
        assert et0 == round(et0, 2)

    def test_hot_sunny_windy_high_et0(self) -> None:
        """Hot, sunny, and windy conditions should yield high ET0."""
        et0 = calculate_et0(temperature=40, solar_radiation=25, wind_speed=5)
        assert et0 > 6

    def test_cool_cloudy_calm_low_et0(self) -> None:
        """Cool, cloudy, and calm conditions should yield low ET0."""
        et0 = calculate_et0(temperature=10, solar_radiation=5, wind_speed=0.5)
        assert et0 < 4

    def test_zero_radiation_still_positive(self) -> None:
        """ET0 should still be positive from temperature/wind component."""
        et0 = calculate_et0(temperature=25, solar_radiation=0, wind_speed=2)
        assert et0 > 0

    def test_known_values(self) -> None:
        """Verify against hand-calculated expected value."""
        # 0.408 * 18 + 0.0023 * (30 + 17.8) * (3 + 1)
        # = 7.344 + 0.0023 * 47.8 * 4
        # = 7.344 + 0.43976
        # = 7.78
        et0 = calculate_et0(30, 18, 3)
        assert et0 == 7.78

    def test_higher_temp_increases_et0(self) -> None:
        low = calculate_et0(20, 15, 2)
        high = calculate_et0(35, 15, 2)
        assert high > low

    def test_higher_radiation_increases_et0(self) -> None:
        low = calculate_et0(25, 10, 2)
        high = calculate_et0(25, 20, 2)
        assert high > low

    def test_higher_wind_increases_et0(self) -> None:
        low = calculate_et0(25, 15, 1)
        high = calculate_et0(25, 15, 5)
        assert high > low


# -- Water Stress Indicator Tests --------------------------------------------


class TestWaterStressIndicator:
    """Tests for the water stress classification."""

    def test_high_stress(self) -> None:
        assert water_stress_indicator(7.0) == "high"

    def test_high_boundary_above(self) -> None:
        assert water_stress_indicator(6.01) == "high"

    def test_high_boundary_exact(self) -> None:
        assert water_stress_indicator(6.0) == "moderate"

    def test_moderate_stress(self) -> None:
        assert water_stress_indicator(5.0) == "moderate"

    def test_moderate_boundary_above(self) -> None:
        assert water_stress_indicator(4.01) == "moderate"

    def test_moderate_boundary_exact(self) -> None:
        assert water_stress_indicator(4.0) == "low"

    def test_low_stress(self) -> None:
        assert water_stress_indicator(3.0) == "low"

    def test_zero(self) -> None:
        assert water_stress_indicator(0.0) == "low"


# -- Build Water Model Tests ------------------------------------------------


class TestBuildWaterModel:
    """Tests for the convenience builder used by the intelligence engine."""

    def test_valid_climate_returns_model(self) -> None:
        climate = {
            "temperature_avg_30d": 29.2,
            "solar_radiation_avg_30d": 18.5,
            "wind_speed_avg_30d": 3.1,
        }
        result = build_water_model(climate)
        assert result is not None
        assert "et0_estimate" in result
        assert "water_stress_risk" in result
        assert result["et0_estimate"] > 0

    def test_none_climate_returns_none(self) -> None:
        assert build_water_model(None) is None

    def test_missing_temperature_returns_none(self) -> None:
        climate = {
            "solar_radiation_avg_30d": 18.5,
            "wind_speed_avg_30d": 3.1,
        }
        assert build_water_model(climate) is None

    def test_missing_radiation_returns_none(self) -> None:
        climate = {
            "temperature_avg_30d": 29.2,
            "wind_speed_avg_30d": 3.1,
        }
        assert build_water_model(climate) is None

    def test_missing_wind_returns_none(self) -> None:
        climate = {
            "temperature_avg_30d": 29.2,
            "solar_radiation_avg_30d": 18.5,
        }
        assert build_water_model(climate) is None

    def test_stress_matches_et0(self) -> None:
        """Verify the stress flag is consistent with the ET0 value."""
        climate = {
            "temperature_avg_30d": 40,
            "solar_radiation_avg_30d": 25,
            "wind_speed_avg_30d": 5,
        }
        result = build_water_model(climate)
        assert result is not None
        assert result["water_stress_risk"] == water_stress_indicator(result["et0_estimate"])
