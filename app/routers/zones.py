from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.geo_utils import geom_to_geojson
from app.schemas import GeoJSONFeature, GeoJSONFeatureCollection

router = APIRouter(prefix="/zones", tags=["zones"])


def _zone_to_feature(zone: models.Zone) -> GeoJSONFeature:
    return GeoJSONFeature(
        geometry=geom_to_geojson(zone.geom),
        properties={
            "id": zone.id,
            "name": zone.name,
            "district": zone.district,
            "slope_angle_deg": zone.slope_angle_deg,
            "historical_landslide_count": zone.historical_landslide_count,
            "risk_score": zone.risk_score,
            "risk_severity": zone.risk_severity.value,
            "updated_at": zone.updated_at.isoformat() if zone.updated_at else None,
        },
    )


@router.get("", response_model=GeoJSONFeatureCollection)
def list_zones(db: Session = Depends(get_db)):
    """All monitored zones as a GeoJSON FeatureCollection — ready to drop onto a Leaflet/Mapbox map."""
    zones = db.query(models.Zone).all()
    return GeoJSONFeatureCollection(features=[_zone_to_feature(z) for z in zones])


@router.get("/{zone_id}", response_model=GeoJSONFeature)
def get_zone(zone_id: int, db: Session = Depends(get_db)):
    zone = db.query(models.Zone).filter(models.Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return _zone_to_feature(zone)


@router.get("/risk/heatmap", response_model=GeoJSONFeatureCollection)
def risk_heatmap(db: Session = Depends(get_db)):
    """Same shape as list_zones, kept as its own endpoint so the frontend's risk-map
    layer has a stable, semantically-named URL even if zones/ gains more fields later."""
    zones = db.query(models.Zone).all()
    return GeoJSONFeatureCollection(features=[_zone_to_feature(z) for z in zones])
