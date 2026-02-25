"""Config-driven tabular feature engineering pipeline.

Loads the processed tabular dataset, applies formula-based feature
transformations defined in ``configs/features.yaml``, fits a
StandardScaler, and saves the feature-ready dataset plus the
scaler artifact for inference reuse.

Usage:
    python training/feature_engineering.py
    # or: make features
"""

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.preprocessing import StandardScaler

try:
    import joblib
except ImportError:  # pragma: no cover
    from sklearn.externals import joblib  # type: ignore[attr-defined]

# ── Logging ──────────────────────────────────────────────────────
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "feature_engineering.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "features.yaml"
PROCESSED_DIR = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "models"


def load_feature_config() -> dict:
    """Load feature engineering configuration from YAML."""
    if not CONFIG_PATH.exists():
        logger.error("Feature config not found: %s", CONFIG_PATH)
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)
    logger.info(
        "Loaded feature config with %d features",
        len(config.get("tabular_features", {})),
    )
    return config


def apply_formula(df: pd.DataFrame, formula: str) -> pd.Series:
    """Safely evaluate a formula against DataFrame columns.

    Only column names from the DataFrame are exposed to ``eval``,
    preventing arbitrary code execution.

    Args:
        df: Source DataFrame.
        formula: String formula referencing column names.

    Returns:
        Computed Series.
    """
    allowed = df.to_dict(orient="series")
    return eval(formula, {"__builtins__": {}}, allowed)  # noqa: S307


def engineer_tabular_features(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Apply all configured feature transformations.

    Args:
        df: Processed tabular DataFrame.
        config: Parsed features.yaml configuration.

    Returns:
        DataFrame with engineered features added and drop columns
        removed.
    """
    tabular_features = config.get("tabular_features", {})

    for feature_name, definition in tabular_features.items():
        formula = definition["formula"]
        df[feature_name] = apply_formula(df, formula)
        logger.info("  + %s = %s", feature_name, formula)

    # Drop non-feature columns
    drop_cols = config.get("drop_columns", [])
    if drop_cols:
        df = df.drop(columns=drop_cols, errors="ignore")
        logger.info("Dropped columns: %s", drop_cols)

    return df


def fit_and_save_scaler(df: pd.DataFrame) -> pd.DataFrame:
    """Fit a StandardScaler on numeric columns and persist it.

    The scaler is saved to ``models/tabular_scaler.pkl`` so that
    the exact same transformation can be applied during inference.

    Args:
        df: Feature-engineered DataFrame.

    Returns:
        Scaled DataFrame with the same column names.
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    scaler = StandardScaler()
    df[numeric_cols] = scaler.fit_transform(df[numeric_cols])

    scaler_path = MODELS_DIR / "tabular_scaler.pkl"
    joblib.dump(scaler, scaler_path)
    logger.info(
        "StandardScaler fitted and saved to %s (%d features)",
        scaler_path,
        len(numeric_cols),
    )

    return df


def validate_features(df: pd.DataFrame) -> bool:
    """Post-engineering validation: no NaN, no Inf values.

    Args:
        df: Engineered DataFrame.

    Returns:
        True if clean, False otherwise.
    """
    nan_count = df.isna().sum().sum()
    inf_count = np.isinf(df.select_dtypes(include=[np.number])).sum().sum()

    if nan_count > 0:
        logger.error("Feature validation FAILED: %d NaN values detected", nan_count)
        return False
    if inf_count > 0:
        logger.error("Feature validation FAILED: %d Inf values detected", inf_count)
        return False

    logger.info("Feature validation passed — 0 NaN, 0 Inf")
    return True


def write_feature_metadata(df: pd.DataFrame, config: dict) -> None:
    """Write feature engineering run metadata."""
    meta = {
        "generated_at": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "feature_count": len(df.columns),
        "rows": len(df),
        "engineered_features": list(config.get("tabular_features", {}).keys()),
        "dropped_columns": config.get("drop_columns", []),
        "scaling": config.get("scaling", {}).get("tabular", "none"),
        "version": "v1.0",
    }
    meta_path = PROCESSED_DIR / "feature_metadata.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    logger.info("Feature metadata written to %s", meta_path)


def build_tabular_features() -> None:
    """Run the full tabular feature engineering pipeline."""
    input_path = PROCESSED_DIR / "tabular.csv"
    if not input_path.exists():
        logger.error(
            "Processed dataset not found: %s — run 'make build' first", input_path
        )
        sys.exit(1)

    logger.info("Loading processed dataset from %s", input_path)
    df = pd.read_csv(input_path)
    logger.info("Input shape: %d rows × %d columns", len(df), len(df.columns))

    config = load_feature_config()

    # Engineer features
    df = engineer_tabular_features(df, config)
    logger.info(
        "Post-engineering shape: %d rows × %d columns", len(df), len(df.columns)
    )

    # Validate
    if not validate_features(df):
        logger.error("Aborting — feature validation failed")
        sys.exit(1)

    # Scale
    df = fit_and_save_scaler(df)

    # Save
    out_path = PROCESSED_DIR / "tabular_features.csv"
    df.to_csv(out_path, index=False)
    logger.info("Feature-ready dataset saved to %s", out_path)

    # Metadata
    write_feature_metadata(df, config)

    logger.info("Tabular feature engineering complete.")


if __name__ == "__main__":
    build_tabular_features()
