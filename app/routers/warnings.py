from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.schemas import WeatherWarningOut

router = APIRouter(prefix="/warnings", tags=["weather warnings"])


@router.get("", response_model=list[WeatherWarningOut])
def latest_warnings(db: Session = Depends(get_db)):
    """Most recent IMD warning fetched per zone. Empty until real IMD
    ingestion is configured and has run at least once — see
    app/ingestion/README or the main README's IMD ingestion section."""
    warnings = (
        db.query(models.WeatherWarning)
        .order_by(models.WeatherWarning.fetched_at.desc())
        .limit(50)
        .all()
    )
    return warnings
