import asyncio
import json
import os
from typing import Any, Dict

import redis.asyncio as redis

from .database import db, stats
from .quality_engine import evaluate_reading, insert_quality_anomalies, update_sensor_health_gauge

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
REDIS_CHANNEL_INGESTION_PROCESSED = os.getenv(
    "REDIS_CHANNEL_INGESTION_PROCESSED", "ingestion:processed"
)
HEALTH_UPDATE_INTERVAL_SECONDS = int(os.getenv("HEALTH_UPDATE_INTERVAL_SECONDS", "60"))


class RedisConsumer:
    def __init__(self):
        self._redis: redis.Redis | None = None
        self._pubsub: redis.client.PubSub | None = None
        self._running = False
        self._health_task: asyncio.Task | None = None

    async def connect(self) -> None:
        self._redis = redis.from_url(REDIS_URL, decode_responses=True)
        self._pubsub = self._redis.pubsub()
        await self._pubsub.subscribe(REDIS_CHANNEL_INGESTION_PROCESSED)

    async def disconnect(self) -> None:
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()

    async def _health_loop(self) -> None:
        while self._running:
            try:
                await update_sensor_health_gauge()
            except Exception as exc:
                print(f"Health gauge update error: {exc}")
            await asyncio.sleep(HEALTH_UPDATE_INTERVAL_SECONDS)

    async def _process_one(self, message: Dict[str, Any]) -> None:
        raw = message.get("data")
        if not raw:
            return

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            await stats.increment(error=True)
            print(f"Invalid JSON on {REDIS_CHANNEL_INGESTION_PROCESSED}: {exc}")
            return

        zone_id = data.get("zone_id")
        sensor_id = data.get("sensor_id")
        timestamp = data.get("timestamp")
        valid = data.get("valid", True)
        sensor_type = data.get("sensor_type", "moisture")

        if not zone_id or not sensor_id:
            await stats.increment(error=True)
            print("Missing zone_id or sensor_id in ingestion:processed message")
            return

        # For invalid readings the data-ingestion already wrote the anomaly;
        # we still run malfunction checks (e.g. a stuck invalid value is useful info).
        value = data.get("value")
        if value is None:
            # ingestion:processed does not carry the raw value; read latest from DB
            row = await db.fetchrow(
                """
                SELECT moisture, temperature
                FROM sensor_readings
                WHERE zone_id = $1 AND sensor_id = $2
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                zone_id,
                sensor_id,
            )
            if not row:
                return
            if sensor_type == "moisture":
                value = row["moisture"]
            elif sensor_type == "temperature":
                temp = row["temperature"]
                value = temp if temp is not None and temp != -1.0 else None
            else:
                value = row["moisture"]
            if value is None:
                return

        anomalies = await evaluate_reading(
            zone_id=zone_id,
            sensor_id=sensor_id,
            timestamp=timestamp,
            value=value,
            sensor_type=sensor_type,
            is_valid=valid,
        )

        if anomalies:
            await insert_quality_anomalies(anomalies)

    async def run(self) -> None:
        self._running = True
        self._health_task = asyncio.create_task(self._health_loop())
        try:
            async for message in self._pubsub.listen():
                if not self._running:
                    break
                if message.get("type") == "message":
                    try:
                        await self._process_one(message)
                    except Exception as exc:
                        await stats.increment(error=True)
                        print(f"Error processing message: {exc}")
        except asyncio.CancelledError:
            pass


consumer = RedisConsumer()
