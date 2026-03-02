"""Crop Recommendation Engine service — classification + ranking.

Enterprise diagnostic engine (no external API calls):
- 30-crop knowledge base with ideal growing conditions
- Region/state filtering with district-level boosting
- Feature-vector scoring against per-crop ideal ranges
- Season filtering (Kharif / Rabi / Zaid)
- Multi-factor ranking with confidence scores
- Explainable reasoning generation
"""

from __future__ import annotations

from typing import Any

from loguru import logger


class CropEngineError(Exception):
    """Raised when crop recommendation fails."""


# =====================================================================
#  CROP KNOWLEDGE BASE  (30 crops)
# =====================================================================
# Each entry contains ideal ranges for the 7-feature vector
# [N, P, K, pH, temperature, humidity, rainfall]
# plus region suitability and seasonal data.

CROP_DB: dict[str, dict[str, Any]] = {
    "Rice": {
        "n": (60, 120),
        "p": (30, 60),
        "k": (30, 60),
        "ph": (5.5, 7.0),
        "temp": (22, 35),
        "humidity": (70, 95),
        "rainfall": (150, 300),
        "seasons": ["Kharif", "Rabi"],
        "states": [
            "Andhra Pradesh",
            "Telangana",
            "Tamil Nadu",
            "West Bengal",
            "Punjab",
            "Uttar Pradesh",
            "Karnataka",
            "Odisha",
            "Bihar",
        ],
        "boost_districts": ["Guntur", "Krishna", "East Godavari", "West Godavari", "Nellore"],
        "category": "Cereal",
    },
    "Wheat": {
        "n": (80, 150),
        "p": (40, 70),
        "k": (30, 50),
        "ph": (6.0, 7.5),
        "temp": (12, 25),
        "humidity": (40, 70),
        "rainfall": (50, 100),
        "seasons": ["Rabi"],
        "states": [
            "Punjab",
            "Haryana",
            "Uttar Pradesh",
            "Madhya Pradesh",
            "Rajasthan",
            "Bihar",
            "Gujarat",
        ],
        "boost_districts": ["Ludhiana", "Karnal", "Meerut"],
        "category": "Cereal",
    },
    "Maize": {
        "n": (60, 120),
        "p": (30, 60),
        "k": (30, 60),
        "ph": (5.5, 7.5),
        "temp": (20, 35),
        "humidity": (50, 80),
        "rainfall": (60, 120),
        "seasons": ["Kharif", "Rabi"],
        "states": [
            "Andhra Pradesh",
            "Karnataka",
            "Rajasthan",
            "Bihar",
            "Madhya Pradesh",
            "Uttar Pradesh",
            "Telangana",
        ],
        "boost_districts": ["Guntur", "Prakasam", "Karimnagar"],
        "category": "Cereal",
    },
    "Red Chilli": {
        "n": (50, 100),
        "p": (40, 80),
        "k": (40, 80),
        "ph": (6.0, 7.0),
        "temp": (25, 38),
        "humidity": (55, 80),
        "rainfall": (60, 150),
        "seasons": ["Kharif"],
        "states": [
            "Andhra Pradesh",
            "Telangana",
            "Karnataka",
            "Maharashtra",
        ],
        "boost_districts": ["Guntur", "Prakasam", "Khammam", "Warangal"],
        "category": "Spice",
    },
    "Cotton": {
        "n": (50, 100),
        "p": (25, 50),
        "k": (20, 50),
        "ph": (6.0, 8.0),
        "temp": (25, 42),
        "humidity": (40, 80),
        "rainfall": (60, 150),
        "seasons": ["Kharif"],
        "states": [
            "Gujarat",
            "Maharashtra",
            "Andhra Pradesh",
            "Telangana",
            "Rajasthan",
            "Madhya Pradesh",
            "Punjab",
            "Haryana",
            "Karnataka",
        ],
        "boost_districts": ["Guntur", "Kurnool", "Adilabad", "Nagpur"],
        "category": "Cash Crop",
    },
    "Groundnut": {
        "n": (15, 40),
        "p": (30, 60),
        "k": (20, 50),
        "ph": (5.5, 7.0),
        "temp": (25, 35),
        "humidity": (50, 80),
        "rainfall": (50, 120),
        "seasons": ["Kharif", "Rabi"],
        "states": [
            "Andhra Pradesh",
            "Gujarat",
            "Tamil Nadu",
            "Rajasthan",
            "Karnataka",
            "Maharashtra",
        ],
        "boost_districts": ["Anantapur", "Kurnool", "Chittoor", "Junagadh"],
        "category": "Oilseed",
    },
    "Soybean": {
        "n": (10, 40),
        "p": (30, 60),
        "k": (20, 50),
        "ph": (5.5, 7.0),
        "temp": (22, 32),
        "humidity": (50, 80),
        "rainfall": (80, 150),
        "seasons": ["Kharif"],
        "states": [
            "Madhya Pradesh",
            "Maharashtra",
            "Rajasthan",
            "Karnataka",
            "Telangana",
        ],
        "boost_districts": ["Indore", "Ujjain", "Latur"],
        "category": "Oilseed",
    },
    "Sugarcane": {
        "n": (100, 200),
        "p": (40, 80),
        "k": (50, 100),
        "ph": (6.0, 7.5),
        "temp": (25, 40),
        "humidity": (65, 90),
        "rainfall": (100, 250),
        "seasons": ["Kharif"],
        "states": [
            "Uttar Pradesh",
            "Maharashtra",
            "Karnataka",
            "Andhra Pradesh",
            "Tamil Nadu",
            "Punjab",
        ],
        "boost_districts": ["Meerut", "Kolhapur", "Belgaum"],
        "category": "Cash Crop",
    },
    "Tobacco": {
        "n": (40, 80),
        "p": (30, 60),
        "k": (30, 60),
        "ph": (5.5, 7.0),
        "temp": (22, 35),
        "humidity": (55, 80),
        "rainfall": (50, 120),
        "seasons": ["Rabi"],
        "states": [
            "Andhra Pradesh",
            "Karnataka",
            "Gujarat",
        ],
        "boost_districts": ["Guntur", "Prakasam", "Mysuru"],
        "category": "Cash Crop",
    },
    "Turmeric": {
        "n": (60, 120),
        "p": (40, 80),
        "k": (60, 120),
        "ph": (5.0, 7.0),
        "temp": (25, 35),
        "humidity": (70, 90),
        "rainfall": (120, 250),
        "seasons": ["Kharif"],
        "states": [
            "Andhra Pradesh",
            "Telangana",
            "Tamil Nadu",
            "Maharashtra",
            "Odisha",
        ],
        "boost_districts": ["Guntur", "Kadapa", "Nizamabad", "Erode"],
        "category": "Spice",
    },
    "Sunflower": {
        "n": (50, 100),
        "p": (40, 80),
        "k": (30, 60),
        "ph": (6.0, 7.5),
        "temp": (20, 30),
        "humidity": (40, 60),
        "rainfall": (40, 80),
        "seasons": ["Kharif", "Rabi"],
        "states": [
            "Karnataka",
            "Andhra Pradesh",
            "Maharashtra",
            "Tamil Nadu",
        ],
        "boost_districts": ["Bellary", "Raichur", "Bijapur"],
        "category": "Oilseed",
    },
    "Sorghum": {
        "n": (40, 80),
        "p": (20, 50),
        "k": (20, 50),
        "ph": (6.0, 8.0),
        "temp": (25, 40),
        "humidity": (40, 70),
        "rainfall": (40, 100),
        "seasons": ["Kharif", "Rabi"],
        "states": [
            "Maharashtra",
            "Karnataka",
            "Rajasthan",
            "Andhra Pradesh",
            "Madhya Pradesh",
        ],
        "boost_districts": ["Solapur", "Bijapur"],
        "category": "Millet",
    },
    "Bajra": {
        "n": (30, 60),
        "p": (15, 40),
        "k": (15, 40),
        "ph": (6.0, 8.0),
        "temp": (28, 42),
        "humidity": (30, 60),
        "rainfall": (20, 60),
        "seasons": ["Kharif"],
        "states": [
            "Rajasthan",
            "Gujarat",
            "Maharashtra",
            "Haryana",
            "Uttar Pradesh",
        ],
        "boost_districts": ["Jodhpur", "Jaipur", "Bhavnagar"],
        "category": "Millet",
    },
    "Pulses (Moong)": {
        "n": (10, 30),
        "p": (30, 60),
        "k": (20, 40),
        "ph": (6.0, 7.5),
        "temp": (25, 35),
        "humidity": (50, 80),
        "rainfall": (40, 100),
        "seasons": ["Kharif", "Zaid"],
        "states": [
            "Rajasthan",
            "Madhya Pradesh",
            "Andhra Pradesh",
            "Maharashtra",
            "Karnataka",
        ],
        "boost_districts": ["Jaipur", "Kurnool", "Nagpur"],
        "category": "Pulse",
    },
    "Pulses (Urad)": {
        "n": (10, 30),
        "p": (30, 60),
        "k": (20, 40),
        "ph": (6.0, 7.5),
        "temp": (25, 35),
        "humidity": (60, 85),
        "rainfall": (60, 120),
        "seasons": ["Kharif"],
        "states": [
            "Madhya Pradesh",
            "Uttar Pradesh",
            "Andhra Pradesh",
            "Rajasthan",
        ],
        "boost_districts": [],
        "category": "Pulse",
    },
    "Chickpea": {
        "n": (10, 30),
        "p": (30, 60),
        "k": (20, 50),
        "ph": (6.0, 8.0),
        "temp": (15, 28),
        "humidity": (30, 60),
        "rainfall": (30, 80),
        "seasons": ["Rabi"],
        "states": [
            "Madhya Pradesh",
            "Rajasthan",
            "Maharashtra",
            "Uttar Pradesh",
            "Andhra Pradesh",
            "Karnataka",
        ],
        "boost_districts": ["Indore", "Latur", "Kurnool"],
        "category": "Pulse",
    },
    "Lentil": {
        "n": (10, 30),
        "p": (20, 50),
        "k": (15, 40),
        "ph": (6.0, 7.5),
        "temp": (15, 25),
        "humidity": (40, 65),
        "rainfall": (25, 60),
        "seasons": ["Rabi"],
        "states": [
            "Uttar Pradesh",
            "Madhya Pradesh",
            "Bihar",
            "West Bengal",
        ],
        "boost_districts": [],
        "category": "Pulse",
    },
    "Mustard": {
        "n": (40, 80),
        "p": (20, 50),
        "k": (15, 40),
        "ph": (6.0, 7.5),
        "temp": (10, 25),
        "humidity": (40, 70),
        "rainfall": (30, 70),
        "seasons": ["Rabi"],
        "states": [
            "Rajasthan",
            "Uttar Pradesh",
            "Madhya Pradesh",
            "Haryana",
            "Gujarat",
        ],
        "boost_districts": ["Bharatpur", "Alwar"],
        "category": "Oilseed",
    },
    "Potato": {
        "n": (80, 150),
        "p": (50, 100),
        "k": (60, 120),
        "ph": (5.0, 6.5),
        "temp": (15, 25),
        "humidity": (60, 80),
        "rainfall": (50, 120),
        "seasons": ["Rabi"],
        "states": [
            "Uttar Pradesh",
            "West Bengal",
            "Bihar",
            "Gujarat",
            "Punjab",
        ],
        "boost_districts": ["Agra", "Hooghly"],
        "category": "Vegetable",
    },
    "Onion": {
        "n": (80, 150),
        "p": (40, 80),
        "k": (50, 100),
        "ph": (6.0, 7.5),
        "temp": (15, 30),
        "humidity": (50, 75),
        "rainfall": (40, 80),
        "seasons": ["Rabi", "Kharif"],
        "states": [
            "Maharashtra",
            "Karnataka",
            "Madhya Pradesh",
            "Andhra Pradesh",
            "Rajasthan",
        ],
        "boost_districts": ["Nashik", "Indore", "Kurnool"],
        "category": "Vegetable",
    },
    "Tomato": {
        "n": (80, 150),
        "p": (50, 100),
        "k": (50, 100),
        "ph": (5.5, 7.0),
        "temp": (20, 30),
        "humidity": (50, 80),
        "rainfall": (50, 100),
        "seasons": ["Kharif", "Rabi"],
        "states": [
            "Andhra Pradesh",
            "Karnataka",
            "Madhya Pradesh",
            "Maharashtra",
            "Tamil Nadu",
        ],
        "boost_districts": ["Kurnool", "Chittoor", "Madanapalle"],
        "category": "Vegetable",
    },
    "Banana": {
        "n": (120, 250),
        "p": (30, 60),
        "k": (100, 200),
        "ph": (5.5, 7.0),
        "temp": (25, 38),
        "humidity": (70, 95),
        "rainfall": (100, 250),
        "seasons": ["Kharif"],
        "states": [
            "Tamil Nadu",
            "Maharashtra",
            "Gujarat",
            "Andhra Pradesh",
            "Karnataka",
        ],
        "boost_districts": ["Jalgaon", "Trichy", "Anantapur"],
        "category": "Fruit",
    },
    "Coconut": {
        "n": (50, 100),
        "p": (20, 50),
        "k": (80, 160),
        "ph": (5.5, 7.0),
        "temp": (25, 35),
        "humidity": (70, 95),
        "rainfall": (120, 300),
        "seasons": ["Kharif"],
        "states": [
            "Kerala",
            "Karnataka",
            "Tamil Nadu",
            "Andhra Pradesh",
        ],
        "boost_districts": ["Tumkur", "Coimbatore", "East Godavari"],
        "category": "Plantation",
    },
    "Mango": {
        "n": (50, 100),
        "p": (25, 60),
        "k": (40, 80),
        "ph": (5.5, 7.5),
        "temp": (25, 40),
        "humidity": (50, 80),
        "rainfall": (75, 200),
        "seasons": ["Kharif"],
        "states": [
            "Andhra Pradesh",
            "Uttar Pradesh",
            "Karnataka",
            "Tamil Nadu",
            "Maharashtra",
            "Gujarat",
        ],
        "boost_districts": ["Krishna", "Chittoor", "Lucknow", "Ratnagiri"],
        "category": "Fruit",
    },
    "Tea": {
        "n": (80, 150),
        "p": (20, 50),
        "k": (40, 80),
        "ph": (4.5, 6.0),
        "temp": (15, 28),
        "humidity": (75, 95),
        "rainfall": (150, 350),
        "seasons": ["Kharif"],
        "states": [
            "Assam",
            "West Bengal",
            "Tamil Nadu",
            "Kerala",
            "Karnataka",
        ],
        "boost_districts": ["Jorhat", "Darjeeling", "Nilgiris"],
        "category": "Plantation",
    },
    "Coffee": {
        "n": (60, 120),
        "p": (20, 50),
        "k": (40, 80),
        "ph": (5.0, 6.5),
        "temp": (18, 28),
        "humidity": (70, 90),
        "rainfall": (150, 300),
        "seasons": ["Kharif"],
        "states": [
            "Karnataka",
            "Kerala",
            "Tamil Nadu",
        ],
        "boost_districts": ["Chikmagalur", "Kodagu", "Wayanad"],
        "category": "Plantation",
    },
    "Jute": {
        "n": (40, 80),
        "p": (20, 40),
        "k": (20, 40),
        "ph": (6.0, 7.5),
        "temp": (25, 35),
        "humidity": (70, 90),
        "rainfall": (120, 250),
        "seasons": ["Kharif"],
        "states": [
            "West Bengal",
            "Bihar",
            "Assam",
            "Odisha",
        ],
        "boost_districts": ["Murshidabad", "North 24 Parganas"],
        "category": "Fibre",
    },
    "Sesame": {
        "n": (20, 50),
        "p": (15, 40),
        "k": (15, 40),
        "ph": (5.5, 7.5),
        "temp": (25, 38),
        "humidity": (40, 70),
        "rainfall": (30, 80),
        "seasons": ["Kharif"],
        "states": [
            "Rajasthan",
            "West Bengal",
            "Madhya Pradesh",
            "Gujarat",
            "Andhra Pradesh",
        ],
        "boost_districts": [],
        "category": "Oilseed",
    },
    "Castor": {
        "n": (20, 50),
        "p": (20, 50),
        "k": (15, 40),
        "ph": (5.5, 7.5),
        "temp": (25, 38),
        "humidity": (30, 60),
        "rainfall": (30, 80),
        "seasons": ["Kharif"],
        "states": [
            "Gujarat",
            "Rajasthan",
            "Andhra Pradesh",
        ],
        "boost_districts": ["Mehsana", "Banaskantha"],
        "category": "Oilseed",
    },
}


# =====================================================================
#  STATE / DISTRICT RESOLUTION
# =====================================================================

_DISTRICT_STATE_MAP: dict[str, str] = {
    # Andhra Pradesh
    "Guntur": "Andhra Pradesh",
    "Krishna": "Andhra Pradesh",
    "East Godavari": "Andhra Pradesh",
    "West Godavari": "Andhra Pradesh",
    "Prakasam": "Andhra Pradesh",
    "Nellore": "Andhra Pradesh",
    "Kurnool": "Andhra Pradesh",
    "Anantapur": "Andhra Pradesh",
    "Chittoor": "Andhra Pradesh",
    "Kadapa": "Andhra Pradesh",
    "Madanapalle": "Andhra Pradesh",
    # Telangana
    "Karimnagar": "Telangana",
    "Khammam": "Telangana",
    "Warangal": "Telangana",
    "Nizamabad": "Telangana",
    # Other states - key districts
    "Ludhiana": "Punjab",
    "Karnal": "Haryana",
    "Meerut": "Uttar Pradesh",
    "Agra": "Uttar Pradesh",
    "Lucknow": "Uttar Pradesh",
    "Indore": "Madhya Pradesh",
    "Ujjain": "Madhya Pradesh",
    "Jaipur": "Rajasthan",
    "Jodhpur": "Rajasthan",
    "Bharatpur": "Rajasthan",
    "Alwar": "Rajasthan",
    "Bhavnagar": "Gujarat",
    "Junagadh": "Gujarat",
    "Mehsana": "Gujarat",
    "Banaskantha": "Gujarat",
    "Nashik": "Maharashtra",
    "Nagpur": "Maharashtra",
    "Solapur": "Maharashtra",
    "Latur": "Maharashtra",
    "Kolhapur": "Maharashtra",
    "Jalgaon": "Maharashtra",
    "Ratnagiri": "Maharashtra",
    "Adilabad": "Telangana",
    "Belgaum": "Karnataka",
    "Bellary": "Karnataka",
    "Raichur": "Karnataka",
    "Bijapur": "Karnataka",
    "Mysuru": "Karnataka",
    "Chikmagalur": "Karnataka",
    "Kodagu": "Karnataka",
    "Tumkur": "Karnataka",
    "Erode": "Tamil Nadu",
    "Coimbatore": "Tamil Nadu",
    "Nilgiris": "Tamil Nadu",
    "Trichy": "Tamil Nadu",
    "Hooghly": "West Bengal",
    "Murshidabad": "West Bengal",
    "North 24 Parganas": "West Bengal",
    "Darjeeling": "West Bengal",
    "Jorhat": "Assam",
    "Wayanad": "Kerala",
}


def parse_location(location: str) -> tuple[str | None, str | None]:
    """Extract district and state from a location string.

    Supports formats:
        "Guntur, Andhra Pradesh"
        "Andhra Pradesh"
        "Guntur"
    """
    parts = [p.strip().title() for p in location.split(",")]

    district: str | None = None
    state: str | None = None

    if len(parts) >= 2:
        district = parts[0]
        state = parts[1]
    elif len(parts) == 1:
        token = parts[0]
        # Check if it's a known district
        if token in _DISTRICT_STATE_MAP:
            district = token
            state = _DISTRICT_STATE_MAP[token]
        else:
            state = token

    return district, state


# =====================================================================
#  SCORING ENGINE
# =====================================================================


def _range_score(value: float, low: float, high: float) -> float:
    """Score a value against an ideal [low, high] range.

    Returns 1.0 when within range, degrades linearly outside.
    """
    if low <= value <= high:
        return 1.0
    span = (high - low) / 2 if high != low else 1.0
    distance = min(abs(value - low), abs(value - high))
    penalty = distance / (span * 2)  # normalise to ~0.5 at 2x span distance
    return max(0.0, round(1.0 - penalty, 4))


def compute_feature_score(
    n: float,
    p: float,
    k: float,
    ph: float,
    temp: float,
    humidity: float,
    rainfall: float,
    crop: dict[str, Any],
) -> float:
    """Score a feature vector [N,P,K,pH,temp,humidity,rainfall] against a crop.

    Weighted scoring:
      N, P, K  -> 15% each  (total 45%)
      pH       -> 15%
      temp     -> 15%
      humidity -> 10%
      rainfall -> 15%
    """
    weights = {
        "n": 0.15,
        "p": 0.15,
        "k": 0.15,
        "ph": 0.15,
        "temp": 0.15,
        "humidity": 0.10,
        "rainfall": 0.15,
    }
    values = {
        "n": (n, crop["n"]),
        "p": (p, crop["p"]),
        "k": (k, crop["k"]),
        "ph": (ph, crop["ph"]),
        "temp": (temp, crop["temp"]),
        "humidity": (humidity, crop["humidity"]),
        "rainfall": (rainfall, crop["rainfall"]),
    }
    total = 0.0
    for key, (val, rng) in values.items():
        total += weights[key] * _range_score(val, rng[0], rng[1])
    return round(total * 100, 2)


def filter_by_region(
    district: str | None,
    state: str | None,
) -> dict[str, dict[str, Any]]:
    """Filter CROP_DB to crops suitable for the given region."""
    if not state:
        return dict(CROP_DB)

    eligible: dict[str, dict[str, Any]] = {}
    for name, info in CROP_DB.items():
        if state in info["states"]:
            eligible[name] = info
    # If nothing matched, fall back to full DB
    return eligible if eligible else dict(CROP_DB)


def filter_by_season(
    crops: dict[str, dict[str, Any]],
    season: str | None,
) -> dict[str, dict[str, Any]]:
    """Filter crops by agricultural season."""
    if not season:
        return crops
    filtered = {name: info for name, info in crops.items() if season in info["seasons"]}
    return filtered if filtered else crops


def apply_region_boost(
    scores: dict[str, float],
    district: str | None,
) -> dict[str, float]:
    """Boost confidence for crops dominant in the given district."""
    if not district:
        return scores
    boosted = dict(scores)
    for crop_name, score in boosted.items():
        info = CROP_DB.get(crop_name, {})
        if district in info.get("boost_districts", []):
            boosted[crop_name] = min(100.0, round(score * 1.12, 2))
    return boosted


# =====================================================================
#  REASONING GENERATOR
# =====================================================================


def generate_reasoning(
    crop_name: str,
    score: float,
    n: float,
    p: float,
    k: float,
    ph: float,
    temp: float,
    humidity: float,
    rainfall: float,
    district: str | None,
    state: str | None,
    season: str | None,
) -> list[str]:
    """Generate human-readable reasoning for why a crop was recommended."""
    info = CROP_DB.get(crop_name, {})
    reasons: list[str] = []

    # Region match
    if district and district in info.get("boost_districts", []):
        reasons.append(f"Highly suitable for {district} region")
    elif state and state in info.get("states", []):
        reasons.append(f"Well-suited for {state}")

    # Rainfall match
    rng = info.get("rainfall", (0, 9999))
    if rng[0] <= rainfall <= rng[1]:
        reasons.append("Matches current rainfall pattern")
    elif rainfall < rng[0]:
        reasons.append("Rainfall is below ideal - irrigation may be needed")

    # Nutrient suitability
    n_ok = info.get("n", (0, 999))[0] <= n <= info.get("n", (0, 999))[1]
    p_ok = info.get("p", (0, 999))[0] <= p <= info.get("p", (0, 999))[1]
    k_ok = info.get("k", (0, 999))[0] <= k <= info.get("k", (0, 999))[1]
    good_count = sum([n_ok, p_ok, k_ok])
    if good_count == 3:
        reasons.append("Soil nutrients (N, P, K) are within ideal range")
    elif good_count >= 2:
        reasons.append("Most soil nutrients support this crop's growth")
    else:
        reasons.append("Soil nutrient adjustment may improve yield")

    # pH match
    ph_rng = info.get("ph", (0, 14))
    if ph_rng[0] <= ph <= ph_rng[1]:
        reasons.append("Soil pH is within optimal range")

    # Temperature match
    temp_rng = info.get("temp", (0, 50))
    if temp_rng[0] <= temp <= temp_rng[1]:
        reasons.append("Temperature conditions are favorable")

    # Season match
    if season and season in info.get("seasons", []):
        reasons.append(f"Suitable for {season} season cultivation")

    # High confidence note
    if score >= 85:
        reasons.append("Overall growing conditions are excellent for this crop")
    elif score >= 70:
        reasons.append("Growing conditions are good with minor adjustments possible")

    # Category
    cat = info.get("category", "")
    if cat:
        reasons.append(f"Category: {cat}")

    return reasons


def classify_confidence(score: float) -> str:
    """Map numeric confidence to a label."""
    if score >= 85:
        return "Very High"
    if score >= 70:
        return "High"
    if score >= 50:
        return "Medium"
    return "Low"


def _suitability_note(crop_name: str, score: float) -> str:
    """Generate a one-line suitability note for an alternative crop."""
    info = CROP_DB.get(crop_name, {})
    cat = info.get("category", "Crop")
    if score >= 80:
        return f"Excellent match - {cat}"
    if score >= 65:
        return f"Good alternative - {cat}"
    if score >= 50:
        return f"Moderate fit - {cat}"
    return f"Possible with adjustments - {cat}"


# =====================================================================
#  MAIN ENTRY POINT
# =====================================================================


def recommend_crops(
    nitrogen: float,
    phosphorus: float,
    potassium: float,
    ph: float,
    temperature: float,
    humidity: float,
    rainfall: float,
    location: str = "India",
    season: str | None = None,
    soil_health: str = "Medium",
) -> dict[str, Any]:
    """Full crop recommendation — classification + ranking.

    This is a **synchronous** function — no I/O calls.

    Args:
        nitrogen:     N level (kg/ha)
        phosphorus:   P level (kg/ha)
        potassium:    K level (kg/ha)
        ph:           Soil pH
        temperature:  Temperature (C)
        humidity:     Relative humidity (%)
        rainfall:     Rainfall (mm)
        location:     "District, State" or "State"
        season:       Kharif / Rabi / Zaid (optional)
        soil_health:  Soil health label (from Soil Engine)

    Returns:
        Complete crop recommendation dict.
    """
    logger.debug(
        "Crop Engine: N={}, P={}, K={}, pH={}, T={}, H={}, R={}, loc={}, season={}",
        nitrogen,
        phosphorus,
        potassium,
        ph,
        temperature,
        humidity,
        rainfall,
        location,
        season,
    )

    district, state = parse_location(location)

    # Step 1: Region filter
    region_crops = filter_by_region(district, state)

    # Step 2: Season filter
    seasonal_crops = filter_by_season(region_crops, season)

    # Step 3: Score all candidates
    raw_scores: dict[str, float] = {}
    for crop_name, crop_info in seasonal_crops.items():
        raw_scores[crop_name] = compute_feature_score(
            nitrogen,
            phosphorus,
            potassium,
            ph,
            temperature,
            humidity,
            rainfall,
            crop_info,
        )

    # Step 4: Region boost
    boosted_scores = apply_region_boost(raw_scores, district)

    # Sort by score descending
    ranked = sorted(boosted_scores.items(), key=lambda x: x[1], reverse=True)

    if not ranked:
        return {
            "recommended_crop": "No suitable crop found",
            "confidence": 0.0,
            "confidence_level": "Low",
            "top_alternatives": [],
            "reasoning": ["No crops matched the given conditions"],
            "season": season or "All",
            "location": location,
            "feature_vector": [
                nitrogen,
                phosphorus,
                potassium,
                ph,
                temperature,
                humidity,
                rainfall,
            ],
            "crop_health_score": 25.0,
        }

    best_name, best_score = ranked[0]

    # Alternatives (next 2-4 crops, excluding the best)
    alternatives = []
    for name, score in ranked[1:5]:
        alternatives.append(
            {
                "crop": name,
                "confidence": score,
                "suitability": _suitability_note(name, score),
            }
        )

    reasoning = generate_reasoning(
        best_name,
        best_score,
        nitrogen,
        phosphorus,
        potassium,
        ph,
        temperature,
        humidity,
        rainfall,
        district,
        state,
        season,
    )

    return {
        "recommended_crop": best_name,
        "confidence": best_score,
        "confidence_level": classify_confidence(best_score),
        "top_alternatives": alternatives,
        "reasoning": reasoning,
        "season": season or "All",
        "location": location,
        "feature_vector": [
            nitrogen,
            phosphorus,
            potassium,
            ph,
            temperature,
            humidity,
            rainfall,
        ],
        # Advisory engine backward compat: map confidence to crop_health_score
        "crop_health_score": min(100.0, round(best_score * 0.85 + 15, 1)),
    }
