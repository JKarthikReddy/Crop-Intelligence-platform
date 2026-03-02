"""Tests for Fertilizer Optimization Engine (deficiency-driven)."""

import pytest

from app.engines.fertilizer.service import (
    _build_schedule,
    _calculate_quantities,
    _determine_severity,
    _generate_notes,
    _parse_deficiency,
    _resolve_crop_needs,
    _select_fertilizers,
    recommend_fertilizer,
)

# ── Crop Nutrient Lookup ─────────────────────────────────────────


class TestCropNutrientLookup:
    """Tests for _resolve_crop_needs."""

    def test_known_crop(self) -> None:
        needs = _resolve_crop_needs("Rice")
        assert needs == {"N": "High", "P": "Medium", "K": "Medium"}

    def test_unknown_crop_falls_back(self) -> None:
        needs = _resolve_crop_needs("Quinoa")
        assert needs == {"N": "Medium", "P": "Medium", "K": "Medium"}

    def test_red_chilli(self) -> None:
        needs = _resolve_crop_needs("Red Chilli")
        assert needs["K"] == "High"

    def test_legume_low_nitrogen(self) -> None:
        needs = _resolve_crop_needs("Soybean")
        assert needs["N"] == "Low"


# ── Deficiency Parsing ───────────────────────────────────────────


class TestParseDeficiency:
    """Tests for _parse_deficiency."""

    def test_nitrogen(self) -> None:
        assert _parse_deficiency("Nitrogen") == "N"

    def test_phosphorus(self) -> None:
        assert _parse_deficiency("Phosphorus") == "P"

    def test_potassium(self) -> None:
        assert _parse_deficiency("Potassium") == "K"

    def test_ph_returns_none(self) -> None:
        assert _parse_deficiency("pH (too acidic)") is None

    def test_unknown_returns_none(self) -> None:
        assert _parse_deficiency("Zinc") is None


# ── Severity Determination ───────────────────────────────────────


class TestDetermineSeverity:
    """Tests for _determine_severity."""

    def test_high_need_crop_with_deficiency(self) -> None:
        severity = _determine_severity(["Nitrogen"], {"N": "High", "P": "Medium", "K": "Medium"})
        assert severity == {"N": "High"}

    def test_multiple_deficiencies(self) -> None:
        severity = _determine_severity(
            ["Nitrogen", "Potassium"], {"N": "High", "P": "Medium", "K": "High"}
        )
        assert severity == {"N": "High", "K": "High"}

    def test_ph_deficiency_ignored(self) -> None:
        severity = _determine_severity(
            ["pH (too acidic)"], {"N": "High", "P": "Medium", "K": "Medium"}
        )
        assert severity == {}

    def test_empty_deficiencies(self) -> None:
        severity = _determine_severity([], {"N": "High", "P": "Medium", "K": "Medium"})
        assert severity == {}


# ── Fertilizer Selection ─────────────────────────────────────────


class TestSelectFertilizers:
    """Tests for _select_fertilizers."""

    def test_nitrogen_only(self) -> None:
        ferts = _select_fertilizers({"N": "High"})
        assert "Urea" in ferts

    def test_phosphorus_only(self) -> None:
        ferts = _select_fertilizers({"P": "Medium"})
        assert "DAP" in ferts
        assert "SSP" in ferts

    def test_multiple_adds_blend(self) -> None:
        ferts = _select_fertilizers({"N": "High", "K": "High"})
        assert "NPK 10-26-26" in ferts

    def test_empty_severity(self) -> None:
        ferts = _select_fertilizers({})
        assert ferts == []


# ── Quantity Calculation ─────────────────────────────────────────


class TestCalculateQuantities:
    """Tests for _calculate_quantities."""

    def test_high_severity_60kg(self) -> None:
        per_acre, total = _calculate_quantities({"N": "High"}, ["Urea"], 1.0)
        assert per_acre["Urea"] == "60.0 kg"
        assert total["Urea"] == "60.0 kg"

    def test_medium_severity_50kg(self) -> None:
        per_acre, _ = _calculate_quantities({"P": "Medium"}, ["DAP"], 1.0)
        assert per_acre["DAP"] == "50.0 kg"

    def test_low_severity_30kg(self) -> None:
        per_acre, _ = _calculate_quantities({"K": "Low"}, ["MOP"], 1.0)
        assert per_acre["MOP"] == "30.0 kg"

    def test_area_scaling(self) -> None:
        _, total = _calculate_quantities({"N": "High"}, ["Urea"], 3.0)
        assert total["Urea"] == "180.0 kg"

    def test_blend_uses_average(self) -> None:
        per_acre, _ = _calculate_quantities(
            {"N": "High", "K": "Low"}, ["Urea", "MOP", "NPK 10-26-26"], 1.0
        )
        # Blend should use average of High(60) + Low(30) = 45
        assert per_acre["NPK 10-26-26"] == "45.0 kg"


# ── Schedule Building ────────────────────────────────────────────


class TestBuildSchedule:
    """Tests for _build_schedule."""

    def test_rice_schedule(self) -> None:
        sched = _build_schedule("Rice", ["Urea", "DAP", "MOP"])
        assert len(sched) >= 2
        stages = [s["stage"] for s in sched]
        assert any("basal" in s.lower() for s in stages)

    def test_unknown_crop_uses_default(self) -> None:
        sched = _build_schedule("Quinoa", ["Urea", "DAP"])
        assert len(sched) >= 2

    def test_filters_unrecommended_products(self) -> None:
        sched = _build_schedule("Rice", ["Urea"])
        # Steps that only had DAP/MOP should show empty products
        for step in sched:
            for p in step["products"]:
                assert p == "Urea"


# ── Notes Generation ─────────────────────────────────────────────


class TestGenerateNotes:
    """Tests for _generate_notes."""

    def test_acidic_ph_gets_lime_tip(self) -> None:
        notes = _generate_notes(["Nitrogen"], "Medium", "Strongly Acidic", "Rice", {"N": "High"})
        assert any("lime" in n.lower() for n in notes)

    def test_alkaline_ph_gets_ammonium_tip(self) -> None:
        notes = _generate_notes([], "Medium", "Strongly Alkaline", "Rice", {})
        assert any("ammonium" in n.lower() for n in notes)

    def test_poor_soil_gets_organic_tip(self) -> None:
        notes = _generate_notes([], "Poor", "Neutral", "Rice", {})
        assert any("organic" in n.lower() for n in notes)

    def test_legume_gets_rhizobium(self) -> None:
        notes = _generate_notes([], "Medium", "Neutral", "Soybean", {})
        assert any("rhizobium" in n.lower() for n in notes)

    def test_no_deficiencies_gets_maintenance_note(self) -> None:
        notes = _generate_notes([], "Good", "Neutral", "Rice", {})
        assert any("maintenance" in n.lower() for n in notes)

    def test_high_severity_gets_split_note(self) -> None:
        notes = _generate_notes(["Nitrogen"], "Medium", "Neutral", "Rice", {"N": "High"})
        assert any("strong" in n.lower() and "nitrogen" in n.lower() for n in notes)


# ── End-to-End ───────────────────────────────────────────────────


class TestRecommendFertilizer:
    """Integration tests for the main recommend_fertilizer function."""

    def test_basic_call(self) -> None:
        result = recommend_fertilizer(
            deficiencies=["Nitrogen", "Potassium"],
            soil_health="Medium",
            ph_status="Neutral",
            selected_crop="Rice",
            land_area=2.0,
            unit="acre",
        )
        assert "fertilizers" in result
        assert "quantity_per_acre" in result
        assert "total_required" in result
        assert "schedule" in result
        assert "notes" in result
        assert "application_schedule" in result  # backward compat
        assert len(result["fertilizers"]) > 0

    def test_no_deficiencies_returns_maintenance(self) -> None:
        result = recommend_fertilizer(
            deficiencies=[],
            selected_crop="Wheat",
        )
        assert "NPK 10-26-26" in result["fertilizers"]

    def test_hectare_conversion(self) -> None:
        result = recommend_fertilizer(
            deficiencies=["Nitrogen"],
            selected_crop="Rice",
            land_area=1.0,
            unit="hectare",
        )
        # 1 ha ~ 2.47 acres -> total should be ~2.47x per-acre
        per_acre_str = result["quantity_per_acre"].get("Urea", "0 kg")
        total_str = result["total_required"].get("Urea", "0 kg")
        per_acre_val = float(per_acre_str.replace(" kg", ""))
        total_val = float(total_str.replace(" kg", ""))
        assert total_val == pytest.approx(per_acre_val * 2.47105, rel=0.01)

    def test_all_deficiencies(self) -> None:
        result = recommend_fertilizer(
            deficiencies=["Nitrogen", "Phosphorus", "Potassium"],
            soil_health="Poor",
            ph_status="Strongly Acidic",
            selected_crop="Potato",
            land_area=5.0,
        )
        assert "Urea" in result["fertilizers"]
        assert "DAP" in result["fertilizers"]
        assert "MOP" in result["fertilizers"]
        assert "NPK 10-26-26" in result["fertilizers"]
        assert any("lime" in n.lower() for n in result["notes"])

    def test_unknown_crop_works(self) -> None:
        result = recommend_fertilizer(
            deficiencies=["Nitrogen"],
            selected_crop="Dragonfruit",
        )
        assert len(result["fertilizers"]) > 0
        assert len(result["schedule"]) > 0

    def test_default_parameters(self) -> None:
        result = recommend_fertilizer()
        assert isinstance(result, dict)
        assert "fertilizers" in result

    def test_schedule_matches_fertilizers(self) -> None:
        result = recommend_fertilizer(
            deficiencies=["Phosphorus"],
            selected_crop="Rice",
        )
        fert_set = set(result["fertilizers"])
        for step in result["schedule"]:
            for product in step["products"]:
                assert product in fert_set
