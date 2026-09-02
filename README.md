# Sentry.ai — starter backend

FastAPI + PostgreSQL/PostGIS scaffold for the landslide early-warning platform.
Ships with mock data (8 sample "sectors" across the North Eastern Region) so
every endpoint returns something real while the frontend is being built.

## What's here

```
app/
  main.py          FastAPI app + router registration
  config.py        Settings (reads .env)
  database.py      SQLAlchemy engine/session
  models.py        Zone, SensorReading, RoadSegment, FieldReport, Forecast
  schemas.py       Pydantic request/response models (incl. GeoJSON shapes)
  geo_utils.py      PostGIS geometry -> GeoJSON conversion
  seed.py          Populates mock data — run once after the DB is up
  routers/
    zones.py       GET /zones, GET /zones/{id}, GET /zones/risk/heatmap
    roads.py       GET /roads, PATCH /roads/{id}/status
    reports.py     GET /reports, POST /reports  (citizen/field uploads)
    sensors.py     GET /sensors/{zone_id}/latest|history|forecast
    dashboard.py   GET /dashboard/summary        (feeds the ops dashboard cards)
docker-compose.yml  Local Postgres+PostGIS (+ Adminer on :8080)
```

## Quickstart

1. **Start the database** (requires Docker):

   ```bash
   docker-compose up -d
   ```

2. **Install dependencies** (Python 3.11+ recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**:

   ```bash
   cp .env.example .env
   ```

   The defaults already match `docker-compose.yml`, so this works as-is for local dev
   — except `ADMIN_API_KEY`, which is intentionally blank. Generate one before you
   need the admin endpoints (see "Auth" below).

4. **Create tables and load mock data**:

   ```bash
   python -m app.seed
   ```

4b. **Train the first-pass risk model** (optional but recommended — powers `POST /risk/recompute`):

   ```bash
   python -m app.ml.train
   ```

   This prints a held-out AUC/accuracy and saves `app/ml/risk_model.joblib`.
   See "The risk model" below for what it actually does.

5. **Run the API**:

   ```bash
   uvicorn app.main:app --reload
   ```

6. Open **http://localhost:8000/docs** — interactive Swagger UI for every endpoint.
   Adminer (DB browser) is at **http://localhost:8080** (System: PostgreSQL, Server: db,
   Username: sentry, Password: sentry, Database: sentry).

## Endpoints at a glance

| Endpoint | Returns |
|---|---|
| `GET /zones` | All monitored sectors as GeoJSON (polygons + risk score/severity) |
| `GET /zones/{id}` | One sector |
| `GET /zones/risk/heatmap` | Same as `/zones` — stable URL for the map's risk layer |
| `GET /roads` | Road segments as GeoJSON, with `status`: open / monitoring / blocked |
| `PATCH /roads/{id}/status` | Update a road's status — **requires `X-API-Key`** |
| `GET /reports` | Recent citizen/field-officer reports |
| `POST /reports` | Submit a geo-tagged crack / slope-movement / road-block report |
| `GET /sensors/{zone_id}/latest` | Latest rainfall + soil moisture reading |
| `GET /sensors/{zone_id}/history?hours=24` | Reading history |
| `GET /sensors/{zone_id}/forecast` | Mocked 72h rainfall forecast |
| `GET /dashboard/summary` | One call for all four ops-dashboard stat cards |
| `POST /risk/recompute` | Re-scores every zone using the trained model + latest sensor reading — **requires `X-API-Key`** (also runs automatically, see below) |
| `GET /warnings` | Latest real IMD district warnings per zone (empty until IMD ingestion is configured and has run) |

All geometry-bearing endpoints return standard **GeoJSON**, so they drop straight
into Leaflet (`L.geoJSON(data)`) or Mapbox GL (`map.addSource(...type: 'geojson')`)
on the frontend.

## Auth

Two mutating "admin" actions require an API key: `PATCH /roads/{id}/status`
and `POST /risk/recompute`. Both are wide open to 401s (or 503s if unset)
until you configure one.

1. Generate a key:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
2. Put it in `.env` as `ADMIN_API_KEY=...`.
3. Call protected endpoints with it:
   ```bash
   curl -X POST http://localhost:8000/risk/recompute \
     -H "X-API-Key: your-key-here"
   ```

This is a single shared key, not role-based auth — it's a reasonable first
pass for a one-admin-role hackathon scaffold, not what the real platform
needs (district admin / field officer / public roles with proper JWTs — see
Next steps).

## Background risk-recompute scheduler

`app/scheduler.py` runs `recompute_all_zones()` automatically on a timer as
long as the API process is running — no external cron needed. Controlled by
two env vars:

```
RISK_RECOMPUTE_ENABLED=true          # set false to disable entirely
RISK_RECOMPUTE_INTERVAL_SECONDS=300  # how often it runs
```

It logs each run (`Risk recompute: updated N zone(s)`) and — importantly —
a single failed iteration (e.g. no trained model yet) is logged and skipped
rather than crashing the loop or the server. `POST /risk/recompute` still
exists for forcing an immediate refresh by hand.

This is one asyncio task in the same process — the right amount of
infrastructure for a single-instance API. If this ever runs as multiple
replicas, move it to something that won't run N times in parallel (Celery
beat, APScheduler with a shared store, or a cloud scheduler hitting the
endpoint instead).

## Real IMD weather data ingestion

`app/ingestion/` pulls real rainfall and warning data from IMD's actual API
gateway (https://api.imd.gov.in — documented at
https://api.imd.gov.in/public/api_reference.html). This is genuinely IMD's
government API, not a mock — but it comes with real constraints, so this
section is honest about what works out of the box and what doesn't.

**Before it will return real data, you need:**

1. **IP whitelisting.** IMD doesn't use an API key — access is controlled by
   whitelisting the calling server's IP. Request this at
   https://api.imd.gov.in/public/index.php. Until it's approved, every call
   fails (timeout or non-200) — expected, not a bug.
2. **Real station/district IDs.** `app/ingestion/zone_mapping.py` ships with
   `"REPLACE_ME"` placeholders for every zone, deliberately — IMD's docs
   don't publish a lookup table, and a guessed-but-wrong ID would silently
   pull another location's weather with no error. Find the real ones via
   https://city.imd.gov.in (station IDs) and
   https://mausam.imd.gov.in/responsive/rainfallinformation.php (district
   Obj_IDs) — full instructions are in that file's docstring. Every zone
   is skipped, loudly, until you fill these in.

**What this actually ingests, and what it deliberately doesn't:**

- ✅ **Rainfall** — IMD's Current Weather API returns a real
  "Last 24 hrs Rainfall" figure in mm per station. This maps directly onto
  `SensorReading.rainfall_mm_24h`.
- ✅ **Official warnings** — IMD's District Warnings API returns categorical,
  colour-coded severity ("Heavy Rain", "Very Heavy Rain", etc.) for the next
  5 days. Stored as-is in the new `WeatherWarning` table via `GET /warnings`
  — not converted into an invented mm figure, because IMD doesn't give one.
- ❌ **Soil moisture** — not an IMD data source at all (they're a
  meteorological department). `SensorReading.soil_moisture_pct` is nullable
  specifically because of this; IMD-sourced readings leave it null rather
  than fake a number. You'll need a separate source for this — ground
  sensors if they exist, or a satellite product (ISRO/Bhuvan, NASA SMAP).
- ❌ **Numeric 72h forecast** — same reasoning as warnings above; the
  `Forecast` table stays mock-only until there's a real numeric source.

**Try it:**

```bash
# after configuring zone_mapping.py with real IDs and getting whitelisted
python -m app.ingestion.imd_ingest
```

Or let it run automatically — set `IMD_INGEST_ENABLED=true` in `.env` and it
runs on the same kind of background loop as risk recompute (default: every
30 minutes, configurable via `IMD_INGEST_INTERVAL_SECONDS`). It's disabled
by default specifically so it doesn't fail loudly on every interval before
you've done the setup above.

## The risk model (first pass)

`app/ml/` holds a small, honest first pass:

- **`train.py`** — there's no real historical landslide dataset available yet,
  so it *synthesizes* one from a hand-tuned domain heuristic: higher rainfall,
  wetter soil, steeper slope, and more past incidents each push risk up, plus
  random noise so it's not a trivial straight line. It fits a plain
  `LogisticRegression` (via an sklearn `Pipeline` with a `StandardScaler`) on
  that synthetic data and saves the fitted pipeline to `risk_model.joblib`.
  On a held-out synthetic test split it lands around **AUC ~0.78** — a
  sanity-check number, not a claim about real-world accuracy.
- **`predict.py`** — loads the saved pipeline once and exposes
  `predict_risk(rainfall_mm_24h, soil_moisture_pct, slope_angle_deg, historical_landslide_count) -> float`.
- **`features.py`** — the single place feature names/order live, so training
  and inference can't silently drift apart.

`POST /risk/recompute` calls `predict_risk()` for every zone using its latest
`SensorReading` plus its static `slope_angle_deg` and
`historical_landslide_count`, then updates `Zone.risk_score` and
`risk_severity`. Try it against the seeded data:

```bash
curl -X POST http://localhost:8000/risk/recompute
```

Sector 07's seeded conditions (86mm rain, 91% soil moisture, 38° slope, 6
historical incidents) score **~0.89** — consistent with its seeded 0.87 "high"
risk, which is a reasonable sanity check that the heuristic behaves the way
the seed data was written to imply.

**This is a first pass, not a production model.** The honest next step is
real historical landslide records for the region (dates, locations, and the
weather/soil conditions at the time) to replace `generate_synthetic_dataset()`
with an actual loader — the training code itself doesn't need to change.

## What's mocked vs. real here

- **Real**: the schema (PostGIS geometry types, relationships), the API
  shape, CORS, the dashboard aggregation logic, the risk model's mechanics
  (a genuinely trained, saved, loadable model), and — now — the IMD
  ingestion client, which calls IMD's actual API gateway with real
  endpoints and real response parsing.
- **Mocked**: seeded sensor readings/forecasts are still random numbers by
  default. Real IMD rainfall ingestion works once you configure zone IDs
  and get IP-whitelisted (see above), but soil moisture and numeric
  forecasts have no IMD source and stay mock/manual regardless. The risk
  model is trained on synthetic data, not real historical landslide records.

## Next steps (in rough priority order)

1. **Configure real IMD access**: fill in `app/ingestion/zone_mapping.py`
   with real station/district IDs and request IP whitelisting — this is the
   one piece of "real data ingestion" that's implemented but not yet usable
   out of the box, purely because it needs your specific IDs and approval.
2. **A soil moisture source**: ground sensors if they exist, otherwise a
   satellite product (ISRO/Bhuvan, NASA SMAP) — IMD doesn't provide this.
3. **Real historical labels for the risk model**: swap
   `generate_synthetic_dataset()` in `app/ml/train.py` for a loader over
   actual landslide incident records, then retrain. Consider a model with
   more capacity (gradient boosting) once there's enough real data to justify it.
4. **Role-based auth**: replace the single shared `ADMIN_API_KEY` with proper
   JWT-based auth and real roles (district admin / field officer / public) —
   the API key is a first pass, not the real thing.
5. **Alerting**: a rule engine that watches `risk_score` crossing thresholds
   (and the new `WeatherWarning` data) and triggers SMS (Twilio, MSG91,
   Kaleyra) + push notifications, localized per district.
6. **File uploads**: `POST /reports` accepts a `photo_url` string today —
   add an actual upload endpoint backed by S3-compatible storage (S3,
   Cloudflare R2, Supabase Storage) and pass the resulting URL through.
7. **Hosting**: for a hackathon-scale deployment, Supabase (Postgres +
   PostGIS + auth + storage, generous free tier) gets you live fastest.
   A plain VM with this docker-compose setup works too.
