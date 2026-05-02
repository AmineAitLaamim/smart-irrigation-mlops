-- ================================================================
-- Migration 009 : Feature Versioning
-- Sprint  : S1
-- Tables  : feature_references
-- ================================================================

-- ── 1. Add model_version column ─────────────────────────────────
ALTER TABLE feature_references ADD COLUMN IF NOT EXISTS model_version VARCHAR(50) NOT NULL DEFAULT 'v1';

-- ── 2. Update Index ──────────────────────────────────────────────
DROP INDEX IF EXISTS idx_feature_references_sensor_feature;
CREATE INDEX IF NOT EXISTS idx_feature_references_v_sensor_feature
    ON feature_references (model_version, sensor_id, feature_name, computed_at DESC);

-- ── 3. Record migration ──────────────────────────────────────────
INSERT INTO schema_migrations (version, description)
VALUES ('009', 'Add model_version to feature_references')
ON CONFLICT (version) DO UPDATE SET description = EXCLUDED.description;

-- ── DOWN ────────────────────────────────────────────────────────
/*
BEGIN;
ALTER TABLE feature_references DROP COLUMN IF EXISTS model_version;
DROP INDEX IF EXISTS idx_feature_references_v_sensor_feature;
CREATE INDEX IF NOT EXISTS idx_feature_references_sensor_feature
    ON feature_references (sensor_id, feature_name, computed_at DESC);
DELETE FROM schema_migrations WHERE version = '009';
COMMIT;
*/
