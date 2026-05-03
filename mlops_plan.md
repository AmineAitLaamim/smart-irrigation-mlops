# MLOps Execution Plan

This file tracks the MLOps tasks extracted from `create_all_issues.sh`.
Mark each item complete as soon as the corresponding implementation is done.

## Critical Path

`ML-01 -> ML-02 -> ML-03 -> ML-04 -> ML-05 -> ML-06`

## Task Order

- [x] ML-01: ML Environment Setup and Data Exploration
- [x] ML-02: Data Preparation Pipeline Integration
- [x] ML-11: Feature Engineering Enhancement
- [x] ML-03: Soil Moisture Prediction Model (XGBoost)
- [x] ML-04: Model Training Pipeline Automation
- [x] ML-05: Model Evaluation and Validation
- [x] ML-06: Prediction API Development
- [x] ML-09: Prediction Scheduling Service
- [x] ML-12: Irrigation Optimization Algorithm
- [x] ML-07: Anomaly Detection Module
- [x] ML-08: Model Monitoring and Performance Tracking
- [x] ML-10: ML Pipeline Containerization
- [ ] ML-13: ML API Integration Testing
- [x] ML-14: ML Documentation and Model Cards
- [x] ML-15: ML Demo and Presentation Preparation

## Execution Details

### 1. Foundation and Data Preparation

#### ML-01: ML Environment Setup and Data Exploration
- [x] Standardize Python 3.11 ML dependencies: `xgboost`, `scikit-learn`, `optuna`, `pandas`, `numpy`, `matplotlib`, and MLflow client support
- [x] Configure MLflow tracking and model registry naming conventions
- [x] Add exploration assets for sensor-data analysis
- [x] Produce a reproducible exploration notebook or script-backed report

#### ML-02: Data Preparation Pipeline Integration
- [x] Build a dataset preparation pipeline that reads raw sensor data from TimescaleDB
- [x] Apply cleaning and normalization before model consumption
- [x] Integrate feature-store reads from `feature_references`
- [x] Implement chronological train/validation/test splitting with time-aware cross-validation
- [x] Log dataset lineage and versions through MLflow datasets

### 2. Feature Engineering and Model Development

#### ML-11: Feature Engineering Enhancement
- [x] Compute rolling averages for `30m`, `1h`, `3h`, and `24h`
- [x] Add rate-of-change metrics, moisture variance, and soil-specific indices
- [x] Persist computed features to `feature_references` with timestamps, zone references, and model version tags

#### ML-03: Soil Moisture Prediction Model (XGBoost)
- [x] Establish baseline models with linear regression and random forest
- [x] Train XGBoost on the prepared datasets
- [x] Run Optuna hyperparameter optimization with time-series cross-validation
- [x] Evaluate with `RMSE`, `MAE`, and `R²`
- [x] Compare XGBoost to baselines and register the best model in MLflow
- [x] Produce a first model card draft during registration

#### ML-04: Model Training Pipeline Automation
- [x] Build an Airflow DAG that refreshes data, computes features, trains, evaluates, and proposes model promotion
- [x] Add a promotion rule based on a configured improvement margin
- [x] Use MLflow stages: `None`, `Staging`, `Production`, `Archived`

#### ML-05: Model Evaluation and Validation
- [x] Add holdout validation
- [x] Add shadow-mode comparisons that do not affect irrigation behavior
- [x] Generate confidence intervals and failure-case analysis
- [x] Automate statistical comparison between candidate and production models

### 3. Serving, Prediction Flow, and Irrigation Decisions

#### ML-06: Prediction API Development
- [x] Build a `model-server` with gRPC on port `5001` and REST on port `8501`
- [x] Expose `POST /v1/predict`
- [x] Expose `GET /v1/model/info`
- [x] Expose `GET /v1/model/version`
- [x] Return predicted moisture and confidence intervals from `/v1/predict`
- [x] Load the production model from MLflow and support hot reload
- [x] Export Prometheus metrics for latency, throughput, and errors

#### ML-09: Prediction Scheduling Service
- [x] Build an Airflow DAG for scheduled per-zone predictions
- [x] Call the model server REST endpoint
- [x] Persist outputs to `model_predictions`
- [x] Publish prediction events on `predictions:new`

#### ML-12: Irrigation Optimization Algorithm
- [x] Build the irrigation controller that evaluates predicted moisture against thresholds
- [x] Consider recent rainfall and soil saturation before recommending irrigation
- [x] Log actions in `irrigation_events`
- [x] Subscribe to prediction events via Redis Pub/Sub
- [x] Keep a periodic evaluation loop as fallback
- [x] Expose `GET /v1/irrigation/events`

### 4. Drift, Monitoring, Packaging, and Completion

#### ML-07: Anomaly Detection Module
- [x] Compute Page-Hinkley statistics
- [x] Compute KL divergence
- [x] Track rolling prediction-error metrics
- [x] Store drift stats
- [x] Publish Redis alerts
- [x] Expose `GET /v1/drift/status`

#### ML-08: Model Monitoring and Performance Tracking
- [x] Emit Prometheus metrics for prediction quality, drift, and latency
- [x] Define Grafana dashboard requirements for ML performance

#### ML-10: ML Pipeline Containerization
- [x] Containerize `model-server`, `drift-monitor`, `irrigation-controller`, and `feature-engineering`
- [x] Use optimized multi-stage builds where practical
- [x] Add health checks for each ML service
- [x] Register services in `docker-compose.ml.yml`
- [x] Verify inter-service startup and connectivity

#### ML-13: ML API Integration Testing
- [x] Add integration tests for `/v1/predict`, `/v1/model/info`, `/v1/model/version`, `/v1/drift/status`, and `/v1/irrigation/events`
- [x] Validate response payloads against Pydantic contracts
- [ ] Reach at least `80%` code coverage for the model-server service

#### ML-14: ML Documentation and Model Cards
- [x] Finalize the model card
- [x] Document feature engineering and agricultural meaning
- [x] Document drift logic and thresholds
- [x] Document ML API usage

#### ML-15: ML Demo and Presentation Preparation
- [x] Prepare an end-to-end demo from sensor input to irrigation decision
- [x] Prepare presentation material for the ML components
- [x] Use the demo rehearsal to catch final integration issues

## Working Rules

- Update this file every time a task or subtask is completed.
- Check the parent task once its required implementation is finished.
- Keep the execution order aligned with dependency constraints from `create_all_issues.sh`.
