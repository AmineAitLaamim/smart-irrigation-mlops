# Model Server Documentation

## Overview

The Model Server is a FastAPI service that serves ML predictions for soil moisture forecasting. It:
- Loads production models from MLflow (stored in MinIO)
- Serves predictions via REST API
- Supports gRPC for high-performance inference
- Auto-reloads models when new versions are promoted to Production

**Location:** `services/model-server/src/main.py`

**Ports:**
- REST API: 8501
- gRPC: 5001

---

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           MODEL SERVER                                          │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐ │
│  │                         FastAPI Application                              │ │
│  │                                                                          │ │
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐  │ │
│  │  │   /health   │   │  /metrics   │   │/v1/model/*  │   │/v1/predict  │  │ │
│  │  └─────────────┘   └─────────────┘   └─────────────┘   └──────┬──────┘  │ │
│  │                                                              │            │ │
│  │                           ┌──────────────────────────────────┘           │ │
│  │                           ▼                                              │ │
│  │                   ┌───────────────┐                                      │ │
│  │                   │ModelRegistry  │                                      │ │
│  │                   │  (in-memory)  │                                      │ │
│  │                   └───────┬───────┘                                      │ │
│  └────────────────────────────┼────────────────────────────────────────────┘ │
│                               │                                               │
│  ┌────────────────────────────┼────────────────────────────────────────────┐ │
│  │                     Background Tasks                                    │ │
│  │                                                                          │ │
│  │  ┌──────────────────┐        ┌──────────────────┐                      │ │
│  │  │  Model Reload    │        │   gRPC Server    │                      │ │
│  │  │  Loop (60 sec)   │        │   (port 5001)    │                      │ │
│  │  └──────────────────┘        └──────────────────┘                      │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────┬──────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL SERVICES                                       │
│                                                                                 │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐          │
│  │     MLflow       │◄───│      MinIO       │◄───│    Airflow       │          │
│  │  (model registry)│    │ (artifact store)│    │     (training)  │          │
│  │    port 5000    │    │    port 9000    │    │                  │          │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘          │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### ModelRegistry Class

The `ModelRegistry` manages model loading and prediction:

```python
# services/model-server/src/model_service.py
class ModelRegistry:
    def __init__(self) -> None:
        self._model: Any = FallbackRegressor()  # Default model
        self._info = LoadedModelInfo(...)       # Model metadata
        self._lock = asyncio.Lock()             # Thread-safe access
```

**Key Properties:**
- `_model`: In-memory loaded model (PyFunc wrapper)
- `_info`: Model metadata (version, stage, source, loaded_at)
- `_lock`: Async lock for thread-safe prediction

### Prediction

```python
async def predict(self, features: list[float]) -> tuple[float, tuple[float, float]]:
    async with self._lock:
        prediction = float(self._model.predict([features])[0])

    # Confidence interval: ±10% of prediction (min 0.05)
    confidence = max(0.05, abs(prediction) * 0.1)
    return prediction, (prediction - confidence, prediction + confidence)
```

### Model Reload

```python
async def reload(self) -> LoadedModelInfo:
    # 1. Query MLflow for Production stage model
    versions = client.get_latest_versions(
        MLFLOW_REGISTERED_MODEL_NAME,
        stages=[MLFLOW_PRODUCTION_STAGE],
    )

    # 2. Load model from MLflow (pulls from MinIO)
    model_uri = f"models:/{MLFLOW_REGISTERED_MODEL_NAME}/Production"
    loaded_model = mlflow.pyfunc.load_model(model_uri)

    # 3. Update in-memory model
    async with self._lock:
        self._model = PyfuncAdapter(loaded_model)
        self._info = LoadedModelInfo(...)
```

---

## API Endpoints

### GET /health

Health check endpoint.

```bash
curl http://localhost:8501/health
```

**Response:**
```json
{"status": "healthy", "service": "model-server"}
```

### GET /metrics

Prometheus metrics endpoint.

```bash
curl http://localhost:8501/metrics
```

**Metrics:**
- `model_server_predictions_total` - Counter of prediction calls
- `model_server_errors_total` - Counter of prediction errors
- `model_server_prediction_latency_seconds` - Histogram of prediction latency

### GET /v1/model/info

Get current model information.

```bash
curl http://localhost:8501/v1/model/info
```

**Response:**
```json
{
  "status": "ok",
  "version": "5",
  "stage": "Production",
  "source": "models:/smart-irrigation-soil-moisture/Production",
  "loaded_at": "2026-05-03T12:00:00+00:00"
}
```

### GET /v1/model/version

Get model version and stage.

```bash
curl http://localhost:8501/v1/model/version
```

**Response:**
```json
{
  "version": "5",
  "stage": "Production"
}
```

### POST /v1/predict

Make a prediction.

**Request:**
```bash
curl -X POST http://localhost:8501/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "zone_id": "2",
    "sensor_id": "2-s1",
    "features": [45.2, 22.5]
  }'
```

**Features:**
- Index 0: Current moisture
- Index 1: Current temperature (or 0.0 as default)

**Response:**
```json
{
  "zone_id": "2",
  "sensor_id": "2-s1",
  "predicted_moisture": 38.5,
  "confidence_interval": [34.65, 42.35],
  "model_version": "5"
}
```

---

## Model Loading Process

### Startup Flow

```
1. FastAPI app starts
   │
   ▼
2. lifespan() triggers
   │
   ▼
3. registry.reload() called
   │   │
   │   ▼
   │   Query MLflow for Production model
   │   │
   │   ▼
   │   Load model from MinIO via MLflow
   │   │
   │   ▼
   │   Store in memory as PyfuncAdapter
   │
   ▼
4. Background tasks start:
   - _reload_loop() - reloads every 60 seconds
   - _grpc_server_task() - starts gRPC server
```

### Model Reload Flow

```
Every 60 seconds:
   │
   ▼
registry.reload() called
   │
   ▼
Query MLflow for Production stage
   │
   ▼
Check if version changed
   │
   ├── Same version → No action
   │
   ▼
New version found
   │
   ▼
Load from MinIO (mlflow.pyfunc.load_model)
   │
   ▼
Update in-memory model (with lock)
   │
   ▼
Update model info metadata
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MLFLOW_TRACKING_URI` | `http://mlflow:5000` | MLflow server URL |
| `MLFLOW_REGISTERED_MODEL_NAME` | `smart-irrigation-soil-moisture` | Model name in MLflow |
| `MLFLOW_PRODUCTION_STAGE` | `Production` | Stage to load from |
| `MODEL_SERVER_REST_PORT` | `8501` | REST API port |
| `MODEL_SERVER_GRPC_PORT` | `5001` | gRPC port |
| `MODEL_RELOAD_INTERVAL_SECONDS` | `60` | How often to check for new model versions |

### Docker Configuration

```yaml
model-server:
  image: model-server:latest
  ports:
    - "8501:8501"  # REST API
    - "5001:5001"  # gRPC
  environment:
    - MLFLOW_TRACKING_URI=http://mlflow:5000
    - MLFLOW_REGISTERED_MODEL_NAME=smart-irrigation-soil-moisture
  depends_on:
    - mlflow
    - minio
```

---

## Error Handling

### Fallback Model

If MLflow is unavailable, the server uses a fallback regressor:

```python
class FallbackRegressor:
    def predict(self, rows: list[list[float]]) -> list[float]:
        # Simple fallback: return average of features
        return [sum(row) / len(row) if row else 0.0 for row in rows]
```

This ensures the service remains available even if MLflow/MinIO is down.

### Logging

```python
logger.warning(
    "Falling back to local model because MLflow registry lookup failed: %s",
    exc,
)
```

---

## Integration with Other Services

### Airflow DAG

Airflow calls the model server for predictions:

```python
# In scheduled_zone_predictions task
response = await client.post(
    f"{MODEL_SERVER_REST_URL}/v1/predict",
    json={
        "zone_id": row["zone_id"],
        "sensor_id": row["sensor_id"],
        "features": [moisture_value, temperature_value],
    },
)
```

### Irrigation Controller

The irrigation controller receives predictions from Airflow via Redis - it does **not** call the model server directly.

---

## gRPC Support

The model server also exposes a gRPC endpoint for high-performance inference:

```python
# gRPC handler
async def grpc_handler(registry: ModelRegistry, payload: bytes) -> bytes:
    data = json.loads(payload.decode("utf-8"))
    features = [float(value) for value in data["features"]]
    prediction, interval = await registry.predict(features)

    return json.dumps({
        "prediction": prediction,
        "confidence_interval": [interval[0], interval[1]],
        "model_version": registry.info.version,
    }).encode("utf-8")
```

---

## Testing

### Test Prediction Endpoint

```bash
# Test with valid features
curl -X POST http://localhost:8501/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"zone_id": "1", "sensor_id": "1-s1", "features": [40.0, 25.0]}'

# Check model info
curl http://localhost:8501/v1/model/info

# Check health
curl http://localhost:8501/health
```

### Integration Test

```python
# services/model-server/tests/integration/test_endpoints.py
def test_predict():
    response = client.post("/v1/predict", json={
        "zone_id": "test",
        "sensor_id": "test-s1",
        "features": [40.0, 25.0]
    })
    assert response.status_code == 200
    data = response.json()
    assert "predicted_moisture" in data
    assert "confidence_interval" in data
```

---

## Monitoring

### Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `model_server_predictions_total` | Counter | Total predictions made |
| `model_server_errors_total` | Counter | Total errors |
| `model_server_prediction_latency_seconds` | Histogram | Prediction time |

View in Prometheus/Grafana dashboard.

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Framework | FastAPI + Uvicorn |
| Model Loading | MLflow pyfunc (from MinIO) |
| In-memory Model | PyfuncAdapter wrapper |
| Auto-reload | Every 60 seconds |
| Fallback | FallbackRegressor if MLflow unavailable |
| API | REST (8501) + gRPC (5001) |
| Integration | Airflow calls REST API for predictions |

The Model Server bridges MLflow/MinIO with the prediction pipeline, ensuring the latest production model is always available for inference.