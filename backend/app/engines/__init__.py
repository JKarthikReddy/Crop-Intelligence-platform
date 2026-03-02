"""Engines package — domain-driven intelligence modules.

Each engine is a self-contained domain module with:
- service.py  — business logic (pure, no FastAPI)
- schemas.py  — Pydantic request/response models
- router.py   — FastAPI endpoints
- __init__.py  — public API surface

Engine Map:
    Farmer App → API Gateway →
    ┌─────────────────────────┐
    │ Soil Engine              │
    │ Crop Engine              │
    │ Fertilizer Engine        │
    │ Weather Engine           │
    │ Disease Engine           │
    │ Market Engine            │
    └─────────────────────────┘
              ↓
    Advisory Aggregator → Farmer Dashboard
"""
