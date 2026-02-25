"""Deterministic tabular dataset builder.

Loads raw CSV, cleans missing values, normalizes units, and exports
a processed tabular dataset ready for XGBoost training.

When raw data files are not available, generates reproducible
synthetic data for development and CI testing.

Usage:
    python training/build_dataset.py
    # or: make build
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

# ── Logging ──────────────────────────────────────────────────────
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "build_dataset.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"


def generate_synthetic_tabular(n: int = 1000, seed: int = 42) -> pd.DataFrame:
    """Generate reproducible synthetic crop yield data.

    Used when raw data files are unavailable (dev / CI environments).
    Produces realistic-range agricultural features.

    Args:
        n: Number of samples.
        seed: Random seed for reproducibility.

    Returns:
        DataFrame with all schema-required columns.
    """
    rng = np.random.default_rng(seed)
    logger.info("Generating %d synthetic tabular samples (seed=%d)", n, seed)

    ph = rng.uniform(4.5, 8.5, n)
    clay = rng.integers(50, 600, n)
    oc = rng.integers(5, 200, n)
    ndvi = rng.uniform(0.1, 0.9, n)
    temp = rng.uniform(15, 42, n)
    rain = rng.uniform(50, 1500, n)
    hist_yield = rng.uniform(1.0, 8.0, n)

    # Synthetic target: influenced by soil, vegetation, and climate
    target = (
        0.3 * ndvi * 10
        + 0.2 * (ph - 4) / 5
        + 0.15 * rain / 500
        - 0.1 * (temp - 25).clip(0, None) / 10
        + 0.25 * hist_yield
        + rng.normal(0, 0.3, n)
    ).clip(0.5, 10.0)

    return pd.DataFrame(
        {
            "farm_id": [f"FARM_{i:04d}" for i in range(n)],
            "ph": ph.round(1),
            "clay_percent": clay,
            "organic_carbon": oc,
            "ndvi_mean": ndvi.round(3),
            "temp_avg_30d": temp.round(1),
            "rainfall_last_30d": rain.round(1),
            "historical_yield": hist_yield.round(2),
            "target_yield": target.round(2),
        }
    )


def clean_tabular(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and normalize the tabular dataset.

    - Drop rows with any NaN
    - Clip pH to valid agronomic range [4, 9]
    - Clip NDVI to [-1, 1]
    - Ensure non-negative rainfall

    Args:
        df: Raw tabular DataFrame.

    Returns:
        Cleaned DataFrame.
    """
    original_len = len(df)
    df = df.dropna().copy()
    dropped = original_len - len(df)
    if dropped:
        logger.info("Dropped %d rows with missing values", dropped)

    df["ph"] = df["ph"].clip(4, 9)
    df["ndvi_mean"] = df["ndvi_mean"].clip(-1, 1)
    df["rainfall_last_30d"] = df["rainfall_last_30d"].clip(lower=0)

    logger.info("Cleaned dataset: %d rows, %d columns", len(df), len(df.columns))
    return df


def write_metadata(df: pd.DataFrame, sources: list[str]) -> None:
    """Write dataset version metadata for reproducibility.

    Args:
        df: The processed DataFrame.
        sources: List of source file names.
    """
    meta = {
        "generated_at": datetime.now(tz=UTC).strftime("%Y-%m-%d"),
        "source": sources,
        "rows": len(df),
        "columns": list(df.columns),
        "version": "v1.0",
    }
    meta_path = PROCESSED_DIR / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    logger.info("Metadata written to %s", meta_path)


def build_tabular() -> None:
    """Build the processed tabular dataset end-to-end."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = RAW_DIR / "tabular_raw.csv"
    if raw_path.exists():
        logger.info("Loading raw data from %s", raw_path)
        raw = pd.read_csv(raw_path)
        sources = ["tabular_raw.csv"]
    else:
        logger.warning("Raw file not found — generating synthetic data")
        raw = generate_synthetic_tabular()
        sources = ["synthetic_generated"]

    processed = clean_tabular(raw)
    out_path = PROCESSED_DIR / "tabular.csv"
    processed.to_csv(out_path, index=False)
    logger.info("Processed tabular dataset saved to %s", out_path)

    write_metadata(processed, sources)


if __name__ == "__main__":
    build_tabular()
