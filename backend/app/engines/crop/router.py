"""Crop Recommendation Engine router — REST endpoints."""

from fastapi import APIRouter, HTTPException

from app.engines.crop.schemas import (
    CropRecommendationRequest,
    CropRecommendationResponse,
)
from app.engines.crop.service import CropEngineError, recommend_crops

router = APIRouter(prefix="/crop", tags=["Crop Engine"])


@router.post("/analyze", response_model=CropRecommendationResponse)
def crop_recommendation(payload: CropRecommendationRequest) -> CropRecommendationResponse:
    """Recommend the best crops based on soil, weather, and location.

    Performs region filtering, feature-vector scoring, and ranking
    to produce a recommended crop with confidence score, alternatives,
    and explainable reasoning.
    """
    try:
        result = recommend_crops(
            nitrogen=payload.soil_data.nitrogen,
            phosphorus=payload.soil_data.phosphorus,
            potassium=payload.soil_data.potassium,
            ph=payload.soil_data.ph,
            temperature=payload.weather_data.temperature,
            humidity=payload.weather_data.humidity,
            rainfall=payload.weather_data.rainfall,
            location=payload.location,
            season=payload.season.value if payload.season else None,
            soil_health=payload.soil_data.soil_health,
        )
        return CropRecommendationResponse(**result)
    except CropEngineError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
