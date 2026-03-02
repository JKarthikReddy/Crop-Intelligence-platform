"""Advisory Aggregator router — unified farm intelligence endpoint."""

from fastapi import APIRouter, HTTPException

from app.engines.advisory.schemas import AdvisoryRequest, AdvisoryResponse
from app.engines.advisory.service import AdvisoryEngineError, generate_advisory

router = APIRouter(prefix="/advisory", tags=["Advisory Aggregator"])


@router.post("/full", response_model=AdvisoryResponse)
async def full_advisory(payload: AdvisoryRequest) -> AdvisoryResponse:
    """Generate comprehensive farm advisory by orchestrating all 6 engines.

    Single endpoint that invokes Soil, Weather, Crop, Fertilizer,
    Disease, and Market engines in parallel. Gracefully degrades
    if any engine fails. Returns unified intelligence with
    prioritized action items.
    """
    try:
        result = await generate_advisory(
            lat=payload.lat,
            lon=payload.lon,
            crop_type=payload.crop_type,
            planting_date=payload.planting_date,
            target_yield=payload.target_yield,
            area_hectares=payload.area_hectares,
            region=payload.region,
            bounds=payload.bounds,
        )
        return AdvisoryResponse(**result)
    except AdvisoryEngineError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
