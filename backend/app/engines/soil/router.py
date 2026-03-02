"""Soil Engine router — REST endpoints for soil intelligence."""

from fastapi import APIRouter, HTTPException

from app.engines.soil.schemas import SoilAnalysisRequest, SoilAnalysisResponse
from app.engines.soil.service import SoilEngineError, analyze_soil

router = APIRouter(prefix="/soil", tags=["Soil Engine"])


@router.post("/analyze", response_model=SoilAnalysisResponse)
async def soil_analysis(payload: SoilAnalysisRequest) -> SoilAnalysisResponse:
    """Analyze soil at a geographic coordinate.

    Returns pH classification, texture, nutrient profile,
    soil health index (0-100), and actionable recommendations.
    """
    try:
        result = await analyze_soil(payload.lat, payload.lon)
        return SoilAnalysisResponse(**result)
    except SoilEngineError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
