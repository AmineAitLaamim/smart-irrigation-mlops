import asyncio
import json
import logging
import os

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis.asyncio import Redis
from redis.asyncio.client import PubSub

from .alert_handler import AlertHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Notification Service")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
REDIS_CHANNEL_ALERTS_ANOMALY = os.getenv("REDIS_CHANNEL_ALERTS_ANOMALY", "alerts:anomaly")
REDIS_CHANNEL_IRRIGATION_TRIGGERED = os.getenv(
    "REDIS_CHANNEL_IRRIGATION_TRIGGERED", "irrigation:triggered"
)

handler = AlertHandler()
redis_client: Redis | None = None
pubsub: PubSub | None = None
listener_task: asyncio.Task | None = None


async def redis_listener() -> None:
    assert pubsub is not None
    logger.info(
        "Subscribed to Redis channels: %s, %s",
        REDIS_CHANNEL_ALERTS_ANOMALY,
        REDIS_CHANNEL_IRRIGATION_TRIGGERED,
    )
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                channel = message["channel"]
                try:
                    data = json.loads(message["data"])
                except json.JSONDecodeError:
                    data = {"raw": message["data"]}
                severity = str(data.get("severity", "info")).lower()
                if not handler.should_dispatch(severity):
                    continue
                logger.info("Alert on %s: severity=%s", channel, severity)
                asyncio.create_task(handler.dispatch_alert({**data, "channel": channel}, "redis"))
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        raise


@app.on_event("startup")
async def startup() -> None:
    global redis_client, pubsub, listener_task
    redis_client = Redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(REDIS_CHANNEL_ALERTS_ANOMALY, REDIS_CHANNEL_IRRIGATION_TRIGGERED)
    listener_task = asyncio.create_task(redis_listener())


@app.on_event("shutdown")
async def shutdown() -> None:
    global redis_client, pubsub, listener_task
    if listener_task is not None:
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass
        listener_task = None
    if pubsub is not None:
        await pubsub.unsubscribe()
        await pubsub.close()
        pubsub = None
    if redis_client is not None:
        await redis_client.close()
        redis_client = None
    handler.shutdown()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    return PlainTextResponse(generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST)


@app.post("/alerts/webhook")
async def alertmanager_webhook(request: Request):
    payload = await request.json()
    alerts = payload.get("alerts", [])
    for alert in alerts:
        normalized = handler.normalize_alertmanager_alert(
            alert,
            payload.get("status", "firing"),
        )
        if handler.should_dispatch(normalized["severity"]):
            await handler.dispatch_alert(normalized, "alertmanager")
    return {"status": "processed", "alerts": len(alerts)}
