# Database Migration Management

## Overview
The Smart Irrigation System uses a custom SQL-based migration runner. Migrations are stored in `migrations/sql/` and tracked in the `schema_migrations` table.

## Conventions
- **Naming**: `XXX_description.sql` (e.g., `009_add_weather_cache.sql`).
- **Idempotency**: All migrations must be safely re-runnable. Use `CREATE TABLE IF NOT EXISTS`, `IF NOT EXISTS` for indexes/columns, and `ON CONFLICT DO NOTHING`.
- **Transactions**: Wrap DDL changes in `BEGIN; ... COMMIT;` blocks.
- **Up/Down**: Include a commented-out `DOWN` block at the bottom of the file for manual rollbacks.

## Execution
Migrations are applied automatically at container startup by the `run_migrations.sh` script located in the `migrations/` directory.

### Manual Execution
To apply migrations manually from within the `timescaledb` container:
```bash
/docker-entrypoint-initdb.d/run_migrations.sh
```

## Creating New Migrations
Copy `migrations/TEMPLATE.sql` to a new file in `migrations/sql/` and increment the version number.
