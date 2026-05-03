-- ================================================================
-- MIGRATION TEMPLATE
-- Version : XXX
-- Title   : Description of changes
-- ================================================================

-- ── UP ──────────────────────────────────────────────────────────
-- Wrap in a transaction if possible (PostgreSQL supports DDL in transactions)
BEGIN;

-- Add your SQL changes here
-- Use IF NOT EXISTS for tables, indexes, and columns (PG11+)
-- ALTER TABLE my_table ADD COLUMN IF NOT EXISTS new_col INT;

-- Record migration
INSERT INTO schema_migrations (version, description)
VALUES ('XXX', 'Description of changes')
ON CONFLICT (version) DO UPDATE SET description = EXCLUDED.description;

COMMIT;

-- ── DOWN ────────────────────────────────────────────────────────
/*
BEGIN;
-- Reverse the changes here
DROP TABLE IF EXISTS my_table;
DELETE FROM schema_migrations WHERE version = 'XXX';
COMMIT;
*/
