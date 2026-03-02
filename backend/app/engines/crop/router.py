"""Crop Engine router — REST endpoints for crop intelligence."""

from fastapi import APIRouter, HTTPException

from app.engines.crop.schemas import CropAnalysisRequest, CropAnalysisResponse
from app.engines.crop.service import CropEngineError, analyze_crop

router = APIRouter(prefix="/crop", tags=["Crop Engine"])


@router.post("/analyze", response_model=CropAnalysisResponse)
async def crop_analysis(payload: CropAnalysisRequest) -> CropAnalysisResponse:
    """Analyze crop health, yield forecast, and growth status.

    Returns vegetation health (NDVI), moisture status, yield prediction,
    harvest window, and crop management recommendations.
    """
    try:
        result = await analyze_crop(
            lat=payload.lat,
            lon=payload.lon,
            bounds=payload.bounds,
            crop_type=payload.crop_type,
            planting_date=payload.planting_date,
        )
        return CropAnalysisResponse(**result)
    except CropEngineError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
