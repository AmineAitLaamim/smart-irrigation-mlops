-- Migration 010: Auto-generate zone_id
-- We use a sequence and a default value for zone_id in the zones table.

CREATE SEQUENCE IF NOT EXISTS zones_zone_id_seq;

-- Start sequence at a higher number to avoid conflict with seed zones if they were numeric
-- But since seed zones are 'zone_a', 'zone_b', etc., any number is fine.
-- However, we should check if there are any numeric IDs already.

-- Set default to sequence value as VARCHAR
ALTER TABLE zones ALTER COLUMN zone_id SET DEFAULT nextval('zones_zone_id_seq')::VARCHAR;

-- Update the schema_migrations table
INSERT INTO schema_migrations (version, description)
VALUES ('010', 'Auto-generate zone_id')
ON CONFLICT (version) DO UPDATE SET description = EXCLUDED.description;
