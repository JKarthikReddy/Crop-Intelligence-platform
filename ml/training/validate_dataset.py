"""Dataset schema validation — runs before any training.

Loads schema contracts from configs/schema.yaml and validates that
raw CSV files contain all required columns.  If validation fails,
training is blocked with a clear error message.

Usage:
    python training/validate_dataset.py
    # or: make validate
"""

import logging
import sys
from pathlib import Path

import pandas as pd
import yaml

# ── Logging ──────────────────────────────────────────────────────
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "validate_dataset.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "configs" / "schema.yaml"
RAW_DIR = ROOT / "data" / "raw"


def load_schema() -> dict:
    """Load schema contracts from YAML config."""
    if not SCHEMA_PATH.exists():
        logger.error("Schema file not found: %s", SCHEMA_PATH)
        sys.exit(1)
    with open(SCHEMA_PATH) as f:
        return yaml.safe_load(f)


def validate_columns(df: pd.DataFrame, required: list[str], name: str) -> bool:
    """Check that all required columns exist in the DataFrame.

    Args:
        df: The DataFrame to validate.
        required: List of required column names.
        name: Human-readable dataset label for logging.

    Returns:
        True if valid, False if columns are missing.
    """
    missing = [col for col in required if col not in df.columns]
    if missing:
        logger.error("[%s] Missing columns: %s", name, missing)
        return False
    logger.info(
        "[%s] Schema valid — %d rows, %d columns", name, len(df), len(df.columns)
    )
    return True


def validate_tabular(schema: dict) -> bool:
    """Validate the tabular raw dataset against its schema."""
    path = RAW_DIR / "tabular_raw.csv"
    if not path.exists():
        logger.warning("Tabular raw file not found: %s — skipping", path)
        return True  # Not a failure if file doesn't exist yet

    df = pd.read_csv(path)
    required = schema["tabular_schema"]["required_columns"]
    return validate_columns(df, required, "tabular")


def validate_timeseries(schema: dict) -> bool:
    """Validate the time-series raw dataset against its schema."""
    path = RAW_DIR / "timeseries_raw.csv"
    if not path.exists():
        logger.warning("Time-series raw file not found: %s — skipping", path)
        return True

    df = pd.read_csv(path)
    required = schema["timeseries_schema"]["required_columns"]
    return validate_columns(df, required, "timeseries")


def main() -> None:
    """Run all schema validations."""
    logger.info("Starting dataset validation...")
    schema = load_schema()

    results = [
        validate_tabular(schema),
        validate_timeseries(schema),
    ]

    if all(results):
        logger.info("All dataset validations passed.")
    else:
        logger.error("Dataset validation FAILED — training blocked.")
        sys.exit(1)


if __name__ == "__main__":
    main()
