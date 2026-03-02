"""Weather Engine router — REST endpoints for weather intelligence."""

from fastapi import APIRouter, HTTPException

from app.engines.weather.schemas import WeatherAnalysisRequest, WeatherAnalysisResponse
from app.engines.weather.service import WeatherEngineError, analyze_weather

router = APIRouter(prefix="/weather", tags=["Weather Engine"])


@router.post("/analyze", response_model=WeatherAnalysisResponse)
async def weather_analysis(payload: WeatherAnalysisRequest) -> WeatherAnalysisResponse:
    """Analyze weather conditions for a geographic coordinate.

    Returns 30-day climate history, 5-day forecast, ET0 water model,
    risk assessment, and actionable recommendations.
    """
    try:
        result = await analyze_weather(payload.lat, payload.lon)
        return WeatherAnalysisResponse(**result)
    except WeatherEngineError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
