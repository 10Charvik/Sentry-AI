from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.auth import require_admin_key
from app.geo_utils import geom_to_geojson
from app.schemas import GeoJSONFeature, GeoJSONFeatureCollection, RoadStatusUpdate

router = APIRouter(prefix="/roads", tags=["roads"])


def _road_to_feature(road: models.RoadSegment) -> GeoJSONFeature:
    return GeoJSONFeature(
        geometry=geom_to_geojson(road.geom),
        properties={
            "id": road.id,
            "name": road.name,
            "zone_id": road.zone_id,
            "status": road.status.value,
            "updated_at": road.updated_at.isoformat() if road.updated_at else None,
        },
    )


@router.get("", response_model=GeoJSONFeatureCollection)
def list_roads(db: Session = Depends(get_db)):
    """All tracked road segments as GeoJSON, colour-code client-side by `status`."""
    roads = db.query(models.RoadSegment).all()
    return GeoJSONFeatureCollection(features=[_road_to_feature(r) for r in roads])


@router.patch("/{road_id}/status", response_model=GeoJSONFeature)
def update_road_status(
    road_id: int,
    payload: RoadStatusUpdate,
    db: Session = Depends(get_db),
    _admin: bool = Depends(require_admin_key),
):
    """Update a road's status. Requires the X-API-Key header (see
    ADMIN_API_KEY in .env) — this used to be wide open, now it isn't."""
    road = db.query(models.RoadSegment).filter(models.RoadSegment.id == road_id).first()
    if not road:
        raise HTTPException(status_code=404, detail="Road segment not found")
    road.status = payload.status
    road.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(road)
    return _road_to_feature(road)
