import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import zones, roads, reports, sensors, dashboard, risk, warnings
from app.scheduler import risk_recompute_loop, imd_ingest_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = []
    if settings.risk_recompute_enabled:
        tasks.append(asyncio.create_task(risk_recompute_loop()))
    if settings.imd_ingest_enabled:
        tasks.append(asyncio.create_task(imd_ingest_loop()))
    yield
    for task in tasks:
        task.cancel()
    for task in tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Sentry.ai API",
    description="AI-powered landslide early warning platform for the North Eastern Region — "
                 "starter backend with mock data. See /docs for interactive API docs.",
    version="0.1.0",
    lifespan=lifespan,
)

origins = ["*"] if settings.cors_origins == "*" else settings.cors_origins.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(zones.router)
app.include_router(roads.router)
app.include_router(reports.router)
app.include_router(sensors.router)
app.include_router(dashboard.router)
app.include_router(risk.router)
app.include_router(warnings.router)


@app.get("/", tags=["health"])
def root():
    return {
        "service": "sentry-ai-backend",
        "status": "ok",
        "docs": "/docs",
        "risk_recompute_scheduler": "enabled" if settings.risk_recompute_enabled else "disabled",
        "imd_ingest_scheduler": "enabled" if settings.imd_ingest_enabled else "disabled",
    }
