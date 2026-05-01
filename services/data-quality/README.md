# Data Quality Service

## Overview
The Data Quality service provides continuous auditing of incoming sensor data. It identifies malfunctions, classifies anomalies, and generates health reports.

## Features Implemented
### 1. Malfunction Detection
The engine implements four core detection algorithms:
- **Stuck Values**: Detects values that stop changing (within a tolerance) over a window.
- **Sudden Jumps**: Monitors for physically impossible spikes in moisture or temperature.
- **Flatlines**: Identifies "dead" sensors using variance analysis.
- **Rate of Change**: Validates that environmental changes stay within realistic bounds.

### 2. Configurable Quality Rules
- Rules are stored in the database (`quality_rules` table) and can be updated at runtime via the API.
- This allows data scientists to tune detection sensitivity (e.g., `consecutive_count`, `max_delta`) without code redeployments.

### 3. Automated Reporting
- `GET /quality/reports/summary`: Aggregate view of data health.
- `GET /quality/reports/sensors`: Individual sensor health scores and status (`healthy`, `degraded`, `unhealthy`).

### 4. Monitoring Integration
- Native Prometheus integration exporting `sensor_health_status` gauges and detection counters.
- Ready for visualization in the Grafana dashboard.

## Technical Stack
- **Framework**: FastAPI
- **Database**: TimescaleDB (Time-series aggregations)
- **Monitoring**: `prometheus_client`
- **Queue**: Redis (Subscribes to `ingestion:processed`)
