"""Fertilizer Engine router — REST endpoints for fertilizer intelligence."""

from fastapi import APIRouter, HTTPException

from app.engines.fertilizer.schemas import FertilizerRequest, FertilizerResponse
from app.engines.fertilizer.service import FertilizerEngineError, recommend_fertilizer

router = APIRouter(prefix="/fertilizer", tags=["Fertilizer Engine"])


@router.post("/recommend", response_model=FertilizerResponse)
async def fertilizer_recommendation(payload: FertilizerRequest) -> FertilizerResponse:
    """Get NPK recommendation, product selection, schedule, and cost estimate.

    Accepts crop type, target yield, and soil data from Soil Engine.
    Returns optimal fertilizer plan with application schedule.
    """
    try:
        result = await recommend_fertilizer(
            crop_type=payload.crop_type,
            target_yield=payload.target_yield,
            soil_ph=payload.soil_ph,
            organic_carbon=payload.organic_carbon,
            clay_percent=payload.clay_percent,
            area_hectares=payload.area_hectares,
        )
        return FertilizerResponse(**result)
    except FertilizerEngineError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
