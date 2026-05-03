-- ================================================================
-- Migration 012 : Remove Default Zones
-- Sprint  : S1
-- Tables  : zones, sensor_metadata
-- ================================================================

-- This migration removes the default zones (zone_a, zone_b, zone_c, zone_d)
-- and their associated metadata that were seeded in migration 002.

DELETE FROM sensor_metadata WHERE zone_id IN ('zone_a', 'zone_b', 'zone_c', 'zone_d');
DELETE FROM zones WHERE zone_id IN ('zone_a', 'zone_b', 'zone_c', 'zone_d');

-- Record migration
INSERT INTO schema_migrations (version, description)
VALUES ('012', 'Remove default zones')
ON CONFLICT (version) DO UPDATE SET description = EXCLUDED.description;
