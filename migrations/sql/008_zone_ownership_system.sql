-- ================================================================
-- Migration 008 : Zone Ownership System
-- Sprint  : S1
-- Tables  : zones
-- ================================================================

-- 1. Add owner_id and source columns
ALTER TABLE zones ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES users(user_id) ON DELETE SET NULL;
ALTER TABLE zones ADD COLUMN IF NOT EXISTS source VARCHAR(20) NOT NULL DEFAULT 'api' CHECK (source IN ('api', 'yaml'));

-- 2. Set existing zones as source='yaml' since they were seeded via migration/yaml
UPDATE zones SET source = 'yaml' WHERE source = 'api';

-- 3. Record migration
INSERT INTO schema_migrations (version)
VALUES ('008')
ON CONFLICT DO NOTHING;
