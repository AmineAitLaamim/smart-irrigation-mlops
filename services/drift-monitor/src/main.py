from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

import asyncpg
import httpx
from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest
import redis.asyncio as redis
from starlette.responses import Response
import uvicorn

try:
    from .drift_detector import DriftSummary, summarize_drift
except (ImportError, ValueError):
    from drift_detector import DriftSummary, summarize_drift  # type: ignore

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://irrigation_user:changeme@timescaledb:5432/irrigation_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
REDIS_CHANNEL_ALERTS_ANOMALY = os.getenv("REDIS_CHANNEL_ALERTS_ANOMALY", "alerts:anomaly")
DRIFT_MONITOR_PORT = int(os.getenv("DRIFT_MONITOR_PORT", "8502"))
DRIFT_SCAN_INTERVAL_SECONDS = int(os.getenv("DRIFT_SCAN_INTERVAL_SECONDS", "60"))

AIRFLOW_URL = os.getenv("AIRFLOW_URL", "http://airflow:8080")
AIRFLOW_ADMIN_USER = os.getenv("AIRFLOW_ADMIN_USER", "admin")
AIRFLOW_ADMIN_PASSWORD = os.getenv("AIRFLOW_ADMIN_PASSWORD", "airflow_dev")

logging.basicConfig(level=logging.INFO)

PAGE_HINKLEY_GAUGE = Gauge("drift_monitor_page_hinkley_score", "Latest Page-Hinkley score")
KL_GAUGE = Gauge("drift_monitor_kl_divergence", "Latest KL divergence score")
ERROR_GAUGE = Gauge("drift_monitor_mean_error", "Latest rolling mean prediction error")


class DriftMonitor:
    def __init__(self) -> None:
        self.db_pool: asyncpg.Pool | None = None
        self.redis_client: redis.Redis | None = None
        self._latest = DriftSummary(0.0, 0.0, 0.0, False)
        self._running = False
        self._last_triggered_at: datetime | None = None
        self.logger = logging.getLogger(__name__)

    async def connect(self) -> None:
        self.db_pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=5)
        self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)

    async def disconnect(self) -> None:
        self._running = False
        if self.redis_client:
            await self.redis_client.close()
        if self.db_pool:
            await self.db_pool.close()

    async def _fetch_prediction_window(self) -> tuple[list[float], list[float]]:
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        if not self.db_pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT prediction, confidence
                FROM model_predictions
                WHERE predicted_at >= $1
                ORDER BY predicted_at DESC
                LIMIT 200
                """,
                since,
            )
        current = [float(row["prediction"]) for row in rows[:100]]
        reference = [float(row["prediction"]) for row in rows[100:200]]
        return reference, current

    async def trigger_retraining_dag(self) -> None:
        now = datetime.now(timezone.utc)
        if self._last_triggered_at and (now - self._last_triggered_at) < timedelta(hours=1):
            self.logger.info("Skipping Airflow trigger (cooldown active).")
            return
            
        url = f"{AIRFLOW_URL.rstrip('/')}/api/v1/dags/smart_irrigation_model_training/dagRuns"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json={"conf": {}},
                    auth=(AIRFLOW_ADMIN_USER, AIRFLOW_ADMIN_PASSWORD),
                    timeout=10.0
                )
                response.raise_for_status()
                self.logger.info("Successfully triggered Airflow retraining DAG.")
                self._last_triggered_at = now
        except Exception as exc:
            self.logger.error("Failed to trigger Airflow DAG: %s", exc)

    async def scan(self) -> DriftSummary:
        reference, current = await self._fetch_prediction_window()
        summary = summarize_drift(reference, current)
        self._latest = summary
        PAGE_HINKLEY_GAUGE.set(summary.page_hinkley_score)
        KL_GAUGE.set(summary.kl_divergence)
        ERROR_GAUGE.set(summary.mean_error)
        if summary.drift_detected:
            if self.redis_client:
                await self.redis_client.publish(
                    REDIS_CHANNEL_ALERTS_ANOMALY,
                    json.dumps(
                        {
                            "type": "model_drift",
                            "detected_at": datetime.now(timezone.utc).isoformat(),
                            **asdict(summary),
                        }
                    ),
                )
            await self.trigger_retraining_dag()
        return summary

    async def run(self) -> None:
        self._running = True
        while self._running:
            try:
                await self.scan()
            except asyncio.CancelledError:
                raise
            except Exception:
                pass
            await asyncio.sleep(DRIFT_SCAN_INTERVAL_SECONDS)

    async def status(self) -> dict:
        return asdict(self._latest)


monitor = DriftMonitor()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await monitor.connect()
    task = asyncio.create_task(monitor.run())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await monitor.disconnect()


app = FastAPI(title="Drift Monitor", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "drift-monitor"}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/v1/drift/status")
async def drift_status():
    return await monitor.status()


def main() -> None:
    uvicorn.run("src.main:app", host="0.0.0.0", port=DRIFT_MONITOR_PORT, log_level="info")


if __name__ == "__main__":
    main()
