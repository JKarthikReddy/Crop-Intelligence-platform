"""Market Engine router — REST endpoints for market intelligence."""

from fastapi import APIRouter, HTTPException

from app.engines.market.schemas import MarketRequest, MarketResponse
from app.engines.market.service import MarketEngineError, analyze_market

router = APIRouter(prefix="/market", tags=["Market Engine"])


@router.post("/analyze", response_model=MarketResponse)
async def market_analysis(payload: MarketRequest) -> MarketResponse:
    """Get market prices, seasonal patterns, profitability, and sell advice.

    Accepts crop type, region, yield estimate, and production costs.
    Returns actionable market intelligence.
    """
    try:
        result = await analyze_market(
            crop_type=payload.crop_type,
            region=payload.region,
            estimated_yield_tons=payload.estimated_yield_tons,
            area_hectares=payload.area_hectares,
            production_cost_usd=payload.production_cost_usd,
        )
        return MarketResponse(**result)
    except MarketEngineError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
