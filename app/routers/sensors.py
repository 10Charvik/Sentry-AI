from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.schemas import SensorReadingOut, ForecastOut

router = APIRouter(prefix="/sensors", tags=["sensors"])


@router.get("/{zone_id}/latest", response_model=SensorReadingOut)
def latest_reading(zone_id: int, db: Session = Depends(get_db)):
    reading = (
        db.query(models.SensorReading)
        .filter(models.SensorReading.zone_id == zone_id)
        .order_by(models.SensorReading.recorded_at.desc())
        .first()
    )
    if not reading:
        raise HTTPException(status_code=404, detail="No readings for this zone yet")
    return reading


@router.get("/{zone_id}/history", response_model=list[SensorReadingOut])
def reading_history(
    zone_id: int,
    hours: int = Query(24, ge=1, le=24 * 30),
    db: Session = Depends(get_db),
):
    since = datetime.utcnow() - timedelta(hours=hours)
    readings = (
        db.query(models.SensorReading)
        .filter(models.SensorReading.zone_id == zone_id, models.SensorReading.recorded_at >= since)
        .order_by(models.SensorReading.recorded_at.asc())
        .all()
    )
    return readings


@router.get("/{zone_id}/forecast", response_model=ForecastOut)
def latest_forecast(zone_id: int, db: Session = Depends(get_db)):
    """Mocked weather-linked forecast — swap the seed/mock generation for a real
    IMD API call feeding into a `Forecast` row on a schedule."""
    forecast = (
        db.query(models.Forecast)
        .filter(models.Forecast.zone_id == zone_id)
        .order_by(models.Forecast.created_at.desc())
        .first()
    )
    if not forecast:
        raise HTTPException(status_code=404, detail="No forecast for this zone yet")
    return forecast
