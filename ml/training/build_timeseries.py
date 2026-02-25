"""Deterministic time-series dataset builder for LSTM training.

Loads raw time-series CSV, validates minimum sequence length,
creates rolling monthly sequences grouped by farm, and exports
a NumPy array of shape (samples, 12, 3) for LSTM consumption.

When raw data files are not available, generates reproducible
synthetic time-series data for development and CI testing.

Usage:
    python training/build_timeseries.py
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
        logging.FileHandler(LOG_DIR / "build_timeseries.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

# ── Constants ────────────────────────────────────────────────────
SEQUENCE_LENGTH = 12  # months
FEATURES = ["temperature", "rainfall", "radiation"]
N_FEATURES = len(FEATURES)


def generate_synthetic_timeseries(
    n_farms: int = 50,
    n_months: int = 24,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate reproducible synthetic monthly time-series data.

    Creates seasonally-varying temperature, rainfall, and radiation
    data for multiple farms across ``n_months`` months.

    Args:
        n_farms: Number of synthetic farms.
        n_months: Number of months per farm.
        seed: Random seed for reproducibility.

    Returns:
        DataFrame with columns: farm_id, date, temperature,
        rainfall, radiation.
    """
    rng = np.random.default_rng(seed)
    logger.info(
        "Generating synthetic time-series: %d farms × %d months (seed=%d)",
        n_farms,
        n_months,
        seed,
    )

    records = []
    base_date = pd.Timestamp("2024-01-01")

    for farm_idx in range(n_farms):
        farm_id = f"FARM_{farm_idx:04d}"
        for month_offset in range(n_months):
            date = base_date + pd.DateOffset(months=month_offset)
            month = date.month

            # Seasonal variation
            temp_base = 25 + 8 * np.sin(2 * np.pi * (month - 4) / 12)
            rain_base = 100 + 80 * np.sin(2 * np.pi * (month - 7) / 12)
            rad_base = 18 + 5 * np.sin(2 * np.pi * (month - 1) / 12)

            records.append(
                {
                    "farm_id": farm_id,
                    "date": date.strftime("%Y-%m-%d"),
                    "temperature": round(temp_base + rng.normal(0, 2), 1),
                    "rainfall": round(max(0, rain_base + rng.normal(0, 30)), 1),
                    "radiation": round(max(0, rad_base + rng.normal(0, 2)), 1),
                }
            )

    return pd.DataFrame(records)


def build_sequences(df: pd.DataFrame) -> np.ndarray:
    """Convert time-series DataFrame into LSTM-ready 3D array.

    Groups by ``farm_id``, sorts by date, and creates rolling
    windows of ``SEQUENCE_LENGTH`` months.

    Args:
        df: Time-series DataFrame with farm_id, date, and feature
            columns.

    Returns:
        NumPy array of shape ``(n_sequences, 12, 3)``.
    """
    all_sequences = []

    for farm_id, group in df.groupby("farm_id"):
        group = group.sort_values("date")
        values = group[FEATURES].values

        if len(values) < SEQUENCE_LENGTH:
            logger.warning(
                "Farm %s has only %d months (need %d) — skipping",
                farm_id,
                len(values),
                SEQUENCE_LENGTH,
            )
            continue

        # Rolling window sequences
        for i in range(len(values) - SEQUENCE_LENGTH + 1):
            seq = values[i : i + SEQUENCE_LENGTH]
            all_sequences.append(seq)

    sequences = np.array(all_sequences, dtype=np.float32)
    logger.info(
        "Built %d sequences — shape: %s",
        len(sequences),
        sequences.shape,
    )
    return sequences


def write_timeseries_metadata(sequences: np.ndarray, sources: list[str]) -> None:
    """Write time-series dataset metadata for reproducibility."""
    meta = {
        "generated_at": datetime.now(tz=UTC).strftime("%Y-%m-%d"),
        "source": sources,
        "n_sequences": int(sequences.shape[0]),
        "sequence_length": int(sequences.shape[1]),
        "n_features": int(sequences.shape[2]),
        "features": FEATURES,
        "shape": list(sequences.shape),
        "version": "v1.0",
    }
    meta_path = PROCESSED_DIR / "timeseries_metadata.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    logger.info("Time-series metadata written to %s", meta_path)


def build_timeseries() -> None:
    """Build the processed time-series dataset end-to-end."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = RAW_DIR / "timeseries_raw.csv"
    if raw_path.exists():
        logger.info("Loading raw time-series from %s", raw_path)
        raw = pd.read_csv(raw_path)
        sources = ["timeseries_raw.csv"]
    else:
        logger.warning("Raw file not found — generating synthetic time-series")
        raw = generate_synthetic_timeseries()
        sources = ["synthetic_generated"]

    sequences = build_sequences(raw)
    out_path = PROCESSED_DIR / "timeseries_sequences.npy"
    np.save(out_path, sequences)
    logger.info("Time-series sequences saved to %s", out_path)

    write_timeseries_metadata(sequences, sources)


if __name__ == "__main__":
    build_timeseries()
