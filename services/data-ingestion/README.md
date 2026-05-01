# Data Ingestion Service

## Overview
The Data Ingestion service is the high-throughput entry point for raw sensor telemetry. It validates, cleans, and persists data to the primary storage.

## Features Implemented
### 1. Real-time Ingestion
- Subscribes to the `sensor:data` Redis channel.
- Handles high-concurrency streams using an asynchronous consumer loop.

### 2. Physical Bound Validation
- Every reading is validated against `min_plausible` and `max_plausible` bounds defined in the `zones` table.
- Invalid readings are flagged and recorded as quality events before reaching downstream consumers.

### 3. Pipeline Coordination
- Successfully processed and validated readings are published to `ingestion:processed`.
- This serves as a "clean data" signal for the Feature Engineering and Data Quality services.

## Technical Stack
- **Framework**: FastAPI
- **Database**: TimescaleDB (Writing to `sensor_readings` and `data_quality_events`)
- **Queue**: Redis (Pub/Sub)
- **Database Driver**: `asyncpg` (Connection pooling)
