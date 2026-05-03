import asyncio
import json
import os
from typing import Any, Dict

import redis.asyncio as redis

from .database import stats
from .db_writer import insert_data_quality_event, insert_sensor_reading
from .validator import validate_reading

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
REDIS_CHANNEL_SENSOR_DATA = os.getenv(
    "REDIS_CHANNEL_SENSOR_DATA", "sensor:data"
)
REDIS_CHANNEL_INGESTION_PROCESSED = os.getenv(
    "REDIS_CHANNEL_INGESTION_PROCESSED", "ingestion:processed"
)


class RedisConsumer:
    def __init__(self):
        self._redis: redis.Redis | None = None
        self._pubsub: redis.client.PubSub | None = None
        self._running = False

    async def connect(self) -> None:
        self._redis = redis.from_url(REDIS_URL, decode_responses=True)
        self._pubsub = self._redis.pubsub()
        await self._pubsub.subscribe(REDIS_CHANNEL_SENSOR_DATA)

    async def disconnect(self) -> None:
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()

    async def _publish_processed(self, payload: Dict[str, Any]) -> None:
        if self._redis:
            await self._redis.publish(
                REDIS_CHANNEL_INGESTION_PROCESSED, json.dumps(payload)
            )

    async def _process_one(self, message: Dict[str, Any]) -> None:
        raw = message.get("data")
        if not raw:
            return

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            await stats.increment(processed=True, error=True)
            print(f"Invalid JSON on {REDIS_CHANNEL_SENSOR_DATA}: {exc}")
            return

        await stats.increment(processed=True)

        result = await validate_reading(data)

        if result.is_valid:
            await insert_sensor_reading(
                zone_id=data.get("zone_id"),
                sensor_id=data.get("sensor_id"),
                timestamp=data.get("timestamp"),
                sensor_type=result.sensor_type,
                moisture=data.get("moisture"),
                temperature=data.get("temperature"),
                value=data.get("value"), # Legacy support
            )
            await stats.increment(valid=True)
        else:
            for anomaly in result.anomalies:
                # unknown_zone cannot be inserted because zone_id FK fails
                if anomaly.get("event_type") == "unknown_zone":
                    await stats.increment(anomaly=True)
                    continue
                await insert_data_quality_event(anomaly)
                await stats.increment(anomaly=True)

        # Notify downstream services
        await self._publish_processed(
            {
                "zone_id": data.get("zone_id"),
                "sensor_id": data.get("sensor_id"),
                "timestamp": data.get("timestamp"),
                "valid": result.is_valid,
                "sensor_type": result.sensor_type,
            }
        )

    async def run(self) -> None:
        self._running = True
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
