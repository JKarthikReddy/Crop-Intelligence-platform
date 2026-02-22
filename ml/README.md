# ML Module — Crop Intelligence Platform

## Purpose

- Model training & evaluation
- Experimentation & feature engineering
- Model artifact generation
- Hyperparameter tuning

## Does NOT Contain

- API logic (lives in `/backend`)
- Frontend code (lives in `/frontend`)
- Docker configuration (lives in `/docker`)
- Production serving endpoints

## Directory Layout

```
ml/
├── notebooks/        # Research only — EDA, visualization, exploration
├── data/             # Raw + processed datasets (git-ignored)
├── models/           # Trained model artifacts (git-ignored)
├── training/         # Production training scripts
├── utils/            # Shared ML utilities
├── configs/          # YAML/JSON experiment configs
├── mlflow/           # Future MLflow integration
├── requirements.txt  # ML-specific Python dependencies
└── README.md
```

## Rules

1. **Notebooks are disposable** — research only, never production logic.
2. **Training scripts are production** — reproducible, config-driven, tested.
3. **No model weights in Git** — `models/` is git-ignored.
4. **No datasets in Git** — `data/` is git-ignored.
5. **Config-driven training** — all hyperparameters in `configs/`.
6. **Isolated environment** — ML has its own `venv` and `requirements.txt`.

## Tech Stack

- **Runtime:** Python 3.12+
- **ML Frameworks:** XGBoost, scikit-learn
- **Data:** Pandas, NumPy
- **Remote Sensing:** Rasterio, GDAL (via backend)
- **Experiment Tracking:** MLflow (future)
- **Notebooks:** Jupyter

## Quick Start

```bash
cd ml
python -m venv venv
source venv/bin/activate   # Linux/Mac
.\venv\Scripts\Activate    # Windows
pip install -r requirements.txt
python training/train_xgboost.py
```

## Directory Structure

```
ml/
├── notebooks/       # Jupyter experiments
├── src/             # Training source code
├── data/            # Local data (git-ignored)
├── models/          # Trained model artifacts (git-ignored)
├── configs/         # Training configurations
└── requirements.txt
```

## Getting Started

```bash
cd ml
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
jupyter notebook
```

## Ownership

ML / Data Science Team
