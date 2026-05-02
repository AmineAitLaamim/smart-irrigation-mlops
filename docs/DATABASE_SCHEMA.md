# Database Schema: TimescaleDB

## Overview
The system uses TimescaleDB (PostgreSQL) as its primary data store. It combines relational tables for metadata and management with hypertables for high-velocity time-series data.

## 1. Relational Tables (Management)

### `users`
Tracks system users and their roles.
- `user_id`: UUID (Primary Key)
- `email`: String (Unique)
- `hashed_password`: String
- `full_name`: String
- `is_admin`: Boolean (Default: FALSE)

### `zones`
Represents physical irrigation areas.
- `zone_id`: String (Primary Key)
- `zone_name`: String
- `soil_type`: String
- `crop_type`: String
- `owner_id`: UUID (FK -> users)
- `source`: String ('api' or 'yaml')
- `min_plausible` / `max_plausible`: JSONB (Bounds per sensor type)

### `sensor_metadata`
Tracks individual sensor deployment.
- `sensor_id`: String (Primary Key)
- `zone_id`: String (FK -> zones)
- `sensor_type`: String ('moisture', 'temperature')
- `active`: Boolean

### `quality_rules`
Configurable rules for malfunction detection.
- `rule_id`: UUID
- `rule_name`: String
- `rule_type`: String (stuck_value, sudden_jump, etc.)
- `parameters`: JSONB

## 2. Hypertables (Time-Series)

### `sensor_readings`
Raw sensor telemetry.
- **Partition Interval**: 1 Day
- `timestamp`: TIMESTAMPTZ
- `zone_id`: FK -> zones
- `moisture`: FLOAT
- `temperature`: FLOAT

### `data_quality_events`
Log of anomalies and malfunctions.
- **Partition Interval**: 1 Day
- `event_type`: String (below_min, stuck_value, etc.)
- `severity`: String (warning, critical)
- `event_value`: FLOAT

### `feature_references`
The ML Feature Store.
- `computed_at`: TIMESTAMPTZ
- `window_size`: String (30m, 1h, 24h)
- `feature_name`: String
- `feature_value`: FLOAT
- `model_version`: String

### `model_predictions`
Inference results.
- **Partition Interval**: 1 Day
- `prediction`: FLOAT (Predicted moisture)
- `confidence`: FLOAT

## 3. Views & Analytics

- `v_sensor_health`: Aggregates quality events to determine per-sensor status (healthy, degraded, unhealthy).
- `v_quality_metrics`: Provides hourly counts of anomalies for Grafana dashboards.
- `v_shadow_comparison`: Compares results between champion and shadow models.
