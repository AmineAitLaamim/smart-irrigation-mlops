import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest
import uvicorn

try:
    from .database import db, stats
    from .etl import run_batch
    from .redis_consumer import consumer
except ImportError:  # pragma: no cover - test import path fallback
    from database import db, stats
    from etl import run_batch
    from redis_consumer import consumer

BATCH_INTERVAL_SECONDS = int(os.getenv("BATCH_INTERVAL_SECONDS", "300"))
FEATURE_ENGINEERING_PORT = int(os.getenv("FEATURE_ENGINEERING_PORT", "8004"))

TOTAL_PROCESSED = Gauge(
    "feature_engineering_total_processed",
    "Total readings processed by the feature engineering service",
)
FEATURES_COMPUTED = Gauge(
    "feature_engineering_features_computed",
    "Feature rows computed by the feature engineering service",
)
ROLLUPS_COMPUTED = Gauge(
    "feature_engineering_rollups_computed",
    "Rollups computed by the feature engineering service",
)
ANOMALIES_SMOOTHED = Gauge(
    "feature_engineering_anomalies_smoothed",
    "Anomalies smoothed by the feature engineering service",
)
FEATURE_ENGINEERING_ERRORS = Gauge(
    "feature_engineering_errors_total",
    "Errors observed by the feature engineering service",
)


def _update_metrics() -> None:
    snapshot = stats.to_dict()
    TOTAL_PROCESSED.set(snapshot["total_processed"])
    FEATURES_COMPUTED.set(snapshot["features_computed"])
    ROLLUPS_COMPUTED.set(snapshot["rollups_computed"])
    ANOMALIES_SMOOTHED.set(snapshot["anomalies_smoothed"])
    FEATURE_ENGINEERING_ERRORS.set(snapshot["errors"])


async def _batch_scheduler():
    """Background coroutine that runs batch ETL every N seconds."""
    while True:
        try:
            await run_batch()
        except Exception as exc:
            await stats.increment(error=True)
            print(f"Batch scheduler error: {exc}")
        await asyncio.sleep(BATCH_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    await consumer.connect()

    consumer_task = asyncio.create_task(consumer.run())
    batch_task = asyncio.create_task(_batch_scheduler())

    yield

    consumer._running = False
    consumer_task.cancel()
    batch_task.cancel()

    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    try:
        await batch_task
    except asyncio.CancelledError:
        pass

    await consumer.disconnect()
    await db.disconnect()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "stats": stats.to_dict(),
    }


@app.get("/metrics")
async def metrics():
    _update_metrics()
    return PlainTextResponse(generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST)


@app.post("/trigger-batch")
async def trigger_batch():
    """Manual trigger for batch ETL (useful for testing)."""
    await run_batch()
    return {"status": "batch_completed", "stats": stats.to_dict()}


def main():
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=FEATURE_ENGINEERING_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
