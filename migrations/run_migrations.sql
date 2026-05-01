-- ================================================================
-- run_migrations.sql
-- Executed at startup — applies migrations in order
-- RULE: never modify an already-applied migration
--       only add new \i lines at the bottom
-- ================================================================

\i /docker-entrypoint-initdb.d/sql/001_init_timescaledb.sql
\i /docker-entrypoint-initdb.d/sql/002_plausibility_bounds.sql
\i /docker-entrypoint-initdb.d/sql/003_feature_references.sql
\i /docker-entrypoint-initdb.d/sql/004_shadow_comparison.sql
\i /docker-entrypoint-initdb.d/sql/005_user_and_zone_ownership.sql
\i /docker-entrypoint-initdb.d/sql/006_quality_rules.sql
\i /docker-entrypoint-initdb.d/sql/007_add_user_roles.sql
\i /docker-entrypoint-initdb.d/sql/008_zone_ownership_system.sql
