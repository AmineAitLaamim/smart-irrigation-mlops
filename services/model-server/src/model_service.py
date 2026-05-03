from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MLFLOW_REGISTERED_MODEL_NAME = os.getenv(
    "MLFLOW_REGISTERED_MODEL_NAME",
    "smart-irrigation-soil-moisture",
)
MLFLOW_PRODUCTION_STAGE = os.getenv("MLFLOW_PRODUCTION_STAGE", "Production")
MODEL_RELOAD_INTERVAL_SECONDS = int(os.getenv("MODEL_RELOAD_INTERVAL_SECONDS", "60"))


@dataclass(frozen=True)
class LoadedModelInfo:
    version: str
    stage: str
    source: str
    loaded_at: str


class FallbackRegressor:
    def predict(self, rows: list[list[float]]) -> list[float]:
        return [sum(row) / len(row) if row else 0.0 for row in rows]


class ModelRegistry:
    def __init__(self) -> None:
        self._model: Any = FallbackRegressor()
        self._info = LoadedModelInfo(
            version="fallback",
            stage="None",
            source="local-fallback",
            loaded_at=datetime.now(timezone.utc).isoformat(),
        )
        self._lock = asyncio.Lock()

    @property
    def info(self) -> LoadedModelInfo:
        return self._info

    async def predict(self, features: list[float]) -> tuple[float, tuple[float, float]]:
        async with self._lock:
            prediction = float(self._model.predict([features])[0])
        confidence = max(0.05, abs(prediction) * 0.1)
        return prediction, (prediction - confidence, prediction + confidence)

    async def reload(self) -> LoadedModelInfo:
        try:
            import mlflow
            from mlflow import MlflowClient
            from mlflow.exceptions import MlflowException
        except ImportError:
            return self._info

        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        client = MlflowClient()
        try:
            versions = client.get_latest_versions(
                MLFLOW_REGISTERED_MODEL_NAME,
                stages=[MLFLOW_PRODUCTION_STAGE],
            )
        except MlflowException as exc:
            logger.warning(
                "Falling back to local model because MLflow registry lookup failed for %s: %s",
                MLFLOW_REGISTERED_MODEL_NAME,
                exc,
            )
            return self._info
        if not versions:
            return self._info

        latest = versions[0]
        model_uri = f"models:/{MLFLOW_REGISTERED_MODEL_NAME}/{MLFLOW_PRODUCTION_STAGE}"
        try:
            loaded_model = mlflow.pyfunc.load_model(model_uri)
        except MlflowException as exc:
            logger.warning("Falling back to local model because MLflow model load failed: %s", exc)
            return self._info

        class PyfuncAdapter:
            def __init__(self, inner: Any) -> None:
                self.inner = inner

            def predict(self, rows: list[list[float]]) -> list[float]:
                try:
                    return [float(value) for value in self.inner.predict(rows)]
                except Exception:
                    import pandas as pd

                    frame = pd.DataFrame(rows)
                    return [float(value) for value in self.inner.predict(frame)]

        async with self._lock:
            self._model = PyfuncAdapter(loaded_model)
            self._info = LoadedModelInfo(
                version=str(latest.version),
                stage=MLFLOW_PRODUCTION_STAGE,
                source=model_uri,
                loaded_at=datetime.now(timezone.utc).isoformat(),
            )
        return self._info

    async def monitoring_payload(self) -> dict[str, Any]:
        return asdict(self._info)


async def grpc_handler(registry: ModelRegistry, payload: bytes) -> bytes:
    data = json.loads(payload.decode("utf-8"))
    features = [float(value) for value in data["features"]]
    prediction, interval = await registry.predict(features)
    response = {
        "prediction": prediction,
        "confidence_interval": [interval[0], interval[1]],
        "model_version": registry.info.version,
    }
    return json.dumps(response).encode("utf-8")
