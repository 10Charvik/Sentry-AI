"""
Creates all tables and populates the database with mock data so every
endpoint has something real to return during development.

Usage:
    python -m app.seed
"""
import random
from datetime import datetime, timedelta

from geoalchemy2.shape import from_shape
from shapely.geometry import Polygon, LineString, Point

from app.database import Base, engine, SessionLocal
from app import models
from app.risk_utils import severity_for

random.seed(42)

# Roughly-placed NER district centers (lat, lon) — not survey-accurate,
# good enough for a demo map.
ZONE_SEED = [
    {"name": "Sector 01", "district": "Guwahati",  "center": (26.14, 91.73), "risk": 0.15, "slope": 22, "hist": 0},
    {"name": "Sector 02", "district": "Shillong",   "center": (25.57, 91.88), "risk": 0.35, "slope": 29, "hist": 2},
    {"name": "Sector 03", "district": "Itanagar",   "center": (27.10, 93.62), "risk": 0.20, "slope": 24, "hist": 1},
    {"name": "Sector 04", "district": "Kohima",     "center": (25.67, 94.11), "risk": 0.42, "slope": 31, "hist": 3},
    {"name": "Sector 05", "district": "Imphal",     "center": (24.82, 93.94), "risk": 0.18, "slope": 19, "hist": 0},
    {"name": "Sector 06", "district": "Aizawl",     "center": (23.73, 92.72), "risk": 0.55, "slope": 34, "hist": 4},
    {"name": "Sector 07", "district": "Aizawl outskirts", "center": (23.78, 92.80), "risk": 0.87, "slope": 38, "hist": 6},
    {"name": "Sector 08", "district": "Gangtok",    "center": (27.33, 88.61), "risk": 0.30, "slope": 27, "hist": 2},
]


def square_polygon(lat: float, lon: float, half_side_deg: float = 0.012) -> Polygon:
    return Polygon([
        (lon - half_side_deg, lat - half_side_deg),
        (lon + half_side_deg, lat - half_side_deg),
        (lon + half_side_deg, lat + half_side_deg),
        (lon - half_side_deg, lat + half_side_deg),
        (lon - half_side_deg, lat - half_side_deg),
    ])


def seed():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if db.query(models.Zone).count() > 0:
            print("Database already has zones — skipping seed. Delete rows or the DB to reseed.")
            return

        print("Seeding zones...")
        zones_by_name = {}
        for z in ZONE_SEED:
            lat, lon = z["center"]
            zone = models.Zone(
                name=z["name"],
                district=z["district"],
                slope_angle_deg=z["slope"],
                historical_landslide_count=z["hist"],
                risk_score=z["risk"],
                risk_severity=severity_for(z["risk"]),
                geom=from_shape(square_polygon(lat, lon), srid=4326),
                updated_at=datetime.utcnow(),
            )
            db.add(zone)
            db.flush()  # get zone.id
            zones_by_name[z["name"]] = zone

            # Sensor reading roughly correlated with risk
            rainfall = round(20 + z["risk"] * 90 + random.uniform(-5, 5), 1)
            soil_moisture = round(30 + z["risk"] * 65 + random.uniform(-4, 4), 1)
            db.add(models.SensorReading(
                zone_id=zone.id,
                rainfall_mm_24h=max(0, rainfall),
                soil_moisture_pct=min(100, max(0, soil_moisture)),
                source="mock",
                recorded_at=datetime.utcnow(),
            ))

            # A short history for the chart endpoint
            for h in range(1, 6):
                db.add(models.SensorReading(
                    zone_id=zone.id,
                    rainfall_mm_24h=max(0, rainfall - h * random.uniform(2, 6)),
                    soil_moisture_pct=min(100, max(0, soil_moisture - h * random.uniform(1, 3))),
                    source="mock",
                    recorded_at=datetime.utcnow() - timedelta(hours=h * 4),
                ))

            # Forecast
            forecast_mm = round(rainfall * random.uniform(0.5, 1.3), 1)
            db.add(models.Forecast(
                zone_id=zone.id,
                forecast_mm_72h=forecast_mm,
                created_at=datetime.utcnow(),
            ))

        db.flush()

        print("Seeding roads...")
        sector07 = zones_by_name["Sector 07"]
        sector06 = zones_by_name["Sector 06"]
        sector02 = zones_by_name["Sector 02"]
        sector04 = zones_by_name["Sector 04"]

        def road(name, zone, from_pt, to_pt, status):
            db.add(models.RoadSegment(
                name=name,
                zone_id=zone.id,
                status=status,
                geom=from_shape(LineString([from_pt, to_pt]), srid=4326),
                updated_at=datetime.utcnow(),
            ))

        # (lon, lat) order for shapely
        road("NH-306", sector07, (92.78, 23.76), (92.82, 23.80), models.RoadState.monitoring)
        road("SH-14", sector07, (92.79, 23.77), (92.83, 23.79), models.RoadState.blocked)
        road("District Road 12", sector06, (92.70, 23.71), (92.74, 23.75), models.RoadState.open)
        road("District Road 4", sector02, (91.86, 25.55), (91.90, 25.59), models.RoadState.open)
        road("NH-40 Bypass", sector04, (94.09, 25.65), (94.13, 25.69), models.RoadState.monitoring)

        print("Seeding field reports...")
        db.add(models.FieldReport(
            zone_id=sector07.id,
            reporter_name="Field Officer — Lalrinmawia",
            report_type=models.ReportType.crack,
            description="Fresh cracking along the upper embankment, roughly 15m wide, widened after last night's rain.",
            photo_url=None,
            geom=from_shape(Point(92.805, 23.782), srid=4326),
            created_at=datetime.utcnow() - timedelta(hours=2),
        ))
        db.add(models.FieldReport(
            zone_id=sector07.id,
            reporter_name=None,
            report_type=models.ReportType.road_block,
            description="SH-14 blocked by debris near the second bend, no vehicle movement possible.",
            photo_url=None,
            geom=from_shape(Point(92.812, 23.788), srid=4326),
            created_at=datetime.utcnow() - timedelta(hours=1),
        ))
        db.add(models.FieldReport(
            zone_id=sector06.id,
            reporter_name="Resident — Zoramthanga",
            report_type=models.ReportType.slope_movement,
            description="Noticeable soil movement below the water tank, small trees leaning downhill.",
            photo_url=None,
            geom=from_shape(Point(92.735, 23.744), srid=4326),
            created_at=datetime.utcnow() - timedelta(hours=6),
        ))

        db.commit()
        print(f"Seeded {len(ZONE_SEED)} zones with sensor readings, roads, forecasts and field reports.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
