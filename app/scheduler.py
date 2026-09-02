"""
A deliberately simple scheduler: one asyncio task, one infinite loop, one
sleep. No Celery, no cron, no external broker — for a single-process
hackathon-scale API this is the right amount of infrastructure. If this
ever runs as multiple replicas, move this to a proper scheduler (Celery
beat, APScheduler with a shared store, or a cloud scheduler hitting
POST /risk/recompute) so it doesn't run N times in parallel.
"""
import asyncio
import logging

from app.database import SessionLocal
from app.services.risk_service import recompute_all_zones
from app.config import settings

logger = logging.getLogger("sentry.scheduler")


async def risk_recompute_loop():
    logger.info(
        "Risk recompute loop started — running every %ss",
        settings.risk_recompute_interval_seconds,
    )
    while True:
        try:
            db = SessionLocal()
            try:
                result = recompute_all_zones(db)
                logger.info("Risk recompute: updated %s zone(s)", result["updated"])
            finally:
                db.close()
        except FileNotFoundError as e:
            logger.warning("Risk recompute skipped — %s", e)
        except Exception:
            # A single bad iteration should never kill the loop.
            logger.exception("Risk recompute loop iteration failed")

        await asyncio.sleep(settings.risk_recompute_interval_seconds)


async def imd_ingest_loop():
    """Same pattern as risk_recompute_loop, for real IMD data ingestion.
    Stays idle-but-safe if zone_mapping.py still has placeholder IDs — each
    run just reports every zone as skipped rather than erroring."""
    from app.ingestion.imd_ingest import ingest_rainfall_and_warnings

    logger.info(
        "IMD ingest loop started — running every %ss",
        settings.imd_ingest_interval_seconds,
    )
    while True:
        try:
            db = SessionLocal()
            try:
                result = ingest_rainfall_and_warnings(db)
                logger.info(
                    "IMD ingest: %s zone(s) ingested, %s skipped",
                    result["ingested"], len(result["skipped"]),
                )
            finally:
                db.close()
        except Exception:
            logger.exception("IMD ingest loop iteration failed")

        await asyncio.sleep(settings.imd_ingest_interval_seconds)
