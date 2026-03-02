"""Disease Engine router — REST endpoints for disease risk intelligence."""

from fastapi import APIRouter, HTTPException

from app.engines.disease.schemas import DiseaseRequest, DiseaseResponse
from app.engines.disease.service import DiseaseEngineError, assess_disease_risk

router = APIRouter(prefix="/disease", tags=["Disease Engine"])


@router.post("/assess", response_model=DiseaseResponse)
async def disease_assessment(payload: DiseaseRequest) -> DiseaseResponse:
    """Assess disease and pest risk for given crop and environmental conditions.

    Accepts weather data, crop NDVI, soil pH, and growth stage.
    Returns ranked disease risks with prevention plan.
    """
    try:
        result = await assess_disease_risk(
            crop_type=payload.crop_type,
            growth_stage=payload.growth_stage,
            avg_temperature=payload.avg_temperature,
            avg_humidity=payload.avg_humidity,
            recent_rainfall_mm=payload.recent_rainfall_mm,
            ndvi_mean=payload.ndvi_mean,
            soil_ph=payload.soil_ph,
        )
        return DiseaseResponse(**result)
    except DiseaseEngineError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
