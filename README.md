# Smart Irrigation System

AI-driven microservices platform for optimized agricultural irrigation.

## 🚀 Quick Start
1. `cp .env.example .env`

2. `docker compose -f docker/docker-compose.yml up -d`
3. `docker compose -f docker/docker-compose.app.yml up -d`

## 📚 Documentation
Detailed documentation is available in the `docs/` directory:

- **[Architecture](./docs/ARCHITECTURE.md)**: System design and data flow.
- **[Database Schema](./docs/DATABASE_SCHEMA.md)**: Tables, hypertables, and views.
- **[MLOps Pipeline](./docs/ML_PIPELINE.md)**: Feature store, model lifecycle, and monitoring.
- **[Model Training Guide](./docs/ML_TRAINING_GUIDE.md)**: When, how, and which models are trained.
- **[Model Server API](./docs/MODEL_SERVER_API.md)**: Prediction and model metadata endpoints.
- **[Feature Engineering Guide](./docs/FEATURE_ENGINEERING_GUIDE.md)**: Derived features and agricultural rationale.
- **[Drift Monitoring](./docs/DRIFT_MONITORING.md)**: Drift signals, thresholds, and alert flow.
- **[Setup Guide](./docs/SETUP_GUIDE.md)**: Deployment and local development instructions.
- **[Project Tree](./docs/PROJECT_TREE.md)**: Complete directory structure.
- **[Branch Naming](./docs/BRANCH_NAMING.md)**: Git workflow conventions.
- **[Sensor Simulator](./docs/SENSOR_SIMULATOR.md)**: Synthetic telemetry generation details.
- **[Web Dashboard](./docs/WEB_DASHBOARD.md)**: Frontend architecture, authentication, and state management.

## 🛠 Features
- **Real-time Telemetry**: High-throughput ingestion with physical bound validation.
- **Data Quality**: Continuous auditing for sensor malfunctions and health reporting.
- **ML Feature Store**: Versioned time-series features for training and inference.
- **Security**: RBAC with zone-level ownership enforced at the gateway.
- **Observability**: Prometheus/Grafana monitoring and shadow model comparison.

## 🤖 MLOps Development
- Install the ML stack from the root project dependencies to work on training and evaluation.
- Generate the exploration report with `python -m mlops.exploration`.
- Build a training-ready dataset from TimescaleDB with the repo-level `mlops.dataset_pipeline` utilities.
- Train baseline and XGBoost models with `python -m mlops.training`.

## 📦 Service Ports
| Service | Port |
| :--- | :--- |
| API Gateway | 8080 |
| User Service | 5005 |
| Data Ingestion | 8001 |
| Feature Engineering | 8004 |
| Data Quality | 8005 |
| MLflow | 5000 |
| MinIO | 9001 |
| Jenkins | 8081 |
