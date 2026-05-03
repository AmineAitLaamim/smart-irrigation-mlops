-- ================================================================
-- Migration 006 : Quality Rules and Monitoring Views
-- ================================================================

-- ── 1. Configurable Quality Rules ────────────────────────────────
CREATE TABLE IF NOT EXISTS quality_rules (
    rule_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_name       VARCHAR(100) NOT NULL UNIQUE,
    rule_type       VARCHAR(50) NOT NULL, -- 'plausibility', 'stuck_value', 'sudden_jump', 'flatline', 'rate_of_change'
    sensor_type     VARCHAR(50),          -- NULL = all sensor types
    zone_id         VARCHAR(50) REFERENCES zones(zone_id) ON DELETE CASCADE,
    parameters      JSONB NOT NULL DEFAULT '{}',
    severity        VARCHAR(20) NOT NULL DEFAULT 'warning',
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quality_rules_active_type
    ON quality_rules (active, rule_type);

CREATE INDEX IF NOT EXISTS idx_quality_rules_zone_sensor
    ON quality_rules (zone_id, sensor_type) WHERE zone_id IS NOT NULL;

DROP TRIGGER IF EXISTS set_quality_rules_updated_at ON quality_rules;

CREATE TRIGGER set_quality_rules_updated_at
    BEFORE UPDATE ON quality_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ── 2. Seed Default Quality Rules ─────────────────────────────
INSERT INTO quality_rules (rule_name, rule_type, sensor_type, parameters, severity, active)
VALUES
    ('stuck_moisture',     'stuck_value', 'moisture',     '{"consecutive_count": 5,  "tolerance": 0.001}', 'warning',  TRUE),
    ('stuck_temperature',  'stuck_value', 'temperature',  '{"consecutive_count": 10, "tolerance": 0.01}',  'warning',  TRUE),
    ('sudden_jump_moisture','sudden_jump', 'moisture',     '{"max_delta": 0.35, "max_pct_change": 50}',   'critical', TRUE),
    ('flatline_moisture',  'flatline',    'moisture',     '{"window_minutes": 30, "max_variance": 0.0001}', 'warning',  TRUE),
    ('flatline_temperature','flatline',    'temperature',  '{"window_minutes": 60, "max_variance": 0.01}',   'warning',  TRUE),
    ('rate_of_change_temp','rate_of_change','temperature','{"window_minutes": 15, "max_rate_per_min": 2.0}', 'warning', TRUE)
ON CONFLICT (rule_name) DO UPDATE
    SET parameters  = EXCLUDED.parameters,
        severity    = EXCLUDED.severity,
        active      = EXCLUDED.active,
        updated_at  = NOW();

-- ── 3. Quality Metrics Summary View (Grafana-friendly) ────────
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

-- ── 4. Sensor Health Score View ─────────────────────────────────
CREATE OR REPLACE VIEW v_sensor_health AS
WITH recent_events AS (
    SELECT
        zone_id,
        sensor_id,
        event_type,
        severity,
        COUNT(*) AS cnt
    FROM data_quality_events
    WHERE timestamp >= NOW() - INTERVAL '24 hours'
    GROUP BY zone_id, sensor_id, event_type, severity
)
SELECT
    sm.zone_id,
    sm.sensor_id,
    sm.sensor_type,
    sm.active,
    COALESCE(SUM(re.cnt) FILTER (WHERE re.severity = 'critical'), 0) AS critical_count,
    COALESCE(SUM(re.cnt) FILTER (WHERE re.severity = 'warning'),  0) AS warning_count,
    COALESCE(SUM(re.cnt), 0) AS total_anomalies,
    CASE
        WHEN COALESCE(SUM(re.cnt) FILTER (WHERE re.severity = 'critical'), 0) > 5 THEN 'unhealthy'
        WHEN COALESCE(SUM(re.cnt), 0) > 10 THEN 'degraded'
        ELSE 'healthy'
    END AS health_status
FROM sensor_metadata sm
LEFT JOIN recent_events re
    ON sm.zone_id = re.zone_id AND sm.sensor_id = re.sensor_id
GROUP BY sm.zone_id, sm.sensor_id, sm.sensor_type, sm.active;

-- ── 5. Permissions ───────────────────────────────────────────────
GRANT INSERT, SELECT, UPDATE ON quality_rules TO ingestion_user;
GRANT SELECT ON v_quality_metrics  TO ingestion_user;
GRANT SELECT ON v_sensor_health    TO ingestion_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ingestion_user;

-- ── 6. Record migration ──────────────────────────────────────────
INSERT INTO schema_migrations (version)
VALUES ('006')
ON CONFLICT DO NOTHING;
