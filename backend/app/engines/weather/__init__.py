"""Weather Engine — meteorological intelligence and forecasting.

Provides historical climate data from NASA POWER, 5-day forecasts from
OpenWeather, ET0 evapotranspiration, and agricultural risk scoring.
"""

from app.engines.weather.service import WeatherEngineError, analyze_weather

__all__ = ["WeatherEngineError", "analyze_weather"]
