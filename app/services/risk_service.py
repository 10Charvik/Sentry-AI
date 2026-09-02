from datetime import datetime

from sqlalchemy.orm import Session

from app import models
from app.risk_utils import severity_for
from app.ml.predict import predict_risk


def recompute_all_zones(db: Session) -> dict:
    """Re-scores every zone using the trained model and its latest sensor
    reading. Plain function (no FastAPI dependencies) so it can be called
    from an HTTP route, a background scheduler loop, or a one-off script
    identically.

    Raises FileNotFoundError if the model hasn't been trained yet
    (see app/ml/train.py) — callers decide how to surface that.
    """
    zones = db.query(models.Zone).all()
    updated = []
    skipped = []

    for zone in zones:
        latest = (
            db.query(models.SensorReading)
            .filter(models.SensorReading.zone_id == zone.id)
            .order_by(models.SensorReading.recorded_at.desc())
            .first()
        )
        if not latest:
            skipped.append({"zone_id": zone.id, "name": zone.name, "reason": "no sensor reading yet"})
            continue

        soil_moisture = latest.soil_moisture_pct
        if soil_moisture is None:
            # IMD-sourced readings carry rainfall but not soil moisture — fall
            # back to the most recent reading that actually has one, rather
            # than invent a number. If there's genuinely none yet, skip this
            # zone rather than score it on incomplete data.
            fallback = (
                db.query(models.SensorReading)
                .filter(
                    models.SensorReading.zone_id == zone.id,
                    models.SensorReading.soil_moisture_pct.isnot(None),
                )
                .order_by(models.SensorReading.recorded_at.desc())
                .first()
            )
            if not fallback:
                skipped.append({"zone_id": zone.id, "name": zone.name, "reason": "no soil moisture reading available"})
                continue
            soil_moisture = fallback.soil_moisture_pct

        new_score = predict_risk(
            rainfall_mm_24h=latest.rainfall_mm_24h,
            soil_moisture_pct=soil_moisture,
            slope_angle_deg=zone.slope_angle_deg or 0,
            historical_landslide_count=zone.historical_landslide_count,
        )
        zone.risk_score = round(new_score, 4)
        zone.risk_severity = severity_for(new_score)
        zone.updated_at = datetime.utcnow()
        updated.append({
            "zone_id": zone.id,
            "name": zone.name,
            "risk_score": zone.risk_score,
            "risk_severity": zone.risk_severity.value,
        })

    db.commit()
    return {"updated": len(updated), "skipped": skipped}
