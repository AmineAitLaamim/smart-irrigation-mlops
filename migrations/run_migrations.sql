-- ================================================================
-- run_migrations.sql
-- Exécuté au démarrage — applique les migrations dans l'ordre
-- RÈGLE : ne jamais modifier un fichier déjà appliqué
--         ajouter uniquement de nouvelles lignes \i en bas
-- ================================================================

\i /migrations/sql/001_init_timescaledb.sql

-- 002 : DataOps  — DA-04 (data_quality_events)
-- 003 : MLOps    — Aya (feature_references)
-- 004 : MLOps    — Aya (shadow_comparison)
-- 005 : DevOps   — Amine (users + zone ownership)