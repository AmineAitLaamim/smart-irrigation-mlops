-- ================================================================
-- Migration 001 : Initial TimescaleDB Schema
-- ================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ── 0. Tracking table ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── 1. Roles per service (passwords via environment variables) ─
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ingestion_user') THEN
        EXECUTE format('CREATE ROLE ingestion_user LOGIN PASSWORD %L',
                       current_setting('app.ingestion_password', true));
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'reader_user') THEN
        EXECUTE format('CREATE ROLE reader_user LOGIN PASSWORD %L',
                       current_setting('app.reader_password', true));
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
        EXECUTE format('CREATE ROLE app_user LOGIN PASSWORD %L',
                       current_setting('app.app_password', true));
    END IF;
END
$$;

-- ── 2. Table zones ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS zones (
    zone_id       VARCHAR(50)  PRIMARY KEY,
    zone_name     VARCHAR(200) NOT NULL,
    soil_type     VARCHAR(50)  NOT NULL,
    crop_type     VARCHAR(50)  NOT NULL,
    moisture_min  FLOAT        NOT NULL CHECK (moisture_min > 0),
    moisture_max  FLOAT        NOT NULL CHECK (moisture_max > moisture_min),
    min_plausible JSONB        NOT NULL DEFAULT '{}',
    max_plausible JSONB        NOT NULL DEFAULT '{}',
    active        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_zones_active
    ON zones (active) WHERE active = TRUE;

CREATE INDEX IF NOT EXISTS idx_zones_min_plausible
    ON zones USING GIN (min_plausible);

CREATE INDEX IF NOT EXISTS idx_zones_max_plausible
    ON zones USING GIN (max_plausible);

-- Auto-update updated_at on zone changes
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_zones_updated_at
    BEFORE UPDATE ON zones
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ── 3. Table sensor_metadata ──────────────────────────────────
CREATE TABLE IF NOT EXISTS sensor_metadata (
    sensor_id    VARCHAR(50) PRIMARY KEY,
    zone_id      VARCHAR(50) NOT NULL
                 REFERENCES zones(zone_id) ON DELETE CASCADE,
    sensor_type  VARCHAR(50) NOT NULL DEFAULT 'moisture',
    installed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    active       BOOLEAN     NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_sensor_metadata_zone
    ON sensor_metadata (zone_id);

CREATE INDEX IF NOT EXISTS idx_sensor_metadata_id_active
    ON sensor_metadata (sensor_id, active);

-- ── 4. Hypertable sensor_readings (chunk: 1 day) ──────────────
CREATE TABLE IF NOT EXISTS sensor_readings (
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
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists       => TRUE
);

CREATE INDEX IF NOT EXISTS idx_sensor_readings_zone_time
    ON sensor_readings (zone_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_sensor_readings_sensor_time
    ON sensor_readings (sensor_id, timestamp DESC);

-- ── 5. Hypertable irrigation_events (chunk: 1 week) ───────────
CREATE TABLE IF NOT EXISTS irrigation_events (
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
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists       => TRUE
);

CREATE INDEX IF NOT EXISTS idx_irrigation_events_zone_time
    ON irrigation_events (zone_id, triggered_at DESC);

CREATE INDEX IF NOT EXISTS idx_irrigation_events_status
    ON irrigation_events (status) WHERE status = 'pending';

-- ── 6. Permissions per service ────────────────────────────────
GRANT SELECT                   ON zones             TO ingestion_user;
GRANT INSERT, SELECT           ON sensor_readings   TO ingestion_user;
GRANT INSERT, SELECT           ON irrigation_events TO ingestion_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ingestion_user;

GRANT SELECT ON zones             TO reader_user;
GRANT SELECT ON sensor_readings   TO reader_user;
GRANT SELECT ON sensor_metadata   TO reader_user;
GRANT SELECT ON irrigation_events TO reader_user;

GRANT SELECT, INSERT, UPDATE ON zones TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- ── 7. Record migration ───────────────────────────────────────
INSERT INTO schema_migrations (version)
VALUES ('001')
ON CONFLICT DO NOTHING;