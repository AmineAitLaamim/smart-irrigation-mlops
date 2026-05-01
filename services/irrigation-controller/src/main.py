from __future__ import annotations

import asyncio
import json
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

    async def evaluate_prediction(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        zone_id = payload["zone_id"]
        prediction = float(payload["prediction"])
        thresholds = await self._zone_thresholds(zone_id)
        if not thresholds:
            return None

        rainfall_proxy = await self._latest_rain_proxy(zone_id)
        if prediction >= thresholds["moisture_min"]:
            return None
        if rainfall_proxy >= 15:
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
        return event

    async def store_event(self, event: dict[str, Any]) -> None:
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
        self._running = True
        while self._running:
            try:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if not message:
                    await asyncio.sleep(1)
                    continue
                payload = json.loads(message["data"])
                await self.evaluate_prediction(payload)
            except asyncio.CancelledError:
                raise
            except Exception:
                await asyncio.sleep(1)

    async def list_events(self, zone_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = """
            SELECT triggered_at, zone_id, trigger_reason, recommended_volume, status
            FROM irrigation_events
            WHERE ($1::varchar IS NULL OR zone_id = $1)
            ORDER BY triggered_at DESC
            LIMIT $2
        """
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


@app.get("/v1/irrigation/events")
async def irrigation_events(zone_id: str | None = Query(default=None), limit: int = 100):
    return {"events": await controller.list_events(zone_id=zone_id, limit=limit)}


def main() -> None:
    uvicorn.run("src.main:app", host="0.0.0.0", port=IRRIGATION_CONTROLLER_PORT, log_level="info")


if __name__ == "__main__":
    main()
