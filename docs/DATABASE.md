# Database Schema

## Overview

The Smart Irrigation System uses PostgreSQL with the TimescaleDB extension for time-series data storage. The database is the central data store for sensor readings, irrigation events, users, zones, and quality metrics.

**Host:** timescaledb:5432

**Database:** irrigation_db

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     POSTGRESQL + TIMESCALEDB                                    │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                       Tables                                             │   │
│  │                                                                          │   │
│  │  ┌─────────────┐  ┌─────────────────┐  ┌─────────────┐  ┌────────────┐   │   │
│  │  │   zones     │  │ sensor_metadata │  │  users     │  │ quality   │   │   │
│  │  │             │  │                 │  │            │  │ _rules    │   │   │
│  │  └─────────────┘  └─────────────────┘  └─────────────┘  └────────────┘   │   │
│  │                                                                          │   │
│  │  ┌───────────────────┐  ┌─────────────────────┐                         │   │
│  │  │  sensor_readings  │  │  irrigation_events │  (Hypertables)        │   │
│  │  │     (hypertable)  │  │    (hypertable)     │                         │   │
│  │  └───────────────────┘  └─────────────────────┘                         │   │
│  │                                                                          │   │
│  │  ┌─────────────────────┐  ┌─────────────────────┐                         │   │
│  │  │ data_quality_events │  │   schema_migrations │                         │   │
│  │  └─────────────────────┘  └─────────────────────┘                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                       Views                                              │   │
│  │                                                                          │   │
│  │  v_quality_metrics  - Hourly quality summary                            │   │
│  │  v_sensor_health    - Sensor health status                              │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Tables

### zones

Zone configuration and irrigation thresholds:

```sql
CREATE TABLE zones (
    zone_id       VARCHAR(50)  PRIMARY KEY,
    zone_name     VARCHAR(200) NOT NULL,
    soil_type     VARCHAR(50)  NOT NULL,
    crop_type     VARCHAR(50)  NOT NULL,
    moisture_min  FLOAT        NOT NULL,  -- irrigation trigger threshold
    moisture_max  FLOAT        NOT NULL,  -- maximum moisture
    min_plausible JSONB       NOT NULL DEFAULT '{}',
    max_plausible JSONB        NOT NULL DEFAULT '{}',
    active        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Indexes:**
- `idx_zones_active` - Filter active zones
- `idx_zones_min_plausible` - GIN index for JSONB
- `idx_zones_max_plausible` - GIN index for JSONB

---

### users

User accounts for authentication:

```sql
CREATE TABLE users (
    user_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

### sensor_metadata

Registered sensors:

```sql
CREATE TABLE sensor_metadata (
    sensor_id    VARCHAR(50) PRIMARY KEY,
    zone_id      VARCHAR(50) NOT NULL REFERENCES zones(zone_id) ON DELETE CASCADE,
    sensor_type  VARCHAR(50) NOT NULL DEFAULT 'moisture',
    installed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    active       BOOLEAN     NOT NULL DEFAULT TRUE
);
```

---

### sensor_readings (Hypertable)

Time-series sensor data:

```sql
CREATE TABLE sensor_readings (
    id          BIGSERIAL,
    timestamp   TIMESTAMPTZ NOT NULL,
    zone_id     VARCHAR(50) NOT NULL REFERENCES zones(zone_id),
    sensor_id   VARCHAR(50) NOT NULL,
    moisture    FLOAT       NOT NULL,
    temperature FLOAT,
    PRIMARY KEY (id, timestamp)
);

SELECT create_hypertable(
    'sensor_readings',
    'timestamp',
    chunk_time_interval => INTERVAL '1 day'
);
```

**Chunk interval:** 1 day (high write volume)

---

### irrigation_events (Hypertable)

Irrigation event log:

```sql
CREATE TABLE irrigation_events (
    id                 BIGSERIAL,
    triggered_at       TIMESTAMPTZ  NOT NULL,
    zone_id            VARCHAR(50)  NOT NULL REFERENCES zones(zone_id),
    trigger_reason     VARCHAR(100) NOT NULL,
    recommended_volume FLOAT,
    actual_volume      FLOAT,
    duration_seconds   INTEGER,
    status             VARCHAR(20)  NOT NULL DEFAULT 'pending'
                       CHECK (status IN ('pending', 'completed', 'failed')),
    completed_at       TIMESTAMPTZ,
    PRIMARY KEY (id, triggered_at)
);

SELECT create_hypertable(
    'irrigation_events',
    'triggered_at',
    chunk_time_interval => INTERVAL '1 week'
);
```

**Chunk interval:** 1 week (low write volume)

---

### data_quality_events

Anomaly and quality events:

```sql
CREATE TABLE data_quality_events (
    id            BIGSERIAL,
    timestamp     TIMESTAMPTZ NOT NULL,
    zone_id       VARCHAR(50) NOT NULL,
    sensor_id     VARCHAR(50) NOT NULL,
    event_type    VARCHAR(100) NOT NULL,
    event_value   FLOAT,
    expected_min  FLOAT,
    expected_max  FLOAT,
    severity      VARCHAR(20) DEFAULT 'warning',
    details       TEXT
);
```

---

### quality_rules

Configurable quality rules:

```sql
CREATE TABLE quality_rules (
    rule_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_name       VARCHAR(100) NOT NULL UNIQUE,
    rule_type       VARCHAR(50) NOT NULL,
    sensor_type     VARCHAR(50),
    zone_id         VARCHAR(50) REFERENCES zones(zone_id) ON DELETE CASCADE,
    parameters      JSONB NOT NULL DEFAULT '{}',
    severity        VARCHAR(20) NOT NULL DEFAULT 'warning',
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Default rules:**
| Rule Name | Type | Sensor | Parameters |
|-----------|------|--------|------------|
| stuck_moisture | stuck_value | moisture | consecutive_count=5, tolerance=0.001 |
| stuck_temperature | stuck_value | temperature | consecutive_count=10, tolerance=0.01 |
| sudden_jump_moisture | sudden_jump | moisture | max_delta=0.35, max_pct_change=50 |
| flatline_moisture | flatline | moisture | window_minutes=30, max_variance=0.0001 |
| flatline_temperature | flatline | temperature | window_minutes=60, max_variance=0.01 |
| rate_of_change_temp | rate_of_change | temperature | window_minutes=15, max_rate_per_min=2.0 |

---

### schema_migrations

Migration tracking:

```sql
CREATE TABLE schema_migrations (
    version     VARCHAR(50) PRIMARY KEY,
    description TEXT,
    checksum    VARCHAR(64),
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## Views

### v_quality_metrics

Hourly quality summary for Grafana:

```sql
CREATE OR REPLACE VIEW v_quality_metrics AS
SELECT
    date_trunc('hour', timestamp) AS bucket,
    zone_id,
    event_type,
    severity,
    COUNT(*) AS event_count,
    COUNT(DISTINCT sensor_id) AS affected_sensors
FROM data_quality_events
WHERE timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY date_trunc('hour', timestamp), zone_id, event_type, severity;
```

---

### v_sensor_health

Sensor health status:

```sql
CREATE OR REPLACE VIEW v_sensor_health AS
SELECT
    sm.zone_id,
    sm.sensor_id,
    sm.sensor_type,
    sm.active,
    COALESCE(SUM(re.cnt) FILTER (WHERE re.severity = 'critical'), 0) AS critical_count,
    COALESCE(SUM(re.cnt) FILTER (WHERE re.severity = 'warning'), 0) AS warning_count,
    COALESCE(SUM(re.cnt), 0) AS total_anomalies,
    CASE
        WHEN COALESCE(SUM(re.cnt) FILTER (WHERE re.severity = 'critical'), 0) > 5 THEN 'unhealthy'
        WHEN COALESCE(SUM(re.cnt), 0) > 10 THEN 'degraded'
        ELSE 'healthy'
    END AS health_status
FROM sensor_metadata sm
LEFT JOIN recent_events re ON ...
GROUP BY sm.zone_id, sm.sensor_id, sm.sensor_type, sm.active;
```

**Health status logic:**
- `unhealthy` - More than 5 critical events in 24h
- `degraded` - More than 10 total events in 24h
- `healthy` - Otherwise

---

## Roles & Permissions

| Role | Tables | Permissions |
|------|--------|-------------|
| `ingestion_user` | sensor_readings, irrigation_events, sensor_metadata, quality_rules | INSERT, SELECT |
| `reader_user` | All tables | SELECT |
| `app_user` | zones, users | SELECT, INSERT, UPDATE |

---

## Migrations

### Migration Order

| # | File | Description |
|---|------|-------------|
| 001 | 001_init_timescaledb.sql | Core schema, hypertables, roles |
| 002 | 002_plausibility_bounds.sql | min/max_plausible columns |
| 003 | 003_feature_references.sql | Feature references |
| 004 | 004_shadow_comparison.sql | Shadow model comparison |
| 005 | 005_user_and_zone_ownership.sql | Users table |
| 006 | 006_quality_rules.sql | Quality rules, views |
| 007 | 007_add_user_roles.sql | User roles |
| 008 | 008_zone_ownership_system.sql | Zone ownership |
| 009 | 009_feature_versioning.sql | Feature versioning |
| 010 | 010_auto_zone_id.sql | Auto zone_id |
| 011 | 011_cascade_zone_deletion.sql | Cascade deletes |
| 012 | 012_remove_default_zones.sql | Remove default zones |

---

## Configuration

### Environment Variables

From `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | irrigation_user | Main user |
| `POSTGRES_PASSWORD` | postgres_dev | Main password |
| `POSTGRES_DB` | irrigation_db | Database name |
| `TIMESCALEDB_SENSOR_CHUNK_INTERVAL` | 1 day | sensor_readings chunk |
| `TIMESCALEDB_IRRIGATION_CHUNK_INTERVAL` | 1 week | irrigation_events chunk |

---

## Connecting

### From host

```bash
psql -h localhost -p 5432 -U irrigation_user -d irrigation_db
```

### From container

```bash
docker exec -it timescaledb psql -U irrigation_user -d irrigation_db
```

---

## Docker Compose

```yaml
timescaledb:
  image: timescale/timescaledb:latest-pg16
  ports:
    - "5432:5432"
  volumes:
    - timescaledb_data:/var/lib/postgresql/data
    - ../migrations:/docker-entrypoint-initdb.d:ro
```

---

## Summary

| Aspect | Value |
|--------|-------|
| Engine | PostgreSQL 16 + TimescaleDB |
| Database | irrigation_db |
| Hypertables | sensor_readings (1d chunks), irrigation_events (1w chunks) |
| Roles | ingestion_user, reader_user, app_user |
| Migrations | 12 migrations in order |

The database provides centralized storage with time-series optimization for high-volume sensor data and efficient querying for dashboards and analytics.