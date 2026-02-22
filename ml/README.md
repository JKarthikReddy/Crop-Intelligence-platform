# ML Service — Crop Intelligence Platform

## Purpose

Machine learning model training, experimentation, and evaluation pipelines for crop intelligence.

## Responsibilities

- Model training workflows (yield prediction, NDVI analysis)
- Data preprocessing pipelines
- Feature engineering
- Experiment tracking
- Model evaluation & metrics
- Export trained models for backend inference

## Does NOT Contain

- API endpoint logic
- Frontend components
- Production serving code
- Docker configuration files

## Tech Stack

- **Runtime:** Python 3.11+
- **ML Frameworks:** PyTorch, scikit-learn, XGBoost
- **Data:** Pandas, NumPy, GeoPandas
- **Remote Sensing:** Rasterio, GDAL
- **Experiment Tracking:** MLflow
- **Notebooks:** Jupyter

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
