#!/bin/bash
# ================================================================
# run_migrations.sh
# Smart Migration Runner for Smart Irrigation System
# ================================================================

set -e

POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-irrigation_db}"
MIGRATIONS_DIR="/docker-entrypoint-initdb.d/sql"

echo ">>> Starting Migration Runner..."

# Function to run a migration file
run_migration() {
    local file=$1
    local version=$(basename "$file" | cut -d'_' -f1)
    
    echo ">>> Applying migration $version: $(basename "$file")"
    
    psql -v ON_ERROR_STOP=1 \
         --username "$POSTGRES_USER" \
         --dbname   "$POSTGRES_DB" \
         -f "$file"
}

# Check if schema_migrations table exists
TABLE_EXISTS=$(psql -t -Ac "SELECT 1 FROM information_schema.tables WHERE table_name = 'schema_migrations'" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" | xargs)

if [ "$TABLE_EXISTS" != "1" ]; then
    echo ">>> Initializing schema_migrations table..."
    # Always run 001 first if table doesn't exist
    run_migration "$MIGRATIONS_DIR/001_init_timescaledb.sql"
fi

# Get applied migrations
APPLIED_MIGRATIONS=$(psql -t -Ac "SELECT version FROM schema_migrations" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB")

# Loop through all migration files in order
for file in $(ls $MIGRATIONS_DIR/*.sql | sort); do
    version=$(basename "$file" | cut -d'_' -f1)
    
    # Check if version is already applied
    if [[ ! " $APPLIED_MIGRATIONS " =~ " $version " ]]; then
        run_migration "$file"
    else
        echo ">>> Migration $version already applied, skipping."
    fi
done

echo ">>> All migrations applied successfully."
