from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.database import get_db
from app import models
from app.geo_utils import geom_to_geojson
from app.schemas import FieldReportCreate, GeoJSONFeature, GeoJSONFeatureCollection

router = APIRouter(prefix="/reports", tags=["field reports"])


def _report_to_feature(report: models.FieldReport) -> GeoJSONFeature:
    return GeoJSONFeature(
        geometry=geom_to_geojson(report.geom),
        properties={
            "id": report.id,
            "zone_id": report.zone_id,
            "reporter_name": report.reporter_name,
            "report_type": report.report_type.value,
            "description": report.description,
            "photo_url": report.photo_url,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        },
    )


@router.get("", response_model=GeoJSONFeatureCollection)
def list_reports(db: Session = Depends(get_db)):
    """Recent citizen/field-officer reports, most recent first."""
    reports = (
        db.query(models.FieldReport)
        .order_by(models.FieldReport.created_at.desc())
        .limit(100)
        .all()
    )
    return GeoJSONFeatureCollection(features=[_report_to_feature(r) for r in reports])


@router.post("", response_model=GeoJSONFeature, status_code=201)
def create_report(payload: FieldReportCreate, db: Session = Depends(get_db)):
    """Submit a geo-tagged crack / slope-movement / road-block report.

    `photo_url` is expected to already point at uploaded media (e.g. an S3 URL) —
    this scaffold doesn't handle the binary upload itself. Wire that to whichever
    object storage you pick (S3, Cloudflare R2, Supabase Storage, etc.) and pass
    the resulting URL here.
    """
    point = from_shape(Point(payload.lon, payload.lat), srid=4326)
    report = models.FieldReport(
        zone_id=payload.zone_id,
        reporter_name=payload.reporter_name,
        report_type=payload.report_type,
        description=payload.description,
        photo_url=payload.photo_url,
        geom=point,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return _report_to_feature(report)
