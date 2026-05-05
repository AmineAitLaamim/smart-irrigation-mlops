from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import asyncpg
from fastapi import FastAPI, Query
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest
import redis.asyncio as redis
from starlette.responses import Response
import uvicorn

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://irrigation_user:changeme@timescaledb:5432/irrigation_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
REDIS_CHANNEL_PREDICTIONS_NEW = os.getenv("REDIS_CHANNEL_PREDICTIONS_NEW", "predictions:new")
IRRIGATION_CONTROLLER_PORT = int(os.getenv("IRRIGATION_CONTROLLER_PORT", "8503"))

IRRIGATION_EVENTS = Counter("irrigation_controller_events_total", "Irrigation events generated")
LAST_RECOMMENDED_VOLUME = Gauge("irrigation_controller_last_recommended_volume", "Last recommended irrigation volume")


class IrrigationController:
    def __init__(self) -> None:
        self.db_pool: asyncpg.Pool | None = None
        self.redis_client: redis.Redis | None = None
        self.pubsub: redis.client.PubSub | None = None
        self._running = False

    async def connect(self) -> None:
        self.db_pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=5)
        self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        self.pubsub = self.redis_client.pubsub()
        await self.pubsub.subscribe(REDIS_CHANNEL_PREDICTIONS_NEW)

    async def disconnect(self) -> None:
        self._running = False
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()
        if self.db_pool:
            await self.db_pool.close()

    async def _zone_thresholds(self, zone_id: str) -> dict[str, Any] | None:
        if not self.db_pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT zone_id, moisture_min, moisture_max, soil_type
                FROM zones
                WHERE zone_id = $1
                """,
                zone_id,
            )
        return dict(row) if row else None

    async def _latest_rain_proxy(self, zone_id: str) -> float:
        if not self.db_pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT feature_value
                FROM feature_references
                WHERE zone_id = $1
                  AND feature_name = 'evapotranspiration_proxy'
                ORDER BY computed_at DESC
                LIMIT 1
                """,
                zone_id,
            )
        return float(row["feature_value"]) if row and row["feature_value"] is not None else 0.0

    async def _recent_event_exists(self, zone_id: str, minutes: int = 10) -> bool:
        if not self.db_pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 1 FROM irrigation_events
                WHERE zone_id = $1
                  AND triggered_at > NOW() - INTERVAL '10 minutes'
                LIMIT 1
                """,
                zone_id,
            )
        return row is not None

    async def evaluate_prediction(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        zone_id = payload["zone_id"]
        prediction = float(payload["prediction"])
        thresholds = await self._zone_thresholds(zone_id)
        if not thresholds:
            logger.debug(f"No thresholds found for zone {zone_id}")
            return None

        logger.debug(f"Zone {zone_id}: prediction={prediction}, threshold_min={thresholds['moisture_min']}")

        if prediction >= thresholds["moisture_min"]:
            return None

        if await self._recent_event_exists(zone_id, minutes=10):
            logger.debug(f"Skipping irrigation for zone {zone_id}: recent event exists")
            return None

        deficit = max(0.0, thresholds["moisture_min"] - prediction)
        recommended_volume = round(deficit * 100, 3)
        event = {
            "zone_id": zone_id,
            "trigger_reason": "predicted_moisture_below_threshold",
            "recommended_volume": recommended_volume,
            "predicted_moisture": prediction,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.store_event(event)
        logger.info(f"Irrigation TRIGGERED for zone {zone_id}: volume={recommended_volume}")

        asyncio.create_task(self._execute_irrigation(event["zone_id"], event["recommended_volume"]))

        return event

    async def _execute_irrigation(self, zone_id: str, volume: float) -> None:
        await asyncio.sleep(5)
        if not self.db_pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE irrigation_events
                SET status = 'completed',
                    actual_volume = $1,
                    duration_seconds = 300,
                    completed_at = NOW()
                WHERE id = (
                    SELECT id FROM irrigation_events
                    WHERE zone_id = $2 AND status = 'pending'
                    ORDER BY triggered_at DESC
                    LIMIT 1
                )
                """,
                volume,
                zone_id,
            )
        logger.info(f"Irrigation COMPLETED for zone {zone_id}: volume={volume}")

        if self.redis_client:
            await self.redis_client.publish(
                "irrigation:triggered",
                json.dumps({
                    "zone_id": zone_id,
                    "status": "completed",
                    "volume": volume,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                })
            )

    async def store_event(self, event: dict[str, Any]) -> None:
        if not self.db_pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO irrigation_events (
                    triggered_at,
                    zone_id,
                    trigger_reason,
                    recommended_volume,
                    status
                )
                VALUES ($1, $2, $3, $4, 'pending')
                """,
                datetime.now(timezone.utc),
                event["zone_id"],
                event["trigger_reason"],
                event["recommended_volume"],
            )
        IRRIGATION_EVENTS.inc()
        LAST_RECOMMENDED_VOLUME.set(event["recommended_volume"])

    async def run(self) -> None:
        if not self.pubsub:
            raise RuntimeError("Redis pubsub not initialized. Call connect() first.")
        self._running = True
        try:
            async for message in self.pubsub.listen():
                if not self._running:
                    break
                if message.get("type") == "message":
                    try:
                        logger.debug(f"Raw message: {message}")
                        payload = json.loads(message["data"])
                        await self.evaluate_prediction(payload)
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
        except asyncio.CancelledError:
            pass

    async def list_events(self, zone_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = """
            SELECT triggered_at, zone_id, trigger_reason, recommended_volume, status
            FROM irrigation_events
            WHERE ($1::varchar IS NULL OR zone_id = $1)
            ORDER BY triggered_at DESC
            LIMIT $2
        """
        if not self.db_pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, zone_id, limit)
        return [dict(row) for row in rows]


controller = IrrigationController()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await controller.connect()
    task = asyncio.create_task(controller.run())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await controller.disconnect()


app = FastAPI(title="Irrigation Controller", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "irrigation-controller"}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/v1/irrigation/recent")
async def irrigation_recent(zone_id: str | None = Query(default=None), limit: int = 100):
    return await controller.list_events(zone_id=zone_id, limit=limit)


@app.get("/v1/irrigation/events")
async def irrigation_events(zone_id: str | None = Query(default=None), limit: int = 100):
    return {"events": await controller.list_events(zone_id=zone_id, limit=limit)}


def main() -> None:
    uvicorn.run("src.main:app", host="0.0.0.0", port=IRRIGATION_CONTROLLER_PORT, log_level="info")


if __name__ == "__main__":
    main()
