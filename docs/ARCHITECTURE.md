# Project Architecture: Smart Irrigation System

> **Note:** For detailed irrigation system documentation including complete flow diagrams, code snippets, event lifecycle, and edge cases, see [IRRIGATION_SYSTEM.md](./IRRIGATION_SYSTEM.md).

## High-Level Overview
The Smart Irrigation System is an AI-driven, event-based microservices platform designed to optimize water usage in agricultural settings. It processes real-time sensor data, applies machine learning for moisture prediction, and automates irrigation control while ensuring data integrity and security.

## Core Architectural Patterns
- **Microservices**: Decoupled services communicating over HTTP and Redis Pub/Sub.
- **Event-Driven Data Pipeline**: Real-time telemetry processing using a multi-stage Redis queue.
- **Time-Series Optimized**: Leverages TimescaleDB (PostgreSQL extension) for high-performance ingestion and analytical queries on sensor data.
- **API-First**: Centralized access through an API Gateway with built-in RBAC and resource ownership.

## System Components

### 1. Data Ingestion & Quality
- **Sensor Simulator**: Generates synthetic telemetry (moisture, temperature). It dynamically discovers active zones via the User Service API and implements realistic moisture depletion models tailored to specific soil types (sandy, loam, clay). It publishes payload directly to Redis `sensor:data` channel.
- **Data Ingestion**: The entry point. Validates readings against physical plausibility bounds.
- **Data Quality**: Audits the pipeline for sensor malfunctions (stuck values, sudden jumps) and generates health scores.

### 2. Feature Engineering & ML
- **Feature Engineering**: A dual-mode (streaming/batch) service that computes rolling metrics (mean, std dev) and agricultural rollups.
- **Feature Store**: Versioned repository in TimescaleDB for ML features.
- **Model Server**: Serves ML models for real-time inference (Rest API).
- **Drift Monitor**: Monitors model performance and data distribution changes.
- **MLflow & MinIO**: Orchestrates the model lifecycle. MinIO acts as the **Object Store** for versioned training datasets and model artifacts, ensuring full reproducibility and decoupling from the live database.

### 3. Management & Control
- **User Service**: Manages identities, authentication (JWT), and roles.
- **API Gateway**: Handles routing, rate limiting, and enforces zone-level security.
- **Irrigation Controller**: Executes irrigation logic based on model predictions and physical constraints.

#### Irrigation Controller

The Irrigation Controller subscribes to the `predictions:new` Redis channel and evaluates each prediction against zone-specific thresholds to determine if irrigation should be triggered.

**Trigger Logic:**
1. Receives prediction payload from Redis (published by Airflow DAG)
2. Fetches zone thresholds from `zones` table (`moisture_min`, `moisture_max`)
3. If prediction >= `moisture_min`: no action (moisture is adequate)
4. If prediction < `moisture_min`: calculates deficit and triggers irrigation event

**Deduplication:**
- To prevent multiple irrigation events from firing simultaneously (e.g., when multiple sensors in the same zone trigger predictions), the controller checks for recent events within the last 10 minutes
- If an irrigation event exists for the zone within 10 minutes, subsequent predictions are skipped

**Event Storage:**
- Triggered events are stored in the `irrigation_events` table with:
  - `zone_id`: The zone that triggered irrigation
  - `trigger_reason`: Currently always `predicted_moisture_below_threshold`
  - `recommended_volume`: Calculated as `(threshold_min - prediction) * 100` liters
  - `status`: Starts as `pending`, then automatically transitions to `completed`

**Autonomous Execution:**
- After creating the event, the controller schedules an automatic execution task
- After 5 seconds, it updates the event:
  - `status`: `completed`
  - `actual_volume`: Set to recommended_volume (simulated execution)
  - `duration_seconds`: 300 (5 minutes simulated irrigation)
  - `completed_at`: Timestamp when execution finished
- Also publishes to `irrigation:triggered` channel for notification service

## Irrigation Trigger Flow

The complete end-to-end process of how irrigation is triggered:

### Step 1: Sensor Data Generation
```
sensor-simulator → Redis (sensor:data channel)
```
- Sensor simulator generates moisture/temperature readings for each zone
- Publishes to Redis channel `sensor:data`

### Step 2: Data Ingestion
```
data-ingestion (consumes sensor:data) → TimescaleDB (sensor_readings table)
```
- Validates readings against physical plausibility bounds
- Stores in `sensor_readings` table

### Step 3: Feature Engineering
```
feature-engineering → feature_references table
```
- Computes rolling metrics (mean moisture, std dev, min, max, evapotranspiration proxy)
- Stores computed features in `feature_references` table

### Step 4: Prediction (Airflow DAG: scheduled_zone_predictions)
```
Airflow DAG:
  1. Queries feature_references for each active zone
  2. Calls model-server REST API (/v1/predict)
  3. Stores prediction in model_predictions table
  4. PUBLISHES to Redis (predictions:new channel)
```
- The DAG runs on schedule or manually
- Publishes payload: `{"zone_id": "2", "prediction": 36.66, "sensor_id": "2-s1", "model_version": "1", "predicted_at": "..."}`

### Step 5: Irrigation Controller (Redis Consumer)
```
irrigation-controller (subscribes to predictions:new):
  1. Receives: {"zone_id": "2", "prediction": 36.66, ...}
  2. Fetches zone thresholds from zones table (moisture_min=55, moisture_max=60)
  3. Checks: prediction < moisture_min? → Yes (36.66 < 55)
  4. Checks: recent event exists in last 10 minutes? → No
  5. Calculates: deficit = 55 - 36.66 = 18.34
  6. Calculates: volume = 18.34 * 100 = 1834 liters
  7. INSERT into irrigation_events (status=pending)
  8. Logs: "Irrigation TRIGGERED for zone 2: volume=1834"
  9. Publishes to irrigation:triggered channel
```

### Step 6: Notification (Optional)
```
notification-service (subscribes to irrigation:triggered)
```
- Receives trigger event
- Sends alerts to users (email, push, etc.)

### Data Flow Diagram
```
┌─────────────────┐    sensor:data     ┌─────────────────┐
│ sensor-simulator│ ──────────────────►│data-ingestion   │
└─────────────────┘                    └────────┬────────┘
                                                 │
                                          ingestion:processed
                                                 │
                                                 ▼
                                        ┌─────────────────────┐
                                        │feature-engineering │
                                        └─────────┬───────────┘
                                                  │
                                        features:computed
                                                  │
                                                  ▼
                                       ┌────────────────────┐
                                       │  model-server      │
                                       │  (inference)       │
                                       └─────────┬──────────┘
                                                 │
                                        predictions:new (Redis)
                                                 │
                                                 ▼
                                       ┌─────────────────────┐
                                       │irrigation-controller│
                                       │ - check threshold   │
                                       │ - deduplicate (10m) │
                                       │ - store event       │
                                       └─────────┬───────────┘
                                                 │
                                        irrigation:triggered
                                                 │
                                                 ▼
                                       ┌─────────────────────┐
                                       │notification-service │
                                       └─────────────────────┘
```

## Data Flow (Telemetry)
1. **Source**: `sensor-simulator` publishes to `sensor:data` (Redis).
2. **Validation**: `data-ingestion` validates and writes to `sensor_readings` (TimescaleDB).
3. **Trigger**: `data-ingestion` publishes success to `ingestion:processed`.
4. **Engineering**: `feature-engineering` recalculates rolling features and publishes to `features:computed`.
5. **Quality**: `data-quality` audits for malfunctions and records events in `data_quality_events`.
6. **Inference**: (Pending) `model-server` consumes features for predictions.

## Monitoring & Observability
- **Prometheus**: Scrapes metrics from microservices (ingestion rates, anomaly counts).
- **Grafana**: Visualizes sensor health, ML performance, and system status.
- **Jenkins**: Orchestrates CI/CD pipelines and automated testing.
