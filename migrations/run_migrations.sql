-- ================================================================
-- run_migrations.sql
-- Executed at startup — applies migrations in order
-- RULE: never modify an already-applied migration
--       only add new \i lines at the bottom
-- ================================================================

\i /migrations/sql/001_init_timescaledb.sql

-- 002 : DataOps  — DA-04 (data_quality_events)
-- 003 : MLOps    — Aya (feature_references)
-- 004 : MLOps    — Aya (shadow_comparison)
-- 005 : DevOps   — Amine (users + zone ownership)