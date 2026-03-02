"""Tests for Soil Engine — diagnostic soil health analysis."""

from typing import ClassVar

from app.engines.soil.service import (
    SOIL_TYPE_DB,
    _classify_nutrient,
    _deviation_pct,
    _score_ph,
    analyze_soil,
    assess_nutrient,
    assess_nutrients,
    classify_health,
    classify_ph,
    compute_soil_health_score,
    detect_deficiencies,
    generate_recommendations,
)

# ── pH Classification ────────────────────────────────────────────


class TestClassifyPh:
    """pH classification tests."""

    def test_strongly_acidic(self) -> None:
        assert classify_ph(3.0) == "Strongly Acidic"

    def test_acidic(self) -> None:
        assert classify_ph(5.0) == "Acidic"

    def test_slightly_acidic(self) -> None:
        assert classify_ph(5.8) == "Slightly Acidic"

    def test_neutral_low(self) -> None:
        assert classify_ph(6.0) == "Neutral"

    def test_neutral_mid(self) -> None:
        assert classify_ph(7.0) == "Neutral"

    def test_neutral_high(self) -> None:
        assert classify_ph(7.5) == "Neutral"

    def test_slightly_alkaline(self) -> None:
        assert classify_ph(7.8) == "Slightly Alkaline"

    def test_alkaline(self) -> None:
        assert classify_ph(8.3) == "Alkaline"

    def test_strongly_alkaline(self) -> None:
        assert classify_ph(9.5) == "Strongly Alkaline"


# ── Nutrient Classification ──────────────────────────────────────


class TestNutrientClassification:
    """Individual nutrient status tests."""

    _N_THRESHOLDS: ClassVar[dict] = {"deficient": 20, "low": 50, "adequate": 120, "high": 200}

    def test_deficient(self) -> None:
        assert _classify_nutrient(10, self._N_THRESHOLDS) == "Deficient"

    def test_low(self) -> None:
        assert _classify_nutrient(35, self._N_THRESHOLDS) == "Low"

    def test_adequate(self) -> None:
        assert _classify_nutrient(80, self._N_THRESHOLDS) == "Adequate"

    def test_high(self) -> None:
        assert _classify_nutrient(150, self._N_THRESHOLDS) == "High"

    def test_excess(self) -> None:
        assert _classify_nutrient(250, self._N_THRESHOLDS) == "Excess"


class TestDeviationPct:
    """Deviation percentage calc tests."""

    def test_at_ideal(self) -> None:
        assert _deviation_pct(85, 85) == 0.0

    def test_below(self) -> None:
        assert _deviation_pct(42.5, 85) == -50.0

    def test_above(self) -> None:
        assert _deviation_pct(170, 85) == 100.0


class TestAssessNutrient:
    """Single nutrient assessment tests."""

    def test_returns_all_fields(self) -> None:
        result = assess_nutrient(
            45, {"deficient": 20, "low": 50, "adequate": 120, "high": 200}, "50 - 120 kg/ha", 85.0
        )
        assert "value" in result
        assert "status" in result
        assert "ideal_range" in result
        assert "deviation_pct" in result

    def test_low_nitrogen(self) -> None:
        result = assess_nutrient(
            30, {"deficient": 20, "low": 50, "adequate": 120, "high": 200}, "50 - 120 kg/ha", 85.0
        )
        assert result["status"] == "Low"
        assert result["deviation_pct"] < 0


class TestAssessNutrients:
    """Full NPK assessment tests."""

    def test_returns_npk(self) -> None:
        result = assess_nutrients(80, 40, 60)
        assert "nitrogen" in result
        assert "phosphorus" in result
        assert "potassium" in result

    def test_good_values(self) -> None:
        result = assess_nutrients(80, 40, 60)
        assert result["nitrogen"]["status"] == "Adequate"
        assert result["phosphorus"]["status"] == "Adequate"
        assert result["potassium"]["status"] == "Adequate"

    def test_all_deficient(self) -> None:
        result = assess_nutrients(5, 5, 5)
        assert result["nitrogen"]["status"] == "Deficient"
        assert result["phosphorus"]["status"] == "Deficient"
        assert result["potassium"]["status"] == "Deficient"


# ── Deficiency Detection ────────────────────────────────────────


class TestDetectDeficiencies:
    """Deficiency detection tests."""

    def test_no_deficiencies(self) -> None:
        defs = detect_deficiencies(80, 40, 60, 6.5)
        assert defs == []

    def test_nitrogen_deficient(self) -> None:
        defs = detect_deficiencies(10, 40, 60, 6.5)
        assert "Nitrogen" in defs

    def test_phosphorus_deficient(self) -> None:
        defs = detect_deficiencies(80, 8, 60, 6.5)
        assert "Phosphorus" in defs

    def test_potassium_deficient(self) -> None:
        defs = detect_deficiencies(80, 40, 10, 6.5)
        assert "Potassium" in defs

    def test_ph_too_acidic(self) -> None:
        defs = detect_deficiencies(80, 40, 60, 4.0)
        assert any("acidic" in d.lower() for d in defs)

    def test_ph_too_alkaline(self) -> None:
        defs = detect_deficiencies(80, 40, 60, 9.0)
        assert any("alkaline" in d.lower() for d in defs)

    def test_multiple_deficiencies(self) -> None:
        defs = detect_deficiencies(10, 5, 5, 4.0)
        assert len(defs) >= 3


# ── Scoring ──────────────────────────────────────────────────────


class TestScoring:
    """Soil health score computation tests."""

    def test_perfect_soil(self) -> None:
        score = compute_soil_health_score(80, 40, 60, 6.5, "Loamy")
        assert score["total"] >= 85

    def test_poor_soil(self) -> None:
        score = compute_soil_health_score(5, 3, 5, 3.5, "Sandy")
        assert score["total"] <= 30

    def test_medium_soil(self) -> None:
        score = compute_soil_health_score(30, 15, 25, 5.5, "Sandy")
        assert 30 <= score["total"] <= 75

    def test_breakdown_keys(self) -> None:
        score = compute_soil_health_score(80, 40, 60, 6.5, "Loamy")
        assert "nitrogen_score" in score
        assert "phosphorus_score" in score
        assert "potassium_score" in score
        assert "ph_score" in score
        assert "soil_type_score" in score
        assert "total" in score

    def test_score_bounded_0_100(self) -> None:
        # Even with extreme inputs, score should be bounded
        score = compute_soil_health_score(500, 200, 500, 7.0, "Loamy")
        assert 0 <= score["total"] <= 100

    def test_ph_score_optimal(self) -> None:
        assert _score_ph(6.5) == 25.0

    def test_ph_score_extreme(self) -> None:
        assert _score_ph(2.0) == 2.0


class TestClassifyHealth:
    """Health level classification tests."""

    def test_excellent(self) -> None:
        assert classify_health(90) == "Excellent"

    def test_good(self) -> None:
        assert classify_health(75) == "Good"

    def test_medium(self) -> None:
        assert classify_health(55) == "Medium"

    def test_low(self) -> None:
        assert classify_health(35) == "Low"

    def test_poor(self) -> None:
        assert classify_health(20) == "Poor"


# ── Recommendations ──────────────────────────────────────────────


class TestRecommendations:
    """Recommendation generation tests."""

    def test_good_soil_gets_general_rec(self) -> None:
        recs = generate_recommendations(80, 40, 60, 6.5, "Loamy", [])
        assert len(recs) >= 1
        assert any(r["priority"] == "Low" for r in recs)

    def test_low_nitrogen_gets_critical_rec(self) -> None:
        recs = generate_recommendations(10, 40, 60, 6.5, "Loamy", ["Nitrogen"])
        assert any(r["priority"] == "Critical" and "nitrogen" in r["action"].lower() for r in recs)

    def test_acidic_ph_gets_lime_rec(self) -> None:
        recs = generate_recommendations(80, 40, 60, 4.5, "Loamy", ["pH (too acidic)"])
        assert any("lime" in r["action"].lower() for r in recs)

    def test_alkaline_ph_gets_gypsum_rec(self) -> None:
        recs = generate_recommendations(80, 40, 60, 9.0, "Loamy", ["pH (too alkaline)"])
        assert any("gypsum" in r["action"].lower() or "sulfur" in r["action"].lower() for r in recs)

    def test_sandy_soil_gets_organic_rec(self) -> None:
        recs = generate_recommendations(80, 40, 60, 6.5, "Sandy", [])
        assert any("sandy" in r["action"].lower() or "compost" in r["action"].lower() for r in recs)

    def test_recommendation_has_product(self) -> None:
        recs = generate_recommendations(10, 40, 60, 6.5, "Loamy", ["Nitrogen"])
        npk_recs = [r for r in recs if r["category"] == "NPK"]
        assert len(npk_recs) > 0
        assert npk_recs[0]["product"] is not None

    def test_recommendation_has_dosage(self) -> None:
        recs = generate_recommendations(10, 40, 60, 6.5, "Loamy", ["Nitrogen"])
        npk_recs = [r for r in recs if r["category"] == "NPK"]
        assert npk_recs[0]["dosage"] is not None


# ── Soil Type Knowledge Base ─────────────────────────────────────


class TestSoilTypeDB:
    """Soil type knowledge base tests."""

    def test_all_types_present(self) -> None:
        expected = [
            "Alluvial",
            "Black",
            "Red",
            "Laterite",
            "Sandy",
            "Clayey",
            "Loamy",
            "Peaty",
            "Saline",
            "Other",
        ]
        for soil_type in expected:
            assert soil_type in SOIL_TYPE_DB

    def test_each_has_required_keys(self) -> None:
        for name, info in SOIL_TYPE_DB.items():
            assert "water_retention" in info, f"{name} missing water_retention"
            assert "drainage" in info, f"{name} missing drainage"
            assert "fertility" in info, f"{name} missing fertility"
            assert "best_crops" in info, f"{name} missing best_crops"
            assert "management_notes" in info, f"{name} missing management_notes"
            assert isinstance(info["best_crops"], list)


# ── Integration: analyze_soil ────────────────────────────────────


class TestAnalyzeSoil:
    """Full diagnostic integration tests."""

    def test_returns_expected_keys(self) -> None:
        result = analyze_soil(45, 30, 40, 6.5, "Black")
        assert "soil_health" in result
        assert "score" in result
        assert "score_breakdown" in result
        assert "deficiencies" in result
        assert "ph_status" in result
        assert "ph_analysis" in result
        assert "nutrient_profile" in result
        assert "soil_insight" in result
        assert "recommendations" in result
        assert "soil_health_index" in result  # backward compat

    def test_score_equals_health_index(self) -> None:
        result = analyze_soil(45, 30, 40, 6.5, "Loamy")
        assert result["score"] == result["soil_health_index"]

    def test_score_bounded(self) -> None:
        result = analyze_soil(45, 30, 40, 6.5, "Black")
        assert 0 <= result["score"] <= 100

    def test_good_soil_scores_high(self) -> None:
        result = analyze_soil(80, 45, 75, 6.8, "Loamy")
        assert result["score"] >= 70
        assert result["soil_health"] in ("Good", "Excellent")
        assert result["deficiencies"] == []

    def test_poor_soil_scores_low(self) -> None:
        result = analyze_soil(5, 3, 5, 3.5, "Sandy")
        assert result["score"] < 35
        assert result["soil_health"] in ("Poor", "Low")
        assert len(result["deficiencies"]) >= 3

    def test_example_input_from_spec(self) -> None:
        """Test with the exact example from the user spec."""
        result = analyze_soil(45, 30, 40, 6.5, "Black")
        assert isinstance(result["soil_health"], str)
        assert isinstance(result["score"], float)
        assert isinstance(result["deficiencies"], list)
        assert isinstance(result["ph_status"], str)
        assert isinstance(result["recommendations"], list)
        assert result["ph_status"] == "Neutral"

    def test_soil_insight_populated(self) -> None:
        result = analyze_soil(45, 30, 40, 6.5, "Black")
        si = result["soil_insight"]
        assert si["soil_type"] == "Black"
        assert "Cotton" in si["best_crops"]

    def test_nutrient_profile_structure(self) -> None:
        result = analyze_soil(45, 30, 40, 6.5, "Black")
        np = result["nutrient_profile"]
        for key in ("nitrogen", "phosphorus", "potassium"):
            assert "value" in np[key]
            assert "status" in np[key]
            assert "ideal_range" in np[key]
            assert "deviation_pct" in np[key]
