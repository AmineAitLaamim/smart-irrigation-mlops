# Project Architecture: Smart Irrigation System

## High-Level Overview
The Smart Irrigation System is an AI-driven, event-based microservices platform designed to optimize water usage in agricultural settings. It processes real-time sensor data, applies machine learning for moisture prediction, and automates irrigation control while ensuring data integrity and security.

## Core Architectural Patterns
- **Microservices**: Decoupled services communicating over HTTP and Redis Pub/Sub.
- **Event-Driven Data Pipeline**: Real-time telemetry processing using a multi-stage Redis queue.
- **Time-Series Optimized**: Leverages TimescaleDB (PostgreSQL extension) for high-performance ingestion and analytical queries on sensor data.
- **API-First**: Centralized access through an API Gateway with built-in RBAC and resource ownership.

## System Components

### 1. Data Ingestion & Quality
- **Sensor Simulator**: Generates synthetic telemetry (moisture, temperature) for testing.
- **Data Ingestion**: The entry point. Validates readings against physical plausibility bounds.
- **Data Quality**: Audits the pipeline for sensor malfunctions (stuck values, sudden jumps) and generates health scores.

### 2. Feature Engineering & ML
- **Feature Engineering**: A dual-mode (streaming/batch) service that computes rolling metrics (mean, std dev) and agricultural rollups.
- **Feature Store**: Versioned repository in TimescaleDB for ML features.
- **Model Server**: Serves ML models for real-time inference (Rest API).
- **Drift Monitor**: Monitors model performance and data distribution changes.

### 3. Management & Control
- **User Service**: Manages identities, authentication (JWT), and roles.
- **API Gateway**: Handles routing, rate limiting, and enforces zone-level security.
- **Irrigation Controller**: Executes irrigation logic based on model predictions and physical constraints.

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
