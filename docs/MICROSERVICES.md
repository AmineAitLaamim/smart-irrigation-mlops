# Smart Irrigation System - Microservices Overview

## Architecture

The Smart Irrigation System is composed of **19 microservices** organized into 5 layers:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION LAYER                                │
│  ┌─────────────────┐  ┌─────────────────┐                                      │
│  │  Web Dashboard  │  │  API Gateway    │                                      │
│  │    (Next.js)    │  │   (FastAPI)     │                                      │
│  └─────────────────┘  └─────────────────┘                                      │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              APPLICATION LAYER                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  User Service   │  │Notification Svc │  │  Airflow DAGs   │                  │
│  │   (FastAPI)     │  │    (FastAPI)   │  │   (Python)      │                  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               DATA LAYER                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │
│  │Data Ingestion   │  │Feature Engine   │  │  Data Quality   │                  │
│  │    (FastAPI)    │  │    (FastAPI)   │  │    (FastAPI)    │                  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                ML LAYER                                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  Model Server   │  │ Drift Monitor   │  │Irrigation Ctrl │                  │
│  │ (TF Serving)    │  │   (FastAPI)     │  │   (FastAPI)     │                  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           INFRASTRUCTURE LAYER                                 │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐       │
│  │ TimescaleDB  │ │    Redis     │ │    MinIO     │ │     MLflow      │       │
│  │ (PostgreSQL) │ │  (Pub/Sub)  │ │   (S3 API)   │ │(Experiment Tray)│       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────┘       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Complete Microservices List

### Presentation Layer

| Service | Technology | Port | Description |
|---------|------------|------|-------------|
| **Web Dashboard** | Next.js 15, React, Tailwind | 3000 | User interface for monitoring and control |
| **API Gateway** | FastAPI, Python | 8080 | Single entry point, routing, auth, rate limiting |

### Application Layer

| Service | Technology | Port | Description |
|---------|------------|------|-------------|
| **User Service** | FastAPI, Python | 5005 | Authentication, user/zone CRUD, JWT tokens |
| **Notification Service** | FastAPI, Python | 8505 | Email/webhook alerts, Alertmanager integration |
| **Airflow** | Airflow, Python | 8085 | DAG workflow orchestration for ML pipelines |

### Data Layer

| Service | Technology | Port | Description |
|---------|------------|------|-------------|
| **Data Ingestion** | FastAPI, Python | 8001 | Redis consumer → PostgreSQL, validation |
| **Feature Engineering** | FastAPI, Python | 8004 | Rolling window features, feature store |
| **Data Quality** | FastAPI, Python | 8005 | Anomaly detection, sensor health monitoring |
| **Sensor Simulator** | Python | 8000 | Synthetic sensor data generation |

### ML Layer

| Service | Technology | Port | Description |
|---------|------------|------|-------------|
| **Model Server** | TensorFlow Serving | 8501 | ML inference, predictions |
| **Drift Monitor** | FastAPI, Python | 8502 | Data/concept drift detection |
| **Irrigation Controller** | FastAPI, Python | 8503 | Trigger irrigation based on predictions |

### Infrastructure

| Service | Technology | Port | Description |
|---------|------------|------|-------------|
| **TimescaleDB** | PostgreSQL 16 + TimescaleDB | 5432 | Time-series database |
| **Redis** | Redis 7 | 6379 | Message broker, cache |
| **MinIO** | MinIO | 9000/9001 | S3-compatible object storage |
| **MLflow** | MLflow | 5000 | Experiment tracking, model registry |

### Monitoring

| Service | Technology | Port | Description |
|---------|------------|------|-------------|
| **Prometheus** | Prometheus | 9090 | Metrics collection |
| **Grafana** | Grafana | 3001 | Dashboards |
| **Alertmanager** | Alertmanager | 9093 | Alert routing |
| **Jenkins** | Jenkins | 8081 | CI/CD automation |
| **Nginx** | Nginx | 80 | Reverse proxy |

---

## Service Communication

### Synchronous (HTTP/REST)

```
Client → API Gateway → User Service
                     → Model Server
                     → Irrigation Controller
                     → Drift Monitor
```

### Asynchronous (Redis Pub/Sub)

```
Sensor Simulator → [sensor:data] → Data Ingestion
                                         ↓
                              [ingestion:processed]
                                         ↓
                    ┌─────────────────────┴─────────────────────┐
                    ↓                                           ↓
            Feature Engineering                          Data Quality
                    ↓                                           ↓
                              [features:computed]
                                         ↓
                                    Model Server
                                         ↓
                              [predictions:new]
                                         ↓
                              Irrigation Controller
```

### Event Flow

| Channel | Publisher | Subscribers |
|---------|-----------|-------------|
| `sensor:data` | Sensor Simulator | Data Ingestion |
| `ingestion:processed` | Data Ingestion | Feature Engineering, Data Quality |
| `features:computed` | Feature Engineering | Model Server |
| `predictions:new` | Model Server | Irrigation Controller |
| `alerts:anomaly` | Data Quality, Drift Monitor | Notification Service |
| `irrigation:triggered` | Irrigation Controller | Notification Service |

---

## Technology Stack Summary

| Layer | Languages | Frameworks |
|-------|-----------|-------------|
| Frontend | TypeScript | Next.js 15, React, Tailwind CSS |
| Backend | Python | FastAPI, TensorFlow Serving |
| Data | SQL, Python | PostgreSQL/TimescaleDB, Redis |
| ML | Python | TensorFlow, scikit-learn, MLflow |
| Orchestration | Python, Groovy | Airflow, Jenkins |
| Infrastructure | - | Docker, Docker Compose |

---

## Service Dependencies

```
TimescaleDB ◄────────────┬─────────────┬──────────────┬──────────────┐
                        │             │              │              │
Redis ◄─────────────────┼─────────────┼──────────────┼──────────────┤
                        │             │              │              │
MinIO ◄────────────────┬┴────────────┴┬─────────────┴┬─────────────┘
                        │             │              │
                        ▼             ▼              ▼
                    ┌────────┐  ┌──────────┐  ┌────────────┐
                    │ MLflow │  │ Feature  │  │  Model     │
                    │        │  │ Engineer │  │  Server    │
                    └────────┘  └──────────┘  └────────────┘
                         │             │              │
                         └─────────────┼──────────────┘
                                       ▼
                               ┌──────────────┐
                               │   Drift      │
                               │   Monitor    │
                               └──────────────┘
                                       │
                                       ▼
                               ┌──────────────┐
                               │ Irrigation   │
                               │ Controller   │
                               └──────────────┘
```

---

## Port Allocation Summary

| Port | Service |
|------|---------|
| 80 | Nginx (Reverse Proxy) |
| 5432 | TimescaleDB |
| 6379 | Redis |
| 3000 | Web Dashboard |
| 3001 | Grafana |
| 5000 | MLflow |
| 5005 | User Service |
| 8080 | API Gateway |
| 8081 | Jenkins |
| 8085 | Airflow |
| 8000 | Sensor Simulator |
| 8001 | Data Ingestion |
| 8004 | Feature Engineering |
| 8005 | Data Quality |
| 8501 | Model Server |
| 8502 | Drift Monitor |
| 8503 | Irrigation Controller |
| 8505 | Notification Service |
| 9000 | MinIO (API) |
| 9001 | MinIO (Console) |
| 9090 | Prometheus |
| 9093 | Alertmanager |

---

## Quick Reference

### Start All Services
```bash
docker compose -f docker/docker-compose.yml \
               -f docker/docker-compose.app.yml \
               -f docker/docker-compose.data.yml \
               -f docker/docker-compose.ml.yml \
               -f docker/docker-compose.monitoring.yml \
               -f docker/docker-compose.nginx.yml up -d
```

### Health Check All
```bash
docker ps --format "{{.Names}}: {{.Status}}" | grep healthy
```

### View Logs
```bash
docker compose logs -f <service-name>
```

The Smart Irrigation System uses a modern microservice architecture with clear separation of concerns, asynchronous communication via Redis, and comprehensive monitoring.