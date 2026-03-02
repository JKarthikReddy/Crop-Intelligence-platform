"""Soil Engine router — REST endpoints for soil diagnostics."""

from fastapi import APIRouter, HTTPException

from app.engines.soil.schemas import SoilAnalysisRequest, SoilAnalysisResponse
from app.engines.soil.service import SoilEngineError, analyze_soil

router = APIRouter(prefix="/soil", tags=["Soil Engine"])


@router.post("/analyze", response_model=SoilAnalysisResponse)
async def soil_analysis(payload: SoilAnalysisRequest) -> SoilAnalysisResponse:
    """Diagnose soil health from farmer-provided soil test data.

    Accepts NPK values, pH, and soil type; returns health score,
    deficiencies, nutrient profiles, and amendment recommendations.
    """
    try:
        result = analyze_soil(
            nitrogen=payload.nitrogen,
            phosphorus=payload.phosphorus,
            potassium=payload.potassium,
            ph=payload.ph,
            soil_type=payload.soil_type.value,
        )
        return SoilAnalysisResponse(**result)
    except SoilEngineError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
