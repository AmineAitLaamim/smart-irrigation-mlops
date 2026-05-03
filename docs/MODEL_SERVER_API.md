# Model Server API

## Endpoints

### `POST /v1/predict`
Request:

```json
{
  "zone_id": "zone_a",
  "sensor_id": "sensor_a1",
  "features": [0.21, 0.34, 0.18]
}
```

Response:

```json
{
  "zone_id": "zone_a",
  "sensor_id": "sensor_a1",
  "predicted_moisture": 0.243,
  "confidence_interval": [0.219, 0.267],
  "model_version": "3"
}
```

### `GET /v1/model/info`
Returns the loaded model metadata, stage, source URI, and load timestamp.

### `GET /v1/model/version`
Returns the active model version and stage.

## Notes
- REST runs on port `8501`.
- The internal gRPC prediction handler runs on port `5001`.
- Prediction latency, throughput, and errors are exported on `/metrics`.
