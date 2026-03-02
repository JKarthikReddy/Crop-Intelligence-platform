"""Tests for Crop Recommendation Engine."""

from app.engines.crop.service import (
    CROP_DB,
    _range_score,
    _suitability_note,
    apply_region_boost,
    classify_confidence,
    compute_feature_score,
    filter_by_region,
    filter_by_season,
    generate_reasoning,
    parse_location,
    recommend_crops,
)

# ── Location Parsing ────────────────────────────────────────────


class TestParseLocation:
    """Location string parsing."""

    def test_district_and_state(self) -> None:
        d, s = parse_location("Guntur, Andhra Pradesh")
        assert d == "Guntur"
        assert s == "Andhra Pradesh"

    def test_state_only(self) -> None:
        d, s = parse_location("Punjab")
        assert d is None
        assert s == "Punjab"

    def test_known_district_only(self) -> None:
        d, s = parse_location("Guntur")
        assert d == "Guntur"
        assert s == "Andhra Pradesh"

    def test_unknown_location_becomes_state(self) -> None:
        d, s = parse_location("Some Place")
        assert d is None
        assert s == "Some Place"

    def test_title_case_normalization(self) -> None:
        d, s = parse_location("guntur, andhra pradesh")
        assert d == "Guntur"
        assert s == "Andhra Pradesh"


# ── Range Scoring ───────────────────────────────────────────────


class TestRangeScore:
    """Range-based value scoring."""

    def test_within_range_scores_one(self) -> None:
        assert _range_score(50, 40, 60) == 1.0

    def test_at_boundary_scores_one(self) -> None:
        assert _range_score(40, 40, 60) == 1.0
        assert _range_score(60, 40, 60) == 1.0

    def test_outside_range_degrades(self) -> None:
        score = _range_score(70, 40, 60)
        assert 0.0 < score < 1.0

    def test_far_outside_approaches_zero(self) -> None:
        score = _range_score(200, 40, 60)
        assert score == 0.0


# ── Feature Scoring ─────────────────────────────────────────────


class TestFeatureScore:
    """Feature vector scoring."""

    def test_perfect_match_near_hundred(self) -> None:
        rice = CROP_DB["Rice"]
        score = compute_feature_score(
            n=90,
            p=45,
            k=45,
            ph=6.2,
            temp=28,
            humidity=80,
            rainfall=200,
            crop=rice,
        )
        assert score == 100.0

    def test_poor_match_below_fifty(self) -> None:
        rice = CROP_DB["Rice"]
        score = compute_feature_score(
            n=300,
            p=150,
            k=300,
            ph=3.0,
            temp=5,
            humidity=10,
            rainfall=5,
            crop=rice,
        )
        assert score < 50

    def test_returns_float(self) -> None:
        crop = CROP_DB["Wheat"]
        score = compute_feature_score(
            n=100,
            p=50,
            k=40,
            ph=6.5,
            temp=18,
            humidity=55,
            rainfall=70,
            crop=crop,
        )
        assert isinstance(score, float)


# ── Region Filtering ────────────────────────────────────────────


class TestRegionFilter:
    """Region-based crop filtering."""

    def test_ap_returns_subset(self) -> None:
        crops = filter_by_region(None, "Andhra Pradesh")
        assert "Rice" in crops
        assert "Red Chilli" in crops
        # Tea not grown in AP
        assert "Tea" not in crops

    def test_no_state_returns_all(self) -> None:
        crops = filter_by_region(None, None)
        assert len(crops) == len(CROP_DB)

    def test_unknown_state_falls_back_to_all(self) -> None:
        crops = filter_by_region(None, "Narnia")
        assert len(crops) == len(CROP_DB)


# ── Season Filtering ────────────────────────────────────────────


class TestSeasonFilter:
    """Season-based crop filtering."""

    def test_kharif_filter(self) -> None:
        crops = filter_by_season(CROP_DB, "Kharif")
        assert "Red Chilli" in crops
        # Pure Rabi crops excluded
        assert "Wheat" not in crops

    def test_rabi_filter(self) -> None:
        crops = filter_by_season(CROP_DB, "Rabi")
        assert "Wheat" in crops
        assert "Cotton" not in crops  # Cotton is Kharif only

    def test_no_season_returns_all(self) -> None:
        crops = filter_by_season(CROP_DB, None)
        assert len(crops) == len(CROP_DB)


# ── Region Boost ────────────────────────────────────────────────


class TestRegionBoost:
    """District-level confidence boosting."""

    def test_guntur_boosts_red_chilli(self) -> None:
        scores = {"Red Chilli": 80.0, "Rice": 75.0}
        boosted = apply_region_boost(scores, "Guntur")
        assert boosted["Red Chilli"] > 80.0
        assert boosted["Rice"] > 75.0  # Rice also boosted in Guntur

    def test_no_district_no_change(self) -> None:
        scores = {"Red Chilli": 80.0}
        boosted = apply_region_boost(scores, None)
        assert boosted["Red Chilli"] == 80.0

    def test_unrelated_district_no_boost(self) -> None:
        scores = {"Tea": 70.0}
        boosted = apply_region_boost(scores, "Guntur")
        assert boosted["Tea"] == 70.0  # Tea not boosted in Guntur


# ── Confidence Classification ───────────────────────────────────


class TestConfidenceClassification:
    """Confidence band labelling."""

    def test_very_high(self) -> None:
        assert classify_confidence(90) == "Very High"

    def test_high(self) -> None:
        assert classify_confidence(75) == "High"

    def test_medium(self) -> None:
        assert classify_confidence(55) == "Medium"

    def test_low(self) -> None:
        assert classify_confidence(30) == "Low"


# ── Suitability Notes ──────────────────────────────────────────


class TestSuitabilityNote:
    """Suitability note generation."""

    def test_excellent(self) -> None:
        assert "Excellent" in _suitability_note("Rice", 85)

    def test_good(self) -> None:
        assert "Good" in _suitability_note("Wheat", 70)

    def test_moderate(self) -> None:
        assert "Moderate" in _suitability_note("Maize", 55)

    def test_possible(self) -> None:
        assert "Possible" in _suitability_note("Tea", 30)


# ── Reasoning ───────────────────────────────────────────────────


class TestReasoning:
    """Reasoning message generation."""

    def test_returns_list(self) -> None:
        reasons = generate_reasoning(
            "Rice",
            85.0,
            90,
            45,
            45,
            6.2,
            28,
            80,
            200,
            "Guntur",
            "Andhra Pradesh",
            "Kharif",
        )
        assert isinstance(reasons, list)
        assert len(reasons) > 0

    def test_includes_region_note(self) -> None:
        reasons = generate_reasoning(
            "Red Chilli",
            80.0,
            70,
            50,
            60,
            6.5,
            30,
            65,
            100,
            "Guntur",
            "Andhra Pradesh",
            "Kharif",
        )
        assert any("Guntur" in r for r in reasons)

    def test_includes_season_note(self) -> None:
        reasons = generate_reasoning(
            "Rice",
            80.0,
            90,
            45,
            45,
            6.2,
            28,
            80,
            200,
            None,
            "Andhra Pradesh",
            "Kharif",
        )
        assert any("Kharif" in r for r in reasons)


# ── Full Recommendation ────────────────────────────────────────


class TestRecommendCrops:
    """End-to-end recommendation tests."""

    def test_returns_expected_keys(self) -> None:
        result = recommend_crops(
            nitrogen=45,
            phosphorus=30,
            potassium=40,
            ph=6.5,
            temperature=32,
            humidity=75,
            rainfall=120,
            location="Guntur, Andhra Pradesh",
            season="Kharif",
        )
        assert "recommended_crop" in result
        assert "confidence" in result
        assert "confidence_level" in result
        assert "top_alternatives" in result
        assert "reasoning" in result
        assert "feature_vector" in result
        assert "crop_health_score" in result

    def test_confidence_in_range(self) -> None:
        result = recommend_crops(
            nitrogen=90,
            phosphorus=45,
            potassium=45,
            ph=6.2,
            temperature=28,
            humidity=80,
            rainfall=200,
            location="Andhra Pradesh",
        )
        assert 0 <= result["confidence"] <= 100

    def test_alternatives_are_list(self) -> None:
        result = recommend_crops(
            nitrogen=100,
            phosphorus=50,
            potassium=40,
            ph=7.0,
            temperature=18,
            humidity=55,
            rainfall=70,
            location="Punjab",
            season="Rabi",
        )
        assert isinstance(result["top_alternatives"], list)

    def test_feature_vector_length(self) -> None:
        result = recommend_crops(
            nitrogen=50,
            phosphorus=30,
            potassium=40,
            ph=6.5,
            temperature=30,
            humidity=70,
            rainfall=100,
        )
        assert len(result["feature_vector"]) == 7

    def test_guntur_kharif_recommends_regional_crop(self) -> None:
        """Guntur + Kharif should recommend chilli, rice, cotton, or similar."""
        result = recommend_crops(
            nitrogen=70,
            phosphorus=55,
            potassium=60,
            ph=6.5,
            temperature=32,
            humidity=65,
            rainfall=100,
            location="Guntur, Andhra Pradesh",
            season="Kharif",
        )
        ap_crops = {
            "Red Chilli",
            "Rice",
            "Cotton",
            "Maize",
            "Tobacco",
            "Turmeric",
            "Groundnut",
            "Mango",
            "Tomato",
            "Sugarcane",
            "Sorghum",
            "Onion",
            "Banana",
            "Coconut",
        }
        assert result["recommended_crop"] in ap_crops

    def test_punjab_rabi_recommends_wheat_family(self) -> None:
        """Punjab + Rabi should lean toward wheat."""
        result = recommend_crops(
            nitrogen=120,
            phosphorus=55,
            potassium=40,
            ph=6.8,
            temperature=18,
            humidity=55,
            rainfall=70,
            location="Ludhiana, Punjab",
            season="Rabi",
        )
        rabi_crops = {"Wheat", "Potato", "Chickpea", "Mustard", "Lentil", "Onion"}
        assert result["recommended_crop"] in rabi_crops

    def test_health_score_backward_compat(self) -> None:
        """crop_health_score should be in [0, 100] for advisory compat."""
        result = recommend_crops(
            nitrogen=50,
            phosphorus=30,
            potassium=40,
            ph=6.5,
            temperature=30,
            humidity=70,
            rainfall=100,
        )
        assert 0 <= result["crop_health_score"] <= 100

    def test_empty_location_fallback(self) -> None:
        result = recommend_crops(
            nitrogen=50,
            phosphorus=30,
            potassium=40,
            ph=6.5,
            temperature=30,
            humidity=70,
            rainfall=100,
            location="India",
        )
        assert result["recommended_crop"] != "No suitable crop found"
