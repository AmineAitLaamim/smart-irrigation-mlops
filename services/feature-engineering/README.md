# Feature Engineering Service

## Overview
The Feature Engineering service is responsible for transforming raw sensor readings into analysis-ready features for ML model training and inference. It operates in both **streaming** (real-time) and **batch** modes.

## Feature Store (TimescaleDB)
Features are persisted in the `feature_references` table, which serves as our ML Feature Store.

### Schema
- `computed_at`: Timestamp of feature computation.
- `zone_id`: Reference to the physical zone.
- `sensor_id`: Reference to the specific sensor.
- `window_size`: The lookback period (e.g., `30m`, `1h`, `24h`).
- `feature_name`: The metric identifier (e.g., `mean_moisture`).
- `feature_value`: The actual computed value.
- `model_version`: Tag indicating the logic version used for computation (default: `v1`).

## Data Pipeline & Redis Contracts

### 1. Ingestion (Streaming)
- **Subscribes to**: `ingestion:processed`
- **Logic**: Triggered whenever a valid reading is written to the database. It immediately recalculates rolling features for the affected sensor.
- **Publishes to**: `features:computed`

### 2. Batch Processing
- **Interval**: Configurable via `BATCH_INTERVAL_SECONDS` (default: 5 mins).
- **Logic**: Computes hourly and daily rollups (`hourly_rollup`, `daily_rollup`) and refreshes rolling features for all active sensors.

## Agricultural Metrics (Sample Features)
The following metrics are computed across multiple windows (`30m`, `1h`, `3h`, `24h`):

| Metric | Feature Name | Description |
| :--- | :--- | :--- |
| **Rolling Mean** | `mean_moisture` | Average moisture levels; used to identify trends. |
| **Variability** | `std_moisture` | Standard deviation; indicates sensor stability or rapid soil change. |
| **Extremes** | `min_moisture` / `max_moisture` | Daily peaks and troughs for crop stress analysis. |
| **Trend** | `rate_of_change_moisture` | Delta between last and first reading in window; predicts drying speed. |
| **Thermal Load** | `mean_temperature` | Average ambient/soil temperature for growth stage modeling. |
| **Soil Retention** | `soil_water_retention_index` | Moisture adjusted by the zone soil profile to capture water-holding behavior. |
| **Dryness Pressure** | `soil_dryness_index` | Dryness proxy adjusted by drainage profile to highlight irrigation urgency. |
| **Evapotranspiration Proxy** | `evapotranspiration_proxy` | Temperature and dryness proxy used for irrigation-related feature enrichment. |

## Configuration
- `REDIS_URL`: Connection string for Redis broker.
- `DATABASE_URL`: Connection string for TimescaleDB.
- `ROLLUP_WINDOWS`: Comma-separated list of windows (e.g., `30m,1h,24h`).
- `OUTLIER_ZSCORE_THRESHOLD`: Sensitivity for outlier smoothing (default: `3.0`).
- `FEATURE_MODEL_VERSION`: Version tag stored alongside computed features in `feature_references`.
