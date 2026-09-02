"""
Thin client for IMD's real API gateway at https://api.imd.gov.in.

This is a genuine, documented government API (see
https://api.imd.gov.in/public/api_reference.html) — not a mock. Two hard
requirements before it will actually return data for you:

1. **IP whitelisting.** IMD does not use an API key — access is controlled
   by whitelisting the calling server's IP address. Request this at
   https://api.imd.gov.in/public/index.php before deploying anywhere. Until
   your IP is whitelisted, every call here will fail (typically a timeout
   or a non-200 response) — that's expected, not a bug in this client.
2. **Correct station/district IDs.** IMD identifies locations by numeric
   "Obj_ID" (districts) or short station call signs (e.g. "NDL" for New
   Delhi) — there's no public "list all IDs" endpoint in the reference
   docs. See app/ingestion/zone_mapping.py for how to find the real IDs
   for your zones; that file ships with placeholders, deliberately, rather
   than guessed numbers.

What this does NOT provide (don't expect it to):
- **Soil moisture.** IMD is a meteorological department; soil moisture
  needs a different source (ground sensors, ISRO/Bhuvan, NASA SMAP).
- **A numeric rainfall forecast.** IMD's district warnings are categorical
  ("Heavy Rain", colour-coded), not a literal "+64mm" figure — see
  get_district_warning() below, which returns that category as-is.
"""
import logging
from typing import Optional

import requests

from app.config import settings

logger = logging.getLogger("sentry.imd_client")

DEFAULT_TIMEOUT = 10  # seconds


class IMDRequestError(Exception):
    """Raised when an IMD API call fails — network error, non-200, or
    unexpected response shape. Callers should catch this per-zone so one
    station being down doesn't abort an entire ingestion run."""


def _get(path: str, params: Optional[dict] = None) -> dict | list:
    url = f"{settings.imd_base_url}{path}"
    try:
        resp = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise IMDRequestError(f"IMD request failed: GET {url} params={params} — {e}") from e
    except ValueError as e:
        raise IMDRequestError(f"IMD returned non-JSON response: GET {url} — {e}") from e


def get_current_weather(station_id: str) -> dict:
    """Current Weather API — includes 'Last 24 hrs Rainfall' in mm, which is
    the field this project actually uses. Also returns temperature, wind,
    humidity, MSLP — unused here but present in the response.
    """
    data = _get("/current_wx", params={"id": station_id})
    if isinstance(data, list):
        if not data:
            raise IMDRequestError(f"IMD returned no data for station '{station_id}'")
        return data[0]
    return data


def get_district_rainfall(district_obj_id: str) -> dict:
    """District-wise Rainfall API — daily/weekly/monthly actual vs. normal
    rainfall for a district, as an alternative or cross-check to the
    per-station current weather reading.
    """
    data = _get("/districtrainfall", params={"id": district_obj_id})
    if isinstance(data, list):
        if not data:
            raise IMDRequestError(f"IMD returned no rainfall data for district '{district_obj_id}'")
        return data[0]
    return data


def get_district_warning(district_obj_id: str) -> dict:
    """District-wise Warnings API — 5-day categorical severity (e.g. 'Heavy
    Rain', 'Very Heavy Rain') with colour codes, NOT a numeric forecast.
    """
    data = _get("/districtwarning", params={"id": district_obj_id})
    if isinstance(data, list):
        if not data:
            raise IMDRequestError(f"IMD returned no warning data for district '{district_obj_id}'")
        return data[0]
    return data
