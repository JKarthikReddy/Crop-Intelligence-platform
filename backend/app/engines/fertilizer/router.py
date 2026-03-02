"""Fertilizer Engine router — REST endpoints for fertilizer intelligence."""

from fastapi import APIRouter, HTTPException

from app.engines.fertilizer.schemas import FertilizerRequest, FertilizerResponse
from app.engines.fertilizer.service import FertilizerEngineError, recommend_fertilizer

router = APIRouter(prefix="/fertilizer", tags=["Fertilizer Engine"])


@router.post("/recommend", response_model=FertilizerResponse)
async def fertilizer_recommendation(payload: FertilizerRequest) -> FertilizerResponse:
    """Deficiency-driven fertilizer recommendation.

    Accepts soil diagnostics (deficiencies, health, pH) from Soil Engine,
    selected crop from Crop Engine, and optional farm area from the farmer.
    Returns optimized fertilizer list, quantities, schedule, and advisory notes.
    """
    try:
        result = recommend_fertilizer(
            deficiencies=payload.soil_report.deficiencies,
            soil_health=payload.soil_report.soil_health,
            ph_status=payload.soil_report.ph_status,
            selected_crop=payload.selected_crop,
            land_area=payload.land_area,
            unit=payload.unit.value,
        )
        return FertilizerResponse(**result)
    except FertilizerEngineError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
