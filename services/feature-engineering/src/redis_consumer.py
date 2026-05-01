import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict

import redis.asyncio as redis

from .database import stats
from .etl import run_streaming

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
REDIS_CHANNEL_INGESTION_PROCESSED = os.getenv(
    "REDIS_CHANNEL_INGESTION_PROCESSED", "ingestion:processed"
)
REDIS_CHANNEL_FEATURES_COMPUTED = os.getenv(
    "REDIS_CHANNEL_FEATURES_COMPUTED", "features:computed"
)


class RedisConsumer:
    def __init__(self):
        self._redis: redis.Redis | None = None
        self._pubsub: redis.client.PubSub | None = None
        self._running = False

    async def connect(self) -> None:
        self._redis = redis.from_url(REDIS_URL, decode_responses=True)
        self._pubsub = self._redis.pubsub()
        await self._pubsub.subscribe(REDIS_CHANNEL_INGESTION_PROCESSED)

    async def disconnect(self) -> None:
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()

    async def _publish_computed(self, payload: Dict[str, Any]) -> None:
        if self._redis:
            await self._redis.publish(
                REDIS_CHANNEL_FEATURES_COMPUTED, json.dumps(payload)
            )

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

        if not zone_id or not sensor_id:
            await stats.increment(error=True)
            print("Missing zone_id or sensor_id in ingestion:processed message")
            return

        features = await run_streaming(zone_id, sensor_id)

        await self._publish_computed({
            "zone_id": zone_id,
            "sensor_id": sensor_id,
            "timestamp": timestamp,
            "computed_at": datetime.utcnow().isoformat(),
            "features": features,
        })

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
