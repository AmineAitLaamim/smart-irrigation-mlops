from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response
import uvicorn

try:
    from .model_service import MODEL_RELOAD_INTERVAL_SECONDS, ModelRegistry, grpc_handler
except (ImportError, ValueError):
    from model_service import MODEL_RELOAD_INTERVAL_SECONDS, ModelRegistry, grpc_handler  # type: ignore

MODEL_SERVER_REST_PORT = int(os.getenv("MODEL_SERVER_REST_PORT", "8501"))
MODEL_SERVER_GRPC_PORT = int(os.getenv("MODEL_SERVER_GRPC_PORT", "5001"))

PREDICTION_COUNTER = Counter("model_server_predictions_total", "Prediction calls")
ERROR_COUNTER = Counter("model_server_errors_total", "Prediction errors")
PREDICTION_LATENCY = Histogram("model_server_prediction_latency_seconds", "Prediction latency")

registry = ModelRegistry()


class PredictRequest(BaseModel):
    zone_id: str
    sensor_id: str
    features: list[float] = Field(default_factory=list)


class PredictResponse(BaseModel):
    zone_id: str
    sensor_id: str
    predicted_moisture: float
    confidence_interval: list[float]
    model_version: str


async def _grpc_server_task() -> None:
    try:
        import grpc
    except ImportError:
        while True:
            await asyncio.sleep(3600)

    async def predict_behavior(request: bytes, context: Any) -> bytes:
        return await grpc_handler(registry, request)

    server = grpc.aio.server()
    handler = grpc.method_handlers_generic_handler(
        "smartirrigation.PredictService",
        {
            "Predict": grpc.unary_unary_rpc_method_handler(
                predict_behavior,
                request_deserializer=lambda payload: payload,
                response_serializer=lambda payload: payload,
            )
        },
    )
    server.add_generic_rpc_handlers((handler,))
    server.add_insecure_port(f"[::]:{MODEL_SERVER_GRPC_PORT}")
    await server.start()
    try:
        await server.wait_for_termination()
    finally:
        await server.stop(5)


async def _reload_loop() -> None:
    while True:
        try:
            await registry.reload()
        except Exception:
            ERROR_COUNTER.inc()
        await asyncio.sleep(MODEL_RELOAD_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await registry.reload()
    grpc_task = asyncio.create_task(_grpc_server_task())
    reload_task = asyncio.create_task(_reload_loop())
    yield
    grpc_task.cancel()
    reload_task.cancel()
    for task in (grpc_task, reload_task):
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Model Server", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "model-server"}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/v1/model/info")
async def model_info():
    return {"status": "ok", **asdict(registry.info)}


@app.get("/v1/model/version")
async def model_version():
    return {"version": registry.info.version, "stage": registry.info.stage}


@app.post("/v1/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    PREDICTION_COUNTER.inc()
    with PREDICTION_LATENCY.time():
        try:
            prediction, interval = await registry.predict(request.features)
        except Exception:
            ERROR_COUNTER.inc()
            raise
    return PredictResponse(
        zone_id=request.zone_id,
        sensor_id=request.sensor_id,
        predicted_moisture=prediction,
        confidence_interval=[interval[0], interval[1]],
        model_version=registry.info.version,
    )


def main() -> None:
    uvicorn.run("src.main:app", host="0.0.0.0", port=MODEL_SERVER_REST_PORT, log_level="info")


if __name__ == "__main__":
    main()
