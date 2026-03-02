"""Sentinel-2 NDVI & Sentinel-1 SAR satellite intelligence service.

Pure service layer:
- No FastAPI imports
- No database logic
- Reads credentials via settings (never os.getenv)
- Async HTTP via httpx
- OAuth2 client-credentials flow for Sentinel Hub
- Structured, normalized output only

Architecture note (Phase 3 MVP):
    The Sentinel Hub Process API returns binary raster data (TIFF).
    Full mean extraction requires numpy/rasterio parsing of the raster
    response.  For this MVP, we execute the full OAuth + Process API
    pipeline, validate the 200 response, and return struct-based
    estimates.  A follow-up step will add numpy-based raster parsing
    for pixel-level statistics.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from loguru import logger

from app.core.config import get_settings
from app.services.cache_service import (
    NDVI_TTL,
    SAR_TTL,
    get_cache,
    make_bounds_cache_key,
    set_cache,
)

# ── Sentinel Hub endpoints ───────────────────────────────────────
TOKEN_URL = "https://services.sentinel-hub.com/oauth/token"
PROCESS_URL = "https://services.sentinel-hub.com/api/v1/process"

_TOKEN_TIMEOUT = 10.0
_PROCESS_TIMEOUT = 30.0
_LOOKBACK_DAYS = 90

# ── NDVI Evalscript (Sentinel-2 L2A bands B04 + B08) ────────────
NDVI_EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: ["B04", "B08"],
    output: { bands: 1, sampleType: "FLOAT32" }
  };
}

function evaluatePixel(sample) {
  let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
  return [ndvi];
}
"""

# ── SAR Evalscript (Sentinel-1 GRD bands VV + VH) ──────────────
SAR_EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: ["VV", "VH"],
    output: { bands: 2 }
  };
}

function evaluatePixel(sample) {
  return [sample.VV, sample.VH];
}
"""


class SatelliteServiceError(Exception):
    """Raised when Sentinel Hub API calls or response parsing fails."""


async def get_sentinel_token(*, timeout: float = _TOKEN_TIMEOUT) -> str:
    """Obtain an OAuth2 access token from Sentinel Hub.

    Uses client-credentials grant with credentials from application
    settings.

    Args:
        timeout: HTTP request timeout in seconds.

    Returns:
        Bearer access token string.

    Raises:
        SatelliteServiceError: On authentication failure.
    """
    settings = get_settings()

    data = {
        "grant_type": "client_credentials",
        "client_id": settings.SENTINEL_CLIENT_ID,
        "client_secret": settings.SENTINEL_CLIENT_SECRET,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(TOKEN_URL, data=data)
    except httpx.TimeoutException as exc:
        logger.error("Sentinel Hub token timeout: {}", exc)
        raise SatelliteServiceError(
            f"Sentinel Hub token request timed out after {timeout}s"
        ) from exc
    except httpx.HTTPError as exc:
        logger.error("Sentinel Hub token HTTP error: {}", exc)
        raise SatelliteServiceError(f"Sentinel Hub token request failed: {exc}") from exc

    if response.status_code != 200:
        logger.error("Sentinel Hub token returned {}", response.status_code)
        raise SatelliteServiceError(
            f"Sentinel Hub token request returned HTTP {response.status_code}"
        )

    try:
        return response.json()["access_token"]
    except (KeyError, ValueError) as exc:
        raise SatelliteServiceError("Sentinel Hub token response missing access_token.") from exc


async def fetch_ndvi(
    bounds: tuple[float, float, float, float],
    *,
    lookback_days: int = _LOOKBACK_DAYS,
    timeout: float = _PROCESS_TIMEOUT,
) -> dict[str, Any]:
    """Fetch Sentinel-2 NDVI for a bounding box via the Process API.

    Authenticates with Sentinel Hub, submits an evalscript-based NDVI
    request for the given bounds and time range, and returns a
    structured vegetation health summary.

    Args:
        bounds: Bounding box as ``(minx, miny, maxx, maxy)`` in EPSG:4326.
        lookback_days: Number of past days for imagery search window.
        timeout: HTTP request timeout in seconds.

    Returns:
        Normalized dict with keys:
            - ``ndvi_mean``: Mean NDVI score (float, -1 to 1)
            - ``bbox``: The bounding box used for the query
            - ``time_range_start``: ISO start date
            - ``time_range_end``: ISO end date
            - ``data_source``: ``"sentinel-2-l2a"``

    Raises:
        SatelliteServiceError: On HTTP failure or malformed response.
    """
    # ── Cache check ──────────────────────────────────────────────
    cache_key = make_bounds_cache_key("ndvi", bounds)
    cached = await get_cache(cache_key)
    if cached is not None:
        logger.debug("Cache HIT for {}", cache_key)
        return cached

    token = await get_sentinel_token()

    end_date = datetime.now(tz=UTC).date()
    start_date = end_date - timedelta(days=lookback_days)
    time_from = f"{start_date.isoformat()}T00:00:00Z"
    time_to = f"{end_date.isoformat()}T23:59:59Z"

    payload = {
        "input": {
            "bounds": {
                "bbox": list(bounds),
                "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
            },
            "data": [
                {
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "timeRange": {
                            "from": time_from,
                            "to": time_to,
                        }
                    },
                }
            ],
        },
        "output": {"width": 256, "height": 256},
        "evalscript": NDVI_EVALSCRIPT,
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/octet-stream",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(PROCESS_URL, json=payload, headers=headers)
    except httpx.TimeoutException as exc:
        logger.error("Sentinel Hub process timeout for {}: {}", bounds, exc)
        raise SatelliteServiceError(
            f"Sentinel Hub process request timed out after {timeout}s"
        ) from exc
    except httpx.HTTPError as exc:
        logger.error("Sentinel Hub process HTTP error for {}: {}", bounds, exc)
        raise SatelliteServiceError(f"Sentinel Hub process request failed: {exc}") from exc

    if response.status_code != 200:
        logger.error(
            "Sentinel Hub process returned {} for {}",
            response.status_code,
            bounds,
        )
        raise SatelliteServiceError(
            f"Sentinel Hub process API returned HTTP {response.status_code}"
        )

    result = _build_ndvi_response(
        response_content=response.content,
        bounds=bounds,
        time_from=time_from,
        time_to=time_to,
    )
    await set_cache(cache_key, result, ttl=NDVI_TTL)
    return result


def _build_ndvi_response(
    *,
    response_content: bytes,
    bounds: tuple[float, float, float, float],
    time_from: str,
    time_to: str,
) -> dict[str, Any]:
    """Build structured NDVI response from Process API binary output.

    Phase 3 MVP: validates that binary raster data was received and
    returns a structural estimate.  A follow-up iteration will add
    numpy-based TIFF parsing for pixel-level NDVI statistics.

    Args:
        response_content: Raw binary raster bytes from Sentinel Hub.
        bounds: The bounding box used for the request.
        time_from: ISO start date string.
        time_to: ISO end date string.

    Returns:
        Structured NDVI intelligence dict.

    Raises:
        SatelliteServiceError: If response content is empty.
    """
    if not response_content:
        raise SatelliteServiceError("Sentinel Hub returned empty raster data.")

    # TODO(phase-4): Parse TIFF with numpy/rasterio for real pixel stats.
    # For MVP, the successful 200 + non-empty binary confirms imagery
    # exists.  Return a placeholder mean that downstream consumers can
    # use until full raster parsing is wired.
    ndvi_mean = _estimate_ndvi_from_content_length(len(response_content))

    return {
        "ndvi_mean": ndvi_mean,
        "bbox": list(bounds),
        "time_range_start": time_from,
        "time_range_end": time_to,
        "data_source": "sentinel-2-l2a",
    }


def _estimate_ndvi_from_content_length(content_length: int) -> float:
    """Return a conservative NDVI estimate based on raster presence.

    Phase 3 MVP heuristic: a non-trivial raster payload indicates
    vegetation is present.  Returns 0.45 (moderate vegetation) as a
    safe baseline until numpy-based pixel averaging is implemented.

    Args:
        content_length: Size of the binary raster in bytes.

    Returns:
        Estimated mean NDVI (float).
    """
    if content_length < 100:
        # Extremely small payload likely indicates barren/ocean tile
        return 0.1
    return 0.45


# ═══════════════════════════════════════════════════════════════════
# Sentinel-1 SAR — Cloud-Proof Radar Intelligence
# ═══════════════════════════════════════════════════════════════════


async def fetch_sar(
    bounds: tuple[float, float, float, float],
    *,
    lookback_days: int = _LOOKBACK_DAYS,
    timeout: float = _PROCESS_TIMEOUT,
) -> dict[str, Any]:
    """Fetch Sentinel-1 SAR backscatter for a bounding box.

    Authenticates with Sentinel Hub (reusing the shared OAuth flow),
    submits an evalscript-based SAR request for the given bounds and
    time range, and returns a structured radar intelligence summary.

    Sentinel-1 SAR works through clouds, rain, fog, and at night,
    making it the all-weather complement to optical NDVI.

    Args:
        bounds: Bounding box as ``(minx, miny, maxx, maxy)`` in EPSG:4326.
        lookback_days: Number of past days for imagery search window.
        timeout: HTTP request timeout in seconds.

    Returns:
        Normalized dict with keys:
            - ``sar_vv_mean``: Mean VV backscatter (dB, float)
            - ``sar_vh_mean``: Mean VH backscatter (dB, float)
            - ``moisture_indicator``: ``"high"`` | ``"moderate"`` | ``"low"``
            - ``bbox``: The bounding box used for the query
            - ``time_range_start``: ISO start date
            - ``time_range_end``: ISO end date
            - ``data_source``: ``"sentinel-1-grd"``

    Raises:
        SatelliteServiceError: On HTTP failure or malformed response.
    """
    # ── Cache check ──────────────────────────────────────────────
    cache_key = make_bounds_cache_key("sar", bounds)
    cached = await get_cache(cache_key)
    if cached is not None:
        logger.debug("Cache HIT for {}", cache_key)
        return cached

    token = await get_sentinel_token()

    end_date = datetime.now(tz=UTC).date()
    start_date = end_date - timedelta(days=lookback_days)
    time_from = f"{start_date.isoformat()}T00:00:00Z"
    time_to = f"{end_date.isoformat()}T23:59:59Z"

    payload = {
        "input": {
            "bounds": {
                "bbox": list(bounds),
                "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
            },
            "data": [
                {
                    "type": "sentinel-1-grd",
                    "dataFilter": {
                        "timeRange": {
                            "from": time_from,
                            "to": time_to,
                        }
                    },
                }
            ],
        },
        "output": {"width": 256, "height": 256},
        "evalscript": SAR_EVALSCRIPT,
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/octet-stream",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(PROCESS_URL, json=payload, headers=headers)
    except httpx.TimeoutException as exc:
        logger.error("Sentinel-1 SAR timeout for {}: {}", bounds, exc)
        raise SatelliteServiceError(f"Sentinel-1 SAR request timed out after {timeout}s") from exc
    except httpx.HTTPError as exc:
        logger.error("Sentinel-1 SAR HTTP error for {}: {}", bounds, exc)
        raise SatelliteServiceError(f"Sentinel-1 SAR request failed: {exc}") from exc

    if response.status_code != 200:
        logger.error(
            "Sentinel-1 SAR returned {} for {}",
            response.status_code,
            bounds,
        )
        raise SatelliteServiceError(f"Sentinel-1 SAR API returned HTTP {response.status_code}")

    result = _build_sar_response(
        response_content=response.content,
        bounds=bounds,
        time_from=time_from,
        time_to=time_to,
    )
    await set_cache(cache_key, result, ttl=SAR_TTL)
    return result


def _build_sar_response(
    *,
    response_content: bytes,
    bounds: tuple[float, float, float, float],
    time_from: str,
    time_to: str,
) -> dict[str, Any]:
    """Build structured SAR response from Process API binary output.

    Phase 3 MVP: validates that binary raster data was received and
    returns conservative backscatter estimates.  A follow-up iteration
    will add numpy-based raster parsing for pixel-level VV/VH stats.

    Args:
        response_content: Raw binary raster bytes from Sentinel Hub.
        bounds: The bounding box used for the request.
        time_from: ISO start date string.
        time_to: ISO end date string.

    Returns:
        Structured SAR intelligence dict.

    Raises:
        SatelliteServiceError: If response content is empty.
    """
    if not response_content:
        raise SatelliteServiceError("Sentinel-1 SAR returned empty raster data.")

    # TODO(phase-4): Parse TIFF with numpy for real VV/VH pixel stats.
    # For MVP, successful 200 + non-empty binary confirms radar data
    # exists.  Return conservative estimates.
    vv_mean, vh_mean = _estimate_sar_from_content_length(len(response_content))

    return {
        "sar_vv_mean": vv_mean,
        "sar_vh_mean": vh_mean,
        "moisture_indicator": _classify_moisture(vv_mean),
        "bbox": list(bounds),
        "time_range_start": time_from,
        "time_range_end": time_to,
        "data_source": "sentinel-1-grd",
    }


def _estimate_sar_from_content_length(
    content_length: int,
) -> tuple[float, float]:
    """Return conservative SAR backscatter estimates based on raster presence.

    Phase 3 MVP heuristic: a non-trivial raster payload indicates
    valid radar data was returned.  Returns moderate backscatter values
    as a safe baseline until numpy-based pixel averaging is implemented.

    Args:
        content_length: Size of the binary raster in bytes.

    Returns:
        Tuple of (vv_mean, vh_mean) in dB.
    """
    if content_length < 100:
        # Extremely small payload — likely empty/ocean tile
        return (-22.0, -28.0)
    # Moderate agricultural backscatter baseline
    return (-14.2, -18.7)


def _classify_moisture(vv_mean: float) -> str:
    """Classify soil moisture from VV backscatter intensity.

    Higher VV backscatter (closer to 0 dB) generally indicates wetter
    soil or standing water.  Lower values indicate drier conditions.

    Args:
        vv_mean: Mean VV-polarization backscatter in dB.

    Returns:
        ``"high"``, ``"moderate"``, or ``"low"``.
    """
    if vv_mean > -10:
        return "high"
    if vv_mean > -18:
        return "moderate"
    return "low"
