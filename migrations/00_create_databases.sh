#!/bin/bash
# ================================================================
# 00_create_databases.sh
# Ensure TimescaleDB is enabled and required databases exist at startup
# Executed automatically by docker-entrypoint-initdb.d
# ================================================================

set -e

POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-irrigation_db}"

echo ">>> Ensuring TimescaleDB and required databases exist"

# Enable TimescaleDB on the main application database and record role passwords
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL

    CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

    -- Pass role passwords as database-level settings for migrations
    ALTER DATABASE "$POSTGRES_DB" SET app.ingestion_password = '${INGESTION_PASSWORD:-ingestion_dev}';
    ALTER DATABASE "$POSTGRES_DB" SET app.reader_password = '${READER_PASSWORD:-reader_dev}';
    ALTER DATABASE "$POSTGRES_DB" SET app.app_password = '${APP_PASSWORD:-app_dev}';

    SELECT default_version, installed_version
    FROM   pg_available_extensions
    WHERE  name = 'timescaledb';

EOSQL

# Create the Airflow metadata database if it doesn't exist
if psql -v ON_ERROR_STOP=0 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -tAc "SELECT 1 FROM pg_database WHERE datname='airflow_db'" | grep -q 1; then
  echo ">>> airflow_db already exists"
else
  echo ">>> Creating airflow_db"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "CREATE DATABASE airflow_db OWNER \"${POSTGRES_USER}\""
fi

# Ensure TimescaleDB extension is available in the airflow_db as well (safe to run repeatedly)
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "airflow_db" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
EOSQL

echo ">>> Databases ready"
