"""XGBoost yield prediction training script — config-driven."""

import json
import sys
from pathlib import Path

import joblib
import pandas as pd
import yaml
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor


def load_config(config_path: str = "../configs/xgboost.yaml") -> dict:
    """Load experiment configuration from YAML."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_data(config: dict) -> pd.DataFrame:
    """Load training data from path specified in config."""
    data_path = config["data"]["input_path"]
    if not Path(data_path).exists():
        print(f"[WARN] Data file not found: {data_path}")
        print("[INFO] Generating synthetic sample data for demonstration...")
        return generate_sample_data()
    return pd.read_csv(data_path)


def generate_sample_data() -> pd.DataFrame:
    """Generate synthetic crop yield data for development/testing."""
    import numpy as np

    rng = np.random.default_rng(42)
    n = 500
    return pd.DataFrame(
        {
            "temperature": rng.uniform(15, 40, n),
            "rainfall": rng.uniform(200, 1200, n),
            "soil_ph": rng.uniform(5.5, 8.0, n),
            "ndvi": rng.uniform(0.2, 0.9, n),
            "yield": rng.uniform(1.5, 8.0, n),
        }
    )


def train(config: dict) -> None:
    """Train XGBoost model with config-driven parameters."""
    df = load_data(config)
    target = config["data"]["target_column"]

    X = df.drop(columns=[target])
    y = df[target]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=config["data"]["test_size"], random_state=42
    )

    model_params = config["model"]
    model = XGBRegressor(**model_params)
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    metrics = {
        "r2": round(r2_score(y_test, y_pred), 4),
        "mae": round(mean_absolute_error(y_test, y_pred), 4),
        "rmse": round(mean_squared_error(y_test, y_pred, squared=False), 4),
    }
    print(f"[METRICS] R²={metrics['r2']}  MAE={metrics['mae']}  RMSE={metrics['rmse']}")

    # Save model
    model_path = Path(config["output"]["model_path"])
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    print(f"[SAVED] Model → {model_path}")

    # Save metrics
    metrics_path = Path(config["output"]["metrics_path"])
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"[SAVED] Metrics → {metrics_path}")


if __name__ == "__main__":
    config_file = sys.argv[1] if len(sys.argv) > 1 else "../configs/xgboost.yaml"
    cfg = load_config(config_file)
    train(cfg)
