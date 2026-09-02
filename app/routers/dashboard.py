from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.schemas import DashboardSummary, SeverityCounts, RoadCounts, ResponseQueueItem

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    """One call that feeds every stat card on the ops dashboard:
    risk severity counts, road connectivity counts, the worst 72h forecast,
    and the top-priority zones for the response queue.
    """
    zones = db.query(models.Zone).all()
    roads = db.query(models.RoadSegment).all()

    severity = SeverityCounts(
        high=sum(1 for z in zones if z.risk_severity == models.RiskSeverity.high),
        watch=sum(1 for z in zones if z.risk_severity == models.RiskSeverity.watch),
        safe=sum(1 for z in zones if z.risk_severity == models.RiskSeverity.safe),
    )

    road_counts = RoadCounts(
        blocked=sum(1 for r in roads if r.status == models.RoadState.blocked),
        monitoring=sum(1 for r in roads if r.status == models.RoadState.monitoring),
        open=sum(1 for r in roads if r.status == models.RoadState.open),
    )

    max_forecast = (
        db.query(func.max(models.Forecast.forecast_mm_72h)).scalar() or 0.0
    )

    top_zones = sorted(zones, key=lambda z: z.risk_score, reverse=True)[:3]
    response_queue = [
        ResponseQueueItem(
            zone_id=z.id,
            name=z.name,
            district=z.district,
            risk_score=z.risk_score,
            risk_severity=z.risk_severity,
        )
        for z in top_zones
    ]

    return DashboardSummary(
        risk_severity=severity,
        roads=road_counts,
        max_forecast_mm_72h=max_forecast,
        response_queue=response_queue,
        generated_at=datetime.utcnow(),
    )
