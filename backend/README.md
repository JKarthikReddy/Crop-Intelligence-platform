# Backend Service — Crop Intelligence Platform

## Purpose

Core API and geospatial processing service for the Crop Intelligence Platform.

## Responsibilities

- FastAPI REST APIs
- Geospatial processing (GDAL, PostGIS)
- Database interactions (PostgreSQL + PostGIS)
- ML inference integration (model serving)
- Authentication & authorization

## Does NOT Contain

- Frontend logic
- UI components
- Training notebooks
- Docker configuration files

## Tech Stack

- **Runtime:** Python 3.11+
- **Framework:** FastAPI
- **Geospatial:** GDAL, Rasterio, GeoPandas, PostGIS
- **Database:** PostgreSQL 15+ with PostGIS extension
- **ORM:** SQLAlchemy 2.0
- **Task Queue:** Celery + Redis

## Getting Started

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Ownership

Backend Engineering Team
