from datetime import datetime
from typing import Optional, Any, Dict, List

from pydantic import BaseModel, Field

from app.models import RiskSeverity, RoadState, ReportType


# ---------- GeoJSON helpers ----------

class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: Dict[str, Any]
    properties: Dict[str, Any]


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]


# ---------- Zones ----------

class ZoneOut(BaseModel):
    id: int
    name: str
    district: str
    slope_angle_deg: Optional[float]
    historical_landslide_count: int
    risk_score: float
    risk_severity: RiskSeverity
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- Sensor readings ----------

class SensorReadingOut(BaseModel):
    id: int
    zone_id: int
    rainfall_mm_24h: float
    soil_moisture_pct: Optional[float]
    source: str
    recorded_at: datetime

    class Config:
        from_attributes = True


# ---------- Roads ----------

class RoadSegmentOut(BaseModel):
    id: int
    name: str
    zone_id: int
    status: RoadState
    updated_at: datetime

    class Config:
        from_attributes = True


class RoadStatusUpdate(BaseModel):
    status: RoadState


# ---------- Field reports ----------

class FieldReportCreate(BaseModel):
    zone_id: Optional[int] = None
    reporter_name: Optional[str] = Field(None, max_length=120)
    report_type: ReportType = ReportType.other
    description: Optional[str] = None
    photo_url: Optional[str] = None
    lat: float
    lon: float


class FieldReportOut(BaseModel):
    id: int
    zone_id: Optional[int]
    reporter_name: Optional[str]
    report_type: ReportType
    description: Optional[str]
    photo_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Forecasts ----------

class ForecastOut(BaseModel):
    id: int
    zone_id: int
    forecast_mm_72h: float
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Weather warnings (real IMD data) ----------

class WeatherWarningOut(BaseModel):
    id: int
    zone_id: int
    source: str
    day1_warning: Optional[str]
    day1_color: Optional[str]
    day2_warning: Optional[str]
    day2_color: Optional[str]
    issued_date: Optional[str]
    fetched_at: datetime

    class Config:
        from_attributes = True


# ---------- Dashboard summary ----------

class SeverityCounts(BaseModel):
    high: int
    watch: int
    safe: int


class RoadCounts(BaseModel):
    blocked: int
    monitoring: int
    open: int


class ResponseQueueItem(BaseModel):
    zone_id: int
    name: str
    district: str
    risk_score: float
    risk_severity: RiskSeverity


class DashboardSummary(BaseModel):
    risk_severity: SeverityCounts
    roads: RoadCounts
    max_forecast_mm_72h: float
    response_queue: List[ResponseQueueItem]
    generated_at: datetime
