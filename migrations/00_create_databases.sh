#!/bin/bash
# ================================================================
# 00_create_databases.sh
# Active TimescaleDB au démarrage du container
# Exécuté automatiquement par docker-entrypoint-initdb.d
# ================================================================

set -e

POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-irrigation_db}"

echo ">>> Activation de TimescaleDB sur $POSTGRES_DB"

psql -v ON_ERROR_STOP=1 \
     --username "$POSTGRES_USER" \
     --dbname   "$POSTGRES_DB" <<-EOSQL

    CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

    SELECT default_version, installed_version
    FROM   pg_available_extensions
    WHERE  name = 'timescaledb';

EOSQL

echo ">>> TimescaleDB prêt sur $POSTGRES_DB"