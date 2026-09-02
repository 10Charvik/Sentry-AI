import enum
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Enum,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


class RiskSeverity(str, enum.Enum):
    safe = "safe"
    watch = "watch"
    high = "high"


class RoadState(str, enum.Enum):
    open = "open"
    monitoring = "monitoring"
    blocked = "blocked"


class ReportType(str, enum.Enum):
    crack = "crack"
    slope_movement = "slope_movement"
    road_block = "road_block"
    other = "other"


class Zone(Base):
    """A monitored sector — a slope/hillside area being tracked for landslide risk."""

    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)          # e.g. "Sector 07"
    district = Column(String, nullable=False)       # e.g. "Aizawl"
    slope_angle_deg = Column(Float, nullable=True)
    historical_landslide_count = Column(Integer, nullable=False, default=0)  # incidents on record, last ~10y
    risk_score = Column(Float, nullable=False, default=0.0)   # 0.0 - 1.0
    risk_severity = Column(Enum(RiskSeverity), nullable=False, default=RiskSeverity.safe)
    geom = Column(Geometry(geometry_type="POLYGON", srid=4326), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sensor_readings = relationship("SensorReading", back_populates="zone", cascade="all, delete-orphan")
    road_segments = relationship("RoadSegment", back_populates="zone", cascade="all, delete-orphan")
    field_reports = relationship("FieldReport", back_populates="zone")
    forecasts = relationship("Forecast", back_populates="zone", cascade="all, delete-orphan")


class SensorReading(Base):
    """A single rainfall / soil-moisture reading for a zone.

    soil_moisture_pct is nullable: IMD's weather API (used for real rainfall
    ingestion) has no soil moisture data — that has to come from a different
    source (ground sensors, ISRO/Bhuvan, NASA SMAP). Readings ingested from
    IMD leave it null rather than fabricate a number.
    """

    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)
    rainfall_mm_24h = Column(Float, nullable=False)
    soil_moisture_pct = Column(Float, nullable=True)
    source = Column(String, nullable=False, default="mock")  # "mock" | "imd"
    recorded_at = Column(DateTime, default=datetime.utcnow)

    zone = relationship("Zone", back_populates="sensor_readings")


class RoadSegment(Base):
    """A road/route whose connectivity status is tracked per zone."""

    __tablename__ = "road_segments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)            # e.g. "NH-306"
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)
    status = Column(Enum(RoadState), nullable=False, default=RoadState.open)
    geom = Column(Geometry(geometry_type="LINESTRING", srid=4326), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    zone = relationship("Zone", back_populates="road_segments")


class FieldReport(Base):
    """A citizen or field-officer submitted geo-tagged report."""

    __tablename__ = "field_reports"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    reporter_name = Column(String, nullable=True)
    report_type = Column(Enum(ReportType), nullable=False, default=ReportType.other)
    description = Column(Text, nullable=True)
    photo_url = Column(String, nullable=True)
    geom = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    zone = relationship("Zone", back_populates="field_reports")


class Forecast(Base):
    """A weather-linked forecast for a zone (mocked — swap for IMD API later)."""

    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)
    forecast_mm_72h = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    zone = relationship("Zone", back_populates="forecasts")


class WeatherWarning(Base):
    """An official IMD district-level warning, as-fetched — IMD reports these
    as day-by-day severity categories (e.g. 'Heavy Rain', colour-coded), not
    a numeric forecast, so this stores exactly that rather than converting
    it into an invented mm figure.
    """

    __tablename__ = "weather_warnings"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)
    source = Column(String, nullable=False, default="IMD")
    day1_warning = Column(String, nullable=True)
    day1_color = Column(String, nullable=True)
    day2_warning = Column(String, nullable=True)
    day2_color = Column(String, nullable=True)
    issued_date = Column(String, nullable=True)  # as reported by IMD, e.g. "2026-08-30"
    fetched_at = Column(DateTime, default=datetime.utcnow)

    zone = relationship("Zone")
