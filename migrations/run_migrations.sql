-- ================================================================
-- run_migrations.sql
-- Executed at startup — applies migrations in order
-- RULE: never modify an already-applied migration
--       only add new \i lines at the bottom
-- ================================================================

\i /migrations/sql/001_init_timescaledb.sql
\i /migrations/sql/005_user_and_zone_ownership.sql