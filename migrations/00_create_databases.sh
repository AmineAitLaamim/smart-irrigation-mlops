#!/bin/bash
# ================================================================
# 00_create_databases.sh
# Enable TimescaleDB at container startup
# Executed automatically by docker-entrypoint-initdb.d
# ================================================================

set -e

POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-irrigation_db}"

echo ">>> Enabling TimescaleDB on $POSTGRES_DB"

psql -v ON_ERROR_STOP=1 \
     --username "$POSTGRES_USER" \
     --dbname   "$POSTGRES_DB" <<-EOSQL

    CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

    -- Pass role passwords as session-level settings for migrations
    ALTER SYSTEM SET app.ingestion_password = '${INGESTION_PASSWORD:-ingestion_dev}';
    ALTER SYSTEM SET app.reader_password = '${READER_PASSWORD:-reader_dev}';
    ALTER SYSTEM SET app.app_password = '${APP_PASSWORD:-app_dev}';
    SELECT pg_reload_conf();

    SELECT default_version, installed_version
    FROM   pg_available_extensions
    WHERE  name = 'timescaledb';

EOSQL

echo ">>> TimescaleDB ready on $POSTGRES_DB"