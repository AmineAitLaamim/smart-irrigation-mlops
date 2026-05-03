-- ================================================================
-- Migration 004 : Shadow Comparison for Model Validation
-- ================================================================

-- ── 1. Shadow Model Predictions ────────────────────────────────
CREATE TABLE IF NOT EXISTS shadow_predictions (
    id            BIGSERIAL,
    predicted_at  TIMESTAMPTZ NOT NULL,
    zone_id       VARCHAR(50) NOT NULL REFERENCES zones(zone_id),
    model_version VARCHAR(100) NOT NULL,
    prediction    FLOAT,
    confidence    FLOAT,
    PRIMARY KEY (id, predicted_at)
);

SELECT create_hypertable(
    'shadow_predictions',
    'predicted_at',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists       => TRUE
);

-- ── 2. Shadow Comparison View ──────────────────────────────────
CREATE OR REPLACE VIEW v_shadow_comparison AS
SELECT
    m.predicted_at,
    m.zone_id,
    m.model_version AS champion_version,
    m.prediction AS champion_prediction,
    s.model_version AS shadow_version,
    s.prediction AS shadow_prediction,
    ABS(m.prediction - s.prediction) AS prediction_delta
FROM model_predictions m
JOIN shadow_predictions s ON m.predicted_at = s.predicted_at AND m.zone_id = s.zone_id;

-- ── 3. Permissions ──────────────────────────────────────────────
GRANT INSERT, SELECT ON shadow_predictions TO ingestion_user;
GRANT SELECT ON v_shadow_comparison TO reader_user;

-- ── 4. Record migration ──────────────────────────────────────────
INSERT INTO schema_migrations (version)
VALUES ('004')
ON CONFLICT DO NOTHING;
