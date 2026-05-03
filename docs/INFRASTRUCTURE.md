# Infrastructure Overview

## Overview

The Smart Irrigation System is deployed using Docker Compose with a modular architecture. The infrastructure is split across multiple compose files that can be combined depending on the deployment scenario.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           HOST MACHINE                                         │
│                                                                                 │
│  Ports: 5432 (PostgreSQL), 6379 (Redis), 8080 (API), 3000 (Dashboard)        │
│         3001 (Grafana), 9090 (Prometheus), 5000 (MLflow), 9001 (MinIO)       │
└─────────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          DOCKER NETWORK: irrigation_net                        │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────────────────────┐
        │                        │                                        │
        ▼                        ▼                                        ▼
┌───────────────────┐  ┌───────────────────┐  ┌─────────────────────────────┐
│ BASE STACK        │  │ APP STACK         │  │ ML STACK                   │
│ (always required) │  │ (user services)   │  │ (ML pipelines)             │
│                   │  │                   │  │                             │
│ - timescaledb     │  │ - api-gateway     │  │ - mlflow                   │
│ - redis          │  │ - user-service    │  │ - minio                    │
│ - minio          │  │ - web-dashboard   │  │ - airflow                  │
│ - mlflow         │  │ - notification    │  │ - drift-monitor            │
│                   │  │                   │  │ - model-server             │
│                   │  │                   │  │ - feature-engineering      │
│                   │  │                   │  │ - data-ingestion           │
│                   │  │                   │  │ - data-quality             │
│                   │  │                   │  │ - sensor-simulator         │
└───────────────────┘  └───────────────────┘  └─────────────────────────────┘
                                                              │
                                                              ▼
                                             ┌─────────────────────────────┐
                                             │ MONITORING STACK            │
                                             │                             │
                                             │ - prometheus                │
                                             │ - grafana                   │
                                             │ - alertmanager             │
                                             │ - jenkins                   │
                                             └─────────────────────────────┘
```

---

## Compose Files

### docker-compose.yml (Base)

**Always required.** Core infrastructure services:

| Service | Port | Description |
|---------|------|-------------|
| timescaledb | 5432 | PostgreSQL 16 + TimescaleDB time-series |
| redis | 6379 | Redis 7 with AOF persistence |
| minio | 9000/9001 | S3-compatible object storage |
| mlflow | 5000 | ML experiment tracking |

**Usage:**
```bash
docker compose -f docker/docker-compose.yml up -d
```

---

### docker-compose.app.yml (Application)

**Depends on base.** User-facing services:

| Service | Port | Description |
|---------|------|-------------|
| api-gateway | 8080 | Single entry point, routing, auth |
| user-service | 5005 | Authentication, user/zone CRUD |
| web-dashboard | 3000 | React/Next.js frontend |
| notification-service | 8505 | Email/webhook alerts |

**Usage:**
```bash
docker compose -f docker/docker-compose.yml \
               -f docker/docker-compose.app.yml up -d
```

---

### docker-compose.data.yml (Data Pipeline)

**Depends on base.** Data processing services:

| Service | Port | Description |
|---------|------|-------------|
| sensor-simulator | 8000 | Synthetic sensor data generator |
| data-ingestion | 8001 | Redis → PostgreSQL ingestion |
| feature-engineering | 8004 | Rolling window features |
| data-quality | 8005 | Anomaly detection |

**Usage:**
```bash
docker compose -f docker/docker-compose.yml \
               -f docker/docker-compose.data.yml up -d
```

---

### docker-compose.ml.yml (ML)

**Depends on base.** Machine learning services:

| Service | Port | Description |
|---------|------|-------------|
| model-server | 8501 | TensorFlow Serving for predictions |
| drift-monitor | 8502 | Data/concept drift detection |
| irrigation-controller | 8503 | Trigger irrigation based on predictions |
| airflow | 8085 | DAG workflow orchestration |

**Usage:**
```bash
docker compose -f docker/docker-compose.yml \
               -f docker/docker-compose.ml.yml up -d
```

---

### docker-compose.monitoring.yml (Monitoring)

**Depends on base.** Observability stack:

| Service | Port | Description |
|---------|------|-------------|
| prometheus | 9090 | Metrics collection |
| grafana | 3001 | Dashboards |
| alertmanager | 9093 | Alert routing |
| jenkins | 8081 | CI/CD automation |

**Usage:**
```bash
docker compose -f docker/docker-compose.yml \
               -f docker/docker-compose.monitoring.yml up -d
```

---

## Full Stack Startup

### All services

```bash
# From repo root
make up

# Or explicitly
docker compose -f docker/docker-compose.yml \
               -f docker/docker-compose.app.yml \
               -f docker/docker-compose.data.yml \
               -f docker/docker-compose.ml.yml \
               -f docker/docker-compose.monitoring.yml up -d
```

### Development (app + data + base)

```bash
docker compose -f docker/docker-compose.yml \
               -f docker/docker-compose.app.yml \
               -f docker/docker-compose.data.yml up -d
```

### Production (app + ml + base)

```bash
docker compose -f docker/docker-compose.yml \
               -f docker/docker-compose.app.yml \
               -f docker/docker-compose.ml.yml up -d
```

---

## Network

All services communicate via Docker network `irrigation_net`:

```yaml
networks:
  irrigation_net:
    name: irrigation_net
    driver: bridge
```

**Internal URLs:**
- `timescaledb:5432` - Database
- `redis:6379` - Message broker
- `minio:9000` - Object storage
- `mlflow:5000` - ML tracking
- `user-service:5005` - Auth API
- `api-gateway:8080` - Public API
- etc.

---

## Volumes

| Volume | Service | Purpose |
|--------|---------|---------|
| timescaledb_data | timescaledb | Database storage |
| redis_data | redis | Cache + pubsub persistence |
| minio_data | minio | S3 artifacts |
| mlflow_data | mlflow | Experiment metadata |
| grafana_data | grafana | Dashboard configs |
| prometheus_data | prometheus | Metrics storage |
| jenkins_data | jenkins | CI/CD state |

---

## Environment

Configuration via `.env` file:

```bash
# Copy example and configure
cp .env.example .env
# Edit .env with your settings
```

Key variables:
- `POSTGRES_*` - Database credentials
- `REDIS_URL` - Redis connection
- `JWT_SECRET_KEY` - Auth signing key
- `MLFLOW_*` - ML tracking config
- `MINIO_*` - S3 credentials

---

## Health Checks

All services have health checks configured:

| Service | Check |
|---------|-------|
| timescaledb | `pg_isready` |
| redis | `redis-cli ping` |
| minio | `/minio/health/live` |
| mlflow | Python HTTP check |
| user-service | `/health` endpoint |
| api-gateway | `/health` endpoint |
| prometheus | `/-/healthy` |
| grafana | `/api/health` |

---

## Service Dependencies

```
timescaledb ─────┬──► user-service ──► api-gateway
                 │                          ▲
redis ───────────┼──► notification-service  │
                 │                          │
minio ───────────┼──► mlflow ───────────────┤
                 │         │                │
                 │         ▼                │
                 └──► feature-engineering ──►│
                         │                   │
                         ▼                   │
                   data-quality ────────────┘
                         │
                         ▼
                   drift-monitor
                         │
                         ▼
                   model-server
                         │
                         ▼
                 irrigation-controller
```

---

## Ports Summary

| Port | Service |
|------|---------|
| 5432 | TimescaleDB |
| 6379 | Redis |
| 8080 | API Gateway |
| 5000 | MLflow |
| 5005 | User Service |
| 8000 | Sensor Simulator |
| 8001 | Data Ingestion |
| 8004 | Feature Engineering |
| 8005 | Data Quality |
| 8085 | Airflow |
| 8501 | Model Server |
| 8502 | Drift Monitor |
| 8503 | Irrigation Controller |
| 8505 | Notification Service |
| 9000 | MinIO (API) |
| 9001 | MinIO (Console) |
| 9090 | Prometheus |
| 9093 | Alertmanager |
| 3000 | Web Dashboard |
| 3001 | Grafana |
| 8081 | Jenkins |

---

## Summary

| Compose File | Services | Purpose |
|--------------|----------|---------|
| docker-compose.yml | timescaledb, redis, minio, mlflow | Core infrastructure |
| docker-compose.app.yml | api-gateway, user-service, web-dashboard, notification | User-facing |
| docker-compose.data.yml | sensor-simulator, data-ingestion, feature-engineering, data-quality | Data pipeline |
| docker-compose.ml.yml | model-server, drift-monitor, irrigation-controller, airflow | ML/AI |
| docker-compose.monitoring.yml | prometheus, grafana, alertmanager, jenkins | Observability |

The modular compose files allow selective deployment based on use case while maintaining a consistent networking and configuration model.