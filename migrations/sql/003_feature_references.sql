-- ================================================================
-- Migration 003 : Feature References and Model Predictions
-- ================================================================

-- ── 1. Feature References (computed rolling features & rollups) ─
CREATE TABLE IF NOT EXISTS feature_references (
    id            BIGSERIAL,
    computed_at   TIMESTAMPTZ NOT NULL,
    zone_id       VARCHAR(50) NOT NULL REFERENCES zones(zone_id),
    sensor_id     VARCHAR(50),
    window_size   VARCHAR(20) NOT NULL, -- e.g. '30m', '1h', '3h', '24h', '1h_rollup', '1d_rollup'
    feature_name  VARCHAR(50) NOT NULL, -- e.g. 'mean_moisture', 'std_temperature', 'rate_of_change'
    feature_value FLOAT,
    PRIMARY KEY (id, computed_at)
);

CREATE INDEX IF NOT EXISTS idx_feature_references_zone_time
    ON feature_references (zone_id, computed_at DESC);

CREATE INDEX IF NOT EXISTS idx_feature_references_sensor_feature
    ON feature_references (sensor_id, feature_name, computed_at DESC);

-- ── 2. Hourly Rollups ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hourly_rollup (
    hour_start    TIMESTAMPTZ NOT NULL,
    zone_id       VARCHAR(50) NOT NULL REFERENCES zones(zone_id),
    sensor_id     VARCHAR(50),
    avg_moisture  FLOAT,
    min_moisture  FLOAT,
    max_moisture  FLOAT,
    std_moisture  FLOAT,
    count_moisture INTEGER,
    avg_temperature  FLOAT,
    min_temperature  FLOAT,
    max_temperature  FLOAT,
    std_temperature  FLOAT,
    count_temperature INTEGER,
    PRIMARY KEY (hour_start, zone_id, sensor_id)
);

CREATE INDEX IF NOT EXISTS idx_hourly_rollup_zone_time
    ON hourly_rollup (zone_id, hour_start DESC);

-- ── 3. Daily Rollups ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS daily_rollup (
    day_start     TIMESTAMPTZ NOT NULL,
    zone_id       VARCHAR(50) NOT NULL REFERENCES zones(zone_id),
    sensor_id     VARCHAR(50),
    avg_moisture  FLOAT,
    min_moisture  FLOAT,
    max_moisture  FLOAT,
    std_moisture  FLOAT,
    count_moisture INTEGER,
    avg_temperature  FLOAT,
    min_temperature  FLOAT,
    max_temperature  FLOAT,
    std_temperature  FLOAT,
    count_temperature INTEGER,
    PRIMARY KEY (day_start, zone_id, sensor_id)
);

CREATE INDEX IF NOT EXISTS idx_daily_rollup_zone_time
    ON daily_rollup (zone_id, day_start DESC);

-- ── 4. Model Predictions Hypertable ──────────────────────────────
CREATE TABLE IF NOT EXISTS model_predictions (
    id            BIGSERIAL,
    predicted_at  TIMESTAMPTZ NOT NULL,
    zone_id       VARCHAR(50) NOT NULL REFERENCES zones(zone_id),
    model_version VARCHAR(100),
    prediction    FLOAT,
    confidence    FLOAT,
    PRIMARY KEY (id, predicted_at)
);

SELECT create_hypertable(
    'model_predictions',
    'predicted_at',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists       => TRUE
);

CREATE INDEX IF NOT EXISTS idx_model_predictions_zone_time
    ON model_predictions (zone_id, predicted_at DESC);

-- ── 5. Permissions ───────────────────────────────────────────────
GRANT INSERT, SELECT ON feature_references TO ingestion_user;
GRANT INSERT, SELECT ON hourly_rollup      TO ingestion_user;
GRANT INSERT, SELECT ON daily_rollup       TO ingestion_user;
GRANT INSERT, SELECT ON model_predictions   TO ingestion_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ingestion_user;

-- ── 6. Record migration ──────────────────────────────────────────
INSERT INTO schema_migrations (version, description)
VALUES ('003', 'Feature References and Model Predictions')
ON CONFLICT (version) DO UPDATE SET description = EXCLUDED.description;

-- ── DOWN ────────────────────────────────────────────────────────
/*
BEGIN;
DROP TABLE IF EXISTS model_predictions CASCADE;
DROP TABLE IF EXISTS daily_rollup CASCADE;
DROP TABLE IF EXISTS hourly_rollup CASCADE;
DROP TABLE IF EXISTS feature_references CASCADE;
DELETE FROM schema_migrations WHERE version = '003';
COMMIT;
*/
