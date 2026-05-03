-- ================================================================
-- Migration 002 : Plausibility Bounds and Data Quality Events
-- ================================================================

-- ── 1. Data Quality Events Hypertable ───────────────────────────
CREATE TABLE IF NOT EXISTS data_quality_events (
    id              BIGSERIAL,
    timestamp       TIMESTAMPTZ NOT NULL,
    zone_id         VARCHAR(50) NOT NULL REFERENCES zones(zone_id),
    sensor_id       VARCHAR(50) NOT NULL,
    event_type      VARCHAR(50) NOT NULL,
    event_value     FLOAT,
    expected_min    FLOAT,
    expected_max    FLOAT,
    severity        VARCHAR(20) NOT NULL DEFAULT 'warning',
    details         TEXT,
    PRIMARY KEY (id, timestamp)
);

SELECT create_hypertable(
    'data_quality_events',
    'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_data_quality_events_zone_time
    ON data_quality_events (zone_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_data_quality_events_severity
    ON data_quality_events (severity) WHERE severity = 'critical';

-- ── 2. Seed Zones with Plausibility Bounds ──────────────────────
/*
INSERT INTO zones (zone_id, zone_name, soil_type, crop_type, moisture_min, moisture_max,
                   min_plausible, max_plausible, active)
VALUES
    ('zone_a', 'North Field', 'clay', 'corn', 0.2, 0.8,
     '{"moisture": 0.15, "temperature": 5}', '{"moisture": 0.85, "temperature": 40}', TRUE),
    ('zone_b', 'South Field', 'sandy_loam', 'wheat', 0.15, 0.7,
     '{"moisture": 0.10, "temperature": 0}', '{"moisture": 0.75, "temperature": 35}', TRUE),
    ('zone_c', 'Greenhouse 1', 'loam', 'tomatoes', 0.3, 0.9,
     '{"moisture": 0.25, "temperature": 15}', '{"moisture": 0.95, "temperature": 45}', TRUE),
    ('zone_d', 'Orchard', 'clay_loam', 'apples', 0.2, 0.75,
     '{"moisture": 0.15, "temperature": -5}', '{"moisture": 0.80, "temperature": 38}', TRUE)
ON CONFLICT (zone_id) DO UPDATE
    SET min_plausible = EXCLUDED.min_plausible,
        max_plausible = EXCLUDED.max_plausible;
*/

-- ── 3. Seed Sensor Metadata ─────────────────────────────────────
/*
INSERT INTO sensor_metadata (sensor_id, zone_id, sensor_type, active)
VALUES
    ('sensor_a1', 'zone_a', 'moisture', TRUE),
    ('sensor_a2', 'zone_a', 'temperature', TRUE),
    ('sensor_b1', 'zone_b', 'moisture', TRUE),
    ('sensor_b2', 'zone_b', 'temperature', TRUE),
    ('sensor_c1', 'zone_c', 'moisture', TRUE),
    ('sensor_c2', 'zone_c', 'temperature', TRUE),
    ('sensor_d1', 'zone_d', 'moisture', TRUE),
    ('sensor_d2', 'zone_d', 'temperature', TRUE)
ON CONFLICT (sensor_id) DO NOTHING;
*/

-- ── 4. Permissions for ingestion_user ───────────────────────────
GRANT INSERT, SELECT ON data_quality_events TO ingestion_user;

-- ── 5. Record migration ─────────────────────────────────────────
INSERT INTO schema_migrations (version, description)
VALUES ('002', 'Plausibility Bounds and Data Quality Events')
ON CONFLICT (version) DO UPDATE SET description = EXCLUDED.description;

-- ── DOWN ────────────────────────────────────────────────────────
/*
BEGIN;
DROP TABLE IF EXISTS data_quality_events CASCADE;
-- Note: Seeding is not easily reversed without a specific DELETE
DELETE FROM schema_migrations WHERE version = '002';
COMMIT;
*/