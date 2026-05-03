# Data Quality Service

## Overview

The Data Quality Service monitors sensor data for malfunctions and anomalies using configurable rules. It evaluates incoming readings in real-time and runs periodic batch scans to detect issues like stuck sensors, sudden jumps, flatlines, and anomalous rates of change.

**Location:** `services/data-quality/`

**Port:** 8005

---

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    DATA INGESTION SERVICE                                       │
│                                                                                 │
│  Publishes to: ingestion:processed                                              │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                   DATA QUALITY SERVICE (8005)                                  │
│                                                                                 │
│  ┌─────────────────────┐    ┌─────────────────────┐    ┌──────────────────┐   │
│  │   Redis Consumer     │───▶│   Quality Engine     │───▶│   Reports API     │   │
│  │                     │    │                     │    │                  │   │
│  │ - Subscribe         │    │ - Stuck value       │    │ - /summary       │   │
│  │ - ingestion:processed    │ - Sudden jump       │    │ - /sensors       │   │
│  │ - Health loop       │    │ - Flatline           │    │ - /hourly        │   │
│  │                     │    │ - Rate of change    │    │ - /rules         │   │
│  └─────────────────────┘    └─────────────────────┘    └──────────────────┘   │
│           │                              │                       │            │
│           ▼                              ▼                       ▼            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      Prometheus Metrics                                 │   │
│  │                                                                          │   │
│  │  /metrics    - Grafana-compatible metrics                               │   │
│  │  /health     - Health check + stats                                     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      DATABASE (TimescaleDB)                                    │
│                                                                                 │
│  Tables:                                                                       │
│  - sensor_readings     - Sensor data to analyze                               │
│  - data_quality_events - Detected anomalies                                   │
│  - quality_rules      - Rule definitions                                      │
│  - sensor_metadata     - Sensor registry                                      │
│  - v_sensor_health     - Materialized view for sensor health                 │
└───────────────────────────────────────────────────────────────────────────────┘
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
    batch_task = asyncio.create_task(_batch_scan_loop())
    yield
    # Cleanup
```

**Endpoints:**
- `GET /health` - Health check with stats
- `GET /metrics` - Prometheus metrics
- `GET /quality/reports/summary` - Quality summary
- `GET /quality/reports/sensors` - Sensor health
- `GET /quality/reports/hourly` - Hourly metrics
- `GET /quality/rules` - List active rules
- `PATCH /quality/rules/{rule_id}` - Update rule

### quality_engine.py

Core rule evaluation logic:

```python
_RULE_TYPE_HANDLERS = {
    "stuck_value": _check_stuck_value,
    "sudden_jump": _check_sudden_jump,
    "flatline": _check_flatline,
    "rate_of_change": _check_rate_of_change,
}

async def evaluate_reading(zone_id, sensor_id, timestamp, value, sensor_type):
    # Run all applicable rules against the reading
    return anomalies
```

### redis_consumer.py

Async Redis consumer:

```python
async def run(self) -> None:
    async for message in self._pubsub.listen():
        if message.get("type") == "message":
            await self._process_one(message)
```

### metrics.py

Prometheus metrics for Grafana:
- `data_quality_readings_checked_total`
- `data_quality_anomalies_detected_total`
- `data_quality_active_rules`
- `data_quality_sensor_health_status`

---

## Quality Rules

### Rule Types

| Rule Type | Description | Parameters |
|-----------|-------------|------------|
| `stuck_value` | Sensor stuck at same value | `consecutive_count`, `tolerance` |
| `sudden_jump` | Unusually large change | `max_delta`, `max_pct_change` |
| `flatline` | No variation over time | `window_minutes`, `max_variance` |
| `rate_of_change` | Too fast/slow changes | `window_minutes`, `max_rate_per_min` |

### Example Rule (SQL)

```sql
INSERT INTO quality_rules (rule_id, rule_name, rule_type, sensor_type, zone_id, parameters, severity, active)
VALUES (
    'stuck-moisture-zone1',
    'Stuck Moisture Sensor Zone 1',
    'stuck_value',
    'moisture',
    'zone-001',
    '{"consecutive_count": 5, "tolerance": 0.001}',
    'warning',
    TRUE
);
```

### Rule Configuration

```json
{
  "rule_id": "stuck-moisture-zone1",
  "rule_name": "Stuck Moisture Sensor Zone 1",
  "rule_type": "stuck_value",
  "sensor_type": "moisture",
  "zone_id": "zone-001",
  "parameters": {
    "consecutive_count": 5,
    "tolerance": 0.001
  },
  "severity": "warning",
  "active": true
}
```

---

## Anomaly Detection

### Stuck Value

Detects when a sensor reports the same value repeatedly:

```python
# Check last N readings (default: 5)
window = values[:consecutive_count]
if all(abs(v - current_value) <= tolerance for v in window):
    # Anomaly detected
```

### Sudden Jump

Detects rapid value changes between consecutive readings:

```python
delta = abs(current_value - previous_value)
pct_change = (delta / abs(previous_value)) * 100

if delta > max_delta or pct_change > max_pct_change:
    # Anomaly detected
```

### Flatline

Detects sensors with no variation over a time window:

```python
variance = sum((x - mean) ** 2 for x in values) / len(values)
if variance <= max_variance:
    # Anomaly detected
```

### Rate of Change

Detects abnormal rates of change over a window:

```python
rate = abs(last_value - first_value) / time_diff_minutes
if rate > max_rate_per_min:
    # Anomaly detected
```

---

## Database Schema

### quality_rules

```sql
CREATE TABLE quality_rules (
    rule_id VARCHAR(100) PRIMARY KEY,
    rule_name VARCHAR(255) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,  -- stuck_value, sudden_jump, flatline, rate_of_change
    sensor_type VARCHAR(50),          -- moisture, temperature
    zone_id UUID,
    parameters JSONB NOT NULL,        -- rule-specific parameters
    severity VARCHAR(20) DEFAULT 'warning',
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### sensor_metadata

```sql
CREATE TABLE sensor_metadata (
    sensor_id UUID PRIMARY KEY,
    zone_id UUID NOT NULL,
    sensor_type VARCHAR(50),
    active BOOLEAN DEFAULT TRUE,
    last_reading_at TIMESTAMPTZ,
    FOREIGN KEY (zone_id) REFERENCES zones(zone_id)
);
```

### v_sensor_health (Materialized View)

```sql
CREATE MATERIALIZED VIEW v_sensor_health AS
SELECT
    zone_id,
    sensor_id,
    sensor_type,
    CASE
        WHEN COUNT(*) = 0 THEN 'unhealthy'
        WHEN MAX(anomaly_count) > 5 THEN 'unhealthy'
        WHEN MAX(anomaly_count) > 0 THEN 'degraded'
        ELSE 'healthy'
    END AS health_status
FROM (
    SELECT
        zone_id,
        sensor_id,
        sensor_type,
        COUNT(*) FILTER (WHERE severity = 'critical') AS critical_count,
        COUNT(*) FILTER (WHERE severity = 'warning') AS anomaly_count
    FROM data_quality_events
    WHERE timestamp > NOW() - INTERVAL '1 hour'
    GROUP BY zone_id, sensor_id, sensor_type
) sub
GROUP BY zone_id, sensor_id, sensor_type;

-- Refresh periodically
REFRESH MATERIALIZED VIEW CONCURRENTLY v_sensor_health;
```

---

## API Endpoints

### GET /quality/reports/summary

Returns quality summary for a time window:

```bash
GET /quality/reports/summary?hours=24&zone_id=zone-001
```

Response:
```json
{
  "total_readings": 1500,
  "total_anomalies": 12,
  "by_severity": {"warning": 10, "critical": 2},
  "by_rule_type": {"stuck_value": 5, "flatline": 7},
  "by_zone": {"zone-001": 8, "zone-002": 4}
}
```

### GET /quality/reports/sensors

Returns sensor health status:

```bash
GET /quality/reports/sensors?zone_id=zone-001
```

Response:
```json
{
  "sensors": [
    {"zone_id": "zone-001", "sensor_id": "sensor-001", "sensor_type": "moisture", "health_status": "healthy"},
    {"zone_id": "zone-001", "sensor_id": "sensor-002", "sensor_type": "moisture", "health_status": "degraded"}
  ]
}
```

### GET /quality/rules

Lists all active rules:

```bash
GET /quality/rules
```

Response:
```json
{
  "rules": [
    {"rule_id": "stuck-moisture-zone1", "rule_name": "...", "rule_type": "stuck_value", "active": true}
  ],
  "count": 1
}
```

### PATCH /quality/rules/{rule_id}

Updates a rule (e.g., enable/disable):

```bash
PATCH /quality/rules/stuck-moisture-zone1
{"active": false}
```

Response:
```json
{"status": "updated", "rule_id": "stuck-moisture-zone1"}
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_QUALITY_PORT` | 8005 | Service port |
| `REDIS_URL` | redis://redis:6379/0 | Redis connection |
| `REDIS_CHANNEL_INGESTION_PROCESSED` | ingestion:processed | Input channel |
| `BATCH_SCAN_INTERVAL_SECONDS` | 300 | Batch scan interval |
| `QUALITY_RULES_CACHE_TTL` | 30 | Rules cache TTL |
| `HEALTH_UPDATE_INTERVAL_SECONDS` | 60 | Health gauge update interval |

---

## Metrics

Prometheus metrics at `/metrics`:

| Metric | Labels | Description |
|--------|--------|-------------|
| `data_quality_readings_checked_total` | zone_id, sensor_id, sensor_type | Readings evaluated |
| `data_quality_anomalies_detected_total` | rule_type, severity, zone_id, sensor_id | Anomalies detected |
| `data_quality_active_rules` | - | Active rule count |
| `data_quality_rule_eval_duration_seconds` | rule_type | Rule evaluation latency |
| `data_quality_sensor_health_status` | zone_id, sensor_id, sensor_type | Sensor health (0=healthy, 1=degraded, 2=unhealthy) |
| `data_quality_stuck_value_detected_total` | zone_id, sensor_id | Stuck value count |
| `data_quality_sudden_jump_detected_total` | zone_id, sensor_id | Sudden jump count |
| `data_quality_flatline_detected_total` | zone_id, sensor_id | Flatline count |

---

## Docker Compose

```yaml
data-quality:
  image: data-quality:latest
  ports:
    - "8005:8005"
  environment:
    - REDIS_URL=redis://redis:6379/0
    - REDIS_CHANNEL_INGESTION_PROCESSED=ingestion:processed
    - BATCH_SCAN_INTERVAL_SECONDS=300
    - QUALITY_RULES_CACHE_TTL=30
  depends_on:
    - redis
    - timescaledb
```

---

## Integration with Other Services

### data-ingestion

Publishes to `ingestion:processed` channel:
```json
{"zone_id": "zone-001", "sensor_id": "sensor-001", "timestamp": "...", "valid": true}
```

### notification-service

Subscribes to `alerts:anomaly` for quality alerts.

### Grafana

Uses `data_quality_sensor_health_status` gauge for dashboard panels.

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Framework | FastAPI + asyncio |
| Language | Python |
| Input | Redis pubsub (ingestion:processed) + batch scan |
| Output | data_quality_events table |
| Rules | Configurable in quality_rules table |
| Anomaly Types | stuck_value, sudden_jump, flatline, rate_of_change |
| Port | 8005 |
| Dependencies | Redis, TimescaleDB |

The Data Quality Service provides comprehensive sensor health monitoring, detecting malfunctions in real-time and through periodic batch analysis.