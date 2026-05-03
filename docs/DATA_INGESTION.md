# Data Ingestion Service

## Overview

The Data Ingestion Service is a real-time data pipeline that consumes sensor readings from Redis and persists them to PostgreSQL (TimescaleDB). It performs validation, anomaly detection, and forwards processed data to downstream services.

**Location:** `services/data-ingestion/`

**Port:** 8001

---

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          SENSOR SIMULATOR                                      │
│                                                                                 │
│  Produces sensor data to Redis channel: sensor:data                           │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    DATA INGESTION SERVICE (8001)                              │
│                                                                                 │
│  ┌─────────────────────┐    ┌─────────────────────┐    ┌──────────────────┐   │
│  │   Redis Consumer    │───▶│    Validator        │───▶│   DB Writer      │   │
│  │                     │    │                     │    │                  │   │
│  │ - Subscribe         │    │ - Zone bounds       │    │ - sensor_readings│   │
│  │ - Parse JSON        │    │ - Range validation  │    │ - data_quality   │   │
│  │ - Error handling    │    │ - Anomaly detection │    │   _events        │   │
│  └─────────────────────┘    └─────────────────────┘    └──────────────────┘   │
│           │                              │                       │            │
│           ▼                              ▼                       ▼            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      Metrics & Health                                  │   │
│  │                                                                          │   │
│  │  /health     - Status + stats                                          │   │
│  │  /metrics    - Prometheus metrics                                      │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    Downstream Services                                         │
│                                                                                 │
│  - irrigation-controller: listens on ingestion:processed                     │
│  - Airflow: triggered for prediction updates                                   │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                      DATABASE (TimescaleDB)                                    │
│                                                                                 │
│  Tables:                                                                       │
│  - sensor_readings     - Valid sensor readings with timestamps                │
│  - data_quality_events - Anomaly records for monitoring                       │
│  - zones               - Zone configuration with min/max plausible bounds     │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### 1. Sensor Data Input

The service subscribes to Redis channel `sensor:data` and expects JSON messages:

```json
{
  "zone_id": "zone-001",
  "sensor_id": "sensor-001",
  "timestamp": "2026-05-03T10:30:00Z",
  "moisture": 45.2,
  "temperature": 22.5
}
```

**Legacy format (single sensor):**
```json
{
  "zone_id": "zone-001",
  "sensor_id": "sensor-001",
  "timestamp": "2026-05-03T10:30:00Z",
  "type": "moisture",
  "value": 45.2
}
```

### 2. Validation

The validator checks each reading against zone-specific bounds:

1. **Zone existence** - Reject if zone_id not in database
2. **Range validation** - Check moisture/temperature against `min_plausible` and `max_plausible`
3. **Severity assignment** - Warning for minor violations, critical for severe (>150% of max)

### 3. Database Write

- **Valid readings** → `sensor_readings` table
- **Anomalies** → `data_quality_events` table with severity and details

### 4. Downstream Notification

After processing, publishes to `ingestion:processed` channel:

```json
{
  "zone_id": "zone-001",
  "sensor_id": "sensor-001",
  "timestamp": "2026-05-03T10:30:00Z",
  "valid": true,
  "sensor_type": "combined"
}
```

---

## Components

### main.py

FastAPI application with lifespan management:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    await consumer.connect()
    consumer_task = asyncio.create_task(consumer.run())
    yield
    consumer._running = False
    consumer_task.cancel()
    await consumer.disconnect()
    await db.disconnect()
```

**Endpoints:**
- `GET /health` - Health check with stats
- `GET /metrics` - Prometheus metrics

### redis_consumer.py

Async Redis consumer using pubsub:

```python
async def run(self) -> None:
    self._running = True
    try:
        async for message in self._pubsub.listen():
            if message.get("type") == "message":
                await self._process_one(message)
    except asyncio.CancelledError:
        pass
```

### validator.py

Validates readings against zone bounds:

```python
async def validate_reading(sensor_data: Dict[str, Any]) -> ValidationResult:
    bounds = await get_zone_bounds(zone_id)
    # Check moisture and temperature against min_plausible/max_plausible
    return ValidationResult(is_valid=..., anomalies=..., sensor_type=...)
```

### db_writer.py

Database write operations:

```python
async def insert_sensor_reading(
    zone_id: str,
    sensor_id: str,
    timestamp: Any,
    sensor_type: str,
    moisture: float | None = None,
    temperature: float | None = None,
) -> None
```

### database.py

Connection pool and statistics:

```python
@dataclass
class IngestionStats:
    total_processed: int
    valid_readings: int
    anomalies_flagged: int
    last_processed_at: Optional[datetime]
    errors: int
```

---

## Database Schema

### sensor_readings

```sql
CREATE TABLE sensor_readings (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    zone_id UUID NOT NULL,
    sensor_id UUID NOT NULL,
    moisture DOUBLE PRECISION NOT NULL,
    temperature DOUBLE PRECISION,
    -- Hypertable for time-series optimization
);

SELECT create_hypertable('sensor_readings', 'timestamp');
```

### data_quality_events

```sql
CREATE TABLE data_quality_events (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    zone_id UUID NOT NULL,
    sensor_id UUID NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_value DOUBLE PRECISION,
    expected_min DOUBLE PRECISION,
    expected_max DOUBLE PRECISION,
    severity VARCHAR(20) DEFAULT 'warning',
    details TEXT
);
```

### zones

```sql
ALTER TABLE zones ADD COLUMN min_plausible JSONB;
ALTER TABLE zones ADD COLUMN max_plausible JSONB;

-- Example configuration:
UPDATE zones SET 
    min_plausible = '{"moisture": 0, "temperature": -10}',
    max_plausible = '{"moisture": 100, "temperature": 50}'
WHERE zone_id = 'zone-001';
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_INGESTION_PORT` | 8001 | Service port |
| `REDIS_URL` | redis://redis:6379/0 | Redis connection |
| `REDIS_CHANNEL_SENSOR_DATA` | sensor:data | Input channel |
| `REDIS_CHANNEL_INGESTION_PROCESSED` | ingestion:processed | Output channel |
| `DATABASE_URL` | postgresql://...@timescaledb:5432/irrigation_db | PostgreSQL connection |
| `DB_POOL_MIN_SIZE` | 2 | Connection pool min |
| `DB_POOL_MAX_SIZE` | 10 | Connection pool max |

---

## Metrics

Prometheus metrics exposed at `/metrics`:

| Metric | Description |
|--------|-------------|
| `data_ingestion_total_processed` | Total messages processed |
| `data_ingestion_valid_readings` | Valid readings persisted |
| `data_ingestion_anomalies_flagged` | Anomalies detected |
| `data_ingestion_errors_total` | Processing errors |

---

## Anomaly Types

| Event Type | Severity | Description |
|------------|----------|-------------|
| `unknown_zone` | critical | Zone ID not in database |
| `below_min_plausible_moisture` | warning | Moisture below zone minimum |
| `above_max_plausible_moisture` | warning/critical | Moisture above zone maximum |
| `below_min_plausible_temperature` | warning | Temperature below zone minimum |
| `above_max_plausible_temperature` | warning/critical | Temperature above zone maximum |

---

## Docker Compose

```yaml
data-ingestion:
  image: data-ingestion:latest
  ports:
    - "8001:8001"
  environment:
    - REDIS_URL=redis://redis:6379/0
    - DATABASE_URL=postgresql://irrigation_user:changeme@timescaledb:5432/irrigation_db
  depends_on:
    - redis
    - timescaledb
```

---

## Monitoring

### Health Check

```bash
curl http://localhost:8001/health
```

Response:
```json
{
  "status": "healthy",
  "stats": {
    "total_processed": 1500,
    "valid_readings": 1480,
    "anomalies_flagged": 18,
    "last_processed_at": "2026-05-03T10:30:00Z",
    "errors": 2
  }
}
```

### Prometheus Metrics

```bash
curl http://localhost:8001/metrics
```

---

## Integration with Other Services

### irrigation-controller

Subscribes to `ingestion:processed` channel for real-time sensor updates:

```python
# When valid reading arrives, trigger irrigation check
if valid and moisture < threshold:
    trigger_irrigation(zone_id)
```

### Airflow DAG Trigger

When new sensor data arrives, Airflow DAG can:
1. Update feature store
2. Run prediction pipeline
3. Update model features

---

## Error Handling

| Error Type | Handling |
|------------|----------|
| JSON decode error | Log error, increment stats, continue |
| Database error | Log error, increment error counter |
| Invalid zone | Create anomaly event (if zone exists), skip insertion |
| Redis disconnect | Service health check fails, k8s restarts |

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Framework | FastAPI + asyncio |
| Language | Python |
| Input | Redis pubsub (sensor:data) |
| Output | PostgreSQL (TimescaleDB) |
| Validation | Zone-based min/max plausible |
| Anomaly Tracking | data_quality_events table |
| Port | 8001 |
| Dependencies | Redis, TimescaleDB |

The Data Ingestion Service is the backbone of real-time sensor data processing, ensuring data quality while feeding downstream services for irrigation control and ML predictions.