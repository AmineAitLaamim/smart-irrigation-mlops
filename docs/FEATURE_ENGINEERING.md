# Feature Engineering Documentation

## Overview

The Feature Engineering service computes rolling metrics and aggregations from raw sensor data. It operates in two modes:

1. **Streaming Mode** - Real-time feature computation triggered by each sensor reading
2. **Batch Mode** - Periodic batch processing (hourly/daily rollups + rolling features)

The service processes raw sensor readings and stores computed features in the `feature_references` table for use by the model server.

**Location:** `services/feature-engineering/src/`

**Port:** 8004

---

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         FEATURE ENGINEERING SERVICE                             │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        FastAPI Application                               │   │
│  │                                                                          │   │
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐  │   │
│  │  │   /health   │   │  /metrics   │   │/trigger-   │   │             │  │   │
│  │  │             │   │             │   │   batch     │   │             │  │   │
│  │  └─────────────┘   └─────────────┘   └──────┬──────┘   │             │  │   │
│  │                                           │          │             │  │   │
│  │                                           ▼          │             │  │   │
│  │  ┌────────────────────────────────────────────────┐ │             │  │   │
│  │  │                  Redis Consumer                │ │             │  │   │
│  │  │            (listens to ingestion:processed)    │ │             │  │   │
│  │  └────────────────────────┬───────────────────────┘ │             │  │   │
│  │                           │                           │             │   │   │
│  │  ┌────────────────────────┴───────────────────────┐ │             │   │   │
│  │  │              Background Batch Scheduler        │ │             │   │   │
│  │  │              (runs every 300 seconds)         │ │             │   │   │
│  │  └────────────────────────┬───────────────────────┘ │             │   │   │
│  └───────────────────────────┼─────────────────────────────────────┘   │   │
│                              │                                                  │
│  ┌───────────────────────────┼──────────────────────────────────────────┐   │
│  │                    Core Logic                                        │   │
│  │                                                                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │   │
│  │  │   ETL       │  │   Feature    │  │   Soil      │  │  Database  │  │   │
│  │  │  (cleaning) │◄─│  Computation │◄─│   Profiles  │  │   Writer   │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │   │
│  └───────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                       │
│                                                                                 │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐          │
│  │ Redis: ingestion │    │   TimescaleDB    │    │     Zones       │          │
│  │   :processed    │    │ sensor_readings  │    │   (soil_type)   │          │
│  │  (streaming)   │    │                  │    │                 │          │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘          │
└───────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              OUTPUT                                             │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                         TimescaleDB                                      │  │
│  │                                                                          │  │
│  │  feature_references ◄─── Rolling window features (30m, 1h, 3h, 24h)    │  │
│  │  hourly_rollup      ◄─── Hourly aggregations                            │  │
│  │  daily_rollup      ◄─── Daily aggregations                              │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                         Redis Channels                                   │  │
│  │                                                                          │  │
│  │  features:computed ──► Published after each computation                 │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Operating Modes

### 1. Streaming Mode (Real-time)

Triggered by each sensor reading via Redis pub/sub:

```
Data Ingestion publishes to "ingestion:processed"
        │
        ▼
Feature Engineering subscribes and processes
        │
        ▼
Computes rolling features for the zone/sensor
        │
        ▼
Publishes to "features:computed"
```

**Redis Channels:**
- Input: `ingestion:processed` (listens for new sensor readings)
- Output: `features:computed` (publishes computed features)

### 2. Batch Mode (Periodic)

Runs every 5 minutes (configurable):

```
Timer triggers every 300 seconds
        │
        ▼
For each active sensor:
        │
        ├─► Hourly rollup (avg, min, max, std of last hour)
        │
        ├─► Daily rollup (avg, min, max, std of last day)
        │
        └─► Rolling features (30m, 1h, 3h, 24h windows)
```

---

## Feature Computation

### Rolling Window Features

The service computes features for configurable windows: `30m`, `1h`, `3h`, `24h`

**Moisture Features:**
| Feature | Description |
|---------|-------------|
| `mean_moisture` | Average moisture over window |
| `std_moisture` | Standard deviation of moisture |
| `min_moisture` | Minimum moisture in window |
| `max_moisture` | Maximum moisture in window |
| `variance_moisture` | Variance of moisture |
| `rate_of_change_moisture` | Change from start to end |
| `moisture_range` | max - min |
| `soil_water_retention_index` | Mean moisture × soil retention factor |
| `soil_dryness_index` | (100 - mean moisture) × drainage factor |

**Temperature Features:**
| Feature | Description |
|---------|-------------|
| `mean_temperature` | Average temperature |
| `std_temperature` | Standard deviation |
| `min_temperature` | Minimum |
| `max_temperature` | Maximum |
| `variance_temperature` | Variance |
| `rate_of_change_temperature` | Change over window |

**Combined Features:**
| Feature | Description |
|---------|-------------|
| `evapotranspiration_proxy` | Temperature × (100 - moisture) / 100 |

### Soil Type Profiles

Features are adjusted based on soil type:

```python
SOIL_TYPE_FACTORS = {
    "sand": {"water_retention_factor": 0.7, "drainage_factor": 1.3},
    "sandy_loam": {"water_retention_factor": 0.85, "drainage_factor": 1.15},
    "loam": {"water_retention_factor": 1.0, "drainage_factor": 1.0},
    "silty_loam": {"water_retention_factor": 1.05, "drainage_factor": 0.98},
    "silt": {"water_retention_factor": 1.08, "drainage_factor": 0.95},
    "clay_loam": {"water_retention_factor": 1.12, "drainage_factor": 0.9},
    "clay": {"water_retention_factor": 1.2, "drainage_factor": 0.8},
    "peat": {"water_retention_factor": 1.5, "drainage_factor": 0.6},
}
```

---

## Data Cleaning (ETL)

Before computing features, raw data goes through cleaning:

### 1. Deduplication
```python
def _deduplicate(records):
    # Average duplicate readings at same timestamp
    # Multiple sensors reporting same zone/timestamp
```

### 2. Null Handling
```python
def _handle_nulls(records):
    # Forward-fill missing temperature values
    # If temp is null, use previous reading
```

### 3. Outlier Smoothing
```python
def _smooth_outliers(records, threshold=3.0):
    # Cap extreme values using z-score
    # If |value - mean| / std > threshold, replace with mean
    # Default threshold: 3.0 (configurable via OUTLIER_ZSCORE_THRESHOLD)
```

---

## API Endpoints

### GET /health

Health check with stats.

```bash
curl http://localhost:8004/health
```

**Response:**
```json
{
  "status": "healthy",
  "stats": {
    "total_processed": 1500,
    "features_computed": 450,
    "rollups_computed": 12,
    "anomalies_smoothed": 5,
    "errors": 0
  }
}
```

### GET /metrics

Prometheus metrics.

```bash
curl http://localhost:8004/metrics
```

**Metrics:**
- `feature_engineering_total_processed` - Total readings processed
- `feature_engineering_features_computed` - Features computed
- `feature_engineering_rollups_computed` - Rollups computed
- `feature_engineering_anomalies_smoothed` - Outliers smoothed
- `feature_engineering_errors_total` - Errors

### POST /trigger-batch

Manually trigger batch ETL (for testing).

```bash
curl -X POST http://localhost:8004/trigger-batch
```

**Response:**
```json
{
  "status": "batch_completed",
  "stats": {...}
}
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FEATURE_ENGINEERING_PORT` | `8004` | Service port |
| `BATCH_INTERVAL_SECONDS` | `300` | Batch run interval (5 min) |
| `ROLLUP_WINDOWS` | `30m,1h,3h,24h` | Rolling windows |
| `FEATURE_MODEL_VERSION` | `v1` | Model version tag |
| `OUTLIER_ZSCORE_THRESHOLD` | `3.0` | Z-score threshold |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `REDIS_CHANNEL_INGESTION_PROCESSED` | `ingestion:processed` | Input channel |
| `REDIS_CHANNEL_FEATURES_COMPUTED` | `features:computed` | Output channel |

### Docker Configuration

```yaml
feature-engineering:
  image: feature-engineering:latest
  ports:
    - "8004:8004"
  environment:
    - BATCH_INTERVAL_SECONDS=300
    - ROLLUP_WINDOWS=30m,1h,3h,24h
  depends_on:
    - timescaledb
    - redis
```

---

## Output Storage

### feature_references Table

Stores computed rolling features:

```sql
CREATE TABLE feature_references (
    id            BIGSERIAL,
    computed_at   TIMESTAMPTZ NOT NULL,
    zone_id       VARCHAR(50) NOT NULL,
    sensor_id     VARCHAR(50),
    window_size   VARCHAR(20) NOT NULL,  -- 30m, 1h, 3h, 24h
    feature_name  VARCHAR(50) NOT NULL, -- mean_moisture, etc.
    feature_value FLOAT,
    model_version VARCHAR(20),
    PRIMARY KEY (id, computed_at)
);
```

**Example data:**
```
computed_at          | zone_id | sensor_id | window_size | feature_name           | feature_value
---------------------+---------+-----------+-------------+------------------------+-------------
2026-05-03 12:00:00 | 2       | 2-s1      | 30m         | mean_moisture         | 45.2
2026-05-03 12:00:00 | 2       | 2-s1      | 30m         | std_moisture           | 3.1
2026-05-03 12:00:00 | 2       | 2-s1      | 30m         | evapotranspiration_proxy | 12.5
2026-05-03 12:00:00 | 2       | 2-s1      | 1h          | mean_moisture         | 48.7
...
```

### Hourly/Daily Rollups

```sql
-- hourly_rollup table
hour_start, zone_id, sensor_id, avg_moisture, min_moisture, max_moisture, std_moisture, ...

-- daily_rollup table
day_start, zone_id, sensor_id, avg_moisture, min_moisture, max_moisture, std_moisture, ...
```

---

## Integration

### Data Ingestion → Feature Engineering

```
data-ingestion validates sensor reading
        │
        ▼
publishes to "ingestion:processed" (Redis)
        │
        ▼
feature-engineering receives message
        │
        ▼
run_streaming(zone_id, sensor_id)
        │
        ▼
computes rolling features
        │
        ▼
publishes to "features:computed" (Redis)
```

### Airflow DAG → Feature Engineering

Airflow queries `feature_references` when generating predictions:

```python
feature_rows = await conn.fetch(
    """
    SELECT feature_name, window_size, feature_value
    FROM feature_references
    WHERE zone_id = $1 AND sensor_id = $2
    ORDER BY computed_at DESC
    """,
    zone_id, sensor_id,
)
```

---

## Feature Payload

### Serialized Format

When published to Redis or returned by API, features are serialized as:

```json
{
  "mean_moisture_30m": 45.2,
  "std_moisture_30m": 3.1,
  "min_moisture_30m": 40.0,
  "max_moisture_30m": 50.0,
  "mean_moisture_1h": 48.7,
  "evapotranspiration_proxy_30m": 12.5,
  "soil_dryness_index_1h": 51.3,
  ...
}
```

Key format: `{feature_name}_{window_size}`

---

## Monitoring

### Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `feature_engineering_total_processed` | Gauge | Readings processed |
| `feature_engineering_features_computed` | Gauge | Features generated |
| `feature_engineering_rollups_computed` | Gauge | Rollups computed |
| `feature_engineering_anomalies_smoothed` | Gauge | Outliers handled |
| `feature_engineering_errors_total` | Gauge | Error count |

### Health Check

```bash
curl http://localhost:8004/health | jq
```

---

## Testing

### Manual Batch Trigger

```bash
# Trigger batch ETL manually
curl -X POST http://localhost:8004/trigger-batch
```

### Check Recent Features

```sql
-- Query recent features for zone 2
SELECT * FROM feature_references
WHERE zone_id = '2'
ORDER BY computed_at DESC
LIMIT 20;
```

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Framework | FastAPI + Uvicorn |
| Input | Redis (ingestion:processed) + sensor_readings table |
| Processing | Rolling windows (30m, 1h, 3h, 24h) |
| Soil Adjustment | 8 soil type profiles |
| Data Cleaning | Deduplication, null fill, outlier smoothing |
| Output | feature_references table + Redis (features:computed) |
| Modes | Streaming (real-time) + Batch (5-min interval) |
| Port | 8004 |

The Feature Engineering service transforms raw sensor data into ML-ready features, applying soil-type adjustments and data cleaning before storing in TimescaleDB for model consumption.