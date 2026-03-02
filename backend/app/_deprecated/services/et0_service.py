"""ET0 evapotranspiration and water stress modeling service.

Pure computational layer:
- No external API calls
- No database logic
- No environment access
- Deterministic calculations
- Based on simplified FAO-56 Penman-Monteith empirical model

Computes reference evapotranspiration (ET0) and water stress risk
from temperature, solar radiation, and wind speed inputs — typically
sourced from the NASA POWER weather service.
"""

from typing import Any


def calculate_et0(
    temperature: float,
    solar_radiation: float,
    wind_speed: float,
) -> float:
    """Estimate daily reference evapotranspiration (ET0).

    Uses a simplified empirical model derived from the FAO-56
    Penman-Monteith equation.  Suitable for MVP agronomic decision
    support; a follow-up iteration will implement the full
    Penman-Monteith with humidity and elevation corrections.

    Args:
        temperature: Mean air temperature at 2 m (°C).
        solar_radiation: Mean surface shortwave downward radiation
            (MJ/m²/day).
        wind_speed: Mean wind speed at 2 m (m/s).

    Returns:
        Estimated daily ET0 in mm/day, rounded to 2 decimal places.
    """
    et0 = 0.408 * solar_radiation + 0.0023 * (temperature + 17.8) * (wind_speed + 1)
    return round(et0, 2)


def water_stress_indicator(et0: float) -> str:
    """Classify water stress risk from ET0 value.

    Higher ET0 means more water is being lost through
    evapotranspiration, indicating greater irrigation demand.

    Args:
        et0: Daily reference evapotranspiration in mm/day.

    Returns:
        ``"high"`` (ET0 > 6), ``"moderate"`` (ET0 > 4), or ``"low"``.
    """
    if et0 > 6:
        return "high"
    if et0 > 4:
        return "moderate"
    return "low"


def build_water_model(climate: dict[str, Any]) -> dict[str, Any] | None:
    """Build the water model section from climate data.

    Convenience function used by the intelligence engine.  Returns
    ``None`` if the required climate fields are missing (graceful
    degradation when weather service failed).

    Args:
        climate: Normalized climate dict from the weather service,
            expected to contain ``temperature_avg_30d``,
            ``solar_radiation_avg_30d``, and ``wind_speed_avg_30d``.

    Returns:
        Water model dict with ``et0_estimate`` and
        ``water_stress_risk``, or None if inputs are insufficient.
    """
    if climate is None:
        return None

    temp = climate.get("temperature_avg_30d")
    solar = climate.get("solar_radiation_avg_30d")
    wind = climate.get("wind_speed_avg_30d")

    if temp is None or solar is None or wind is None:
        return None

    et0 = calculate_et0(temp, solar, wind)

    return {
        "et0_estimate": et0,
        "water_stress_risk": water_stress_indicator(et0),
    }
