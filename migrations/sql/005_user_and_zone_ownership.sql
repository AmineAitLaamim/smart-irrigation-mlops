-- ================================================================
-- Migration 005 : User and Zone Ownership
-- Sprint  : S1
-- Tables  : users
-- ================================================================

CREATE TABLE IF NOT EXISTS users (
    user_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Auto-update updated_at on user changes
CREATE TRIGGER set_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Record migration
INSERT INTO schema_migrations (version, description)
VALUES ('005', 'User and Zone Ownership')
ON CONFLICT (version) DO UPDATE SET description = EXCLUDED.description;

-- ── DOWN ────────────────────────────────────────────────────────
/*
BEGIN;
DROP TABLE IF EXISTS users CASCADE;
DELETE FROM schema_migrations WHERE version = '005';
COMMIT;
*/
