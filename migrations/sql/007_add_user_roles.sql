-- ================================================================
-- Migration 007 : Add User Roles
-- Sprint  : S1
-- Tables  : users
-- ================================================================

ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;

-- Record migration
INSERT INTO schema_migrations (version)
VALUES ('007')
ON CONFLICT DO NOTHING;
