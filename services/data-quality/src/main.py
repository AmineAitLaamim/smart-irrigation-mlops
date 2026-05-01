import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import FastAPI, Query
from fastapi.responses import PlainTextResponse
import uvicorn

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from .database import db, stats
from .metrics import active_rules_gauge
from .quality_engine import _load_active_rules, update_sensor_health_gauge
from .redis_consumer import consumer
from .reports import (
    get_active_rules,
    get_hourly_metrics,
    get_quality_summary,
    get_sensor_health,
    update_rule,
)

BATCH_SCAN_INTERVAL_SECONDS = int(os.getenv("BATCH_SCAN_INTERVAL_SECONDS", "300"))
DATA_QUALITY_PORT = int(os.getenv("DATA_QUALITY_PORT", "8005"))


async def _batch_scan_loop():
    """Background coroutine that periodically refreshes rules and health gauges."""
    while True:
        try:
            await _load_active_rules(force=True)
            await update_sensor_health_gauge()
        except Exception as exc:
            await stats.increment(error=True)
            print(f"Batch scan error: {exc}")
        await asyncio.sleep(BATCH_SCAN_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    await consumer.connect()

    consumer_task = asyncio.create_task(consumer.run())
    batch_task = asyncio.create_task(_batch_scan_loop())

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
async def metrics_endpoint():
    """Prometheus scrape endpoint for Grafana integration."""
    return PlainTextResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/quality/reports/summary")
async def quality_report_summary(
    hours: int = Query(24, ge=1, le=168),
    zone_id: Optional[str] = None,
    sensor_id: Optional[str] = None,
):
    return await get_quality_summary(hours=hours, zone_id=zone_id, sensor_id=sensor_id)


@app.get("/quality/reports/sensors")
async def quality_report_sensors(
    zone_id: Optional[str] = None,
):
    return await get_sensor_health(zone_id=zone_id)


@app.get("/quality/reports/hourly")
async def quality_report_hourly(
    hours: int = Query(24, ge=1, le=168),
):
    return await get_hourly_metrics(hours=hours)


@app.get("/quality/rules")
async def list_quality_rules():
    rules = await get_active_rules()
    return {"rules": rules, "count": len(rules)}


@app.patch("/quality/rules/{rule_id}")
async def patch_quality_rule(rule_id: str, payload: Dict[str, Any]):
    updated = await update_rule(rule_id, payload)
    if not updated:
        return {"status": "not_found", "rule_id": rule_id}
    # Force refresh so the change is picked up immediately
    await _load_active_rules(force=True)
    return {"status": "updated", "rule_id": rule_id}


def main():
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=DATA_QUALITY_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
