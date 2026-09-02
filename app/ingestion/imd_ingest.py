"""
Real IMD data ingestion. Pulls each mapped zone's current rainfall and
district warning from IMD's actual API and writes them as new
SensorReading / WeatherWarning rows.

Requires:
- Your server's IP whitelisted with IMD (see app/ingestion/imd_client.py)
- Real station/district IDs configured in app/ingestion/zone_mapping.py
  (ships with placeholders — every zone is skipped, loudly, until configured)

Usage:
    python -m app.ingestion.imd_ingest
"""
import logging
from datetime import datetime

from app.database import SessionLocal
from app import models
from app.ingestion.imd_client import get_current_weather, get_district_warning, IMDRequestError
from app.ingestion.zone_mapping import ZONE_TO_IMD, is_configured

logger = logging.getLogger("sentry.imd_ingest")


def _parse_rainfall_mm(raw: str) -> float:
    """IMD reports 'NIL' for no rain rather than 0 — normalize that, and be
    defensive about anything else unparseable rather than crash the run."""
    if raw is None:
        raise ValueError("missing rainfall value")
    raw = str(raw).strip()
    if raw.upper() in ("NIL", "N/A", "", "-"):
        return 0.0
    return float(raw)


def ingest_rainfall_and_warnings(db) -> dict:
    zones = db.query(models.Zone).all()
    ingested = []
    skipped = []

    for zone in zones:
        if not is_configured(zone.name):
            skipped.append({"zone": zone.name, "reason": "no real IMD IDs configured in zone_mapping.py"})
            continue

        mapping = ZONE_TO_IMD[zone.name]

        # Rainfall — from Current Weather API
        try:
            weather = get_current_weather(mapping["station_id"])
            rainfall_mm = _parse_rainfall_mm(weather.get("Last 24 hrs Rainfall"))
            db.add(models.SensorReading(
                zone_id=zone.id,
                rainfall_mm_24h=rainfall_mm,
                soil_moisture_pct=None,  # not an IMD data source — see module docstring
                source="imd",
                recorded_at=datetime.utcnow(),
            ))
            ingested.append({"zone": zone.name, "rainfall_mm_24h": rainfall_mm})
        except (IMDRequestError, ValueError, KeyError) as e:
            logger.warning("Rainfall ingest failed for %s: %s", zone.name, e)
            skipped.append({"zone": zone.name, "reason": f"rainfall fetch failed: {e}"})

        # Warning — from District Warnings API (categorical, not numeric)
        try:
            warning = get_district_warning(mapping["district_obj_id"])
            db.add(models.WeatherWarning(
                zone_id=zone.id,
                source="IMD",
                day1_warning=warning.get("Day_1"),
                day1_color=warning.get("Day1_Color"),
                day2_warning=warning.get("Day_2"),
                day2_color=warning.get("Day2_Color"),
                issued_date=warning.get("Date"),
                fetched_at=datetime.utcnow(),
            ))
        except (IMDRequestError, KeyError) as e:
            logger.warning("Warning ingest failed for %s: %s", zone.name, e)
            # Not fatal to the run — rainfall may have succeeded even if this didn't.

    db.commit()
    return {"ingested": len(ingested), "zones": ingested, "skipped": skipped}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db = SessionLocal()
    try:
        result = ingest_rainfall_and_warnings(db)
        print(f"Ingested {result['ingested']} zone(s).")
        if result["skipped"]:
            print(f"Skipped {len(result['skipped'])} zone(s):")
            for s in result["skipped"]:
                print(f"  - {s['zone']}: {s['reason']}")
    finally:
        db.close()
