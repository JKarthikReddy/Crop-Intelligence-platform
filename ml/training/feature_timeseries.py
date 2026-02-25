"""Config-driven time-series feature engineering pipeline.

Loads processed time-series sequences, normalizes values with a
MinMaxScaler, computes rolling statistical features, and saves
the feature-ready tensor plus scaler artifact for inference reuse.

Usage:
    python training/feature_timeseries.py
    # or: make features
"""

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import yaml

try:
    import joblib
except ImportError:  # pragma: no cover
    from sklearn.externals import joblib  # type: ignore[attr-defined]

from sklearn.preprocessing import MinMaxScaler

# ── Logging ──────────────────────────────────────────────────────
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "feature_timeseries.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "features.yaml"
PROCESSED_DIR = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "models"

# ── Constants ────────────────────────────────────────────────────
FEATURE_NAMES = ["temperature", "rainfall", "radiation"]


def load_feature_config() -> dict:
    """Load feature engineering configuration from YAML."""
    if not CONFIG_PATH.exists():
        logger.error("Feature config not found: %s", CONFIG_PATH)
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def load_sequences() -> np.ndarray:
    """Load the raw time-series sequences from the build step.

    Expected shape: ``(n_sequences, 12, 3)``

    Returns:
        3D NumPy array of time-series sequences.
    """
    path = PROCESSED_DIR / "timeseries_sequences.npy"
    if not path.exists():
        logger.error(
            "Time-series sequences not found: %s — run 'make build' first",
            path,
        )
        sys.exit(1)

    sequences = np.load(path)
    logger.info("Loaded sequences — shape: %s", sequences.shape)
    return sequences


def scale_sequences(sequences: np.ndarray) -> np.ndarray:
    """Apply MinMaxScaler to time-series sequences.

    Reshapes the 3D tensor to 2D for scaling, fits the scaler,
    saves it for inference reuse, and reshapes back to 3D.

    Args:
        sequences: Input array of shape ``(n, 12, 3)``.

    Returns:
        Scaled array of the same shape.
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    n_samples, seq_len, n_features = sequences.shape
    flat = sequences.reshape(-1, n_features)

    scaler = MinMaxScaler()
    scaled_flat = scaler.fit_transform(flat)

    scaler_path = MODELS_DIR / "timeseries_scaler.pkl"
    joblib.dump(scaler, scaler_path)
    logger.info(
        "MinMaxScaler fitted and saved to %s (%d features)",
        scaler_path,
        n_features,
    )

    return scaled_flat.reshape(n_samples, seq_len, n_features)


def compute_rolling_stats(sequences: np.ndarray) -> np.ndarray:
    """Compute rolling statistical features per sequence.

    For each sequence of shape ``(12, 3)``, computes:
    - Rolling 3-month mean (last value)
    - Rolling 3-month std  (last value)
    - Trend slope (last 6 months linear fit)

    These are appended as extra features, expanding the feature
    dimension from 3 to 12 (3 original + 3 means + 3 stds + 3
    slopes).

    Args:
        sequences: Scaled array of shape ``(n, 12, 3)``.

    Returns:
        Enhanced array of shape ``(n, 12, 12)``.
    """
    n_samples, seq_len, n_features = sequences.shape
    enhanced = np.zeros((n_samples, seq_len, n_features * 4), dtype=np.float32)

    for i in range(n_samples):
        seq = sequences[i]  # (12, 3)
        enhanced[i, :, :n_features] = seq

        for t in range(seq_len):
            window_start = max(0, t - 2)
            window = seq[window_start : t + 1]

            # Rolling 3-month mean
            enhanced[i, t, n_features : n_features * 2] = window.mean(axis=0)

            # Rolling 3-month std
            enhanced[i, t, n_features * 2 : n_features * 3] = (
                window.std(axis=0) if len(window) > 1 else 0.0
            )

        # Trend slope (simple linear fit over last 6 months)
        trend_window = min(6, seq_len)
        x = np.arange(trend_window, dtype=np.float32)
        x_mean = x.mean()
        for f in range(n_features):
            y = seq[-trend_window:, f]
            y_mean = y.mean()
            denom = ((x - x_mean) ** 2).sum()
            slope = ((x - x_mean) * (y - y_mean)).sum() / denom if denom > 0 else 0.0
            enhanced[i, :, n_features * 3 + f] = slope

    logger.info(
        "Rolling stats computed — enhanced shape: %s",
        enhanced.shape,
    )
    return enhanced


def validate_sequences(sequences: np.ndarray) -> bool:
    """Post-engineering validation: no NaN, no Inf values.

    Args:
        sequences: Engineered 3D array.

    Returns:
        True if clean, False otherwise.
    """
    nan_count = int(np.isnan(sequences).sum())
    inf_count = int(np.isinf(sequences).sum())

    if nan_count > 0:
        logger.error("Validation FAILED: %d NaN values in sequences", nan_count)
        return False
    if inf_count > 0:
        logger.error("Validation FAILED: %d Inf values in sequences", inf_count)
        return False

    logger.info("Sequence validation passed — 0 NaN, 0 Inf")
    return True


def write_timeseries_feature_metadata(
    sequences: np.ndarray,
    config: dict,
) -> None:
    """Write time-series feature engineering metadata."""
    meta = {
        "generated_at": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "shape": list(sequences.shape),
        "n_sequences": int(sequences.shape[0]),
        "sequence_length": int(sequences.shape[1]),
        "n_features": int(sequences.shape[2]),
        "base_features": FEATURE_NAMES,
        "enhanced_features": [
            *FEATURE_NAMES,
            *[f"{f}_rolling_mean" for f in FEATURE_NAMES],
            *[f"{f}_rolling_std" for f in FEATURE_NAMES],
            *[f"{f}_trend_slope" for f in FEATURE_NAMES],
        ],
        "scaling": config.get("scaling", {}).get("timeseries", "none"),
        "version": "v1.0",
    }
    meta_path = PROCESSED_DIR / "timeseries_feature_metadata.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    logger.info("Time-series feature metadata written to %s", meta_path)


def build_timeseries_features() -> None:
    """Run the full time-series feature engineering pipeline."""
    config = load_feature_config()

    # Load raw sequences
    sequences = load_sequences()

    # Scale
    scaled = scale_sequences(sequences)

    # Compute rolling features
    enhanced = compute_rolling_stats(scaled)

    # Validate
    if not validate_sequences(enhanced):
        logger.error("Aborting — time-series feature validation failed")
        sys.exit(1)

    # Save
    out_path = PROCESSED_DIR / "timeseries_features.npy"
    np.save(out_path, enhanced)
    logger.info("Time-series features saved to %s", out_path)

    # Metadata
    write_timeseries_feature_metadata(enhanced, config)

    logger.info("Time-series feature engineering complete.")


if __name__ == "__main__":
    build_timeseries_features()
