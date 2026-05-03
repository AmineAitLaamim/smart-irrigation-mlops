-- ================================================================
-- Migration 011 : Cascade Zone Deletion
-- Sprint  : S1
-- Tables  : multiple
-- ================================================================

-- This migration adds ON DELETE CASCADE to all foreign keys that reference zones(zone_id).
-- This ensures that when a zone is deleted, all related sensor data, events, and features
-- are also removed, preventing foreign key violations.

DO $$
DECLARE
    r RECORD;
BEGIN
    -- Dynamically find and drop foreign key constraints that reference zones(zone_id)
    -- but do not already have ON DELETE CASCADE (or just drop all and re-add for simplicity)
    FOR r IN (
        SELECT tc.table_name, tc.constraint_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND kcu.column_name = 'zone_id'
          AND kcu.table_schema = 'public'
          AND tc.table_name IN (
              'sensor_readings', 
              'irrigation_events', 
              'data_quality_events',
              'feature_references', 
              'hourly_rollup', 
              'daily_rollup',
              'model_predictions', 
              'shadow_predictions'
          )
    ) LOOP
        EXECUTE 'ALTER TABLE ' || quote_ident(r.table_name) || ' DROP CONSTRAINT ' || quote_ident(r.constraint_name);
    END LOOP;
END $$;

-- 1. sensor_readings
ALTER TABLE sensor_readings 
ADD CONSTRAINT sensor_readings_zone_id_fkey 
FOREIGN KEY (zone_id) REFERENCES zones(zone_id) ON DELETE CASCADE;

-- 2. irrigation_events
ALTER TABLE irrigation_events 
ADD CONSTRAINT irrigation_events_zone_id_fkey 
FOREIGN KEY (zone_id) REFERENCES zones(zone_id) ON DELETE CASCADE;

-- 3. data_quality_events
ALTER TABLE data_quality_events 
ADD CONSTRAINT data_quality_events_zone_id_fkey 
FOREIGN KEY (zone_id) REFERENCES zones(zone_id) ON DELETE CASCADE;

-- 4. feature_references
ALTER TABLE feature_references 
ADD CONSTRAINT feature_references_zone_id_fkey 
FOREIGN KEY (zone_id) REFERENCES zones(zone_id) ON DELETE CASCADE;

-- 5. hourly_rollup
ALTER TABLE hourly_rollup 
ADD CONSTRAINT hourly_rollup_zone_id_fkey 
FOREIGN KEY (zone_id) REFERENCES zones(zone_id) ON DELETE CASCADE;

-- 6. daily_rollup
ALTER TABLE daily_rollup 
ADD CONSTRAINT daily_rollup_zone_id_fkey 
FOREIGN KEY (zone_id) REFERENCES zones(zone_id) ON DELETE CASCADE;

-- 7. model_predictions
ALTER TABLE model_predictions 
ADD CONSTRAINT model_predictions_zone_id_fkey 
FOREIGN KEY (zone_id) REFERENCES zones(zone_id) ON DELETE CASCADE;

-- 8. shadow_predictions
ALTER TABLE shadow_predictions 
ADD CONSTRAINT shadow_predictions_zone_id_fkey 
FOREIGN KEY (zone_id) REFERENCES zones(zone_id) ON DELETE CASCADE;

-- 9. Record migration
INSERT INTO schema_migrations (version, description)
VALUES ('011', 'Add ON DELETE CASCADE to zone references')
ON CONFLICT (version) DO UPDATE SET description = EXCLUDED.description;
