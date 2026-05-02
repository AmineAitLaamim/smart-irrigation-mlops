import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest
import uvicorn

from .database import db, stats
from .redis_consumer import consumer

DATA_INGESTION_PORT = int(os.getenv("DATA_INGESTION_PORT", "8001"))

TOTAL_PROCESSED = Gauge(
    "data_ingestion_total_processed",
    "Total sensor readings processed by the ingestion service",
)
VALID_READINGS = Gauge(
    "data_ingestion_valid_readings",
    "Valid sensor readings persisted by the ingestion service",
)
ANOMALIES_FLAGGED = Gauge(
    "data_ingestion_anomalies_flagged",
    "Anomalous sensor readings flagged by the ingestion service",
)
INGESTION_ERRORS = Gauge(
    "data_ingestion_errors_total",
    "Errors observed by the ingestion service",
)


def _update_metrics() -> None:
    snapshot = stats.to_dict()
    TOTAL_PROCESSED.set(snapshot["total_processed"])
    VALID_READINGS.set(snapshot["valid_readings"])
    ANOMALIES_FLAGGED.set(snapshot["anomalies_flagged"])
    INGESTION_ERRORS.set(snapshot["errors"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    await consumer.connect()
    consumer_task = asyncio.create_task(consumer.run())
    yield
    consumer._running = False
    consumer_task.cancel()
    try:
        await consumer_task
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


def main():
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=DATA_INGESTION_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
