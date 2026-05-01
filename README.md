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
- **[Setup Guide](./docs/SETUP_GUIDE.md)**: Deployment and local development instructions.
- **[Project Tree](./docs/PROJECT_TREE.md)**: Complete directory structure.
- **[Branch Naming](./docs/BRANCH_NAMING.md)**: Git workflow conventions.

## 🛠 Features
- **Real-time Telemetry**: High-throughput ingestion with physical bound validation.
- **Data Quality**: Continuous auditing for sensor malfunctions and health reporting.
- **ML Feature Store**: Versioned time-series features for training and inference.
- **Security**: RBAC with zone-level ownership enforced at the gateway.
- **Observability**: Prometheus/Grafana monitoring and shadow model comparison.

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
