╔══════════════════════════════════════════════════════════════════════════════╗
║                   SMART IRRIGATION SYSTEM - COMPLETE DOCUMENTATION            ║
╚══════════════════════════════════════════════════════════════════════════════╝

This document contains the complete documentation for the Smart Irrigation System.
Organized into 12 sections covering architecture, services, ML, DevOps, and operations.

────────────────────────────────────────────────────────────────────────────────
TABLE OF CONTENTS
────────────────────────────────────────────────────────────────────────────────


1. GETTING STARTED
  • Getting Started Guide
  • Project Structure & File Tree

2. ARCHITECTURE
  • System Architecture
  • Complete System Schema
  • Microservices Overview
  • End-to-End Data Flow

3. INFRASTRUCTURE
  • Infrastructure & Docker Compose
  • Nginx Reverse Proxy
  • Database Schema
  • Database Schema Details

4. CORE SERVICES
  • API Gateway
  • User Service & Authentication

5. DATA PIPELINE SERVICES
  • Sensor Simulator
  • Data Ingestion Service
  • Feature Engineering
  • Feature Engineering Guide
  • Data Quality Service

6. ML SERVICES
  • Model Server
  • Model Server API
  • Model Versioning
  • Drift Monitoring
  • Irrigation Trigger System

7. ML PIPELINE & TRAINING
  • ML Pipeline
  • ML Training Guide
  • ML Exploration
  • ML Demo Script
  • Model Card Template

8. CI/CD & DEVOPS
  • Jenkins CI/CD
  • Airflow DAG Pipeline

9. FRONTEND
  • Web Dashboard

10. MONITORING & ALERTS
  • Prometheus Monitoring
  • Grafana Dashboards
  • Alertmanager
  • Notification Service

11. DEPLOYMENT & OPERATIONS
  • Deployment Guide
  • Testing Guide

12. DEVELOPMENT PRACTICES
  • Code Review Guidelines
  • Branch Naming Convention

────────────────────────────────────────────────────────────────────────────────
DOCUMENT CONTENT
────────────────────────────────────────────────────────────────────────────────


═══════════════════════════════════════════════════════════════════

SECTION: Getting Started Guide

# Setup & Deployment Guide

## Prerequisites
- **Docker** and **Docker Compose**
- **Python 3.11+** (for local development)
- **uv** (recommended for dependency management)

## 1. Environment Configuration
Copy the example environment file and customize your secrets:
```bash
cp .env.example .env
```
Key variables to check:
- `JWT_SECRET_KEY`: Used for authentication.
- `POSTGRES_PASSWORD`: Root DB password.
- `INGESTION_PASSWORD`: Credentials for the ingestion role.

## 2. Infrastructure Deployment
Start the core infrastructure (DB, Redis, MLflow, MinIO):
```bash
docker compose -f docker/docker-compose.yml up -d
```
Verify the database is healthy:
```bash
docker inspect timescaledb --format '{{.State.Health.Status}}'
```

## 3. Database Migrations
Migrations run automatically at container startup. To apply them manually:
```bash
docker exec -it timescaledb /docker-entrypoint-initdb.d/01_run_migrations.sh
```

## 4. Application Services
Start the microservices stack:
```bash
docker compose -f docker/docker-compose.app.yml up -d
```
This starts the `api-gateway`, `user-service`, `data-ingestion`, `feature-engineering`, and `data-quality` services.

## 5. Local Development
To run a service locally (e.g., User Service):
```bash
cd services/user-service
uv pip install -r requirements.txt
$env:PYTHONPATH=".;src"
$env:ENV="development"
uvicorn src.main:app --reload --port 5005
```

## 6. Running Tests
We use `pytest` for unit and integration testing.
```bash
# Run all tests using uv
uv run pytest

# Run tests for a specific service
uv run pytest services/user-service/tests/unit/test_routes.py
```

## 7. Service Endpoints
- **API Gateway**: `http://localhost:8080`
- **User Service**: `http://localhost:5005`
- **Data Ingestion (Stats)**: `http://localhost:8001/health`
- **Data Quality (Reports)**: `http://localhost:8005/quality/reports/summary`
- **MLflow UI**: `http://localhost:5000`
- **MinIO Console**: `http://localhost:9001`

## 8. Utility Commands

### Fast-Forward Simulation
The `fast-forward` command is used to quickly populate the system with data for testing and development. It simulates 12 hours of system activity in seconds.

```bash
make fast-forward
```

**What it does:**
- **Future Data**: Generates sensor readings for the next 12 hours.
- **Realistic Activity**: Simulates irrigation cycles (moisture recovery) so the data looks like a real farm.
- **Immediate Ingestion**: The data is pushed through the real ingestion pipeline, triggering all quality checks and feature engineering.
- **Multi-Sensor**: Generates consistent data for all active zones and sensors simultaneously.

## 9. Troubleshooting
...



═══════════════════════════════════════════════════════════════════

SECTION: Project Structure & File Tree

# Smart Irrigation System — Complete Project Tree & Ownership

> **Version:** 8.0 | **Last Updated:** 2026-04-12

## Ownership Legend

| Tag | Role | Responsibility |
|---|---|---|
| `[DO]` | **DevOps** | API Gateway, user-service, web-dashboard, notification-service, CI/CD, monitoring, infrastructure |
| `[DA]` | **DataOps** | Data pipeline, sensor simulation, data ingestion, database, migrations, backups |
| `[ML]` | **MLOps** | Feature engineering, model server, drift monitoring, irrigation controller, Airflow DAGs |
| `[SHARED]` | **Shared** | Requires coordination across multiple roles |

---

## Complete Project Tree

```
smart-irrigation/
│
├── 📄 .env.example                      [SHARED] Environment variable template
│                                         Defines all required env vars for services
│
├── 📄 .env                              [SHARED] Local environment secrets (git-ignored)
│                                         Never committed — contains real passwords/keys
│
├── 📄 .gitignore                        [SHARED] Git exclusion rules
│                                         Prevents committing secrets, build artifacts, ML models
│
├── 📄 .dockerignore                     [SHARED] Docker build context exclusions
│                                         Speeds up builds by excluding node_modules, .venv, etc.
│
├── 📄 .pre-commit-config.yaml           [SHARED] Pre-commit hook configuration
│                                         Runs ruff, ruff-format, mypy, detect-secrets on commit
│
├── 📄 .python-version                   [SHARED] Python version pin (3.11)
│                                         Used by uv to select correct Python interpreter
│
├── 📄 pyproject.toml                    [SHARED] Python project configuration
│                                         Defines dependencies, tools (uv), test/lint settings
│
├── 📄 uv.lock                           [SHARED] Deterministic Python dependency lock
│                                         Generated by uv — ensures reproducible builds
│
├── 📄 main.py                           [SHARED] Project entry point (optional orchestrator)
│
├── 📄 Makefile                          [SHARED] Build & run automation
│                                         Shortcut commands for docker, tests, linting
│
├── 📄 Jenkinsfile                       [DO]  Main CI/CD pipeline definition
│                                         Jenkins declarative pipeline — builds, tests, deploys
│
├── 📄 README.md                         [SHARED] Project overview & quick start guide
│
│
├── 📁 docker/                           [SHARED] Docker Compose orchestration layer
│    │
│    ├── 📄 docker-compose.yml           [SHARED] Core infrastructure services
│    │                                     TimescaleDB, Redis, MLflow, MinIO — base network
│    │
│    ├── 📄 docker-compose.data.yml      [DA]  Data pipeline services
│    │                                     Sensor-simulator, data-ingestion, feature-engineering
│    │
│    ├── 📄 docker-compose.ml.yml        [ML]  ML pipeline services
│    │                                     Model-server, drift-monitor, irrigation-controller, Airflow
│    │
│    ├── 📄 docker-compose.app.yml       [DO]  Application services
│    │                                     API Gateway, user-service, web-dashboard, notification-service
│    │
│    └── 📄 docker-compose.monitoring.yml [DO] Monitoring & observability stack
│                                          Jenkins, Prometheus, Grafana, Alertmanager
│
│
├── 📁 services/                         All 10 microservices (each with Dockerfile)
│    │
│    ├── 📁 api-gateway/                [DO]  JWT authentication & request routing
│    │    ├── 📄 Dockerfile                 FastAPI reverse proxy with JWT middleware
│    │    ├── 📄 requirements.txt           Python dependencies
│    │    └── 📁 src/
│    │         ├── 📄 __init__.py
│    │         ├── 📄 main.py               FastAPI app, route definitions, service routing
│    │         ├── 📄 auth.py               JWT validation, token extraction, role checking
│    │         └── 📄 rate_limiter.py       Request rate limiting (Redis-backed)
│    │
│    ├── 📁 user-service/               [DO]  User authentication & management
│    │    ├── 📄 Dockerfile                 FastAPI user CRUD, JWT token issuance
│    │    ├── 📄 requirements.txt
│    │    └── 📁 src/
│    │         ├── 📄 __init__.py
│    │         ├── 📄 main.py               User registration, login, token refresh endpoints
│    │         ├── 📄 auth.py               Password hashing (bcrypt), JWT generation
│    │         ├── 📄 models.py             Pydantic schemas (UserCreate, LoginRequest, TokenResponse)
│    │         └── 📄 database.py           TimescaleDB connection, user table queries
│    │
│    ├── 📁 web-dashboard/              [DO]  Next.js 15 monitoring dashboard
│    │    ├── 📄 Dockerfile                 Node.js build + production server
│    │    ├── 📄 package.json               npm dependencies (Next.js 15, React, Tailwind, Recharts)
│    │    ├── 📄 tsconfig.json              TypeScript configuration
│    │    ├── 📄 next.config.ts             Next.js custom configuration
│    │    ├── 📄 next-env.d.ts              TypeScript Next.js type declarations
│    │    └── 📁 src/
│    │         └── 📁 app/
│    │              ├── 📄 layout.tsx         Root layout, metadata, global providers
│    │              ├── 📄 page.tsx           Main dashboard page (sensor data, zone status)
│    │              └── 📄 globals.css        Tailwind CSS 4 + shadcn/ui global styles
│    │
│    ├── 📁 notification-service/       [DO]  Alert delivery (email, webhook)
│    │    ├── 📄 Dockerfile                 Python notification dispatcher
│    │    ├── 📄 requirements.txt
│    │    └── 📁 src/
│    │         ├── 📄 __init__.py
│    │         └── 📄 main.py               Email/webhook alert handlers, template rendering
│    │
│    ├── 📁 sensor-simulator/           [DA]  IoT sensor data generation
│    │    ├── 📄 Dockerfile                 Python sensor simulator
│    │    ├── 📄 requirements.txt
│    │    └── 📁 src/
│    │         ├── 📄 __init__.py
│    │         ├── 📄 main.py               Simulator orchestrator, publishes to Redis Pub/Sub
│    │         └── 📄 sensor_generator.py   Realistic sensor value generation (soil moisture, temp, humidity)
│    │
│    ├── 📁 data-ingestion/             [DA]  Sensor data persistence layer
│    │    ├── 📄 Dockerfile                 Python consumer → TimescaleDB writer
│    │    ├── 📄 requirements.txt
│    │    └── 📁 src/
│    │         ├── 📄 __init__.py
│    │         ├── 📄 main.py               Ingestion service entry point
│    │         ├── 📄 redis_consumer.py     Redis Pub/Sub subscriber (sensor:data channel)
│    │         └── 📄 db_writer.py          Batch inserts into TimescaleDB sensor_readings table
│    │
│    ├── 📁 feature-engineering/        [ML]  Derived feature computation
│    │    ├── 📄 Dockerfile                 Python feature pipeline
│    │    ├── 📄 requirements.txt
│    │    └── 📁 src/
│    │         ├── 📄 __init__.py
│    │         ├── 📄 main.py               Feature computation scheduler
│    │         └── 📄 feature_computation.py Rolling stats (mean, std, min, max) over time windows
│    │
│    ├── 📁 model-server/               [ML]  XGBoost model inference service
│    │    ├── 📄 Dockerfile                 gRPC + REST model serving
│    │    ├── 📄 requirements.txt            xgboost, mlflow, grpcio, fastapi
│    │    ├── 📁 models/                     Local model cache (hot-reloadable)
│    │    │    └── 📄 xgboost_moisture_v1.json  Current production model artifact
│    │    └── 📁 src/
│    │         ├── 📄 __init__.py
│    │         ├── 📄 main.py               FastAPI (REST:8501) + gRPC (5001) server
│    │         └── 📄 model_service.py       Model loading from MLflow, prediction logic, hot-reload
│    │
│    ├── 📁 drift-monitor/              [ML]  Model performance & data drift detection
│    │    ├── 📄 Dockerfile                 Python drift detection service
│    │    ├── 📄 requirements.txt
│    │    └── 📁 src/
│    │         ├── 📄 __init__.py
│    │         ├── 📄 main.py               Drift monitoring scheduler
│    │         └── 📄 drift_detector.py     Page-Hinkley test + KL divergence calculations
│    │
│    ├── 📁 irrigation-controller/      [ML]  Automated irrigation decision engine
│    │    ├── 📄 Dockerfile                 Python irrigation controller
│    │    ├── 📄 requirements.txt
│    │    └── 📁 src/
│    │         ├── 📄 __init__.py
│    │         └── 📄 main.py               Redis pub/sub consumer, threshold-based trigger, 10-min deduplication
│    │
│
├── 📁 migrations/                     [SHARED] Database schema versioning
│    │
│    ├── 📄 00_create_databases.sh      [DA]  Database initialization script
│    │                                     Creates databases: irrigation_db, airflow_db, etc.
│    │
│    ├── 📄 run_migrations.sql          [SHARED] Migration runner (applies SQL in order)
│    │                                     Tracks applied migrations in schema_migrations table
│    │
│    └── 📁 sql/
│         ├── 📄 001_init_timescaledb.sql    [DA]  Core tables: sensor_readings, zones,
│         │                                      sensor_metadata, irrigation_events
│         │
│         ├── 📄 002_plausibility_bounds.sql [DA]  Data quality validation rules,
│         │                                      data_quality_events hypertable
│         │
│         ├── 📄 003_feature_references.sql  [ML]  Feature store: feature_references,
│         │                                      model_predictions hypertable
│         │
│         ├── 📄 004_shadow_comparison.sql   [ML]  Shadow mode: shadow_model_predictions,
│         │                                      prediction_outcomes tables
│         │
│         └── 📄 005_user_and_zone_ownership.sql [DO]  Users table (JWT auth), zone ownership
│                                                    (source=yaml vs source=api distinction)
│
│
├── 📁 configs/                        Shared configuration files
│    │
│    ├── 📁 zones/
│    │    └── 📄 zone_config.yaml       [SHARED] Zone definitions (YAML-loaded, read-only)
│    │                                     Defines zone_id, crop_type, soil_type, thresholds
│    │                                     Zones with source=yaml cannot be modified by users
│    │
│    └── 📁 monitoring/               [DO]  Observability stack configuration
│         ├── 📄 prometheus.yml           Prometheus scrape targets & intervals
│         ├── 📄 alertmanager.yml         Alert routing, receivers (email, Slack, webhook)
│         ├── 📄 alert_rules.yml          Prometheus alerting rules (service health, drift)
│         └── 📁 grafana/
│              ├── 📄 datasources.yml     Prometheus, TimescaleDB datasource definitions
│              ├── 📄 dashboards.yml      Dashboard provisioning config
│              ├── 📄 dashboard_sensors.json  Real-time sensor metrics dashboard
│              └── 📄 dashboard_ml.json       ML model performance & drift dashboard
│
│
├── 📁 airflow/                        [ML]  Apache Airflow ML pipeline orchestration
│    └── 📁 dags/
│         └── 📄 smart_irrigation_dags.py   Airflow DAGs: data validation → feature engineering
│                                             → model training → evaluation → MLflow registry
│
│
├── 📁 jenkins/                        [DO]  CI/CD shared library
│    └── 📁 shared-lib/
│         └── 📁 vars/
│              └── 📄 smartIrrigation.groovy  Jenkins shared steps (build, test, deploy)
│
│
├── 📁 scripts/                        Utility scripts
│    │
│    ├── 📄 init_env.sh               [SHARED] Environment setup (creates .env from template)
│    ├── 📄 check_env.sh              [SHARED] Validates environment variables are set
│    ├── 📄 backup.sh                 [DA]  Database backup with 7-day retention
│    │                                     Uses pg_dump, stores in backups/ (git-ignored)
│    └── 📄 smoke_test.sh             [DO]  End-to-end system health verification
│                                          Checks all containers, API endpoints, data flow
│
│
├── 📁 docs/                           [SHARED] Developer documentation
│    ├── 📄 BRANCH_NAMING.md             Git branch naming conventions
│    ├── 📄 CODE_REVIEW.md               Code review checklist & guidelines
│    └── 📄 PROJECT_TREE.md              This file — complete project structure & ownership
│
│
├── 📁 .github/                        [SHARED] GitHub collaboration templates
│    ├── 📄 CONTRIBUTING.md              Contribution guidelines, code standards
│    └── 📄 PULL_REQUEST_TEMPLATE.md     PR description template (checklist, testing notes)
│
│
├── 📁 project_pdfs/                   [SHARED] Original specification PDFs (git-ignored)
│    ├── 📄 Smart_Irrigation_Project_Structure_v8.pdf
│    ├── 📄 Smart_Irrigation_System_Architecture_v8.pdf
│    ├── 📄 Smart_Irrigation_Team_Collaboration_Guide_v8.pdf
│    └── 📄 Smart_Irrigation_Team_Task_Assignment_v8.pdf
│
│
├── 📁 .venv/                          [SHARED] Python virtual environment (git-ignored)
│                                          Managed by uv — never commit
│
│
└── 📁 .git/                             Git repository metadata

```

---

## Service Ownership Summary

### DevOps (`[DO]`) — 4 services + infrastructure

| Service | Purpose | Port |
|---|---|---|
| `api-gateway` | JWT auth middleware, request routing, rate limiting | 8080 |
| `user-service` | User registration, login, token management | 5005 |
| `web-dashboard` | Next.js 15 dashboard (polls API every 10s) | 3000 |
| `notification-service` | Email/webhook alert delivery | Internal |
| `configs/monitoring/` | Prometheus, Grafana, Alertmanager | 9090/3001/9093 |
| `jenkins/` | CI/CD shared library | 8081 |
| `docker-compose.monitoring.yml` | Observability stack | — |

### DataOps (`[DA]`) — 2 services + data layer

| Service | Purpose | Port |
|---|---|---|
| `sensor-simulator` | Generates realistic sensor data, publishes to Redis | Internal |
| `data-ingestion` | Consumes from Redis, writes to TimescaleDB | 8001 (health) |
| `migrations/sql/` | Database schema (all 5 migrations) | — |
| `scripts/backup.sh` | Database backup automation | — |

### MLOps (`[ML]`) — 4 services + ML pipeline

| Service | Purpose | Port |
|---|---|---|
| `feature-engineering` | Computes rolling stats & derived features | Internal |
| `model-server` | XGBoost inference (gRPC + REST) | 5001/8501 |
| `drift-monitor` | Page-Hinkley + KL divergence drift detection | Internal |
| `irrigation-controller` | Threshold-based valve control | Internal |
| `airflow/dags/` | ML pipeline orchestration (train → evaluate → deploy) | — |

### Shared (`[SHARED]`) — Cross-role coordination

| Artifact | Reason |
|---|---|
| `docker/docker-compose.yml` | Core infra used by all services |
| `docker/docker-compose.data.yml` | Data pipeline (DA owns services, DO owns compose file) |
| `docker/docker-compose.ml.yml` | ML pipeline (ML owns services, DO owns compose file) |
| `docker/docker-compose.app.yml` | App services (DO owns services, shared compose structure) |
| `configs/zones/zone_config.yaml` | Zone definitions loaded by multiple services |
| `migrations/` | DA writes SQL, DO manages migration runner |
| `pyproject.toml` / `uv.lock` | Shared Python dependency management |
| `.pre-commit-config.yaml` | Shared linting/testing configuration |
| `scripts/init_env.sh` / `check_env.sh` | Shared environment setup |
| `.github/` | Shared contribution guidelines |
| `docs/` | Shared developer documentation |

---

## Data Flow & Service Dependencies

```
┌─────────────────────┐
│  sensor-simulator   │ [DA]  Generates sensor data
└─────────┬───────────┘
          │ Redis Pub/Sub (sensor:data)
          ▼
┌─────────────────────┐
│   data-ingestion    │ [DA]  Consumes → writes to TimescaleDB
└─────────┬───────────┘
          │ TimescaleDB (sensor_readings)
          ▼
┌─────────────────────┐
│ feature-engineering │ [ML]  Computes rolling features
└─────────┬───────────┘
          │ TimescaleDB (feature_references)
          ▼
┌─────────────────────┐
│    model-server     │ [ML]  XGBoost predictions via gRPC/REST
└─────────┬───────────┘
          │ Predictions stored in TimescaleDB
          ▼
┌─────────────────────┐
│ drift-monitor       │ [ML]  Detects model/data drift
│ irrigation-controller│ [ML]  Triggers irrigation based on predictions
└─────────────────────┘

          ▲
          │ API calls (JWT authenticated)
┌─────────────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│   api-gateway:8080  │─────▶│  user-service:5005│      │ web-dashboard:3000  │
│   [DO] JWT + routing│      │  [DO] Auth        │      │ [DO] Next.js 15     │
└─────────────────────┘      └──────────────────┘      └─────────────────────┘
          │
          ▼
┌─────────────────────┐
│notification-service │ [DO]  Sends alerts on events
└─────────────────────┘
```

---

## Redis Communication Contracts

| Channel | Producer | Consumer | Purpose |
|---|---|---|---|
| `sensor:data` | sensor-simulator [DA] | data-ingestion [DA] | Raw sensor readings |
| `ingestion:processed` | data-ingestion [DA] | feature-engineering [ML] | Acknowledged writes |
| `features:computed` | feature-engineering [ML] | model-server [ML] | Ready feature vectors |
| `token:blacklist` | api-gateway [DO] | api-gateway [DO] | Revoked JWT tokens |

---

## Database Table Ownership

| Table | Type | Migration | Owner | Description |
|---|---|---|---|---|
| `sensor_readings` | Hypertable | 001 | [DA] | Raw sensor data (time-partitioned) |
| `zones` | Standard | 001+005 | [DA]/[DO] | Zone definitions & ownership |
| `sensor_metadata` | Standard | 001 | [DA] | Sensor hardware metadata |
| `irrigation_events` | Hypertable | 001 | [DA] | Irrigation action log |
| `data_quality_events` | Hypertable | 002 | [DA] | Plausibility validation failures |
| `feature_references` | Standard | 003 | [ML] | Computed feature store |
| `model_predictions` | Hypertable | 003 | [ML] | Production model outputs |
| `shadow_model_predictions` | Hypertable | 004 | [ML] | Shadow model outputs for comparison |
| `prediction_outcomes` | Standard | 004 | [ML] | Prediction accuracy tracking |
| `users` | Standard | 005 | [DO] | User accounts & JWT metadata |
| `schema_migrations` | Standard | Auto | [DO] | Migration version tracking |

---

## Key Ownership Rules

1. **Never modify files outside your service directories** without coordination
2. **Migrations are immutable** — create a new migration, never edit an existing one
3. **YAML zones are read-only** — `source=yaml` zones cannot be modified via API
4. **Docker Compose structure** — service names/ports require team-wide agreement
5. **Pydantic schemas** — changes to shared types (UserCreate, TokenResponse) need coordination
6. **Redis channels** — channel names and message formats are cross-team contracts

---

## Quick Reference: Who to Contact

| Task | Contact | Files |
|---|---|---|
| Add API endpoint | [DO] | `services/api-gateway/`, `services/user-service/` |
| Change database schema | [DA] + [DO] | `migrations/sql/` |
| Train/deploy new ML model | [ML] | `services/model-server/`, `airflow/dags/` |
| Update monitoring dashboards | [DO] | `configs/monitoring/grafana/` |
| Modify zone thresholds | [SHARED] | `configs/zones/zone_config.yaml` |
| Add CI/CD step | [DO] | `Jenkinsfile`, `jenkins/shared-lib/` |
| Change data pipeline | [DA] + [ML] | `services/data-ingestion/`, `services/feature-engineering/` |



═══════════════════════════════════════════════════════════════════

SECTION: System Architecture

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



═══════════════════════════════════════════════════════════════════

SECTION: Complete System Schema

# Complete System Schema

## Overview

This document provides a comprehensive visual overview of the entire Smart Irrigation System, showing all components as a continuous pipeline from sensor data generation to irrigation actuation and notification.

---

## Complete Pipeline Cycle

```
╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                    SMART IRRIGATION SYSTEM - COMPLETE PIPELINE                                            ║
╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    DATA FLOW (Left to Right)                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

     ┌──────────────┐        ┌──────────────┐        ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
     │   STAGE 1    │        │   STAGE 2    │        │   STAGE 3    │        │   STAGE 4    │        │   STAGE 5    │
     │   SENSOR     │        │   INGEST     │        │   PROCESS    │        │   PREDICT    │        │   ACTUATE    │
     │   INPUT      │──────▶│   & VALIDATE  │──────▶│   & ENRICH   │──────▶│   & DECIDE   │──────▶│   & NOTIFY    │
     └──────────────┘        └──────────────┘        └──────────────┘        └──────────────┘        └──────────────┘
            │                        │                        │                        │                        │
            ▼                        ▼                        ▼                        ▼                        ▼
     ┌──────────────┐        ┌──────────────┐        ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
     │   Sensor     │        │    Data      │        │   Feature    │        │    Model     │        │  Irrigation  │
     │  Simulator   │        │  Ingestion   │        │ Engineering  │        │    Server    │        │ Controller   │
     │  :8000      │        │   :8001      │        │   :8004      │        │   :8501      │        │   :8503      │
     │              │        │              │        │              │        │              │        │              │
     │ ┌──────────┐ │        │ ┌──────────┐ │        │ ┌──────────┐ │        │ ┌──────────┐ │        │ ┌──────────┐ │
     │ │ Zone Config│ │        │ │ Validate │ │        │ │ Features │ │        │ │ TensorFlow│ │        │ │ Trigger  │ │
     │ │(soil/crop)│ │        │ │  Bounds  │ │        │ │ Rolling  │ │        │ │   Serve   │ │        │ │  Logic   │ │
     │ └──────────┘ │        │ └──────────┘ │        │ │ Windows  │ │        │ └──────────┘ │        │ └──────────┘ │
     │              │        │              │        │ └──────────┘ │        │              │        │              │
     │ ┌──────────┐ │        │ ┌──────────┐ │        │ ┌──────────┐ │        │ ┌──────────┐ │        │ ┌──────────┐ │
     │ │Diurnal   │ │        │ │  Insert  │ │        │ │  Store   │ │        │ │  Load    │ │        │ │Dedupe   │ │
     │ │ Cycles   │ │        │ │ Readings │ │        │ │ Features │ │        │ │ Features │ │        │ │ 10min   │ │
     │ └──────────┘ │        │ └──────────┘ │        │ └──────────┘ │        │ └──────────┘ │        │ └──────────┘ │
     └──────────────┘        └──────────────┘        └──────────────┘        └──────────────┘        └──────────────┘
                                                                                      │
                                                                                      ▼
                                                                           ┌──────────────────────┐
                                                                           │    DRIFT MONITOR      │
                                                                           │       :8502           │
                                                                           │                       │
                                                                           │ ┌──────────────────┐ │
                                                                           │ │  Page-Hinkley    │ │
                                                                           │ │  KL Divergence   │ │
                                                                           │ └──────────────────┘ │
                                                                           └──────────────────────┘

══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
                                                  INFRASTRUCTURE & STORAGE
══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

     ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
     │                                            DATA STORES (Bottom Layer)                                                         │
     └──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

     ┌────────────────┐   ┌────────────────┐   ┌────────────────┐   ┌────────────────┐   ┌────────────────┐   ┌────────────────┐
     │   PostgreSQL   │   │    Redis      │   │    MinIO       │   │    MLflow     │   │   Prometheus  │   │   Grafana     │
     │  TimescaleDB   │   │   (Pub/Sub)   │   │   (S3 Store)   │   │   (Registry)  │   │  (Metrics)    │   │  (Dashboards)│
     │   :5432        │   │    :6379      │   │  9000/9001     │   │    :5000      │   │    :9090      │   │    :3001      │
     ├────────────────┤   ├────────────────┤   ├────────────────┤   ├────────────────┤   ├────────────────┤   ├────────────────┤
     │                │   │                │   │                │   │                │   │                │   │                │
     │ • sensor_      │   │ Channels:      │   │ Buckets:       │   │ • Experiments  │   │ • Scrape      │   │ Dashboards:   │
     │   readings     │   │                │   │                │   │ • Runs        │   │   services    │   │                │
     │ • irrigation_ │   │ • sensor:data  │   │ • mlflow-      │   │ • Models      │   │ • Store       │   │ • Sensor Ops  │
     │   events      │   │ • ingestion:_  │   │   artifacts    │   │ • Parameters  │   │   metrics     │   │ • ML Perf     │
     │ • zones        │   │   processed    │   │                │   │               │   │               │   │               │
     │ • users        │   │ • features:_   │   │                │   │               │   │               │   │               │
     │ • predictions  │   │   computed     │   │                │   │               │   │               │   │               │
     │ • feature_     │   │ • predictions: │   │                │   │               │   │               │   │               │
     │   store        │   │   new          │   │                │   │               │   │               │   │               │
     │ • quality_     │   │ • alerts:_     │   │                │   │               │   │               │   │               │
     │   events       │   │   anomaly      │   │                │   │               │   │               │   │               │
     │                │   │                │   │                │   │               │   │               │   │               │
     └────────────────┘   └────────────────┘   └────────────────┘   └────────────────┘   └────────────────┘   └────────────────┘

══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
                                                  SERVICES BY LAYER
══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                            MICROSERVICES (Middle Layer)                                                               │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │                                                    PRESENTATION LAYER                                                            │
  ├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │                                                                                                                                 │
  │    ┌─────────────────────┐                                      ┌──────────────────────────────────────────────────────┐          │
  │    │    Web Dashboard   │                                      │                API Gateway                         │          │
  │    │      :3000         │                                      │                  :8080                               │          │
  │    │                    │                                      │                                                     │          │
  │    │  • Next.js 15      │                                      │  • JWT Authentication                              │          │
  │    │  • React           │                                      │  • Rate Limiting (100 req/min)                     │          │
  │    │  • Tailwind CSS   │                                      │  • Zone Ownership Validation                      │          │
  │    │  • Recharts       │                                      │  • Path Routing                                   │          │
  │    │                    │                                      │  • CORS                                           │          │
  │    └─────────────────────┘                                      └──────────────────────────────────────────────────────┘          │
  │                                                                                                                                 │
  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │                                                    APPLICATION LAYER                                                             │
  ├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │                                                                                                                                 │
  │    ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────────────────────────────────────────────┐          │
  │    │    User Service    │   │Notification Service│   │                    Airflow DAGs                            │          │
  │    │      :5005         │   │      :8505          │   │                      :8085                                   │          │
  │    │                    │   │                    │   │                                                             │          │
  │    │  • JWT Tokens     │   │  • Email (SMTP)     │   │  • data_pipeline_dag                                     │          │
  │    │  • bcrypt (12)    │   │  • Webhooks         │   │  • model_training_dag                                    │          │
  │    │  • Zone Ownership │   │  • Alertmanager    │   │  • scheduled_predictions_dag                            │          │
  │    │  • CRUD Users     │   │  • Severity Filter │   │                                                             │          │
  │    └─────────────────────┘   └─────────────────────┘   └─────────────────────────────────────────────────────────────┘          │
  │                                                                                                                                 │
  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │                                                       DATA LAYER                                                                 │
  ├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │                                                                                                                                 │
  │    ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐                   │
  │    │  Data Ingestion     │   │ Feature Engineering │   │    Data Quality     │   │  Sensor Simulator  │                   │
  │    │      :8001         │   │      :8004          │   │      :8005          │   │      :8000         │                   │
  │    │                    │   │                    │   │                    │   │                    │                   │
  │    │  • Redis Consumer  │   │  • Rolling Windows │   │  • Quality Rules   │   │  • Zone Config     │                   │
  │    │  • Validation      │   │  • Feature Store   │   │  • Anomaly Detect  │   │  • Diurnal Cycles  │                   │
  │    │  • TimescaleDB     │   │  • Min/Max Stats   │   │  • Sensor Health   │   │  • Noise (±2%)     │                   │
  │    │                    │   │                    │   │                    │   │                    │                   │
  │    └─────────────────────┘   └─────────────────────┘   └─────────────────────┘   └─────────────────────┘                   │
  │                                                                                                                                 │
  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │                                                        ML LAYER                                                                 │
  ├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │                                                                                                                                 │
  │    ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐                                       │
  │    │   Model Server      │   │   Drift Monitor     │   │Irrigation Controller│                                       │
  │    │      :8501         │   │      :8502          │   │      :8503          │                                       │
  │    │                    │   │                    │   │                    │                                       │
  │    │  • TensorFlow Serv  │   │  • Page-Hinkley     │   │  • Trigger Logic   │                                       │
  │    │  • Production Model │   │  • KL Divergence    │   │  • Deduplication   │                                       │
  │    │  • gRPC/REST       │   │  • Alerts           │   │  • Auto-complete   │                                       │
  │    │                    │   │                    │   │                    │                                       │
  │    └─────────────────────┘   └─────────────────────┘   └─────────────────────┘                                       │
  │                                                                                                                                 │
  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │                                                  MONITORING LAYER                                                               │
  ├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │                                                                                                                                 │
  │    ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐                   │
  │    │   Prometheus       │   │     Grafana         │   │   Alertmanager      │   │      Jenkins        │                   │
  │    │      :9090         │   │      :3001          │   │      :9093          │   │      :8081         │                   │
  │    │                    │   │                    │   │                    │   │                    │                   │
  │    │  • Metrics Collection│ │  • Dashboards     │   │  • Alert Routing   │   │  • CI/CD Pipeline  │                   │
  │    │  • Alert Rules     │   │  • Visualizations │   │  • SMTP/Webhook    │   │  • Docker Agents   │                   │
  │    │                    │   │                    │   │                    │   │  • GitHub Webhook │                   │
  │    └─────────────────────┘   └─────────────────────┘   └─────────────────────┘   └─────────────────────┘                   │
  │                                                                                                                                 │
  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │                                                PROXY & INFRASTRUCTURE                                                           │
  ├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │                                                                                                                                 │
  │    ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐                   │
  │    │       Nginx         │   │     Docker          │   │    Docker Compose   │   │       Makefile      │                   │
  │    │        :80          │   │    Containers       │   │    Orchestration    │   │    Automation      │                   │
  │    │                    │   │                    │   │                    │   │                    │                   │
  │    │  • Reverse Proxy   │   │  • 19 Services     │   │  • 5 Compose Files  │   │  • make up/down   │                   │
  │    │  • SSL Termination │   │  • Health Checks    │   │  • Networks/Volumes│   │  • make logs/test │   │
  │    │  • Path Routing    │   │  • Restart Policy   │   │  • Dependencies    │   │  • make tunnel    │                   │
  │    └─────────────────────┘   └─────────────────────┘   └─────────────────────┘   └─────────────────────┘                   │
  │                                                                                                                                 │
  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
                                                  COMPLETE WORKFLOW CYCLE
══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

     ╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
     ║                                                    FULL PIPELINE CYCLE                                                       ║
     ╠═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
     ║                                                                                                                                   ║
     ║    ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐   ║
     ║    │                                                                                                                     │   ║
     ║    │   SENSOR SIMULATOR (8000)                                                                                           │   ║
     ║    │   Generates: zone_id, sensor_id, timestamp, moisture, temperature                                                  │   ║
     ║    │   ──────────────────────────────────────────────────────────────────────────────────────► Redis [sensor:data]  │   ║
     ║    │                                                                                                                     │   ║
     ║    └────────────────────────────────────────────────────────────┬────────────────────────────────────────────────────────┘   ║
     ║                                                              │                                                              ║
     ║                                                              ▼                                                              ║
     ║    ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐   ║
     ║    │   DATA INGESTION (8001)                                                                                              │   ║
     ║    │   Validates, writes to TimescaleDB, publishes to Redis                                                             │   ║
     ║    │   ───────────────────────────────────────────────────────────────────────────────► Redis [ingestion:processed]   │   ║
     ║    │                                                                                                                     │   ║
     ║    └────────────────────────────────────────────────────────────┬────────────────────────────────────────────────────────┘   ║
     ║                                                              │                                                              ║
     ║                          ┌───────────────────────────────────┼───────────────────────────────────┐                         ║
     ║                          ▼                                   ▼                                   ▼                         ║
     ║    ┌──────────────────────────────┐   ┌──────────────────────────────┐   ┌──────────────────────────────────────────┐        ║
     ║    │    FEATURE ENGINEERING (8004) │   │      DATA QUALITY (8005)   │   │                                          │        ║
     ║    │  Computes rolling window       │   │  Detects anomalies          │   │                                          │        ║
     ║    │  features (1h, 6h, 24h)       │   │  Updates health status      │   │                                          │        ║
     ║    │  ───────────────────────────►  │   │  ───────────────────────►  │   │                                          │        ║
     ║    │  Redis [features:computed]     │   │  DB + Prometheus           │   │                                          │        ║
     ║    └───────────────────────────────┘   └─────────────────────────────┘   │                                          │        ║
     ║                                                          │               │                                          │        ║
     ║                                                          └───────────────┼──────────────────────────────────────────┘        ║
     ║                                                                      ▼                                                    ║
     ║    ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐   ║
     ║    │   MODEL SERVER (8501)                                                                                               │   ║
     ║    │   Runs ML inference, outputs predictions                                                                           │   ║
     ║    │   ───────────────────────────────────────────────────────────────────────────────► Redis [predictions:new]        │   ║
     ║    │                                                                                                                     │   ║
     ║    └────────────────────────────────────────────────────────────┬────────────────────────────────────────────────────────┘   ║
     ║                                                              │                                                              ║
     ║                          ┌───────────────────────────────────┼───────────────────────────────────┐                         ║
     ║                          ▼                                   ▼                                   ▼                         ║
     ║    ┌──────────────────────────────┐   ┌──────────────────────────────────────────────────────────┐                         ║
     ║    │    DRIFT MONITOR (8502)     │   │        IRRIGATION CONTROLLER (8503)                     │                         ║
     ║    │  Detects data/concept drift │   │  Triggers irrigation based on predictions               │                         ║
     ║    │  ───────────────────────────►  │   │  ───────────────────────────────────────────────────►   │                         ║
     ║    │  Redis [alerts:anomaly]       │   │  DB irrigation_events + Redis [irrigation:triggered] │                         ║
     ║    └───────────────────────────────┘   └───────────────────────────────────────────────────────────┘                         ║
     ║                                              │                                                                        ║
     ║                                              ▼                                                                        ║
     ║    ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐   ║
     ║    │   NOTIFICATION SERVICE (8505)                                                                                       │   ║
     ║    │   Sends email/webhook alerts, receives from Alertmanager                                                           │   ║
     ║    │   ───────────────────────────────────────────────────────────────────────────────────────────────────────────────►   │   ║
     ║    │   Email, Webhook, Alertmanager                                                                                      │   ║
     ║    └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘   ║
     ║                                                                                                                                   ║
     ╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
                                                  PORT REFERENCE TABLE
══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

     ╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
     ║                                                      PORT ALLOCATION                                                        ║
     ╠═══════════════════╦═══════════════════════════════╦══════════════════════════════════════════════════════════════════════╣
     ║       PORT         ║          SERVICE               ║                         PURPOSE                                        ║
     ╠═══════════════════╬═══════════════════════════════╬══════════════════════════════════════════════════════════════════════╣
     ║        80         ║  Nginx                         ║  Reverse proxy, main entry point                                     ║
     ║       5432        ║  TimescaleDB                   ║  PostgreSQL with TimescaleDB extension                              ║
     ║       6379        ║  Redis                        ║  Pub/Sub message broker                                             ║
     ║       3000         ║  Web Dashboard               ║  User interface                                                      ║
     ║       3001         ║  Grafana                      ║  Dashboards & visualization                                         ║
     ║       5000         ║  MLflow                       ║  Experiment tracking & model registry                               ║
     ║       5005         ║  User Service                ║  Authentication & user management                                    ║
     ║       8080         ║  API Gateway                 ║  Single entry point, routing, auth                                   ║
     ║       8081         ║  Jenkins                     ║  CI/CD automation                                                    ║
     ║       8085         ║  Airflow                     ║  DAG workflow orchestration                                          ║
     ║       8000         ║  Sensor Simulator           ║  Synthetic data generation                                           ║
     ║       8001         ║  Data Ingestion             ║  Redis → DB, validation                                              ║
     ║       8004         ║  Feature Engineering        ║  Rolling window features                                             ║
     ║       8005         ║  Data Quality               ║  Anomaly detection                                                    ║
     ║       8501         ║  Model Server               ║  TensorFlow Serving for predictions                                   ║
     ║       8502         ║  Drift Monitor              ║  Data/concept drift detection                                        ║
     ║       8503         ║  Irrigation Controller      ║  Trigger irrigation based on predictions                             ║
     ║       8505         ║  Notification Service       ║  Email/webhook alerts                                                ║
     ║       9000         ║  MinIO (API)                ║  S3-compatible object storage                                         ║
     ║       9001         ║  MinIO (Console)            ║  MinIO web UI                                                         ║
     ║       9090         ║  Prometheus                 ║  Metrics collection                                                  ║
     ║       9093         ║  Alertmanager               ║  Alert routing                                                       ║
     ╚═══════════════════╩═══════════════════════════════╩══════════════════════════════════════════════════════════════════════╝

══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
                                                  TECHNOLOGY STACK
══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

     ╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
     ║                                                    COMPLETE TECHNOLOGY SUMMARY                                                  ║
     ╠═══════════════════════╦══════════════════════════════════════════════════════════════════════════════════════════════════╣
     ║      LAYER            ║                    TECHNOLOGIES                                                                      ║
     ╠══════════════════════╬══════════════════════════════════════════════════════════════════════════════════════════════════╣
     ║  Frontend            ║  Next.js 15, React 18, TypeScript, Tailwind CSS 4, shadcn/ui, Recharts, Zustand, Lucide Icons  ║
     ║  Backend (Python)    ║  FastAPI, Uvicorn, Pydantic, Pydantic-Settings, python-jose, bcrypt, python-multipart            ║
     ║  Database             ║  PostgreSQL 16, TimescaleDB, asyncpg, psycopg2                                                   ║
     ║  Cache & Pub/Sub     ║  Redis 7 (redis-py async), fakeredis                                                              ║
║  ML                 ║  TensorFlow, TensorFlow Serving, XGBoost, scikit-learn, Pandas, NumPy, MLflow                              ║
     ║  API Clients         ║  httpx, aiohttp                                                                                  ║
     ║  Authentication       ║  JWT (python-jose), bcrypt, cryptography                                                          ║
     ║  Validation           ║  Pydantic v2                                                                                     ║
     ║  Monitoring           ║  Prometheus Client, Grafana, Alertmanager                                                          ║
     ║  Orchestration       ║  Docker Compose, Airflow, Jenkins, Nginx                                                             ║
     ║  CI/CD               ║  Jenkins (JCasC), Docker Agents, Python Agents, Ruff, Mypy, Pytest                               ║
     ║  Object Storage      ║  MinIO (S3-compatible), boto3                                                                     ║
     ║  Testing             ║  pytest, pytest-asyncio, pytest-cov                                                                ║
     ║  Code Quality        ║  Ruff, Mypy, ESLint, Pre-commit                                                                   ║
     ║  Task Scheduling     ║  Airflow (PythonOperator, BashOperator), Cron                                                    ║
     ╚══════════════════════╩══════════════════════════════════════════════════════════════════════════════════════════════════╝

This schema provides a complete visual overview of the Smart Irrigation System, showing all 19 microservices,
their data flow, storage, monitoring, and how they work together as a continuous pipeline from sensor to actuation.


═══════════════════════════════════════════════════════════════════

SECTION: Microservices Overview

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


═══════════════════════════════════════════════════════════════════

SECTION: End-to-End Data Flow

# End-to-End Pipeline Workflow

## Overview

The Smart Irrigation System operates as a continuous data pipeline, transforming raw sensor data into automated irrigation actions. This document presents the complete workflow as a unified pipeline.

---

## The Big Pipeline

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      SMART IRRIGATION PIPELINE                                              │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   STAGE 1    │    │   STAGE 2    │    │   STAGE 3    │    │   STAGE 4    │    │   STAGE 5    │
│   SENSOR     │    │   INGEST     │    │   PROCESS    │    │   PREDICT    │    │   ACTUATE    │
│   INPUT     │───▶│   & VALIDATE │───▶│   & ENRICH   │───▶│   & DECIDE   │───▶│   & NOTIFY    │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                  │                  │                  │                  │
       ▼                  ▼                  ▼                  ▼                  ▼
   ┌────────┐         ┌────────┐         ┌────────┐         ┌────────┐         ┌────────┐
   │Sensor  │         │Data    │         │Feature │         │Model   │         │Irrig.  │
   │Simulator│        │Ingestion│        │Engineer│         │Server  │         │Controller│
   │:8000   │         │:8001   │         │:8004   │         │:8501   │         │:8503   │
   └────────┘         └────────┘         └────────┘         └────────┘         └────────┘
                          │                                     │                  │
                          ▼                                     ▼                  ▼
                   ┌────────────┐                      ┌────────────┐      ┌────────────┐
                   │Redis Pub/Sub│                     │Drift       │      │Notification│
                   │Channels    │                      │Monitor     │      │Service     │
                   └────────────┘                      │:8502       │      │:8505       │
                                                        └────────────┘      └────────────┘
                                                                  │
                                                                  ▼
                                                        ┌────────────┐
                                                        │Prometheus  │
                                                        │Grafana     │
                                                        │Alertmanager│
                                                        └────────────┘

══════════════════════════════════════════════════════════════════════════════════════════════════════════════
                                                    DETAILED STAGES
══════════════════════════════════════════════════════════════════════════════════════════════════════════════
```

---

## STAGE 1: SENSOR INPUT

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1: SENSOR INPUT                                                        │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│   ┌──────────────────────────────────────────────────────────────────────┐    │
│   │                     SENSOR SIMULATOR (:8000)                         │    │
│   │                                                                      │    │
│   │   Input Sources:                                                     │    │
│   │   • Real sensors (hardware)                                          │    │
│   │   • Simulator (for testing/development)                              │    │
│   │                                                                      │    │
│   │   Logic:                                                              │    │
│   │   1. Fetch zone config (soil_type, crop_type)                       │    │
│   │   2. Apply diurnal cycles (evaporation peaks afternoon)             │    │
│   │   3. Add noise (±2% random variation)                               │    │
│   │   4. Post-irrigation: moisture spike + gradual decline              │    │
│   │                                                                      │    │
│   │   Output Rate: Every 30 seconds (configurable)                       │    │
│   └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                │
│   ┌──────────────────────────────────────────────────────────────────────┐    │
│   │  MESSAGE FORMAT                                                      │    │
│   │  ────────────────                                                     │    │
│   │  {                                                                  │    │
│   │    "zone_id": "zone-001",                                          │    │
│   │    "sensor_id": "sensor-001",                                      │    │
│   │    "timestamp": "2026-05-03T14:30:00Z",                            │    │
│   │    "moisture": 42.5,  // percent                                    │    │
│   │    "temperature": 24.3  // celsius                                  │    │
│   │  }                                                                  │    │
│   └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                │
│   [sensor:data channel]                                                       │
│          │                                                                    │
│          ▼                                                                    │
└────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
══════════════════════════════════════════════════════════════════════════════════════════════════════════════
```

---

## STAGE 2: INGEST & VALIDATE

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  STAGE 2: INGEST & VALIDATE                                                   │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│   ┌──────────────────────────────────────────────────────────────────────┐    │
│   │                   DATA INGESTION (:8001)                              │    │
│   │                                                                      │    │
│   │   Process:                                                            │    │
│   │   1. Subscribe to [sensor:data]                                      │    │
│   │   2. Parse JSON message                                              │    │
│   │   3. Fetch zone bounds (min_plausible/max_plausible)                 │    │
│   │   4. Validate:                                                        │    │
│   │      ✓ Check zone exists in DB                                       │    │
│   │      ✓ Check moisture within plausible range                        │    │
│   │      ✓ Check temperature within plausible range                     │    │
│   │   5. Decision:                                                       │    │
│   │      ✓ Valid → INSERT into sensor_readings                           │    │
│   │      ✗ Invalid → INSERT anomaly into data_quality_events            │    │
│   │   6. Publish [ingestion:processed]                                  │    │
│   │                                                                      │    │
│   └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                │
│   ┌─────────────────────────────┬──────────────────────────────────────────┐ │
│   │      VALID PATH              │          INVALID PATH                    │ │
│   ├─────────────────────────────┼──────────────────────────────────────────┤ │
│   │ sensor_readings (hypertable) │   data_quality_events                    │ │
│   │ • timestamp                 │   • event_type (below_min, above_max)    │ │
│   │ • zone_id                   │   • severity (warning/critical)          │ │
│   │ • sensor_id                 │   • details                              │ │
│   │ • moisture                  │                                         │ │
│   │ • temperature              │   → Triggers alert if critical           │ │
│   └─────────────────────────────┴──────────────────────────────────────────┘ │
│                                                                                │
│   [ingestion:processed channel]                                              │
│          │                                                                    │
│          ▼                                                                    │
└────────────────────────────────────────────────────────────────────────────────┘
                                    │
               ┌────────────────────┼────────────────────┐
               │                    │                    │
               ▼                    ▼                    ▼
══════════════════════════════════════════════════════════════════════════════════════════════════════════════
```

---

## STAGE 3: PROCESS & ENRICH

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  STAGE 3: PROCESS & ENRICH                                                   │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│   ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│   │  FEATURE ENGINEERING│  │    DATA QUALITY     │  │   STORE RAW DATA    │  │
│   │      (:8004)        │  │      (:8005)        │  │                     │  │
│   ├─────────────────────┤  ├─────────────────────┤  ├─────────────────────┤  │
│   │                     │  │                     │  │                     │  │
│   │ Subscribe to        │  │ Subscribe to         │  │ TimescaleDB         │  │
│   │ [ingestion:processed│  │ [ingestion:processed│  │ • sensor_readings  │  │
│   │                     │  │                     │  │ • sensor_metadata  │  │
│   │ Compute features:  │  │ Quality rules:       │  │ • zones             │  │
│   │ • 1h rolling mean  │  │ • stuck_value       │  │ • users             │  │
│   │ • 6h rolling mean  │  │ • sudden_jump       │  │                     │  │
│   │ • 24h rolling mean │  │ • flatline          │  │                     │  │
│   │ • trend (slope)   │  │ • rate_of_change    │  │                     │  │
│   │ • volatility       │  │                     │  │                     │  │
│   │                     │  │ Update health:      │  │                     │  │
│   │ Store to:          │  │ • healthy (0)       │  │                     │  │
│   │ feature_store      │  │ • degraded (1)      │  │                     │  │
│   │ table              │  │ • unhealthy (2)     │  │                     │  │
│   │                     │  │                     │  │                     │  │
│   │ Publish to:        │  │ Prometheus gauge:    │  │                     │  │
│   │ [features:computed]│  │ data_quality_sensor │  │                     │  │
│   │                    │  │ _health_status      │  │                     │  │
│   └─────────────────────┘  └─────────────────────┘  └─────────────────────┘  │
│                                                                                │
│   [features:computed channel]                                                │
│          │                                                                    │
│          ▼                                                                    │
└────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
══════════════════════════════════════════════════════════════════════════════════════════════════════════════
```

---

## STAGE 4: PREDICT & DECIDE

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  STAGE 4: PREDICT & DECIDE                                                   │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│   ┌──────────────────────────────────────────────────────────────────────┐    │
│   │                         MODEL SERVER (:8501)                        │    │
│   │                                                                      │    │
│   │   Subscribe to: [features:computed]                                 │    │
│   │                                                                      │    │
│   │   Process:                                                            │    │
│   │   1. Load features from feature_store (last 24h window)             │    │
│   │   2. Prepare input tensor for TensorFlow model                      │    │
│   │   3. Run inference: model.predict(features)                         │    │
│   │   4. Output: Predicted moisture for next 6 hours (hourly)           │    │
│   │   5. Store predictions in predictions table                         │    │
│   │   6. Publish to [predictions:new]                                    │    │
│   │                                                                      │    │
│   │   Model: Production model from MLflow (Staging/Production)          │    │
│   │   Latency: < 100ms per prediction                                    │    │
│   │                                                                      │    │
│   └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                │
│   [predictions:new channel]                                                  │
│          │                                                                    │
│          ├──────────────────────┐                                          │
│          │                      │                                          │
│          ▼                      ▼                                          │
│   ┌──────────────────┐   ┌──────────────────┐                               │
│   │  DRIFT MONITOR   │   │IRRIGATION CTRL  │                               │
│   │     (:8502)      │   │     (:8503)      │                               │
│   ├──────────────────┤   ├──────────────────┤                               │
│   │                  │   │                  │                               │
│   │ Compare:        │   │ Trigger Logic:   │                               │
│   │ prediction vs   │   │ IF predicted <   │                               │
│   │ actual (when     │   │   moisture_min    │                               │
│   │   actual arrives)│   │   THEN           │                               │
│   │                  │   │   create event   │                               │
│   │ Drift Tests:     │   │                  │                               │
│   │ • Page-Hinkley   │   │ Deduplication:   │                               │
│   │ • KL Divergence  │   │ 10min per zone   │                               │
│   │                  │   │                  │                               │
│   │ If drift >       │   │ Auto-complete:   │                               │
│   │ threshold →      │   │ after 5 seconds │                               │
│   │ [alerts:anomaly] │   │                  │                               │
│   └──────────────────┘   └──────────────────┘                               │
│                                                                                │
│   ┌──────────────────────────────────────────────────────────────────────┐    │
│   │  IRRIGATION EVENT TABLE                                               │    │
│   │  ─────────────────────                                               │    │
│   │  • zone_id            • trigger_reason (prediction_based)          │    │
│   │  • triggered_at       • recommended_volume                           │    │
│   │  • status (pending/completed) • actual_volume                       │    │
│   │  • duration_seconds   • completed_at                                 │    │
│   └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                │
│   [irrigation:triggered channel]                                              │
│          │                                                                    │
│          ▼                                                                    │
└────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
══════════════════════════════════════════════════════════════════════════════════════════════════════════════
```

---

## STAGE 5: ACTUATE & NOTIFY

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  STAGE 5: ACTUATE & NOTIFY                                                   │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│   ┌──────────────────────────────────────────────────────────────────────┐    │
│   │                   NOTIFICATION SERVICE (:8505)                     │    │
│   │                                                                      │    │
│   │   Subscribes to:                                                     │    │
│   │   • [alerts:anomaly]  (from drift-monitor, data-quality)           │    │
│   │   • [irrigation:triggered] (from irrigation-controller)             │    │
│   │   • /alerts/webhook (from Alertmanager)                              │    │
│   │                                                                      │    │
│   │   Process:                                                            │    │
│   │   1. Receive alert payload                                          │    │
│   │   2. Check severity threshold (info/warning/critical)              │    │
│   │   3. If meets threshold:                                            │    │
│   │      • Send email via SMTP                                           │    │
│   │      • Send webhook HTTP POST                                        │    │
│   │   4. Track metrics: notification_service_deliveries_total           │    │
│   │                                                                      │    │
│   └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                │
│   ┌──────────────────────────────────────────────────────────────────────┐    │
│   │                     ACTUATION (Physical)                            │    │
│   │                                                                      │    │
│   │   In a real system, irrigation:triggered signals would control:     │    │
│   │   • Solenoid valves (open/close)                                    │    │
│   │   • Water pumps (on/off)                                            │    │
│   │   • Flow meters (measure actual volume)                             │    │
│   │                                                                      │    │
│   │   For this implementation:                                          │    │
│   │   • Event logged in irrigation_events table                         │    │
│   │   • Status changed from 'pending' to 'completed' after 5 seconds    │    │
│   │   • actual_volume and duration_seconds recorded                     │    │
│   │                                                                      │    │
│   └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
══════════════════════════════════════════════════════════════════════════════════════════════════════════════
                                    │
                                    ▼
                    ┌───────────────────────────────────────┐
                    │          COMPLETE CYCLE                │
                    │                                       │
                    │   Sensor → Ingest → Process →        │
                    │   Predict → Actuate → Notify          │
                    │                                       │
                    │   Then: Repeat from Stage 1           │
                    │   (Continuous pipeline)               │
                    └───────────────────────────────────────┘
```

---

## Pipeline Summary

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         PIPELINE AT A GLANCE                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  STAGE          │ SERVICE         │ INPUT                │ OUTPUT              │
│  ──────────────────────────────────────────────────────────────────────────────│
│  1. INPUT       │ Sensor Sim      │ (generated)         │ sensor:data          │
│  2. INGEST      │ Data Ingestion  │ sensor:data          │ sensor_readings      │
│  3. PROCESS     │ Feature Eng     │ ingestion:processed  │ features:computed   │
│  4. PREDICT     │ Model Server    │ features:computed    │ predictions:new      │
│  5. ACTUATE     │ Irrig Ctrl      │ predictions:new      │ irrigation_events    │
│       +         │ Notify Svc      │ irrigation:triggered│ email/webhook       │
│                                                                                 │
│  ══════════════════════════════════════════════════════════════════════════════│
│                                                                                 │
│  TIMING:                                                                      │
│  • Stage 1 → 2: ~1 second                                                     │
│  • Stage 2 → 3: ~1 second                                                     │
│  • Stage 3 → 4: ~2 seconds                                                    │
│  • Stage 4 → 5: ~1 second                                                     │
│  • Auto-complete: 5 seconds                                                   │
│                                                                                 │
│  Total cycle: ~10-15 seconds                                                 │
│                                                                                 │
│  ══════════════════════════════════════════════════════════════════════════════│
│                                                                                 │
│  METRICS AT EACH STAGE:                                                        │
│  Stage 1: sensor_simulator_readings_total                                     │
│  Stage 2: data_ingestion_total_processed, data_ingestion_valid_readings       │
│  Stage 3: feature_engineering_features_computed, data_quality_sensor_health    │
│  Stage 4: model_server_predictions_total, drift_monitor_kl_divergence         │
│  Stage 5: irrigation_triggers_total, notification_service_deliveries_total     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Redis Channel Flow

```
                    ┌─────────────────┐
                    │  sensor:data     │
                    │  (Stage 1 out)  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ ingestion:      │
                    │ processed       │
                    │ (Stage 2 out)  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
      ┌────────────┐  ┌───────────┐  ┌─────────────┐
      │features:   │  │(directly) │  │(not used)   │
      │computed    │  │           │  │             │
      └─────┬──────┘  └─────┬─────┘  └──────┬──────┘
            │              │              │
            ▼              │              │
      ┌────────────┐       │              │
      │predictions:│◄──────┘              │
      │new         │                     │
      └─────┬──────┘                     │
            │                             │
     ┌──────┴──────┐                      │
     ▼             ▼                      │
┌─────────┐  ┌─────────────┐              │
│drift:   │  │irrigation:  │              │
│alerts   │  │triggered    │              │
└────┬────┘  └──────┬──────┘              │
     │             │                      │
     └──────┬──────┘                      │
            ▼                             │
      ┌─────────────────────────────┐    │
      │    Notification Service      │◄───┘
      │    (Stage 5 - Notify)        │
      └─────────────────────────────┘
```

This pipeline runs continuously, processing new sensor data every 30 seconds and triggering irrigation automatically based on ML predictions.


═══════════════════════════════════════════════════════════════════

SECTION: Infrastructure & Docker Compose

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


═══════════════════════════════════════════════════════════════════

SECTION: Nginx Reverse Proxy

# Nginx Reverse Proxy

## Overview

Nginx acts as a single entry point for all Smart Irrigation services, providing reverse proxy functionality, routing requests to appropriate backend services, and optionally handling SSL/TLS termination.

**Port:** 80

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CLIENTS                                           │
│                                                                                 │
│  Browser → http://localhost/                                                  │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         NGINX (:80)                                            │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                       Route Map                                          │   │
│  │                                                                          │   │
│  │  /             → web-dashboard:3000                                     │   │
│  │  /api/         → api-gateway:8080                                       │   │
│  │  /grafana/     → grafana:3000                                           │   │
│  │  /prometheus/  → prometheus:9090                                        │   │
│  │  /alertmanager/→ alertmanager:9093                                       │   │
│  │  /mlflow/      → mlflow:5000                                             │   │
│  │  /minio/       → minio:9001                                             │   │
│  │  /airflow/     → airflow:8085                                            │   │
│  │  /health       → (nginx returns 200)                                     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
     ┌─────────────┬─────────────┼─────────────┬─────────────┐
     ▼             ▼             ▼             ▼             ▼
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│Dashboard│   │   API   │   │ Grafana │   │Prometheus│  │  MLflow │
│  :3000  │   │ :8080   │   │  :3000  │   │  :9090  │  │  :5000  │
└─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘
```

---

## Configuration

### nginx.conf

```nginx
server {
    listen 80;
    server_name localhost;

    # Web Dashboard
    location / {
        proxy_pass http://web-dashboard:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # API Gateway
    location /api/ {
        proxy_pass http://api-gateway:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Grafana
    location /grafana/ {
        proxy_pass http://grafana:3000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        rewrite ^/grafana/(.*) /$1 break;
    }

    # Prometheus
    location /prometheus/ {
        proxy_pass http://prometheus:9090/;
        rewrite ^/prometheus/(.*) /$1 break;
    }

    # Alertmanager
    location /alertmanager/ {
        proxy_pass http://alertmanager:9093/;
        rewrite ^/alertmanager/(.*) /$1 break;
    }

    # MLflow
    location /mlflow/ {
        proxy_pass http://mlflow:5000/;
        rewrite ^/mlflow/(.*) /$1 break;
    }

    # MinIO Console
    location /minio/ {
        proxy_pass http://minio:9001/;
        rewrite ^/minio/(.*) /$1 break;
    }

    # Airflow
    location /airflow/ {
        proxy_pass http://airflow:8085/;
        rewrite ^/airflow/(.*) /$1 break;
    }

    # Health check
    location /health {
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

---

## Docker Compose

### docker-compose.nginx.yml

```yaml
services:
  nginx:
    image: nginx:alpine
    container_name: nginx
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./configs/nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    networks:
      - irrigation_net
    depends_on:
      - web-dashboard
      - api-gateway
      - grafana
      - prometheus
      - alertmanager
      - mlflow
      - minio
      - airflow
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "-", "http://localhost/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

---

## Starting with Nginx

```bash
# Full stack with Nginx
docker compose -f docker-compose.yml \
               -f docker-compose.app.yml \
               -f docker-compose.data.yml \
               -f docker-compose.ml.yml \
               -f docker-compose.monitoring.yml \
               -f docker-compose.nginx.yml up -d
```

---

## Access Routes

| URL | Service |
|-----|---------|
| http://localhost/ | Web Dashboard |
| http://localhost/api/v1/* | API Gateway |
| http://localhost/api/auth/* | Auth endpoints |
| http://localhost/grafana/ | Grafana |
| http://localhost/prometheus/ | Prometheus |
| http://localhost/alertmanager/ | Alertmanager |
| http://localhost/mlflow/ | MLflow |
| http://localhost/minio/ | MinIO Console |
| http://localhost/airflow/ | Airflow |
| http://localhost/health | Nginx health check |

---

## SSL/HTTPS Configuration

### Generate SSL Certificate

```bash
# Using Let's Encrypt (requires domain pointing to server)
sudo apt install certbot
sudo certbot --nginx -d your-domain.com

# Self-signed (for local testing)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem
```

### HTTPS Configuration

```nginx
server {
    listen 443 ssl;
    server_name localhost;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # ... proxy configuration same as HTTP
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name localhost;
    return 301 https://$server_name$request_uri;
}
```

---

## Load Balancing (Future)

For horizontal scaling:

```nginx
upstream dashboard_cluster {
    server web-dashboard-1:3000;
    server web-dashboard-2:3000;
    server web-dashboard-3:3000;
}

server {
    location / {
        proxy_pass http://dashboard_cluster;
    }
}
```

---

## Summary

| Aspect | Value |
|--------|-------|
| Port | 80 |
| Image | nginx:alpine |
| Config | docker/configs/nginx/nginx.conf |
| Compose | docker/docker-compose.nginx.yml |
| Routes | 8 backend services |

Nginx provides centralized access to all services through a single port, making deployment simpler and enabling future SSL termination.


═══════════════════════════════════════════════════════════════════

SECTION: Database Schema

# Database Schema

## Overview

The Smart Irrigation System uses PostgreSQL with the TimescaleDB extension for time-series data storage. The database is the central data store for sensor readings, irrigation events, users, zones, and quality metrics.

**Host:** timescaledb:5432

**Database:** irrigation_db

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     POSTGRESQL + TIMESCALEDB                                    │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                       Tables                                             │   │
│  │                                                                          │   │
│  │  ┌─────────────┐  ┌─────────────────┐  ┌─────────────┐  ┌────────────┐   │   │
│  │  │   zones     │  │ sensor_metadata │  │  users     │  │ quality   │   │   │
│  │  │             │  │                 │  │            │  │ _rules    │   │   │
│  │  └─────────────┘  └─────────────────┘  └─────────────┘  └────────────┘   │   │
│  │                                                                          │   │
│  │  ┌───────────────────┐  ┌─────────────────────┐                         │   │
│  │  │  sensor_readings  │  │  irrigation_events │  (Hypertables)        │   │
│  │  │     (hypertable)  │  │    (hypertable)     │                         │   │
│  │  └───────────────────┘  └─────────────────────┘                         │   │
│  │                                                                          │   │
│  │  ┌─────────────────────┐  ┌─────────────────────┐                         │   │
│  │  │ data_quality_events │  │   schema_migrations │                         │   │
│  │  └─────────────────────┘  └─────────────────────┘                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                       Views                                              │   │
│  │                                                                          │   │
│  │  v_quality_metrics  - Hourly quality summary                            │   │
│  │  v_sensor_health    - Sensor health status                              │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Tables

### zones

Zone configuration and irrigation thresholds:

```sql
CREATE TABLE zones (
    zone_id       VARCHAR(50)  PRIMARY KEY,
    zone_name     VARCHAR(200) NOT NULL,
    soil_type     VARCHAR(50)  NOT NULL,
    crop_type     VARCHAR(50)  NOT NULL,
    moisture_min  FLOAT        NOT NULL,  -- irrigation trigger threshold
    moisture_max  FLOAT        NOT NULL,  -- maximum moisture
    min_plausible JSONB       NOT NULL DEFAULT '{}',
    max_plausible JSONB        NOT NULL DEFAULT '{}',
    active        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Indexes:**
- `idx_zones_active` - Filter active zones
- `idx_zones_min_plausible` - GIN index for JSONB
- `idx_zones_max_plausible` - GIN index for JSONB

---

### users

User accounts for authentication:

```sql
CREATE TABLE users (
    user_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

### sensor_metadata

Registered sensors:

```sql
CREATE TABLE sensor_metadata (
    sensor_id    VARCHAR(50) PRIMARY KEY,
    zone_id      VARCHAR(50) NOT NULL REFERENCES zones(zone_id) ON DELETE CASCADE,
    sensor_type  VARCHAR(50) NOT NULL DEFAULT 'moisture',
    installed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    active       BOOLEAN     NOT NULL DEFAULT TRUE
);
```

---

### sensor_readings (Hypertable)

Time-series sensor data:

```sql
CREATE TABLE sensor_readings (
    id          BIGSERIAL,
    timestamp   TIMESTAMPTZ NOT NULL,
    zone_id     VARCHAR(50) NOT NULL REFERENCES zones(zone_id),
    sensor_id   VARCHAR(50) NOT NULL,
    moisture    FLOAT       NOT NULL,
    temperature FLOAT,
    PRIMARY KEY (id, timestamp)
);

SELECT create_hypertable(
    'sensor_readings',
    'timestamp',
    chunk_time_interval => INTERVAL '1 day'
);
```

**Chunk interval:** 1 day (high write volume)

---

### irrigation_events (Hypertable)

Irrigation event log:

```sql
CREATE TABLE irrigation_events (
    id                 BIGSERIAL,
    triggered_at       TIMESTAMPTZ  NOT NULL,
    zone_id            VARCHAR(50)  NOT NULL REFERENCES zones(zone_id),
    trigger_reason     VARCHAR(100) NOT NULL,
    recommended_volume FLOAT,
    actual_volume      FLOAT,
    duration_seconds   INTEGER,
    status             VARCHAR(20)  NOT NULL DEFAULT 'pending'
                       CHECK (status IN ('pending', 'completed', 'failed')),
    completed_at       TIMESTAMPTZ,
    PRIMARY KEY (id, triggered_at)
);

SELECT create_hypertable(
    'irrigation_events',
    'triggered_at',
    chunk_time_interval => INTERVAL '1 week'
);
```

**Chunk interval:** 1 week (low write volume)

---

### data_quality_events

Anomaly and quality events:

```sql
CREATE TABLE data_quality_events (
    id            BIGSERIAL,
    timestamp     TIMESTAMPTZ NOT NULL,
    zone_id       VARCHAR(50) NOT NULL,
    sensor_id     VARCHAR(50) NOT NULL,
    event_type    VARCHAR(100) NOT NULL,
    event_value   FLOAT,
    expected_min  FLOAT,
    expected_max  FLOAT,
    severity      VARCHAR(20) DEFAULT 'warning',
    details       TEXT
);
```

---

### quality_rules

Configurable quality rules:

```sql
CREATE TABLE quality_rules (
    rule_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_name       VARCHAR(100) NOT NULL UNIQUE,
    rule_type       VARCHAR(50) NOT NULL,
    sensor_type     VARCHAR(50),
    zone_id         VARCHAR(50) REFERENCES zones(zone_id) ON DELETE CASCADE,
    parameters      JSONB NOT NULL DEFAULT '{}',
    severity        VARCHAR(20) NOT NULL DEFAULT 'warning',
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Default rules:**
| Rule Name | Type | Sensor | Parameters |
|-----------|------|--------|------------|
| stuck_moisture | stuck_value | moisture | consecutive_count=5, tolerance=0.001 |
| stuck_temperature | stuck_value | temperature | consecutive_count=10, tolerance=0.01 |
| sudden_jump_moisture | sudden_jump | moisture | max_delta=0.35, max_pct_change=50 |
| flatline_moisture | flatline | moisture | window_minutes=30, max_variance=0.0001 |
| flatline_temperature | flatline | temperature | window_minutes=60, max_variance=0.01 |
| rate_of_change_temp | rate_of_change | temperature | window_minutes=15, max_rate_per_min=2.0 |

---

### schema_migrations

Migration tracking:

```sql
CREATE TABLE schema_migrations (
    version     VARCHAR(50) PRIMARY KEY,
    description TEXT,
    checksum    VARCHAR(64),
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## Views

### v_quality_metrics

Hourly quality summary for Grafana:

```sql
CREATE OR REPLACE VIEW v_quality_metrics AS
SELECT
    date_trunc('hour', timestamp) AS bucket,
    zone_id,
    event_type,
    severity,
    COUNT(*) AS event_count,
    COUNT(DISTINCT sensor_id) AS affected_sensors
FROM data_quality_events
WHERE timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY date_trunc('hour', timestamp), zone_id, event_type, severity;
```

---

### v_sensor_health

Sensor health status:

```sql
CREATE OR REPLACE VIEW v_sensor_health AS
SELECT
    sm.zone_id,
    sm.sensor_id,
    sm.sensor_type,
    sm.active,
    COALESCE(SUM(re.cnt) FILTER (WHERE re.severity = 'critical'), 0) AS critical_count,
    COALESCE(SUM(re.cnt) FILTER (WHERE re.severity = 'warning'), 0) AS warning_count,
    COALESCE(SUM(re.cnt), 0) AS total_anomalies,
    CASE
        WHEN COALESCE(SUM(re.cnt) FILTER (WHERE re.severity = 'critical'), 0) > 5 THEN 'unhealthy'
        WHEN COALESCE(SUM(re.cnt), 0) > 10 THEN 'degraded'
        ELSE 'healthy'
    END AS health_status
FROM sensor_metadata sm
LEFT JOIN recent_events re ON ...
GROUP BY sm.zone_id, sm.sensor_id, sm.sensor_type, sm.active;
```

**Health status logic:**
- `unhealthy` - More than 5 critical events in 24h
- `degraded` - More than 10 total events in 24h
- `healthy` - Otherwise

---

## Roles & Permissions

| Role | Tables | Permissions |
|------|--------|-------------|
| `ingestion_user` | sensor_readings, irrigation_events, sensor_metadata, quality_rules | INSERT, SELECT |
| `reader_user` | All tables | SELECT |
| `app_user` | zones, users | SELECT, INSERT, UPDATE |

---

## Migrations

### Migration Order

| # | File | Description |
|---|------|-------------|
| 001 | 001_init_timescaledb.sql | Core schema, hypertables, roles |
| 002 | 002_plausibility_bounds.sql | min/max_plausible columns |
| 003 | 003_feature_references.sql | Feature references |
| 004 | 004_shadow_comparison.sql | Shadow model comparison |
| 005 | 005_user_and_zone_ownership.sql | Users table |
| 006 | 006_quality_rules.sql | Quality rules, views |
| 007 | 007_add_user_roles.sql | User roles |
| 008 | 008_zone_ownership_system.sql | Zone ownership |
| 009 | 009_feature_versioning.sql | Feature versioning |
| 010 | 010_auto_zone_id.sql | Auto zone_id |
| 011 | 011_cascade_zone_deletion.sql | Cascade deletes |
| 012 | 012_remove_default_zones.sql | Remove default zones |

---

## Configuration

### Environment Variables

From `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | irrigation_user | Main user |
| `POSTGRES_PASSWORD` | postgres_dev | Main password |
| `POSTGRES_DB` | irrigation_db | Database name |
| `TIMESCALEDB_SENSOR_CHUNK_INTERVAL` | 1 day | sensor_readings chunk |
| `TIMESCALEDB_IRRIGATION_CHUNK_INTERVAL` | 1 week | irrigation_events chunk |

---

## Connecting

### From host

```bash
psql -h localhost -p 5432 -U irrigation_user -d irrigation_db
```

### From container

```bash
docker exec -it timescaledb psql -U irrigation_user -d irrigation_db
```

---

## Docker Compose

```yaml
timescaledb:
  image: timescale/timescaledb:latest-pg16
  ports:
    - "5432:5432"
  volumes:
    - timescaledb_data:/var/lib/postgresql/data
    - ../migrations:/docker-entrypoint-initdb.d:ro
```

---

## Summary

| Aspect | Value |
|--------|-------|
| Engine | PostgreSQL 16 + TimescaleDB |
| Database | irrigation_db |
| Hypertables | sensor_readings (1d chunks), irrigation_events (1w chunks) |
| Roles | ingestion_user, reader_user, app_user |
| Migrations | 12 migrations in order |

The database provides centralized storage with time-series optimization for high-volume sensor data and efficient querying for dashboards and analytics.


═══════════════════════════════════════════════════════════════════

SECTION: Database Schema Details

# Database Schema: TimescaleDB

## Overview
The system uses TimescaleDB (PostgreSQL) as its primary data store. It combines relational tables for metadata and management with hypertables for high-velocity time-series data.

## 1. Relational Tables (Management)

### `users`
Tracks system users and their roles.
- `user_id`: UUID (Primary Key)
- `email`: String (Unique)
- `hashed_password`: String
- `full_name`: String
- `is_admin`: Boolean (Default: FALSE)

### `zones`
Represents physical irrigation areas.
- `zone_id`: String (Primary Key)
- `zone_name`: String
- `soil_type`: String
- `crop_type`: String
- `owner_id`: UUID (FK -> users)
- `source`: String ('api' or 'yaml')
- `min_plausible` / `max_plausible`: JSONB (Bounds per sensor type)
- `moisture_min`: FLOAT (Threshold for triggering irrigation)
- `moisture_max`: FLOAT (Upper bound for alerts)

### `sensor_metadata`
Tracks individual sensor deployment.
- `sensor_id`: String (Primary Key)
- `zone_id`: String (FK -> zones)
- `sensor_type`: String ('moisture', 'temperature')
- `active`: Boolean

### `quality_rules`
Configurable rules for malfunction detection.
- `rule_id`: UUID
- `rule_name`: String
- `rule_type`: String (stuck_value, sudden_jump, etc.)
- `parameters`: JSONB

## 2. Hypertables (Time-Series)

### `sensor_readings`
Raw sensor telemetry.
- **Partition Interval**: 1 Day
- `timestamp`: TIMESTAMPTZ
- `zone_id`: FK -> zones
- `moisture`: FLOAT
- `temperature`: FLOAT

### `data_quality_events`
Log of anomalies and malfunctions.
- **Partition Interval**: 1 Day
- `event_type`: String (below_min, stuck_value, etc.)
- `severity`: String (warning, critical)
- `event_value`: FLOAT

### `feature_references`
The ML Feature Store.
- `computed_at`: TIMESTAMPTZ
- `window_size`: String (30m, 1h, 24h)
- `feature_name`: String
- `feature_value`: FLOAT
- `model_version`: String

### `model_predictions`
Inference results.
- **Partition Interval**: 1 Day
- `prediction`: FLOAT (Predicted moisture)
- `confidence`: FLOAT

### `irrigation_events`
Irrigation trigger events.
- **Partition Interval**: 1 Day
- `triggered_at`: TIMESTAMPTZ (When irrigation was triggered)
- `zone_id`: String (FK -> zones)
- `trigger_reason`: String (e.g., 'predicted_moisture_below_threshold')
- `recommended_volume`: FLOAT (Calculated liters needed)
- `actual_volume`: FLOAT (Actual liters applied, nullable)
- `duration_seconds`: INTEGER (Irrigation duration, nullable)
- `status`: String ('pending', 'completed', 'cancelled')

## 3. Views & Analytics

- `v_sensor_health`: Aggregates quality events to determine per-sensor status (healthy, degraded, unhealthy).
- `v_quality_metrics`: Provides hourly counts of anomalies for Grafana dashboards.
- `v_shadow_comparison`: Compares results between champion and shadow models.



═══════════════════════════════════════════════════════════════════

SECTION: API Gateway

# API Gateway Documentation

## Overview

The API Gateway is the central entry point for all client requests to the Smart Irrigation System. It provides:
- **Authentication** - JWT-based auth with access/refresh tokens
- **Authorization** - Zone-level ownership validation
- **Rate Limiting** - Redis-based per-IP rate limiting
- **Routing** - Proxy requests to backend services
- **Monitoring** - Prometheus metrics for all requests
- **CORS** - Cross-origin request handling

**Location:** `services/api-gateway/src/`

**Port:** 8080

---

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY                                         │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        FastAPI Application                              │   │
│  │                                                                          │   │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │   │
│  │  │                     Middleware Stack                             │  │   │
│  │  │                                                                   │  │   │
│  │  │  1. CORS Middleware (allow_origins)                               │  │   │
│  │  │  2. Rate Limit Middleware (per IP, 100/min)                      │  │   │
│  │  │  3. Prometheus Metrics Middleware                                │  │   │
│  │  │  4. Authentication Middleware                                     │  │   │
│  │  │  5. Zone Ownership Validation                                     │  │   │
│  │  │  6. Proxy to Upstream Services                                    │  │   │
│  │  │                                                                   │  │   │
│  │  └──────────────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Clients      │    │    Redis        │    │  PostgreSQL     │
│                 │    │                 │    │  (zones data)   │
│ - Web Browser   │    │  Rate limiting  │    │                 │
│ - Mobile App    │    │  - rate_limit:  │    │  Ownership      │
│ - External APIs │    │    {client_ip}  │    │  validation     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         UPSTREAM SERVICES                                      │
│                                                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │User Service │ │Model Server │ │Drift Monitor│ │Irrigation   │            │
│  │   (5005)    │ │   (8501)    │ │   (8502)    │ │ Controller  │            │
│  │             │ │             │ │             │ │   (8503)    │            │
│  │ - /auth/*   │ │ - /v1/predict│ │ - /v1/drift │ │ - /v1/      │            │
│  │ - /users/*  │ │ - /v1/model  │ │             │ │   irrigation│            │
│  │ - /v1/zones │ │             │ │             │ │             │            │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘            │
│                                                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                             │
│  │Notification │ │Data Quality │ │Web Dashboard│                             │
│  │ Service     │ │  Service    │ │   (3000)   │                             │
│  │   (8505)    │ │   (8005)    │ │             │                             │
│  │             │ │             │ │             │                             │
│  │/v1/notif.*  │ │  /quality/* │ │ /dashboard/*│                             │
│  └─────────────┘ └─────────────┘ └─────────────┘                             │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Routing

### Route Mapping

The gateway maps incoming paths to upstream services:

```python
ROUTES = {
    "/auth":           USER_SERVICE_URL,         # Strip /auth prefix
    "/users":         USER_SERVICE_URL,
    "/v1/predict":    MODEL_SERVER_URL,
    "/v1/model":      MODEL_SERVER_URL,
    "/v1/zones":      USER_SERVICE_URL,
    "/v1/drift":      DRIFT_MONITOR_URL,
    "/v1/irrigation": IRRIGATION_CONTROLLER_URL,
    "/v1/notifications": NOTIFICATION_SERVICE_URL,
    "/quality":       DATA_QUALITY_URL,
    "/dashboard":     WEB_DASHBOARD_URL,
}
```

### Example Translations

| Client Request | Upstream Service | Upstream Path |
|----------------|------------------|---------------|
| `GET /auth/login` | User Service | `/login` (stripped `/auth`) |
| `GET /users/me` | User Service | `/users/me` |
| `POST /v1/predict` | Model Server | `/v1/predict` |
| `GET /v1/zones` | User Service | `/v1/zones` |
| `GET /v1/drift/status` | Drift Monitor | `/v1/drift/status` |
| `GET /v1/irrigation/events` | Irrigation Controller | `/v1/irrigation/events` |

---

## Authentication

### JWT Tokens

The gateway handles JWT-based authentication:

**Access Token:**
- Expiry: 15 minutes
- Purpose: API authentication
- Payload: `{"sub": "user_id", "type": "access", "iat": ..., "exp": ...}`

**Refresh Token:**
- Expiry: 7 days
- Purpose: Get new access token
- Payload: `{"sub": "user_id", "type": "refresh", "iat": ..., "exp": ...}`

### Token Flow

```
1. Client sends credentials to /auth/login
                   │
                   ▼
2. User Service validates and returns tokens
                   │
                   ▼
3. Client includes in Authorization header:
   Authorization: Bearer {access_token}
                   │
                   ▼
4. Gateway validates token (auth.py)
                   │
                   ├── Valid ──► Proxy to service
                   │
                   └── Invalid ──► 401 Unauthorized
```

### Token Refresh

```bash
POST /auth/refresh
{
  "refresh_token": "eyJ..."
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

---

## Authorization

### Protected Routes

These routes require authentication:

```python
# Routes requiring auth
if path.startswith(("auth/", "users/", "v1/zones/", "v1/irrigation/", "v1/notifications/", "quality/")):
    require_auth = True

# Exception: public auth endpoints
if path in ("auth/login", "auth/register", "auth/auth_refresh"):
    require_auth = False
```

### Zone Ownership Validation

When users modify zones, the gateway validates ownership:

```python
async def validate_zone_ownership(request: Request, zone_id: str):
    user_payload = await get_current_user_payload(request)
    user_id = user_payload.get("sub")
    is_admin = user_payload.get("is_admin", False)

    # Admin can do anything
    if is_admin:
        return

    # Check zone ownership
    row = await conn.fetchrow(
        "SELECT owner_id, source FROM zones WHERE zone_id = $1",
        zone_id,
    )

    is_owner = row["owner_id"] and str(row["owner_id"]) == user_id

    # System zones (yaml, no owner) are read-only
    if row["source"] == "yaml" and not row["owner_id"]:
        raise 403 Forbidden

    # Only owner can modify
    if not is_owner:
        raise 403 Forbidden
```

**Ownership Rules:**
| Zone Source | Has Owner | Can User Modify? |
|-------------|-----------|-------------------|
| `yaml` | No (system) | ❌ No (read-only) |
| `yaml` | Yes | ✅ Yes (if owner) |
| `api` | Yes | ✅ Yes (if owner) |
| `api` | No | ❌ No (orphan) |

---

## Rate Limiting

### Configuration

Rate limiting is Redis-based with sliding window:

```python
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "100"))
```

Default: 100 requests per minute per IP

### How It Works

```python
async def check_rate_limit(client_ip: str) -> bool:
    key = f"rate_limit:{client_ip}"
    current_time = int(time.time())
    window_start = current_time - 60  # 1 minute window

    # Remove old entries
    redis.zremrangebyscore(key, "-inf", str(window_start))

    # Count current entries
    request_count = redis.zcard(key)

    # Add new entry
    redis.zadd(key, {str(current_time): current_time})
    redis.expire(key, 60)

    return request_count < 100
```

### Response Headers

When rate limited, returns:
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
```

---

## Middleware Stack

### 1. CORS Middleware

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # From env var
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. Rate Limit Middleware

Applies to all requests except testing environment.

### 3. Prometheus Metrics Middleware

Tracks request count and latency.

### 4. Authentication Middleware

Validates JWT for protected routes.

### 5. Proxy Middleware

Forwards requests to upstream services.

---

## API Endpoints

### Health Check

```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "api-gateway"
}
```

### Metrics

```bash
GET /metrics
```

**Prometheus metrics:**
- `api_gateway_http_requests_total` - Total requests by method, path, status
- `api_gateway_request_duration_seconds` - Request latency histogram

### Root

```bash
GET /
```

**Response:**
```json
{
  "message": "Smart Irrigation API Gateway",
  "version": "1.0.0"
}
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_GATEWAY_PORT` | `8080` | Gateway port |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` | Allowed CORS origins |
| `USER_SERVICE_URL` | `http://user-service:5005` | User service URL |
| `MODEL_SERVER_URL` | `http://model-server:8501` | Model server URL |
| `DRIFT_MONITOR_URL` | `http://drift-monitor:8502` | Drift monitor URL |
| `IRRIGATION_CONTROLLER_URL` | `http://irrigation-controller:8503` | Irrigation controller URL |
| `NOTIFICATION_SERVICE_URL` | `http://notification-service:8505` | Notification service URL |
| `DATA_QUALITY_URL` | `http://data-quality:8005` | Data quality service URL |
| `WEB_DASHBOARD_URL` | `http://web-dashboard:3000` | Web dashboard URL |
| `RATE_LIMIT_PER_MIN` | `100` | Requests per minute per IP |
| `JWT_SECRET_KEY` | `dev_jwt_secret_key...` | JWT signing key |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `REDIS_URL` | `redis://redis:6379/0` | Redis for rate limiting |

### Docker Configuration

```yaml
api-gateway:
  image: api-gateway:latest
  ports:
    - "8080:8080"
  environment:
    - CORS_ALLOWED_ORIGINS=http://localhost:3000
    - RATE_LIMIT_PER_MIN=100
    - JWT_SECRET_KEY=${JWT_SECRET_KEY}
  depends_on:
    - redis
    - user-service
```

---

## Security Features

### 1. Token Validation

- JWT signature verification
- Token type checking (access vs refresh)
- Expiration validation

### 2. Zone-Level Authorization

- Users can only modify their own zones
- System zones (yaml, no owner) are read-only
- Admins can modify any zone

### 3. Rate Limiting

- Prevents abuse and DoS attacks
- Per-IP sliding window
- Configurable limits

### 4. CORS Protection

- Only allowed origins can access
- Configurable via environment

### 5. Request Sanitization

- Headers forwarded with original client IP
- X-Forwarded-For header added

---

## Monitoring

### Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `api_gateway_http_requests_total` | Counter | method, path, status | Total requests |
| `api_gateway_request_duration_seconds` | Histogram | method, path | Request latency |

### Health Check

```bash
curl http://localhost:8080/health
```

### Grafana Integration

Import the API Gateway dashboard to visualize:
- Requests per second
- Error rate
- Latency percentiles
- Top endpoints

---

## Example Usage

### Authentication Flow

```bash
# 1. Register
curl -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secret", "full_name": "John"}'

# 2. Login
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secret"}'

# Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}

# 3. Use access token
curl http://localhost:8080/v1/zones \
  -H "Authorization: Bearer eyJ..."

# 4. Refresh token (when access expires)
curl -X POST http://localhost:8080/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJ..."}'
```

### Making Predictions

```bash
curl -X POST http://localhost:8080/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "zone_id": "2",
    "sensor_id": "2-s1",
    "features": [45.2, 22.5]
  }'
```

### Managing Zones

```bash
# Get zones (requires auth)
curl http://localhost:8080/v1/zones \
  -H "Authorization: Bearer {access_token}"

# Create zone (requires auth)
curl -X POST http://localhost:8080/v1/zones \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{"zone_name": "Garden", "soil_type": "loam", "crop_type": "tomatoes", "moisture_min": 30, "moisture_max": 60}'
```

---

## Error Handling

| Error | Status Code | Description |
|-------|-------------|-------------|
| Invalid token | 401 | JWT expired or invalid |
| Missing auth | 401 | No Authorization header |
| Rate limited | 429 | Too many requests |
| Zone access denied | 403 | Not zone owner |
| System zone modify | 403 | System zone is read-only |
| Route not found | 404 | Unknown path |
| Service unavailable | 502 | Upstream service error |

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Framework | FastAPI + Uvicorn |
| Authentication | JWT (access + refresh tokens) |
| Authorization | Zone-level ownership |
| Rate Limiting | Redis sliding window (100/min) |
| Routing | Path-based proxy to 9 services |
| CORS | Configurable allowed origins |
| Monitoring | Prometheus metrics |
| Port | 8080 |

The API Gateway provides a unified entry point with authentication, authorization, and rate limiting for all Smart Irrigation services.


═══════════════════════════════════════════════════════════════════

SECTION: User Service & Authentication

# User Service Documentation

## Overview

The User Service provides:
- **User Authentication** - Registration, login, JWT tokens
- **Zone Management** - CRUD operations for irrigation zones
- **Data APIs** - Sensor readings, predictions, irrigation events
- **Access Control** - Role-based permissions (admin vs user)

**Location:** `services/user-service/src/`

**Port:** 5005

---

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              USER SERVICE                                       │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        FastAPI Application                             │   │
│  │                                                                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │   │
│  │  │   Auth      │  │   Users     │  │   Zones     │  │  Data     │  │   │
│  │  │  Endpoints  │  │  Endpoints  │  │  Endpoints  │  │  APIs     │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │   │
│  │                                                                          │   │
│  │  ┌──────────────────────────────────────────────────────────────────┐   │   │
│  │  │                    Authentication Layer                         │   │   │
│  │  │  - Password hashing (bcrypt)                                    │   │   │
│  │  │  - JWT token creation/validation                              │   │   │
│  │  │  - Token blacklist (Redis)                                    │   │   │
│  │  │  - Account lockout                                            │   │   │
│  │  └──────────────────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                    Prometheus Metrics                                    │   │
│  │                                                                          │   │
│  │  user_service_http_requests_total                                      │   │
│  │  user_service_request_duration_seconds                                 │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    PostgreSQL   │    │     Redis      │    │    API Gateway │
│                 │    │                 │    │                │
│  - users       │    │  - Token       │    │  - Proxied     │
│  - zones       │    │    blacklist   │    │    requests    │
│  - sensor_*    │    │  - Auth        │    │                │
│  - model_*     │    │    lockouts    │    │                │
│  - irrigation_ │    │                 │    │                │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## Authentication

### Registration

```bash
POST /register
{
  "email": "user@example.com",
  "password": "secretpassword",
  "full_name": "John Doe"
}
```

**Response:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_admin": false,
  "created_at": "2026-05-03T12:00:00"
}
```

### Login

```bash
POST /login
{
  "email": "user@example.com",
  "password": "secretpassword"
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### Token Refresh

```bash
POST /refresh
{
  "refresh_token": "eyJ..."
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### Security Features

#### Password Hashing
- Algorithm: bcrypt
- Rounds: 12 (configurable)

#### JWT Tokens

| Token Type | Expiry | Purpose |
|------------|--------|---------|
| Access | 15 minutes | API authentication |
| Refresh | 7 days | Get new access token |

#### Account Lockout
- Max failed attempts: 5 (configurable)
- Lockout duration: 15 minutes (configurable)
- Stored in Redis with TTL

#### Token Blacklist
- Used for token rotation
- Stored in separate Redis DB
- Automatically expires when token expires

---

## User Management

### Get Current User

```bash
GET /users/me
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_admin": false,
  "created_at": "2026-05-03T12:00:00"
}
```

### Update Current User

```bash
PUT /users/me
{
  "full_name": "Jane Doe",
  "password": "newpassword"
}
```

### List Users (Admin only)

```bash
GET /users
Authorization: Bearer {admin_access_token}
```

### Delete User (Admin only)

```bash
DELETE /users/{user_id}
```

---

## Zone Management

### Create Zone

```bash
POST /v1/zones
Authorization: Bearer {access_token}
{
  "zone_name": "Garden",
  "soil_type": "loam",
  "crop_type": "tomatoes",
  "moisture_min": 30,
  "moisture_max": 60
}
```

**Or with custom zone_id:**
```json
{
  "zone_id": "garden-1",
  "zone_name": "Garden",
  ...
}
```

### List Zones

```bash
GET /v1/zones
```

### Get Zone

```bash
GET /v1/zones/{zone_id}
```

### Update Zone

```bash
PUT /v1/zones/{zone_id}
{
  "zone_name": "Updated Name",
  "moisture_min": 25
}
```

### Delete Zone

```bash
DELETE /v1/zones/{zone_id}
```

### Assign Zone to User (Admin only)

```bash
POST /v1/zones/{zone_id}/assign
{
  "owner_id": "user-uuid"
}
```

---

## Data APIs

### Sensor Readings

```bash
# Last 24 hours
GET /v1/zones/{zone_id}/sensors

# Last N hours
GET /v1/zones/{zone_id}/sensors?hours=48
```

**Response:**
```json
[
  {
    "timestamp": "2026-05-03T12:00:00",
    "sensor_id": "2-s1",
    "moisture": 45.2,
    "temperature": 22.5
  },
  ...
]
```

### Latest Sensor Readings

```bash
GET /v1/zones/{zone_id}/sensors/latest
```

### Predictions

```bash
GET /v1/zones/{zone_id}/predictions
```

### Irrigation Events

```bash
# Zone events
GET /v1/zones/{zone_id}/irrigation

# Recent events (all zones)
GET /v1/irrigation/recent
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | `dev_jwt_secret_key` | JWT signing key |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_ACCESS_EXPIRE_MIN` | `15` | Access token expiry (minutes) |
| `JWT_REFRESH_EXPIRE_DAYS` | `7` | Refresh token expiry (days) |
| `BCRYPT_ROUNDS` | `12` | Password hashing rounds |
| `AUTH_MAX_ATTEMPTS` | `5` | Max failed login attempts |
| `AUTH_LOCKOUT_MINUTES` | `15` | Lockout duration |
| `REDIS_URL` | `redis://redis:6379/0` | Main Redis DB |
| `REDIS_TOKEN_BLACKLIST_URL` | `redis://redis:6379/1` | Token blacklist DB |

### Docker Configuration

```yaml
user-service:
  image: user-service:latest
  ports:
    - "5005:5005"
  environment:
    - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    - REDIS_URL=redis://redis:6379/0
    - REDIS_TOKEN_BLACKLIST_URL=redis://redis:6379/1
  depends_on:
    - timescaledb
    - redis
```

---

## Database Schema

### users Table

```sql
CREATE TABLE users (
    user_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email        VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name    VARCHAR(255),
    is_admin     BOOLEAN DEFAULT FALSE,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
```

### zones Table

```sql
CREATE TABLE zones (
    zone_id       VARCHAR(50) PRIMARY KEY,
    zone_name    VARCHAR(200) NOT NULL,
    soil_type    VARCHAR(50) NOT NULL,
    crop_type    VARCHAR(50),
    owner_id     UUID REFERENCES users(user_id),
    source       VARCHAR(20) NOT NULL,  -- 'api' or 'yaml'
    moisture_min FLOAT NOT NULL,
    moisture_max FLOAT NOT NULL,
    active       BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Access Control

### Role-Based Permissions

| Action | User | Admin |
|--------|------|-------|
| Register | ✅ | - |
| Login | ✅ | - |
| View own profile | ✅ | ✅ |
| Update own profile | ✅ | ✅ |
| List all users | - | ✅ |
| Delete user | - | ✅ |
| Create zone | ✅ | ✅ |
| Update own zones | ✅ | ✅ |
| Update any zone | - | ✅ |
| Delete zone | ✅ (own) | ✅ |
| Assign zone | - | ✅ |
| View zone data | ✅ (own) | ✅ |

### Ownership Validation

- Users can only modify zones they own
- System zones (source='yaml', no owner) are read-only
- Admin can modify any zone

---

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `user_service_http_requests_total` | Counter | Total requests by method, path, status |
| `user_service_request_duration_seconds` | Histogram | Request latency |

---

## API Endpoints Summary

### Authentication
| Method | Endpoint | Auth | Description |
|--------|-----------|------|-------------|
| POST | /register | No | Register new user |
| POST | /login | No | Login, get tokens |
| POST | /refresh | No | Refresh tokens |

### Users
| Method | Endpoint | Auth | Description |
|--------|-----------|------|-------------|
| GET | /users/me | Yes | Get current user |
| PUT | /users/me | Yes | Update current user |
| GET | /users | Admin | List all users |
| DELETE | /users/{id} | Admin | Delete user |

### Zones
| Method | Endpoint | Auth | Description |
|--------|-----------|------|-------------|
| POST | /v1/zones | Yes | Create zone |
| GET | /v1/zones | No | List zones |
| GET | /v1/zones/{id} | No | Get zone |
| PUT | /v1/zones/{id} | Owner | Update zone |
| DELETE | /v1/zones/{id} | Owner | Delete zone |
| POST | /v1/zones/{id}/assign | Admin | Assign zone to user |

### Data
| Method | Endpoint | Description |
|--------|-----------|-------------|
| GET | /v1/zones/{id}/sensors | Sensor readings |
| GET | /v1/zones/{id}/sensors/latest | Latest readings |
| GET | /v1/zones/{id}/predictions | Model predictions |
| GET | /v1/zones/{id}/irrigation | Irrigation events |
| GET | /v1/irrigation/recent | Recent events |

---

## Example Usage

### Register and Login

```bash
# Register
curl -X POST http://localhost:5005/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secret", "full_name": "John"}'

# Login
curl -X POST http://localhost:5005/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secret"}'

# Get access token from response, use in subsequent requests
export TOKEN="eyJ..."

# Get own profile
curl http://localhost:5005/users/me -H "Authorization: Bearer $TOKEN"
```

### Zone Management

```bash
# Create zone
curl -X POST http://localhost:5005/v1/zones \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"zone_name": "Garden", "soil_type": "loam", "crop_type": "tomatoes", "moisture_min": 30, "moisture_max": 60}'

# Get zone data
curl http://localhost:5005/v1/zones/garden-1/sensors?hours=24

# Get predictions
curl http://localhost:5005/v1/zones/garden-1/predictions

# Get irrigation events
curl http://localhost:5005/v1/zones/garden-1/irrigation
```

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Framework | FastAPI |
| Auth | JWT + bcrypt |
| Token Storage | Redis (blacklist + lockout) |
| Database | PostgreSQL (users, zones) |
| Rate Limiting | Redis-based lockout |
| Port | 5005 |

The User Service provides complete user authentication, zone management, and data access APIs for the Smart Irrigation System.


═══════════════════════════════════════════════════════════════════

SECTION: Sensor Simulator

# Sensor Simulator Documentation

## Overview

The Sensor Simulator generates realistic synthetic sensor data for the Smart Irrigation System. It simulates:
- **Soil moisture** readings with realistic depletion patterns
- **Temperature** readings with daily variation
- **Soil-specific behavior** based on soil type
- **Irrigation events** (responds to irrigation triggers from the controller)

**Location:** `services/sensor-simulator/src/`

---

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           SENSOR SIMULATOR                                      │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                      Main Loop (every 10 seconds)                        │   │
│  │                                                                          │   │
│  │   1. Check Redis for irrigation events                                  │   │
│  │   2. Sync zones from User Service API (every 60 sec)                     │   │
│  │   3. Generate readings for all active sensors                            │   │
│  │   4. Publish to Redis channel "sensor:data"                              │   │
│  │   5. Sleep 10 seconds                                                    │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                    Zone & Sensor Management                            │   │
│  │                                                                          │   │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                   │   │
│  │   │   Zone 1   │  │   Zone 2    │  │   Zone 3    │                   │   │
│  │   │             │  │             │  │             │                   │   │
│  │   │ - s1        │  │ - s1        │  │ - s1        │                   │   │
│  │   │ - s2        │  │ - s2        │  │ - s2        │                   │   │
│  │   └─────────────┘  └─────────────┘  └─────────────┘                   │   │
│  │                                                                          │   │
│  │   Each zone: 2 sensors (for redundancy simulation)                     │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  User Service   │    │     Redis      │    │   Irrigation   │
│                 │    │                 │    │   Controller   │
│  /v1/zones      │    │  sensor:data   │    │                 │
│  (get active    │    │   (output)     │    │irrigation:     │
│   zones)        │    │                 │    │ triggered      │
│                 │    │                 │    │   (input)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## Components

### 1. SensorGenerator Class

Generates realistic sensor readings based on soil type.

**Key Properties:**
- `current_moisture` - Current moisture level (0-100%)
- `current_temperature` - Current temperature (°C)
- `depletion_base` - Base rate of moisture loss per tick
- `retention_variance` - Random variation in depletion
- `irrigating_ticks` - Counter for active irrigation

**Methods:**
```python
def generate_reading(self) -> SensorReading:
    # 1. Update temperature (slight warming trend)
    temp_delta = random.uniform(-0.2, 1.5)
    self.current_temperature = max(10.0, min(40.0, self.current_temperature + temp_delta))

    # 2. Calculate moisture depletion
    temp_factor = max(0.5, self.current_temperature / 20.0)
    demo_multiplier = 10.0  # Aggressive for demo
    depletion = (self.depletion_base + random_variance) * temp_factor * demo_multiplier

    # 3. Apply irrigation or depletion
    if self.irrigating_ticks > 0:
        self.current_moisture += random.uniform(5.0, 10.0)  # Increase
        self.irrigating_ticks -= 1
    else:
        self.current_moisture -= depletion  # Decrease

    # 4. Add sensor noise and return
    noise = random.uniform(-0.5, 0.5)
    return SensorReading(...)
```

### 2. Main Loop

Runs continuously, performing these tasks:

```python
while True:
    # 1. Check for irrigation events from Redis
    message = pubsub.get_message(IRRIGATION_CHANNEL)
    if message:
        zone_id = message["zone_id"]
        generators[zone_id].trigger_irrigation()

    # 2. Sync zones from API (every 60 seconds)
    if time elapsed > 60:
        active_zones = get_zones_from_api()
        add_new_generators()
        remove_inactive_generators()

    # 3. Generate and publish readings
    for each generator:
        reading = generate_reading()
        r.publish("sensor:data", reading.json())

    sleep(10 seconds)
```

---

## Soil Type Behavior

Each soil type has different moisture characteristics:

| Soil Type | Depletion Base | Initial Moisture | Behavior |
|------------|----------------|-------------------|----------|
| **Sand** | 0.6 | 35-45% | Fast drainage, low retention |
| **Sandy Loam** | 0.45 | 40-50% | Moderate drainage |
| **Loam** | 0.25 | 45-55% | Balanced |
| **Silty Loam** | 0.2 | 48-58% | Good retention |
| **Silt** | 0.18 | 50-60% | Slow drainage |
| **Clay Loam** | 0.15 | 52-62% | High retention |
| **Clay** | 0.1 | 55-65% | Very slow drainage |
| **Peat** | 0.05 | 60-70% | Extremely high retention |

**Moisture Depletion Formula:**
```
depletion = (depletion_base ± variance) × temperature_factor × demo_multiplier
```

---

## Data Model

### SensorReading

```python
class SensorReading(BaseModel):
    zone_id: str        # Zone identifier (e.g., "2")
    sensor_id: str       # Sensor identifier (e.g., "2-s1")
    moisture: float      # Moisture percentage (0-100)
    temperature: float  # Temperature in Celsius
    timestamp: str      # ISO 8601 timestamp
```

**Example JSON:**
```json
{
  "zone_id": "2",
  "sensor_id": "2-s1",
  "moisture": 48.32,
  "temperature": 22.45,
  "timestamp": "2026-05-03T12:00:00.123456Z"
}
```

---

## Output

### Redis Channel

The simulator publishes to `sensor:data` channel:

```python
r.publish("sensor:data", reading.model_dump_json())
```

### Consumer

The `data-ingestion` service consumes this channel and processes the data.

---

## Irrigation Response

When the irrigation controller triggers an irrigation event:

```
Irrigation Controller → Redis (irrigation:triggered)
        │
        ▼
Sensor Simulator subscribes to irrigation:triggered
        │
        ▼
For each sensor in zone:
    trigger_irrigation()  # Sets irrigating_ticks = 10
        │
        ▼
Next 10 readings:
    moisture += random(5.0, 10.0)  # Increase rapidly
    temperature -= random(0.5, 1.5)  # Slight cooling
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `USER_SERVICE_URL` | `http://user-service:5005` | User service API |
| `SENSOR_PUBLISH_INTERVAL` | `10.0` | Seconds between readings |
| `REDIS_CHANNEL_SENSOR_DATA` | `sensor:data` | Output channel |
| `REDIS_CHANNEL_IRRIGATION_TRIGGERED` | `irrigation:triggered` | Input channel |

### Docker Configuration

```yaml
sensor-simulator:
  image: sensor-simulator:latest
  environment:
    - REDIS_URL=redis://redis:6379/0
    - USER_SERVICE_URL=http://user-service:5005
    - SENSOR_PUBLISH_INTERVAL=10.0
  depends_on:
    - redis
    - user-service
```

---

## Simulation Logic

### Temperature Simulation

```python
# Slight warming trend with random variation
temp_delta = random.uniform(-0.2, 1.5)
self.current_temperature = max(10.0, min(40.0, self.current_temperature + temp_delta))
```

- Range: 10°C to 40°C
- Trend: Slight warming
- Variation: -0.2 to +1.5 per tick

### Moisture Simulation

```python
# Depletion based on soil type and temperature
temp_factor = max(0.5, self.current_temperature / 20.0)
depletion = depletion_base * temp_factor * demo_multiplier

# 10x multiplier for demo (makes irrigation trigger faster)
# In production, use multiplier=1.0
```

### Irrigation Effect

```python
if self.irrigating_ticks > 0:
    # Rapid moisture increase
    self.current_moisture += random.uniform(5.0, 10.0)
    # Slight cooling
    self.current_temperature -= random.uniform(0.5, 1.5)
    self.irrigating_ticks -= 1
```

### Natural Variation

```python
# 0.1% chance of natural moisture increase (rain)
if random.random() < 0.001:
    self.current_moisture += random.uniform(2.0, 5.0)
```

### Sensor Noise

```python
# Add realistic sensor noise
noise = random.uniform(-0.5, 0.5)
reported_moisture = current_moisture + noise
```

---

## Features

### 1. Dynamic Zone Discovery

The simulator fetches active zones from the User Service API every 60 seconds:
- New zones are automatically added
- Removed zones are automatically cleaned up

### 2. Multi-Sensor Per Zone

Each zone gets 2 sensors (s1 and s2) for redundancy:
- Independent moisture readings
- Simulates real-world sensor network

### 3. Soil-Specific Behavior

Different soil types have:
- Different depletion rates
- Different initial moisture levels
- Realistic moisture retention characteristics

### 4. Irrigation Response

When irrigation triggers:
- Moisture rapidly increases
- Temperature slightly decreases
- Continues for 10 ticks (100 seconds with 10s interval)

### 5. Realistic Variation

- Random noise on readings
- Natural moisture variation (rare rain events)
- Temperature trends

---

## Monitoring

### Log Messages

```
INFO - Starting sensor simulator... Connecting to Redis at redis://redis:6379/0
INFO - Successfully connected to Redis.
INFO - Subscribed to irrigation channel: irrigation:triggered
INFO - Syncing zones from API...
INFO - Initialized sensors for new zone: 2 (Soil: loam)
INFO - Irrigation triggered for zone 2. Increasing moisture!
DEBUG - Published 6 readings.
```

### Check Active Sensors

```python
# In the simulator code
generators = {
    "1": [sensor_s1, sensor_s2],
    "2": [sensor_s1, sensor_s2],
    "3": [sensor_s1, sensor_s2],
}
```

---

## Testing

### Manual Simulation

```bash
# Check Redis for sensor data
docker exec redis redis-cli
> SUBSCRIBE sensor:data

# Check irrigation channel
> SUBSCRIBE irrigation:triggered
```

### Batch Generation

For testing, use the batch generator:

```bash
# Generate 100 readings with 30-second interval
make generate-data count=100 interval=30

# Simulate 12 hours (1440 data points)
make fast-forward
```

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Input | User Service API (active zones) |
| Output | Redis `sensor:data` channel |
| Irrigation Input | Redis `irrigation:triggered` channel |
| Per Zone | 2 sensors (redundancy) |
| Tick Interval | 10 seconds (configurable) |
| Soil Types | 8 types (sand to peat) |
| Response | Moisture increases for 10 ticks after irrigation |

The Sensor Simulator provides realistic, dynamic sensor data that drives the entire Smart Irrigation system's ML pipeline and automated irrigation logic.


═══════════════════════════════════════════════════════════════════

SECTION: Data Ingestion Service

# Data Ingestion Service

## Overview

The Data Ingestion Service is a real-time data pipeline that consumes sensor readings from Redis and persists them to PostgreSQL (TimescaleDB). It performs validation, anomaly detection, and forwards processed data to downstream services.

**Location:** `services/data-ingestion/`

**Port:** 8001

---

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          SENSOR SIMULATOR                                      │
│                                                                                 │
│  Produces sensor data to Redis channel: sensor:data                           │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    DATA INGESTION SERVICE (8001)                              │
│                                                                                 │
│  ┌─────────────────────┐    ┌─────────────────────┐    ┌──────────────────┐   │
│  │   Redis Consumer    │───▶│    Validator        │───▶│   DB Writer      │   │
│  │                     │    │                     │    │                  │   │
│  │ - Subscribe         │    │ - Zone bounds       │    │ - sensor_readings│   │
│  │ - Parse JSON        │    │ - Range validation  │    │ - data_quality   │   │
│  │ - Error handling    │    │ - Anomaly detection │    │   _events        │   │
│  └─────────────────────┘    └─────────────────────┘    └──────────────────┘   │
│           │                              │                       │            │
│           ▼                              ▼                       ▼            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      Metrics & Health                                  │   │
│  │                                                                          │   │
│  │  /health     - Status + stats                                          │   │
│  │  /metrics    - Prometheus metrics                                      │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    Downstream Services                                         │
│                                                                                 │
│  - irrigation-controller: listens on ingestion:processed                     │
│  - Airflow: triggered for prediction updates                                   │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                      DATABASE (TimescaleDB)                                    │
│                                                                                 │
│  Tables:                                                                       │
│  - sensor_readings     - Valid sensor readings with timestamps                │
│  - data_quality_events - Anomaly records for monitoring                       │
│  - zones               - Zone configuration with min/max plausible bounds     │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### 1. Sensor Data Input

The service subscribes to Redis channel `sensor:data` and expects JSON messages:

```json
{
  "zone_id": "zone-001",
  "sensor_id": "sensor-001",
  "timestamp": "2026-05-03T10:30:00Z",
  "moisture": 45.2,
  "temperature": 22.5
}
```

**Legacy format (single sensor):**
```json
{
  "zone_id": "zone-001",
  "sensor_id": "sensor-001",
  "timestamp": "2026-05-03T10:30:00Z",
  "type": "moisture",
  "value": 45.2
}
```

### 2. Validation

The validator checks each reading against zone-specific bounds:

1. **Zone existence** - Reject if zone_id not in database
2. **Range validation** - Check moisture/temperature against `min_plausible` and `max_plausible`
3. **Severity assignment** - Warning for minor violations, critical for severe (>150% of max)

### 3. Database Write

- **Valid readings** → `sensor_readings` table
- **Anomalies** → `data_quality_events` table with severity and details

### 4. Downstream Notification

After processing, publishes to `ingestion:processed` channel:

```json
{
  "zone_id": "zone-001",
  "sensor_id": "sensor-001",
  "timestamp": "2026-05-03T10:30:00Z",
  "valid": true,
  "sensor_type": "combined"
}
```

---

## Components

### main.py

FastAPI application with lifespan management:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    await consumer.connect()
    consumer_task = asyncio.create_task(consumer.run())
    yield
    consumer._running = False
    consumer_task.cancel()
    await consumer.disconnect()
    await db.disconnect()
```

**Endpoints:**
- `GET /health` - Health check with stats
- `GET /metrics` - Prometheus metrics

### redis_consumer.py

Async Redis consumer using pubsub:

```python
async def run(self) -> None:
    self._running = True
    try:
        async for message in self._pubsub.listen():
            if message.get("type") == "message":
                await self._process_one(message)
    except asyncio.CancelledError:
        pass
```

### validator.py

Validates readings against zone bounds:

```python
async def validate_reading(sensor_data: Dict[str, Any]) -> ValidationResult:
    bounds = await get_zone_bounds(zone_id)
    # Check moisture and temperature against min_plausible/max_plausible
    return ValidationResult(is_valid=..., anomalies=..., sensor_type=...)
```

### db_writer.py

Database write operations:

```python
async def insert_sensor_reading(
    zone_id: str,
    sensor_id: str,
    timestamp: Any,
    sensor_type: str,
    moisture: float | None = None,
    temperature: float | None = None,
) -> None
```

### database.py

Connection pool and statistics:

```python
@dataclass
class IngestionStats:
    total_processed: int
    valid_readings: int
    anomalies_flagged: int
    last_processed_at: Optional[datetime]
    errors: int
```

---

## Database Schema

### sensor_readings

```sql
CREATE TABLE sensor_readings (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    zone_id UUID NOT NULL,
    sensor_id UUID NOT NULL,
    moisture DOUBLE PRECISION NOT NULL,
    temperature DOUBLE PRECISION,
    -- Hypertable for time-series optimization
);

SELECT create_hypertable('sensor_readings', 'timestamp');
```

### data_quality_events

```sql
CREATE TABLE data_quality_events (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    zone_id UUID NOT NULL,
    sensor_id UUID NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_value DOUBLE PRECISION,
    expected_min DOUBLE PRECISION,
    expected_max DOUBLE PRECISION,
    severity VARCHAR(20) DEFAULT 'warning',
    details TEXT
);
```

### zones

```sql
ALTER TABLE zones ADD COLUMN min_plausible JSONB;
ALTER TABLE zones ADD COLUMN max_plausible JSONB;

-- Example configuration:
UPDATE zones SET 
    min_plausible = '{"moisture": 0, "temperature": -10}',
    max_plausible = '{"moisture": 100, "temperature": 50}'
WHERE zone_id = 'zone-001';
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_INGESTION_PORT` | 8001 | Service port |
| `REDIS_URL` | redis://redis:6379/0 | Redis connection |
| `REDIS_CHANNEL_SENSOR_DATA` | sensor:data | Input channel |
| `REDIS_CHANNEL_INGESTION_PROCESSED` | ingestion:processed | Output channel |
| `DATABASE_URL` | postgresql://...@timescaledb:5432/irrigation_db | PostgreSQL connection |
| `DB_POOL_MIN_SIZE` | 2 | Connection pool min |
| `DB_POOL_MAX_SIZE` | 10 | Connection pool max |

---

## Metrics

Prometheus metrics exposed at `/metrics`:

| Metric | Description |
|--------|-------------|
| `data_ingestion_total_processed` | Total messages processed |
| `data_ingestion_valid_readings` | Valid readings persisted |
| `data_ingestion_anomalies_flagged` | Anomalies detected |
| `data_ingestion_errors_total` | Processing errors |

---

## Anomaly Types

| Event Type | Severity | Description |
|------------|----------|-------------|
| `unknown_zone` | critical | Zone ID not in database |
| `below_min_plausible_moisture` | warning | Moisture below zone minimum |
| `above_max_plausible_moisture` | warning/critical | Moisture above zone maximum |
| `below_min_plausible_temperature` | warning | Temperature below zone minimum |
| `above_max_plausible_temperature` | warning/critical | Temperature above zone maximum |

---

## Docker Compose

```yaml
data-ingestion:
  image: data-ingestion:latest
  ports:
    - "8001:8001"
  environment:
    - REDIS_URL=redis://redis:6379/0
    - DATABASE_URL=postgresql://irrigation_user:changeme@timescaledb:5432/irrigation_db
  depends_on:
    - redis
    - timescaledb
```

---

## Monitoring

### Health Check

```bash
curl http://localhost:8001/health
```

Response:
```json
{
  "status": "healthy",
  "stats": {
    "total_processed": 1500,
    "valid_readings": 1480,
    "anomalies_flagged": 18,
    "last_processed_at": "2026-05-03T10:30:00Z",
    "errors": 2
  }
}
```

### Prometheus Metrics

```bash
curl http://localhost:8001/metrics
```

---

## Integration with Other Services

### irrigation-controller

Subscribes to `ingestion:processed` channel for real-time sensor updates:

```python
# When valid reading arrives, trigger irrigation check
if valid and moisture < threshold:
    trigger_irrigation(zone_id)
```

### Airflow DAG Trigger

When new sensor data arrives, Airflow DAG can:
1. Update feature store
2. Run prediction pipeline
3. Update model features

---

## Error Handling

| Error Type | Handling |
|------------|----------|
| JSON decode error | Log error, increment stats, continue |
| Database error | Log error, increment error counter |
| Invalid zone | Create anomaly event (if zone exists), skip insertion |
| Redis disconnect | Service health check fails, k8s restarts |

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Framework | FastAPI + asyncio |
| Language | Python |
| Input | Redis pubsub (sensor:data) |
| Output | PostgreSQL (TimescaleDB) |
| Validation | Zone-based min/max plausible |
| Anomaly Tracking | data_quality_events table |
| Port | 8001 |
| Dependencies | Redis, TimescaleDB |

The Data Ingestion Service is the backbone of real-time sensor data processing, ensuring data quality while feeding downstream services for irrigation control and ML predictions.


═══════════════════════════════════════════════════════════════════

SECTION: Feature Engineering

# Feature Engineering Documentation

## Overview

The Feature Engineering service computes rolling metrics and aggregations from raw sensor data. It operates in two modes:

1. **Streaming Mode** - Real-time feature computation triggered by each sensor reading
2. **Batch Mode** - Periodic batch processing (hourly/daily rollups + rolling features)

The service processes raw sensor readings and stores computed features in the `feature_references` table for use by the model server.

**Location:** `services/feature-engineering/src/`

**Port:** 8004

---

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         FEATURE ENGINEERING SERVICE                             │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        FastAPI Application                               │   │
│  │                                                                          │   │
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐  │   │
│  │  │   /health   │   │  /metrics   │   │/trigger-   │   │             │  │   │
│  │  │             │   │             │   │   batch     │   │             │  │   │
│  │  └─────────────┘   └─────────────┘   └──────┬──────┘   │             │  │   │
│  │                                           │          │             │  │   │
│  │                                           ▼          │             │  │   │
│  │  ┌────────────────────────────────────────────────┐ │             │  │   │
│  │  │                  Redis Consumer                │ │             │  │   │
│  │  │            (listens to ingestion:processed)    │ │             │  │   │
│  │  └────────────────────────┬───────────────────────┘ │             │  │   │
│  │                           │                           │             │   │   │
│  │  ┌────────────────────────┴───────────────────────┐ │             │   │   │
│  │  │              Background Batch Scheduler        │ │             │   │   │
│  │  │              (runs every 300 seconds)         │ │             │   │   │
│  │  └────────────────────────┬───────────────────────┘ │             │   │   │
│  └───────────────────────────┼─────────────────────────────────────┘   │   │
│                              │                                                  │
│  ┌───────────────────────────┼──────────────────────────────────────────┐   │
│  │                    Core Logic                                        │   │
│  │                                                                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │   │
│  │  │   ETL       │  │   Feature    │  │   Soil      │  │  Database  │  │   │
│  │  │  (cleaning) │◄─│  Computation │◄─│   Profiles  │  │   Writer   │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │   │
│  └───────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                       │
│                                                                                 │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐          │
│  │ Redis: ingestion │    │   TimescaleDB    │    │     Zones       │          │
│  │   :processed    │    │ sensor_readings  │    │   (soil_type)   │          │
│  │  (streaming)   │    │                  │    │                 │          │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘          │
└───────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              OUTPUT                                             │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                         TimescaleDB                                      │  │
│  │                                                                          │  │
│  │  feature_references ◄─── Rolling window features (30m, 1h, 3h, 24h)    │  │
│  │  hourly_rollup      ◄─── Hourly aggregations                            │  │
│  │  daily_rollup      ◄─── Daily aggregations                              │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                         Redis Channels                                   │  │
│  │                                                                          │  │
│  │  features:computed ──► Published after each computation                 │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Operating Modes

### 1. Streaming Mode (Real-time)

Triggered by each sensor reading via Redis pub/sub:

```
Data Ingestion publishes to "ingestion:processed"
        │
        ▼
Feature Engineering subscribes and processes
        │
        ▼
Computes rolling features for the zone/sensor
        │
        ▼
Publishes to "features:computed"
```

**Redis Channels:**
- Input: `ingestion:processed` (listens for new sensor readings)
- Output: `features:computed` (publishes computed features)

### 2. Batch Mode (Periodic)

Runs every 5 minutes (configurable):

```
Timer triggers every 300 seconds
        │
        ▼
For each active sensor:
        │
        ├─► Hourly rollup (avg, min, max, std of last hour)
        │
        ├─► Daily rollup (avg, min, max, std of last day)
        │
        └─► Rolling features (30m, 1h, 3h, 24h windows)
```

---

## Feature Computation

### Rolling Window Features

The service computes features for configurable windows: `30m`, `1h`, `3h`, `24h`

**Moisture Features:**
| Feature | Description |
|---------|-------------|
| `mean_moisture` | Average moisture over window |
| `std_moisture` | Standard deviation of moisture |
| `min_moisture` | Minimum moisture in window |
| `max_moisture` | Maximum moisture in window |
| `variance_moisture` | Variance of moisture |
| `rate_of_change_moisture` | Change from start to end |
| `moisture_range` | max - min |
| `soil_water_retention_index` | Mean moisture × soil retention factor |
| `soil_dryness_index` | (100 - mean moisture) × drainage factor |

**Temperature Features:**
| Feature | Description |
|---------|-------------|
| `mean_temperature` | Average temperature |
| `std_temperature` | Standard deviation |
| `min_temperature` | Minimum |
| `max_temperature` | Maximum |
| `variance_temperature` | Variance |
| `rate_of_change_temperature` | Change over window |

**Combined Features:**
| Feature | Description |
|---------|-------------|
| `evapotranspiration_proxy` | Temperature × (100 - moisture) / 100 |

### Soil Type Profiles

Features are adjusted based on soil type:

```python
SOIL_TYPE_FACTORS = {
    "sand": {"water_retention_factor": 0.7, "drainage_factor": 1.3},
    "sandy_loam": {"water_retention_factor": 0.85, "drainage_factor": 1.15},
    "loam": {"water_retention_factor": 1.0, "drainage_factor": 1.0},
    "silty_loam": {"water_retention_factor": 1.05, "drainage_factor": 0.98},
    "silt": {"water_retention_factor": 1.08, "drainage_factor": 0.95},
    "clay_loam": {"water_retention_factor": 1.12, "drainage_factor": 0.9},
    "clay": {"water_retention_factor": 1.2, "drainage_factor": 0.8},
    "peat": {"water_retention_factor": 1.5, "drainage_factor": 0.6},
}
```

---

## Data Cleaning (ETL)

Before computing features, raw data goes through cleaning:

### 1. Deduplication
```python
def _deduplicate(records):
    # Average duplicate readings at same timestamp
    # Multiple sensors reporting same zone/timestamp
```

### 2. Null Handling
```python
def _handle_nulls(records):
    # Forward-fill missing temperature values
    # If temp is null, use previous reading
```

### 3. Outlier Smoothing
```python
def _smooth_outliers(records, threshold=3.0):
    # Cap extreme values using z-score
    # If |value - mean| / std > threshold, replace with mean
    # Default threshold: 3.0 (configurable via OUTLIER_ZSCORE_THRESHOLD)
```

---

## API Endpoints

### GET /health

Health check with stats.

```bash
curl http://localhost:8004/health
```

**Response:**
```json
{
  "status": "healthy",
  "stats": {
    "total_processed": 1500,
    "features_computed": 450,
    "rollups_computed": 12,
    "anomalies_smoothed": 5,
    "errors": 0
  }
}
```

### GET /metrics

Prometheus metrics.

```bash
curl http://localhost:8004/metrics
```

**Metrics:**
- `feature_engineering_total_processed` - Total readings processed
- `feature_engineering_features_computed` - Features computed
- `feature_engineering_rollups_computed` - Rollups computed
- `feature_engineering_anomalies_smoothed` - Outliers smoothed
- `feature_engineering_errors_total` - Errors

### POST /trigger-batch

Manually trigger batch ETL (for testing).

```bash
curl -X POST http://localhost:8004/trigger-batch
```

**Response:**
```json
{
  "status": "batch_completed",
  "stats": {...}
}
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FEATURE_ENGINEERING_PORT` | `8004` | Service port |
| `BATCH_INTERVAL_SECONDS` | `300` | Batch run interval (5 min) |
| `ROLLUP_WINDOWS` | `30m,1h,3h,24h` | Rolling windows |
| `FEATURE_MODEL_VERSION` | `v1` | Model version tag |
| `OUTLIER_ZSCORE_THRESHOLD` | `3.0` | Z-score threshold |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `REDIS_CHANNEL_INGESTION_PROCESSED` | `ingestion:processed` | Input channel |
| `REDIS_CHANNEL_FEATURES_COMPUTED` | `features:computed` | Output channel |

### Docker Configuration

```yaml
feature-engineering:
  image: feature-engineering:latest
  ports:
    - "8004:8004"
  environment:
    - BATCH_INTERVAL_SECONDS=300
    - ROLLUP_WINDOWS=30m,1h,3h,24h
  depends_on:
    - timescaledb
    - redis
```

---

## Output Storage

### feature_references Table

Stores computed rolling features:

```sql
CREATE TABLE feature_references (
    id            BIGSERIAL,
    computed_at   TIMESTAMPTZ NOT NULL,
    zone_id       VARCHAR(50) NOT NULL,
    sensor_id     VARCHAR(50),
    window_size   VARCHAR(20) NOT NULL,  -- 30m, 1h, 3h, 24h
    feature_name  VARCHAR(50) NOT NULL, -- mean_moisture, etc.
    feature_value FLOAT,
    model_version VARCHAR(20),
    PRIMARY KEY (id, computed_at)
);
```

**Example data:**
```
computed_at          | zone_id | sensor_id | window_size | feature_name           | feature_value
---------------------+---------+-----------+-------------+------------------------+-------------
2026-05-03 12:00:00 | 2       | 2-s1      | 30m         | mean_moisture         | 45.2
2026-05-03 12:00:00 | 2       | 2-s1      | 30m         | std_moisture           | 3.1
2026-05-03 12:00:00 | 2       | 2-s1      | 30m         | evapotranspiration_proxy | 12.5
2026-05-03 12:00:00 | 2       | 2-s1      | 1h          | mean_moisture         | 48.7
...
```

### Hourly/Daily Rollups

```sql
-- hourly_rollup table
hour_start, zone_id, sensor_id, avg_moisture, min_moisture, max_moisture, std_moisture, ...

-- daily_rollup table
day_start, zone_id, sensor_id, avg_moisture, min_moisture, max_moisture, std_moisture, ...
```

---

## Integration

### Data Ingestion → Feature Engineering

```
data-ingestion validates sensor reading
        │
        ▼
publishes to "ingestion:processed" (Redis)
        │
        ▼
feature-engineering receives message
        │
        ▼
run_streaming(zone_id, sensor_id)
        │
        ▼
computes rolling features
        │
        ▼
publishes to "features:computed" (Redis)
```

### Airflow DAG → Feature Engineering

Airflow queries `feature_references` when generating predictions:

```python
feature_rows = await conn.fetch(
    """
    SELECT feature_name, window_size, feature_value
    FROM feature_references
    WHERE zone_id = $1 AND sensor_id = $2
    ORDER BY computed_at DESC
    """,
    zone_id, sensor_id,
)
```

---

## Feature Payload

### Serialized Format

When published to Redis or returned by API, features are serialized as:

```json
{
  "mean_moisture_30m": 45.2,
  "std_moisture_30m": 3.1,
  "min_moisture_30m": 40.0,
  "max_moisture_30m": 50.0,
  "mean_moisture_1h": 48.7,
  "evapotranspiration_proxy_30m": 12.5,
  "soil_dryness_index_1h": 51.3,
  ...
}
```

Key format: `{feature_name}_{window_size}`

---

## Monitoring

### Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `feature_engineering_total_processed` | Gauge | Readings processed |
| `feature_engineering_features_computed` | Gauge | Features generated |
| `feature_engineering_rollups_computed` | Gauge | Rollups computed |
| `feature_engineering_anomalies_smoothed` | Gauge | Outliers handled |
| `feature_engineering_errors_total` | Gauge | Error count |

### Health Check

```bash
curl http://localhost:8004/health | jq
```

---

## Testing

### Manual Batch Trigger

```bash
# Trigger batch ETL manually
curl -X POST http://localhost:8004/trigger-batch
```

### Check Recent Features

```sql
-- Query recent features for zone 2
SELECT * FROM feature_references
WHERE zone_id = '2'
ORDER BY computed_at DESC
LIMIT 20;
```

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Framework | FastAPI + Uvicorn |
| Input | Redis (ingestion:processed) + sensor_readings table |
| Processing | Rolling windows (30m, 1h, 3h, 24h) |
| Soil Adjustment | 8 soil type profiles |
| Data Cleaning | Deduplication, null fill, outlier smoothing |
| Output | feature_references table + Redis (features:computed) |
| Modes | Streaming (real-time) + Batch (5-min interval) |
| Port | 8004 |

The Feature Engineering service transforms raw sensor data into ML-ready features, applying soil-type adjustments and data cleaning before storing in TimescaleDB for model consumption.


═══════════════════════════════════════════════════════════════════

SECTION: Feature Engineering Guide

# Feature Engineering Guide

## Core Feature Families
- Rolling moisture aggregates: mean, std, min, max, variance, range
- Rolling temperature aggregates: mean, std, min, max, variance
- Trend features: rate of change for moisture and temperature
- Soil-aware indices: `soil_water_retention_index`, `soil_dryness_index`
- Environmental proxy: `evapotranspiration_proxy`

## Agricultural Intent
- Retention index increases for soils that hold water longer.
- Dryness index increases when average moisture is low and drainage is high.
- Evapotranspiration proxy combines heat and dryness pressure for irrigation relevance.

## Versioning
- Every computed feature row is stored in `feature_references` with `model_version`.
- `FEATURE_MODEL_VERSION` controls the active feature logic tag.



═══════════════════════════════════════════════════════════════════

SECTION: Data Quality Service

# Data Quality Service

## Overview

The Data Quality Service monitors sensor data for malfunctions and anomalies using configurable rules. It evaluates incoming readings in real-time and runs periodic batch scans to detect issues like stuck sensors, sudden jumps, flatlines, and anomalous rates of change.

**Location:** `services/data-quality/`

**Port:** 8005

---

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    DATA INGESTION SERVICE                                       │
│                                                                                 │
│  Publishes to: ingestion:processed                                              │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                   DATA QUALITY SERVICE (8005)                                  │
│                                                                                 │
│  ┌─────────────────────┐    ┌─────────────────────┐    ┌──────────────────┐   │
│  │   Redis Consumer     │───▶│   Quality Engine     │───▶│   Reports API     │   │
│  │                     │    │                     │    │                  │   │
│  │ - Subscribe         │    │ - Stuck value       │    │ - /summary       │   │
│  │ - ingestion:processed    │ - Sudden jump       │    │ - /sensors       │   │
│  │ - Health loop       │    │ - Flatline           │    │ - /hourly        │   │
│  │                     │    │ - Rate of change    │    │ - /rules         │   │
│  └─────────────────────┘    └─────────────────────┘    └──────────────────┘   │
│           │                              │                       │            │
│           ▼                              ▼                       ▼            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      Prometheus Metrics                                 │   │
│  │                                                                          │   │
│  │  /metrics    - Grafana-compatible metrics                               │   │
│  │  /health     - Health check + stats                                     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      DATABASE (TimescaleDB)                                    │
│                                                                                 │
│  Tables:                                                                       │
│  - sensor_readings     - Sensor data to analyze                               │
│  - data_quality_events - Detected anomalies                                   │
│  - quality_rules      - Rule definitions                                      │
│  - sensor_metadata     - Sensor registry                                      │
│  - v_sensor_health     - Materialized view for sensor health                 │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Components

### main.py

FastAPI application with lifespan management:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    await consumer.connect()
    consumer_task = asyncio.create_task(consumer.run())
    batch_task = asyncio.create_task(_batch_scan_loop())
    yield
    # Cleanup
```

**Endpoints:**
- `GET /health` - Health check with stats
- `GET /metrics` - Prometheus metrics
- `GET /quality/reports/summary` - Quality summary
- `GET /quality/reports/sensors` - Sensor health
- `GET /quality/reports/hourly` - Hourly metrics
- `GET /quality/rules` - List active rules
- `PATCH /quality/rules/{rule_id}` - Update rule

### quality_engine.py

Core rule evaluation logic:

```python
_RULE_TYPE_HANDLERS = {
    "stuck_value": _check_stuck_value,
    "sudden_jump": _check_sudden_jump,
    "flatline": _check_flatline,
    "rate_of_change": _check_rate_of_change,
}

async def evaluate_reading(zone_id, sensor_id, timestamp, value, sensor_type):
    # Run all applicable rules against the reading
    return anomalies
```

### redis_consumer.py

Async Redis consumer:

```python
async def run(self) -> None:
    async for message in self._pubsub.listen():
        if message.get("type") == "message":
            await self._process_one(message)
```

### metrics.py

Prometheus metrics for Grafana:
- `data_quality_readings_checked_total`
- `data_quality_anomalies_detected_total`
- `data_quality_active_rules`
- `data_quality_sensor_health_status`

---

## Quality Rules

### Rule Types

| Rule Type | Description | Parameters |
|-----------|-------------|------------|
| `stuck_value` | Sensor stuck at same value | `consecutive_count`, `tolerance` |
| `sudden_jump` | Unusually large change | `max_delta`, `max_pct_change` |
| `flatline` | No variation over time | `window_minutes`, `max_variance` |
| `rate_of_change` | Too fast/slow changes | `window_minutes`, `max_rate_per_min` |

### Example Rule (SQL)

```sql
INSERT INTO quality_rules (rule_id, rule_name, rule_type, sensor_type, zone_id, parameters, severity, active)
VALUES (
    'stuck-moisture-zone1',
    'Stuck Moisture Sensor Zone 1',
    'stuck_value',
    'moisture',
    'zone-001',
    '{"consecutive_count": 5, "tolerance": 0.001}',
    'warning',
    TRUE
);
```

### Rule Configuration

```json
{
  "rule_id": "stuck-moisture-zone1",
  "rule_name": "Stuck Moisture Sensor Zone 1",
  "rule_type": "stuck_value",
  "sensor_type": "moisture",
  "zone_id": "zone-001",
  "parameters": {
    "consecutive_count": 5,
    "tolerance": 0.001
  },
  "severity": "warning",
  "active": true
}
```

---

## Anomaly Detection

### Stuck Value

Detects when a sensor reports the same value repeatedly:

```python
# Check last N readings (default: 5)
window = values[:consecutive_count]
if all(abs(v - current_value) <= tolerance for v in window):
    # Anomaly detected
```

### Sudden Jump

Detects rapid value changes between consecutive readings:

```python
delta = abs(current_value - previous_value)
pct_change = (delta / abs(previous_value)) * 100

if delta > max_delta or pct_change > max_pct_change:
    # Anomaly detected
```

### Flatline

Detects sensors with no variation over a time window:

```python
variance = sum((x - mean) ** 2 for x in values) / len(values)
if variance <= max_variance:
    # Anomaly detected
```

### Rate of Change

Detects abnormal rates of change over a window:

```python
rate = abs(last_value - first_value) / time_diff_minutes
if rate > max_rate_per_min:
    # Anomaly detected
```

---

## Database Schema

### quality_rules

```sql
CREATE TABLE quality_rules (
    rule_id VARCHAR(100) PRIMARY KEY,
    rule_name VARCHAR(255) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,  -- stuck_value, sudden_jump, flatline, rate_of_change
    sensor_type VARCHAR(50),          -- moisture, temperature
    zone_id UUID,
    parameters JSONB NOT NULL,        -- rule-specific parameters
    severity VARCHAR(20) DEFAULT 'warning',
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### sensor_metadata

```sql
CREATE TABLE sensor_metadata (
    sensor_id UUID PRIMARY KEY,
    zone_id UUID NOT NULL,
    sensor_type VARCHAR(50),
    active BOOLEAN DEFAULT TRUE,
    last_reading_at TIMESTAMPTZ,
    FOREIGN KEY (zone_id) REFERENCES zones(zone_id)
);
```

### v_sensor_health (Materialized View)

```sql
CREATE MATERIALIZED VIEW v_sensor_health AS
SELECT
    zone_id,
    sensor_id,
    sensor_type,
    CASE
        WHEN COUNT(*) = 0 THEN 'unhealthy'
        WHEN MAX(anomaly_count) > 5 THEN 'unhealthy'
        WHEN MAX(anomaly_count) > 0 THEN 'degraded'
        ELSE 'healthy'
    END AS health_status
FROM (
    SELECT
        zone_id,
        sensor_id,
        sensor_type,
        COUNT(*) FILTER (WHERE severity = 'critical') AS critical_count,
        COUNT(*) FILTER (WHERE severity = 'warning') AS anomaly_count
    FROM data_quality_events
    WHERE timestamp > NOW() - INTERVAL '1 hour'
    GROUP BY zone_id, sensor_id, sensor_type
) sub
GROUP BY zone_id, sensor_id, sensor_type;

-- Refresh periodically
REFRESH MATERIALIZED VIEW CONCURRENTLY v_sensor_health;
```

---

## API Endpoints

### GET /quality/reports/summary

Returns quality summary for a time window:

```bash
GET /quality/reports/summary?hours=24&zone_id=zone-001
```

Response:
```json
{
  "total_readings": 1500,
  "total_anomalies": 12,
  "by_severity": {"warning": 10, "critical": 2},
  "by_rule_type": {"stuck_value": 5, "flatline": 7},
  "by_zone": {"zone-001": 8, "zone-002": 4}
}
```

### GET /quality/reports/sensors

Returns sensor health status:

```bash
GET /quality/reports/sensors?zone_id=zone-001
```

Response:
```json
{
  "sensors": [
    {"zone_id": "zone-001", "sensor_id": "sensor-001", "sensor_type": "moisture", "health_status": "healthy"},
    {"zone_id": "zone-001", "sensor_id": "sensor-002", "sensor_type": "moisture", "health_status": "degraded"}
  ]
}
```

### GET /quality/rules

Lists all active rules:

```bash
GET /quality/rules
```

Response:
```json
{
  "rules": [
    {"rule_id": "stuck-moisture-zone1", "rule_name": "...", "rule_type": "stuck_value", "active": true}
  ],
  "count": 1
}
```

### PATCH /quality/rules/{rule_id}

Updates a rule (e.g., enable/disable):

```bash
PATCH /quality/rules/stuck-moisture-zone1
{"active": false}
```

Response:
```json
{"status": "updated", "rule_id": "stuck-moisture-zone1"}
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_QUALITY_PORT` | 8005 | Service port |
| `REDIS_URL` | redis://redis:6379/0 | Redis connection |
| `REDIS_CHANNEL_INGESTION_PROCESSED` | ingestion:processed | Input channel |
| `BATCH_SCAN_INTERVAL_SECONDS` | 300 | Batch scan interval |
| `QUALITY_RULES_CACHE_TTL` | 30 | Rules cache TTL |
| `HEALTH_UPDATE_INTERVAL_SECONDS` | 60 | Health gauge update interval |

---

## Metrics

Prometheus metrics at `/metrics`:

| Metric | Labels | Description |
|--------|--------|-------------|
| `data_quality_readings_checked_total` | zone_id, sensor_id, sensor_type | Readings evaluated |
| `data_quality_anomalies_detected_total` | rule_type, severity, zone_id, sensor_id | Anomalies detected |
| `data_quality_active_rules` | - | Active rule count |
| `data_quality_rule_eval_duration_seconds` | rule_type | Rule evaluation latency |
| `data_quality_sensor_health_status` | zone_id, sensor_id, sensor_type | Sensor health (0=healthy, 1=degraded, 2=unhealthy) |
| `data_quality_stuck_value_detected_total` | zone_id, sensor_id | Stuck value count |
| `data_quality_sudden_jump_detected_total` | zone_id, sensor_id | Sudden jump count |
| `data_quality_flatline_detected_total` | zone_id, sensor_id | Flatline count |

---

## Docker Compose

```yaml
data-quality:
  image: data-quality:latest
  ports:
    - "8005:8005"
  environment:
    - REDIS_URL=redis://redis:6379/0
    - REDIS_CHANNEL_INGESTION_PROCESSED=ingestion:processed
    - BATCH_SCAN_INTERVAL_SECONDS=300
    - QUALITY_RULES_CACHE_TTL=30
  depends_on:
    - redis
    - timescaledb
```

---

## Integration with Other Services

### data-ingestion

Publishes to `ingestion:processed` channel:
```json
{"zone_id": "zone-001", "sensor_id": "sensor-001", "timestamp": "...", "valid": true}
```

### notification-service

Subscribes to `alerts:anomaly` for quality alerts.

### Grafana

Uses `data_quality_sensor_health_status` gauge for dashboard panels.

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Framework | FastAPI + asyncio |
| Language | Python |
| Input | Redis pubsub (ingestion:processed) + batch scan |
| Output | data_quality_events table |
| Rules | Configurable in quality_rules table |
| Anomaly Types | stuck_value, sudden_jump, flatline, rate_of_change |
| Port | 8005 |
| Dependencies | Redis, TimescaleDB |

The Data Quality Service provides comprehensive sensor health monitoring, detecting malfunctions in real-time and through periodic batch analysis.


═══════════════════════════════════════════════════════════════════

SECTION: Model Server

# Model Server Documentation

## Overview

The Model Server is a FastAPI service that serves ML predictions for soil moisture forecasting. It:
- Loads production models from MLflow (stored in MinIO)
- Serves predictions via REST API
- Supports gRPC for high-performance inference
- Auto-reloads models when new versions are promoted to Production

**Location:** `services/model-server/src/main.py`

**Ports:**
- REST API: 8501
- gRPC: 5001

---

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           MODEL SERVER                                          │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐ │
│  │                         FastAPI Application                              │ │
│  │                                                                          │ │
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐  │ │
│  │  │   /health   │   │  /metrics   │   │/v1/model/*  │   │/v1/predict  │  │ │
│  │  └─────────────┘   └─────────────┘   └─────────────┘   └──────┬──────┘  │ │
│  │                                                              │            │ │
│  │                           ┌──────────────────────────────────┘           │ │
│  │                           ▼                                              │ │
│  │                   ┌───────────────┐                                      │ │
│  │                   │ModelRegistry  │                                      │ │
│  │                   │  (in-memory)  │                                      │ │
│  │                   └───────┬───────┘                                      │ │
│  └────────────────────────────┼────────────────────────────────────────────┘ │
│                               │                                               │
│  ┌────────────────────────────┼────────────────────────────────────────────┐ │
│  │                     Background Tasks                                    │ │
│  │                                                                          │ │
│  │  ┌──────────────────┐        ┌──────────────────┐                      │ │
│  │  │  Model Reload    │        │   gRPC Server    │                      │ │
│  │  │  Loop (60 sec)   │        │   (port 5001)    │                      │ │
│  │  └──────────────────┘        └──────────────────┘                      │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────┬──────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL SERVICES                                       │
│                                                                                 │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐          │
│  │     MLflow       │◄───│      MinIO       │◄───│    Airflow       │          │
│  │  (model registry)│    │ (artifact store)│    │     (training)  │          │
│  │    port 5000    │    │    port 9000    │    │                  │          │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘          │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### ModelRegistry Class

The `ModelRegistry` manages model loading and prediction:

```python
# services/model-server/src/model_service.py
class ModelRegistry:
    def __init__(self) -> None:
        self._model: Any = FallbackRegressor()  # Default model
        self._info = LoadedModelInfo(...)       # Model metadata
        self._lock = asyncio.Lock()             # Thread-safe access
```

**Key Properties:**
- `_model`: In-memory loaded model (PyFunc wrapper)
- `_info`: Model metadata (version, stage, source, loaded_at)
- `_lock`: Async lock for thread-safe prediction

### Prediction

```python
async def predict(self, features: list[float]) -> tuple[float, tuple[float, float]]:
    async with self._lock:
        prediction = float(self._model.predict([features])[0])

    # Confidence interval: ±10% of prediction (min 0.05)
    confidence = max(0.05, abs(prediction) * 0.1)
    return prediction, (prediction - confidence, prediction + confidence)
```

### Model Reload

```python
async def reload(self) -> LoadedModelInfo:
    # 1. Query MLflow for Production stage model
    versions = client.get_latest_versions(
        MLFLOW_REGISTERED_MODEL_NAME,
        stages=[MLFLOW_PRODUCTION_STAGE],
    )

    # 2. Load model from MLflow (pulls from MinIO)
    model_uri = f"models:/{MLFLOW_REGISTERED_MODEL_NAME}/Production"
    loaded_model = mlflow.pyfunc.load_model(model_uri)

    # 3. Update in-memory model
    async with self._lock:
        self._model = PyfuncAdapter(loaded_model)
        self._info = LoadedModelInfo(...)
```

---

## API Endpoints

### GET /health

Health check endpoint.

```bash
curl http://localhost:8501/health
```

**Response:**
```json
{"status": "healthy", "service": "model-server"}
```

### GET /metrics

Prometheus metrics endpoint.

```bash
curl http://localhost:8501/metrics
```

**Metrics:**
- `model_server_predictions_total` - Counter of prediction calls
- `model_server_errors_total` - Counter of prediction errors
- `model_server_prediction_latency_seconds` - Histogram of prediction latency

### GET /v1/model/info

Get current model information.

```bash
curl http://localhost:8501/v1/model/info
```

**Response:**
```json
{
  "status": "ok",
  "version": "5",
  "stage": "Production",
  "source": "models:/smart-irrigation-soil-moisture/Production",
  "loaded_at": "2026-05-03T12:00:00+00:00"
}
```

### GET /v1/model/version

Get model version and stage.

```bash
curl http://localhost:8501/v1/model/version
```

**Response:**
```json
{
  "version": "5",
  "stage": "Production"
}
```

### POST /v1/predict

Make a prediction.

**Request:**
```bash
curl -X POST http://localhost:8501/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "zone_id": "2",
    "sensor_id": "2-s1",
    "features": [45.2, 22.5]
  }'
```

**Features:**
- Index 0: Current moisture
- Index 1: Current temperature (or 0.0 as default)

**Response:**
```json
{
  "zone_id": "2",
  "sensor_id": "2-s1",
  "predicted_moisture": 38.5,
  "confidence_interval": [34.65, 42.35],
  "model_version": "5"
}
```

---

## Model Loading Process

### Startup Flow

```
1. FastAPI app starts
   │
   ▼
2. lifespan() triggers
   │
   ▼
3. registry.reload() called
   │   │
   │   ▼
   │   Query MLflow for Production model
   │   │
   │   ▼
   │   Load model from MinIO via MLflow
   │   │
   │   ▼
   │   Store in memory as PyfuncAdapter
   │
   ▼
4. Background tasks start:
   - _reload_loop() - reloads every 60 seconds
   - _grpc_server_task() - starts gRPC server
```

### Model Reload Flow

```
Every 60 seconds:
   │
   ▼
registry.reload() called
   │
   ▼
Query MLflow for Production stage
   │
   ▼
Check if version changed
   │
   ├── Same version → No action
   │
   ▼
New version found
   │
   ▼
Load from MinIO (mlflow.pyfunc.load_model)
   │
   ▼
Update in-memory model (with lock)
   │
   ▼
Update model info metadata
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MLFLOW_TRACKING_URI` | `http://mlflow:5000` | MLflow server URL |
| `MLFLOW_REGISTERED_MODEL_NAME` | `smart-irrigation-soil-moisture` | Model name in MLflow |
| `MLFLOW_PRODUCTION_STAGE` | `Production` | Stage to load from |
| `MODEL_SERVER_REST_PORT` | `8501` | REST API port |
| `MODEL_SERVER_GRPC_PORT` | `5001` | gRPC port |
| `MODEL_RELOAD_INTERVAL_SECONDS` | `60` | How often to check for new model versions |

### Docker Configuration

```yaml
model-server:
  image: model-server:latest
  ports:
    - "8501:8501"  # REST API
    - "5001:5001"  # gRPC
  environment:
    - MLFLOW_TRACKING_URI=http://mlflow:5000
    - MLFLOW_REGISTERED_MODEL_NAME=smart-irrigation-soil-moisture
  depends_on:
    - mlflow
    - minio
```

---

## Error Handling

### Fallback Model

If MLflow is unavailable, the server uses a fallback regressor:

```python
class FallbackRegressor:
    def predict(self, rows: list[list[float]]) -> list[float]:
        # Simple fallback: return average of features
        return [sum(row) / len(row) if row else 0.0 for row in rows]
```

This ensures the service remains available even if MLflow/MinIO is down.

### Logging

```python
logger.warning(
    "Falling back to local model because MLflow registry lookup failed: %s",
    exc,
)
```

---

## Integration with Other Services

### Airflow DAG

Airflow calls the model server for predictions:

```python
# In scheduled_zone_predictions task
response = await client.post(
    f"{MODEL_SERVER_REST_URL}/v1/predict",
    json={
        "zone_id": row["zone_id"],
        "sensor_id": row["sensor_id"],
        "features": [moisture_value, temperature_value],
    },
)
```

### Irrigation Controller

The irrigation controller receives predictions from Airflow via Redis - it does **not** call the model server directly.

---

## gRPC Support

The model server also exposes a gRPC endpoint for high-performance inference:

```python
# gRPC handler
async def grpc_handler(registry: ModelRegistry, payload: bytes) -> bytes:
    data = json.loads(payload.decode("utf-8"))
    features = [float(value) for value in data["features"]]
    prediction, interval = await registry.predict(features)

    return json.dumps({
        "prediction": prediction,
        "confidence_interval": [interval[0], interval[1]],
        "model_version": registry.info.version,
    }).encode("utf-8")
```

---

## Testing

### Test Prediction Endpoint

```bash
# Test with valid features
curl -X POST http://localhost:8501/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"zone_id": "1", "sensor_id": "1-s1", "features": [40.0, 25.0]}'

# Check model info
curl http://localhost:8501/v1/model/info

# Check health
curl http://localhost:8501/health
```

### Integration Test

```python
# services/model-server/tests/integration/test_endpoints.py
def test_predict():
    response = client.post("/v1/predict", json={
        "zone_id": "test",
        "sensor_id": "test-s1",
        "features": [40.0, 25.0]
    })
    assert response.status_code == 200
    data = response.json()
    assert "predicted_moisture" in data
    assert "confidence_interval" in data
```

---

## Monitoring

### Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `model_server_predictions_total` | Counter | Total predictions made |
| `model_server_errors_total` | Counter | Total errors |
| `model_server_prediction_latency_seconds` | Histogram | Prediction time |

View in Prometheus/Grafana dashboard.

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Framework | FastAPI + Uvicorn |
| Model Loading | MLflow pyfunc (from MinIO) |
| In-memory Model | PyfuncAdapter wrapper |
| Auto-reload | Every 60 seconds |
| Fallback | FallbackRegressor if MLflow unavailable |
| API | REST (8501) + gRPC (5001) |
| Integration | Airflow calls REST API for predictions |

The Model Server bridges MLflow/MinIO with the prediction pipeline, ensuring the latest production model is always available for inference.


═══════════════════════════════════════════════════════════════════

SECTION: Model Server API

# Model Server API

## Endpoints

### `POST /v1/predict`
Request:

```json
{
  "zone_id": "zone_a",
  "sensor_id": "sensor_a1",
  "features": [0.21, 0.34, 0.18]
}
```

Response:

```json
{
  "zone_id": "zone_a",
  "sensor_id": "sensor_a1",
  "predicted_moisture": 0.243,
  "confidence_interval": [0.219, 0.267],
  "model_version": "3"
}
```

### `GET /v1/model/info`
Returns the loaded model metadata, stage, source URI, and load timestamp.

### `GET /v1/model/version`
Returns the active model version and stage.

## Notes
- REST runs on port `8501`.
- The internal gRPC prediction handler runs on port `5001`.
- Prediction latency, throughput, and errors are exported on `/metrics`.



═══════════════════════════════════════════════════════════════════

SECTION: Model Versioning

# Model & Data Versioning with MinIO

## Overview

MinIO provides S3-compatible object storage for the Smart Irrigation System's MLOps pipeline. It serves as the backend for:
- **MLflow** - Stores model artifacts, datasets, and experiment files
- **Versioning** - Maintains history of all models and datasets

**Location:** Docker container `minio`

**Access:**
- API: http://localhost:9000
- Console: http://localhost:9001

---

## Architecture

### System Integration

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              MINIO STORAGE                                     │
│                                                                                 │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐   │
│  │   ml-artifacts/     │  │   datasets/         │  │   exports/          │   │
│  │                     │  │                     │  │                     │   │
│  │  - model versions   │  │  - training data    │  │  - summaries        │   │
│  │  - sklearn models   │  │  - dataset JSON     │  │  - reports          │   │
│  │  - model cards      │  │  - metadata         │  │                     │   │
│  │                     │  │                     │  │                     │   │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘   │
└────────────────────────────────┬──────────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
         ┌──────────────────┐      ┌──────────────────┐
         │     MLFLOW       │      │   OTHER SERVICES │
         │                  │      │                  │
         │ - Experiment     │      │ - Model Server   │
         │   tracking      │      │ - Airflow DAG    │
         │ - Model         │      │ - Dashboard      │
         │   registry      │      │                  │
         │ - Version       │      │                  │
         │   management    │      │                  │
         └──────────────────┘      └──────────────────┘
```

### MLflow with MinIO

**MLflow Configuration (docker-compose.yml):**
```yaml
mlflow:
  environment:
    MLFLOW_S3_ENDPOINT_URL: ${MLFLOW_S3_ENDPOINT_URL}
    AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
    AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
  command: >
    mlflow server
    --backend-store-uri ${DATABASE_URL}
    --default-artifact-root s3://${MLFLOW_ARTIFACT_BUCKET}/
```

**Environment Variables (from .env):**
```
MLFLOW_S3_ENDPOINT_URL=http://minio:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
MLFLOW_ARTIFACT_BUCKET=ml-artifacts
```

---

## Storage Structure

### Buckets

| Bucket | Purpose | Contents |
|--------|---------|----------|
| `ml-artifacts` | ML model storage | Trained models, sklearn/XGBoost artifacts |
| `datasets` | Training datasets | Versioned training data |
| `exports` | Export artifacts | Training summaries, reports |

### Artifacts Path Structure

```
ml-artifacts/
├── smart-irrigation-soil-moisture/
│   ├── <run_id>/
│   │   ├── model/
│   │   │   ├── model.pkl
│   │   │   ├── conda.yaml
│   │   │   ├── requirements.txt
│   │   │   └── MLmodel
│   │   ├── best_run.json
│   │   └── model_card.md
│   └── ...
│
datasets/
├── smart-irrigation-training-dataset/
│   ├── <run_id>/
│   │   └── dataset.json
│   └── ...

exports/
└── training-summaries/
    └── ...
```

> **Note:** Both MLflow and MinIO are involved in storing artifacts. When `mlflow.log_artifact()` is called, MLflow acts as the interface/manager while MinIO serves as the actual S3-compatible storage backend. All files (models, datasets, summaries) flow through MLflow APIs but are physically stored in MinIO buckets.

---

## Versioning Mechanism

### Model Versioning

#### 1. Training Creates New Version

When `log_training_to_mlflow()` runs in Airflow DAG:

```python
# mlops/training.py
mlflow.sklearn.log_model(
    sk_model=pipeline,
    artifact_path="model",
    registered_model_name=settings.mlflow_registered_model_name,
    registered_model_version={"version": mlflow_result["version"]},
)
```

#### 2. Version Stages

Models can be promoted through stages:

| Stage | Description | Use Case |
|-------|-------------|----------|
| `None` | Staging | New training, not yet deployed |
| `Staging` | Testing | Validating before production |
| `Production` | Live | Currently serving predictions |
| `Archived` | Retired | Old models kept for rollback |

#### 3. Promotion Decision

```python
# mlops/promotion.py
def decide_promotion(new_rmse: float, production_rmse: float) -> PromotionDecision:
    if new_rmse < production_rmse:
        return PromotionDecision(should_promote=True, target_stage="Production")
    elif new_rmse < production_rmse * 1.1:
        return PromotionDecision(should_promote=True, target_stage="Staging")
    else:
        return PromotionDecision(should_promote=False, target_stage=None)
```

### Dataset Versioning

Dataset versioning follows the same MLflow → MinIO pattern as model versioning.

#### 1. Dataset Creation

```python
# mlops/dataset_pipeline.py
def log_dataset_to_mlflow(dataset: DatasetBuildResult) -> dict[str, Any]:
    mlflow_dataset = mlflow.data.from_pandas(
        df,
        name=settings.mlflow_dataset_name,
    )

    with mlflow.start_run(run_name="dataset-build") as run:
        # Log dataset as MLflow input (tracks lineage)
        mlflow.log_input(mlflow_dataset, context="training")

        # Log metadata (query params, time range, source)
        mlflow.log_params(dataset.metadata)

        # Log dataset metrics
        mlflow.log_metric("dataset_rows", len(dataset.rows))
        mlflow.log_metric("dataset_features", len(dataset.feature_columns))

        # Save and log dataset JSON to MinIO (via MLflow API)
        tmp_path = Path(tmpdir) / "dataset.json"
        dataset.to_json(tmp_path)
        mlflow.log_artifact(str(tmp_path))  # → Physically stored in MinIO

    return {
        "run_id": run.info.run_id,
        "artifact_path": "dataset.json",
    }
```

**Data Flow:**
```
mlflow.log_artifact(str(tmp_path))
         │
         ▼
    ┌────────────┐
    │  MLflow    │  (manages the interface)
    │   API      │
    └─────┬──────┘
          │ Stores to (via S3 protocol)
          ▼
    ┌────────────┐
    │   MinIO    │  (actual storage: s3://datasets/...)
    │  Storage   │
    └────────────┘
```

#### 2. Dataset Metadata

Each dataset version captures:
- Number of rows
- Feature columns
- Time range
- Source query parameters
- Full raw data (dataset.json)

#### 3. Dataset Lineage

Every model version in MLflow is linked to its dataset version through MLflow's **dataset input tracking**:

- When you train a model, MLflow records which dataset was used
- You can trace back: `Model v5` → `was trained on` → `Dataset from run <run_id>`
- This enables full reproducibility

To view in MLflow UI:
1. Go to **Experiments** → Select an experiment
2. Click on a run
3. Look at **Datasets** section (shows input datasets with version)
4. Look at **Artifacts** → `dataset.json` (actual data stored in MinIO)

---

## Usage in Pipeline

### Airflow DAG Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          AIRFLOW DAG                                           │
│                                                                                 │
│  1. prepare_dataset                                                            │
│     └─► Calls build_dataset_from_database()                                     │
│     └─► Calls log_dataset_to_mlflow() ──► MinIO: datasets/                     │
│     └─► Pushes run_id to XCom                                                  │
│                                                                                 │
│  2. train_candidate_models                                                     │
│     └─► Pulls dataset from MinIO (via run_id)                                  │
│     └─► Trains XGBoost model                                                   │
│     └─► Calls log_training_to_mlflow() ──► MinIO: ml-artifacts/                │
│                                                                                 │
│  3. evaluate_and_register                                                      │
│     └─► Compares with production model                                         │
│     └─► Promotes if better (updates version stage)                             │
│                                                                                 │
│  4. scheduled_zone_predictions                                                 │
│     └─► Loads model from MLflow (from MinIO)                                   │
│     └─► Runs inference                                                         │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         MINIO STORAGE                                           │
│                                                                                 │
│  Bucket: ml-artifacts                                                          │
│  ├── smart-irrigation-soil-moisture/                                          │
│  │   └── <run_id>/                                                             │
│  │       ├── model/  (sklearn model + metadata)                               │
│  │       ├── best_run.json                                                    │
│  │       └── model_card.md                                                    │
│  └── ...                                                                       │
│                                                                                 │
│  Bucket: datasets                                                              │
│  └── smart-irrigation-training-dataset/                                        │
│      └── <run_id>/                                                             │
│          └── dataset.json                                                      │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       MODEL SERVER                                             │
│                                                                                 │
│  At startup:                                                                   │
│  1. Loads production model from MLflow (from MinIO)                           │
│  2. Serves predictions via REST API                                            │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Accessing MinIO

### Via Console (Web UI)

1. Open http://localhost:9001
2. Login with credentials from `.env`:
   - Username: `minioadmin` (or from `MINIO_ROOT_USER`)
   - Password: `minioadmin` (or from `MINIO_ROOT_PASSWORD`)

### Via AWS CLI

```bash
# Configure AWS CLI for MinIO
aws configure set aws_access_key_id minioadmin
aws configure set aws_secret_access_key minioadmin
aws configure set region us-east-1

# List buckets
aws --endpoint-url http://localhost:9000 s3 ls

# List objects in bucket
aws --endpoint-url http://localhost:9000 s3 ls s3://ml-artifacts/

# Download model artifact
aws --endpoint-url http://localhost:9000 s3 cp s3://ml-artifacts/smart-irrigation-soil-moisture/<run_id>/model/ ./model/ --recursive
```

### Via Python (boto3)

```python
import boto3

s3 = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='minioadmin',
    aws_secret_access_key='minioadmin',
)

# List buckets
response = s3.list_buckets()
print([b['Name'] for b in response['Buckets']])

# List objects
response = s3.list_objects_v2(Bucket='ml-artifacts')
print([o['Key'] for o in response.get('Contents', [])])
```

---

## MLflow UI

Access MLflow at http://localhost:5000

### Features

1. **Experiments** - View all training runs
2. **Runs** - Individual run details with metrics
3. **Models** - Registered model versions with stages
4. **Artifacts** - Browse stored files in MinIO

### Model Registry

```
smart-irrigation-soil-moisture
├── Version 1 (Production)
│   - Created: 2026-01-01
│   - RMSE: 5.2
│   - Stage: Production
├── Version 2 (Staging)
│   - Created: 2026-01-15
│   - RMSE: 4.8
│   - Stage: Staging
└── Version 3 (None)
    - Created: 2026-02-01
    - RMSE: 4.5
    - Stage: None
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MINIO_ROOT_USER` | `minioadmin` | MinIO admin username |
| `MINIO_ROOT_PASSWORD` | `minioadmin` | MinIO admin password |
| `MLFLOW_S3_ENDPOINT_URL` | `http://minio:9000` | MLflow → MinIO connection |
| `AWS_ACCESS_KEY_ID` | `minioadmin` | S3 access key |
| `AWS_SECRET_ACCESS_KEY` | `minioadmin` | S3 secret key |
| `MLFLOW_ARTIFACT_BUCKET` | `ml-artifacts` | Default artifact bucket |

### Docker Compose Service

```yaml
minio:
  image: minio/minio:latest
  command: server /data --console-address ":9001"
  ports:
    - "9000:9000"    # API
    - "9001:9001"    # Console
  volumes:
    - minio_data:/data
```

---

## Cleanup & Maintenance

### Pruning Old Runs

```python
from mlflow.tracking import MlflowClient

client = MlflowClient()

# Delete runs older than 30 days
for exp in client.list_experiments():
    for run in client.list_run_infos(exp.experiment_id):
        if run.end_time < (datetime.now() - timedelta(days=30)):
            client.delete_run(run.run_id)
```

### Deleting Old Model Versions

```python
client = MlflowClient()

# Delete old versions (keep last 5)
for version in client.get_model_version_download_links("smart-irrigation-soil-moisture"):
    if version.version < 5:
        client.delete_model_version("smart-irrigation-soil-moisture", version.version)
```

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Storage Backend | MinIO (S3-compatible) |
| ML Integration | MLflow artifact storage |
| Model Versioning | MLflow Model Registry |
| Dataset Versioning | MLflow dataset inputs |
| Access | MinIO Console (9001), MLflow UI (5000) |
| API | AWS S3 API via boto3 |

MinIO provides the foundation for reproducible MLOps by storing all model and dataset artifacts with full versioning support. MLflow manages the lifecycle from training to production deployment.


═══════════════════════════════════════════════════════════════════

SECTION: Drift Monitoring

# Drift Monitoring Documentation

## Overview

The Drift Monitoring service detects when the ML model's predictions drift from expected behavior. It monitors:
1. **Data Drift** - Changes in input data distribution
2. **Concept Drift** - Changes in the relationship between inputs and outputs
3. **Model Performance** - Prediction error increases

When drift is detected, the service automatically triggers Airflow to retrain the model.

**Location:** `services/drift-monitor/src/`

**Port:** 8502

---

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DRIFT MONITOR SERVICE                                 │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        FastAPI Application                              │   │
│  │                                                                          │   │
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                  │   │
│  │  │   /health   │   │  /metrics   │   │/v1/drift/   │                  │   │
│  │  │             │   │             │   │   status    │                  │   │
│  │  └─────────────┘   └─────────────┘   └──────┬──────┘                  │   │
│  │                                           │                           │   │
│  │                                           ▼                           │   │
│  │  ┌──────────────────────────────────────────────────────────────┐      │   │
│  │  │                    DriftMonitor Class                         │      │   │
│  │  │                                                              │      │   │
│  │  │  - scan()       : Detects drift                              │      │   │
│  │  │  - _fetch_prediction_window() : Gets prediction data        │      │   │
│  │  │  - summarize_drift() : Calculates drift metrics            │      │   │
│  │  │  - trigger_retraining_dag() : Triggers Airflow             │      │   │
│  │  └──────────────────────────────────────────────────────────────┘      │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                   Background Scan Loop (every 60 sec)                    │   │
│  │                                                                          │   │
│  │  while running:                                                          │   │
│  │    1. Fetch last 200 predictions (100 current, 100 reference)          │   │
│  │    2. Run drift detection algorithms                                   │   │
│  │    3. If drift detected:                                                │   │
│  │       - Publish to alerts:anomaly                                       │   │   │
│  │       - Trigger Airflow retraining                                      │   │
│  │    4. Sleep 60 seconds                                                  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            DATA SOURCES                                         │
│                                                                                 │
│  ┌──────────────────┐    ┌──────────────────┐                                │
│  │   TimescaleDB    │    │      Redis       │                                │
│  │                  │    │                  │                                │
│  │ model_predictions│    │  alerts:anomaly  │                                │
│  │ (last 24 hours) │    │    (output)       │                                │
│  └──────────────────┘    └──────────────────┘                                │
└───────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           OUTPUT                                                │
│                                                                                 │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐        │
│  │   Redis Pub/Sub  │    │   Prometheus     │    │     Airflow      │        │
│  │                  │    │     Metrics      │    │   (retraining)   │        │
│  │ alerts:anomaly   │    │                  │    │                  │        │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘        │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Drift Detection Algorithms

### 1. Page-Hinkley Test

Used for detecting abrupt changes in the mean of a sequence.

```python
def page_hinkley(values: list[float], delta: float = 0.005, threshold: float = 0.5) -> tuple[float, bool]:
    """
    Page-Hinkley change detection test.

    Args:
        values: Sequence of values to test
        delta: Minor change allowance (default: 0.005)
        threshold: Detection threshold (default: 0.5)

    Returns:
        (score, detected): Score and whether drift was detected
    """
    mean_value = 0.0
    cumulative = 0.0
    min_cumulative = 0.0
    best_score = 0.0

    for index, value in enumerate(values, start=1):
        mean_value += (value - mean_value) / index
        cumulative += value - mean_value - delta
        min_cumulative = min(min_cumulative, cumulative)
        best_score = max(best_score, cumulative - min_cumulative)

    return best_score, best_score > threshold
```

**How it works:**
- Tracks cumulative sum of deviations from the running mean
- Detects when cumulative deviation exceeds threshold
- Returns score and boolean (drift detected if score > 0.5)

### 2. KL Divergence

Used for detecting distribution changes between reference and current data.

```python
def kl_divergence(reference: list[float], current: list[float], bins: int = 10) -> float:
    """
    Kullback-Leibler divergence between two distributions.

    Args:
        reference: Reference distribution (historical data)
        current: Current distribution to compare
        bins: Number of histogram bins (default: 10)

    Returns:
        KL divergence score (higher = more different)
    """
    # Create histograms
    ref_hist = [1e-6] * bins
    cur_hist = [1e-6] * bins

    # Fill histograms
    for value in reference:
        index = min(bins - 1, int((value - minimum) / bucket_width))
        ref_hist[index] += 1
    ...

    # Calculate KL divergence
    return sum(
        (cur / cur_total) * math.log((cur / cur_total) / (ref / ref_total))
        for ref, cur in zip(ref_hist, cur_hist)
    )
```

**How it works:**
- Creates histogram of reference and current distributions
- Measures information loss when using reference to encode current
- KL > 0.1 indicates significant distribution change

### 3. Prediction Error

Monitors the mean absolute error between predictions and actual values (if available).

```python
mean_error = sum(abs(a - c) for a, c in zip(actual, current)) / len(actual)
```

**How it works:**
- Compares predicted vs actual values
- If mean_error > 0.15 (15%), indicates model degradation

---

## Drift Summary

Combines all metrics into a single summary:

```python
def summarize_drift(reference: list[float], current: list[float], actual: list[float] | None = None) -> DriftSummary:
    score, detected = page_hinkley(current)
    divergence = kl_divergence(reference, current)
    mean_error = ...

    drift_detected = detected or divergence > 0.1 or mean_error > 0.15

    return DriftSummary(
        page_hinkley_score=score,
        kl_divergence=divergence,
        mean_error=mean_error,
        drift_detected=drift_detected,
    )
```

**Drift Detection Logic:**
```
Drift detected if ANY of:
├── Page-Hinkley score > 0.5 (detected)
├── KL divergence > 0.1 (distribution change)
└── Mean error > 0.15 (prediction degradation)
```

---

## Scan Process

### 1. Fetch Data Window

```python
async def _fetch_prediction_window(self) -> tuple[list[float], list[float]]:
    # Get last 24 hours of predictions
    rows = await conn.fetch("""
        SELECT prediction, confidence
        FROM model_predictions
        WHERE predicted_at >= $1
        ORDER BY predicted_at DESC
        LIMIT 200
    """, since)

    # Split into:
    # - current: most recent 100 predictions
    # - reference: previous 100 predictions
    current = [float(row["prediction"]) for row in rows[:100]]
    reference = [float(row["prediction"]) for row in rows[100:200]]
    return reference, current
```

### 2. Run Detection

```python
async def scan(self) -> DriftSummary:
    reference, current = await self._fetch_prediction_window()
    summary = summarize_drift(reference, current)

    # Update Prometheus metrics
    PAGE_HINKLEY_GAUGE.set(summary.page_hinkley_score)
    KL_GAUGE.set(summary.kl_divergence)
    ERROR_GAUGE.set(summary.mean_error)

    # If drift detected, take action
    if summary.drift_detected:
        # Publish to Redis
        await self.redis_client.publish(REDIS_CHANNEL_ALERTS_ANOMALY, json.dumps(...))
        # Trigger retraining
        await self.trigger_retraining_dag()

    return summary
```

### 3. Trigger Retraining

```python
async def trigger_retraining_dag(self) -> None:
    # Cooldown: don't trigger more than once per hour
    if (now - self._last_triggered_at) < timedelta(hours=1):
        return

    # Call Airflow API
    response = await client.post(
        f"{AIRFLOW_URL}/api/v1/dags/smart_irrigation_model_training/dagRuns",
        json={"conf": {}},
        auth=(AIRFLOW_ADMIN_USER, AIRFLOW_ADMIN_PASSWORD),
    )
```

---

## API Endpoints

### GET /health

Health check.

```bash
curl http://localhost:8502/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "drift-monitor"
}
```

### GET /metrics

Prometheus metrics.

```bash
curl http://localhost:8502/metrics
```

**Metrics:**
- `drift_monitor_page_hinkley_score` - Latest Page-Hinkley score
- `drift_monitor_kl_divergence` - Latest KL divergence
- `drift_monitor_mean_error` - Latest mean error

### GET /v1/drift/status

Get current drift status.

```bash
curl http://localhost:8502/v1/drift/status
```

**Response (No drift):**
```json
{
  "page_hinkley_score": 0.12,
  "kl_divergence": 0.03,
  "mean_error": 0.05,
  "drift_detected": false
}
```

**Response (Drift detected):**
```json
{
  "page_hinkley_score": 0.73,
  "kl_divergence": 0.15,
  "mean_error": 0.22,
  "drift_detected": true
}
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DRIFT_MONITOR_PORT` | `8502` | Service port |
| `DRIFT_SCAN_INTERVAL_SECONDS` | `60` | Scan every 60 seconds |
| `DATABASE_URL` | `postgresql://...` | Database connection |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `REDIS_CHANNEL_ALERTS_ANOMALY` | `alerts:anomaly` | Alert output channel |
| `AIRFLOW_URL` | `http://airflow:8080` | Airflow API URL |
| `AIRFLOW_ADMIN_USER` | `admin` | Airflow username |
| `AIRFLOW_ADMIN_PASSWORD` | `airflow_dev` | Airflow password |

### Docker Configuration

```yaml
drift-monitor:
  image: drift-monitor:latest
  ports:
    - "8502:8502"
  environment:
    - DRIFT_SCAN_INTERVAL_SECONDS=60
    - AIRFLOW_URL=http://airflow:8080
  depends_on:
    - timescaledb
    - redis
    - airflow
```

---

## Drift Detection Thresholds

| Metric | Threshold | Description |
|--------|-----------|-------------|
| Page-Hinkley Score | > 0.5 | Mean shift detected |
| KL Divergence | > 0.1 | Distribution change detected |
| Mean Error | > 0.15 | Prediction accuracy degraded |

---

## Alert Output

When drift is detected, an alert is published to Redis:

```json
{
  "type": "model_drift",
  "detected_at": "2026-05-03T12:00:00+00:00",
  "page_hinkley_score": 0.73,
  "kl_divergence": 0.15,
  "mean_error": 0.22,
  "drift_detected": true
}
```

---

## Integration

### With Airflow

When drift is detected, the service triggers Airflow DAG:

```
Drift Monitor detects drift
        │
        ▼
POST to Airflow API /api/v1/dags/smart_irrigation_model_training/dagRuns
        │
        ▼
Airflow starts new DAG run
        │
        ▼
Model retraining pipeline executes
        │
        ▼
New model promoted to Production (if better)
```

### With Notification Service

The `alerts:anomaly` channel is consumed by the notification service to alert users.

---

## Cooldown Mechanism

To prevent excessive retraining, there's a 1-hour cooldown between triggers:

```python
if self._last_triggered_at and (now - self._last_triggered_at) < timedelta(hours=1):
    self.logger.info("Skipping Airflow trigger (cooldown active).")
    return
```

---

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `drift_monitor_page_hinkley_score` | Gauge | Latest Page-Hinkley score |
| `drift_monitor_kl_divergence` | Gauge | Latest KL divergence |
| `drift_monitor_mean_error` | Gauge | Latest mean prediction error |

---

## Monitoring

### Check Drift Status

```bash
curl http://localhost:8502/v1/drift/status | jq
```

### View in Grafana

Import the drift monitoring dashboard to visualize:
- Page-Hinkley score over time
- KL divergence trends
- Mean error history
- Alert frequency

---

## Testing

### Manual Drift Detection Test

```python
from drift_detector import page_hinkley, kl_divergence, summarize_drift

# Test Page-Hinkley
values = [0.1] * 100 + [0.5] * 50  # Sudden shift at index 100
score, detected = page_hinkley(values)
print(f"Score: {score}, Detected: {detected}")

# Test KL divergence
reference = [random.gauss(50, 10) for _ in range(1000)]
current = [random.gauss(60, 15) for _ in range(1000)]  # Different distribution
divergence = kl_divergence(reference, current)
print(f"KL Divergence: {divergence}")

# Test full summary
summary = summarize_drift(reference, current)
print(f"Drift Detected: {summary.drift_detected}")
```

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Framework | FastAPI + Uvicorn |
| Detection | Page-Hinkley + KL Divergence + Mean Error |
| Scan Interval | Every 60 seconds |
| Data Window | Last 200 predictions (100 current, 100 reference) |
| Triggers | Airflow DAG retraining + Redis alert |
| Cooldown | 1 hour between triggers |
| Port | 8502 |
| Alert Channel | `alerts:anomaly` |

The Drift Monitoring service ensures model quality by automatically detecting when predictions drift from expected behavior and triggering retraining to maintain accuracy.


═══════════════════════════════════════════════════════════════════

SECTION: Irrigation Trigger System

# Smart Irrigation System - Complete Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Irrigation Controller Service](#irrigation-controller-service)
3. [Airflow DAG - Prediction Generation](#airflow-dag---prediction-generation)
4. [Database Schema](#database-schema)
5. [Redis Channels](#redis-channels)
6. [Complete Flow Diagram](#complete-flow-diagram)
7. [Event Lifecycle](#event-lifecycle)
8. [Configuration](#configuration)
9. [Edge Cases](#edge-cases)

---

## 1. System Overview

The smart irrigation system is a fully automated MLOps pipeline that:

1. **Generates predictions** via scheduled Airflow DAG
2. **Publishes predictions** to Redis
3. **Evaluates predictions** against zone thresholds
4. **Triggers irrigation** autonomously when moisture is below threshold
5. **Notifies** stakeholders of irrigation events

### Architecture Summary

| Component | Role | Key Technology |
|-----------|------|----------------|
| Airflow DAG | Generate predictions | Python, asyncpg, httpx, Redis |
| irrigation-controller | Evaluate & trigger | FastAPI, asyncpg, Redis pubsub |
| sensor-simulator | Simulate sensor data | Redis publisher |
| notification-service | Alert users | Redis subscriber |
| database | Store events/data | TimescaleDB (PostgreSQL) |
| model-server | Serve ML predictions | MLflow |
| Redis | Message broker | Pub/Sub |

---

## 2. Irrigation Controller Service

**Location:** `services/irrigation-controller/src/main.py`

The Irrigation Controller is a FastAPI service that subscribes to Redis and automatically triggers irrigation when predicted moisture falls below zone thresholds.

### 2.1 Redis Subscription

The service connects to Redis using async pubsub:

```python
# Connection setup
async def connect(self) -> None:
    self.db_pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=5)
    self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    self.pubsub = self.redis_client.pubsub()
    await self.pubsub.subscribe(REDIS_CHANNEL_PREDICTIONS_NEW)
```

### 2.2 Message Listener

The controller uses async iterator pattern to listen for messages:

```python
async def run(self) -> None:
    self._running = True
    try:
        async for message in self.pubsub.listen():
            if not self._running:
                break
            if message.get("type") == "message":
                try:
                    payload = json.loads(message["data"])
                    await self.evaluate_prediction(payload)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
    except asyncio.CancelledError:
        pass
```

### 2.3 Prediction Evaluation Logic

This is the core logic that decides whether to trigger irrigation:

```python
async def evaluate_prediction(self, payload: dict[str, Any]) -> dict[str, Any] | None:
    zone_id = payload["zone_id"]
    prediction = float(payload["prediction"])
    
    # 1. Fetch zone thresholds from database
    thresholds = await self._zone_thresholds(zone_id)
    if not thresholds:
        logger.debug(f"No thresholds found for zone {zone_id}")
        return None

    # 2. Log for debugging
    logger.debug(f"Zone {zone_id}: prediction={prediction}, threshold_min={thresholds['moisture_min']}")

    # 3. Check if prediction meets minimum threshold
    # If prediction >= moisture_min, moisture is adequate - no irrigation needed
    if prediction >= thresholds["moisture_min"]:
        return None

    # 4. Deduplication: check for recent events in last 10 minutes
    # Prevents multiple triggers from multiple sensors in same zone
    if await self._recent_event_exists(zone_id, minutes=10):
        logger.debug(f"Skipping irrigation for zone {zone_id}: recent event exists")
        return None

    # 5. Calculate deficit and recommended volume
    # deficit = moisture_min - prediction (how much moisture is needed)
    deficit = max(0.0, thresholds["moisture_min"] - prediction)
    # volume = deficit * 100 (convert to liters, assuming 100 units per deficit)
    recommended_volume = round(deficit * 100, 3)

    # 6. Create event with pending status
    event = {
        "zone_id": zone_id,
        "trigger_reason": "predicted_moisture_below_threshold",
        "recommended_volume": recommended_volume,
        "predicted_moisture": prediction,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await self.store_event(event)
    logger.info(f"Irrigation TRIGGERED for zone {zone_id}: volume={recommended_volume}")

    # 7. Schedule autonomous execution (runs in background)
    asyncio.create_task(self._execute_irrigation(event["zone_id"], event["recommended_volume"]))

    return event
```

### 2.4 Threshold Checking

Thresholds are fetched from the zones table:

```python
async def _zone_thresholds(self, zone_id: str) -> dict[str, Any] | None:
    async with self.db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT zone_id, moisture_min, moisture_max, soil_type
            FROM zones
            WHERE zone_id = $1
            """,
            zone_id,
        )
    return dict(row) if row else None
```

### 2.5 Deduplication Mechanism

Prevents rapid repeated triggers when multiple sensors in the same zone generate predictions:

```python
async def _recent_event_exists(self, zone_id: str, minutes: int = 10) -> bool:
    async with self.db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT 1 FROM irrigation_events
            WHERE zone_id = $1
              AND triggered_at > NOW() - INTERVAL '10 minutes'
            LIMIT 1
            """,
            zone_id,
        )
    return row is not None
```

**Why this matters:**
- Zone 2 has 2 sensors (2-s1 and 2-s2)
- When Airflow runs, it publishes predictions for both sensors
- Without deduplication, 2 events would be created
- With deduplication, only 1 event is created within 10 minutes

### 2.6 Event Storage

Events are initially stored with status `pending`:

```python
async def store_event(self, event: dict[str, Any]) -> None:
    async with self.db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO irrigation_events (
                triggered_at,
                zone_id,
                trigger_reason,
                recommended_volume,
                status
            )
            VALUES ($1, $2, $3, $4, 'pending')
            """,
            datetime.now(timezone.utc),
            event["zone_id"],
            event["trigger_reason"],
            event["recommended_volume"],
        )
```

### 2.7 Autonomous Execution (pending → completed)

After creating the event, the controller schedules an automatic execution task:

```python
async def _execute_irrigation(self, zone_id: str, volume: float) -> None:
    # Wait 5 seconds (simulated execution time)
    await asyncio.sleep(5)

    async with self.db_pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE irrigation_events
            SET status = 'completed',
                actual_volume = $1,
                duration_seconds = 300,
                completed_at = NOW()
            WHERE id = (
                SELECT id FROM irrigation_events
                WHERE zone_id = $2 AND status = 'pending'
                ORDER BY triggered_at DESC
                LIMIT 1
            )
            """,
            volume,
            zone_id,
        )

    logger.info(f"Irrigation COMPLETED for zone {zone_id}: volume={volume}")

    # Publish completion event to Redis for notification service
    if self.redis_client:
        await self.redis_client.publish(
            "irrigation:triggered",
            json.dumps({
                "zone_id": zone_id,
                "status": "completed",
                "volume": volume,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })
        )
```

**What happens:**
- Status changes from `pending` → `completed`
- `actual_volume` is set to the recommended volume
- `duration_seconds` is set to 300 (5 minutes)
- `completed_at` timestamp is recorded
- A message is published to `irrigation:triggered` for notifications

---

## 3. Airflow DAG - Prediction Generation

**Location:** `airflow/dags/smart_irrigation_dags.py`

The `scheduled_zone_predictions` function generates predictions for all active zones and publishes them to Redis.

### 3.1 Function Overview

```python
def scheduled_zone_predictions(**context):
    import asyncio
    import asyncpg
    import httpx
    import redis.asyncio as redis

    async def _run():
        # Connect to database and Redis
        conn = await asyncpg.connect(DATABASE_URL)
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)

        try:
            # Get all active zones and sensors
            zones = await conn.fetch(
                "SELECT DISTINCT zone_id, sensor_id FROM sensor_metadata WHERE active = TRUE"
            )

            async with httpx.AsyncClient(timeout=30.0) as client:
                for row in zones:
                    # 1. Get latest sensor reading
                    latest_reading = await conn.fetchrow(
                        """SELECT moisture FROM sensor_readings
                           WHERE zone_id = $1 AND sensor_id = $2
                           ORDER BY timestamp DESC LIMIT 1""",
                        row["zone_id"], row["sensor_id"]
                    )
                    if not latest_reading:
                        continue

                    # 2. Assemble feature vector
                    features = [
                        float(latest_reading["moisture"]),
                        0.0  # Default temperature
                    ]

                    # 3. Call model-server for prediction
                    response = await client.post(
                        f"{MODEL_SERVER_REST_URL}/v1/predict",
                        json={
                            "zone_id": row["zone_id"],
                            "sensor_id": row["sensor_id"],
                            "features": features,
                        },
                    )
                    payload = response.json()

                    # 4. Store prediction in database
                    await conn.execute(
                        """INSERT INTO model_predictions
                           (predicted_at, zone_id, model_version, prediction, confidence)
                           VALUES ($1, $2, $3, $4, $5)""",
                        datetime.utcnow(),
                        row["zone_id"],
                        payload["model_version"],
                        payload["predicted_moisture"],
                        payload["confidence_interval"][1] - payload["confidence_interval"][0],
                    )

                    # 5. PUBLISH to Redis for irrigation-controller
                    publish_payload = json.dumps({
                        "zone_id": row["zone_id"],
                        "sensor_id": row["sensor_id"],
                        "prediction": payload["predicted_moisture"],
                        "model_version": payload["model_version"],
                        "predicted_at": datetime.utcnow().isoformat(),
                    })
                    await redis_client.publish(REDIS_CHANNEL_PREDICTIONS_NEW, publish_payload)

        finally:
            await conn.close()
            await redis_client.close()

    asyncio.run(_run())
```

### 3.2 DAG Task Flow

The full DAG has 5 tasks:

```
prepare_dataset → train_candidate_models → evaluate_and_register → export_training_summary → scheduled_zone_predictions
```

The last task (`scheduled_zone_predictions`) publishes predictions to Redis.

---

## 4. Database Schema

### 4.1 zones Table

Defines irrigation zones and their thresholds:

```sql
CREATE TABLE IF NOT EXISTS zones (
    zone_id       VARCHAR(50)  PRIMARY KEY,
    zone_name     VARCHAR(200) NOT NULL,
    soil_type     VARCHAR(50)  NOT NULL,
    crop_type     VARCHAR(50)  NOT NULL,
    moisture_min  FLOAT        NOT NULL,  -- Threshold for triggering irrigation
    moisture_max  FLOAT        NOT NULL,  -- Upper bound for alerts
    min_plausible JSONB        NOT NULL DEFAULT '{}',
    max_plausible JSONB        NOT NULL DEFAULT '{}',
    active        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
```

**Example data:**
```
 zone_id | zone_name | soil_type | crop_type | moisture_min | moisture_max
---------+-----------+-----------+-----------+---------------+--------------
 1       | Zone A    | loam      | corn      |            30 |           60
 2       | Zone B    | clay      | wheat     |            55 |           60
 3       | Zone C    | sandy     | barley    |            50 |           60
```

### 4.2 irrigation_events Table

Tracks irrigation trigger events:

```sql
CREATE TABLE IF NOT EXISTS irrigation_events (
    id                 BIGSERIAL,
    triggered_at       TIMESTAMPTZ  NOT NULL,
    zone_id            VARCHAR(50)  NOT NULL REFERENCES zones(zone_id),
    trigger_reason     VARCHAR(100) NOT NULL,
    recommended_volume FLOAT,
    actual_volume      FLOAT,
    duration_seconds   INTEGER,
    status             VARCHAR(20)  NOT NULL DEFAULT 'pending'
                       CHECK (status IN ('pending', 'completed', 'failed')),
    completed_at       TIMESTAMPTZ,
    PRIMARY KEY (id, triggered_at)
);
```

**Status values:**
- `pending`: Event created, irrigation not yet executed
- `completed`: Irrigation executed successfully
- `failed`: Irrigation failed

**Example data:**
```
 zone_id | status   | recommended_volume | actual_volume | duration_seconds | triggered_at          | completed_at
---------+----------+--------------------+---------------+------------------+-----------------------+--------------------
 2       | completed|            1833.68 |       1833.68 |              300 | 2026-05-03 13:17:08+00 | 2026-05-03 13:17:13+00
 3       | completed|            773.265 |       773.265 |              300 | 2026-05-03 13:17:11+00 | 2026-05-03 13:17:16+00
```

### 4.3 model_predictions Table

Stores prediction results:

```sql
CREATE TABLE IF NOT EXISTS model_predictions (
    id            BIGSERIAL,
    predicted_at  TIMESTAMPTZ NOT NULL,
    zone_id       VARCHAR(50) NOT NULL REFERENCES zones(zone_id),
    model_version VARCHAR(100),
    prediction    FLOAT,
    confidence    FLOAT,
    PRIMARY KEY (id, predicted_at)
);
```

---

## 5. Redis Channels

### 5.1 predictions:new

| Property | Value |
|----------|-------|
| Channel name | `predictions:new` |
| Publisher | Airflow DAG (`scheduled_zone_predictions`) |
| Subscriber | irrigation-controller |
| Payload format | JSON |

**Payload example:**
```json
{
  "zone_id": "2",
  "sensor_id": "2-s1",
  "prediction": 36.66,
  "model_version": "1",
  "predicted_at": "2026-05-03T13:17:13.103229"
}
```

### 5.2 irrigation:triggered

| Property | Value |
|----------|-------|
| Channel name | `irrigation:triggered` |
| Publisher | irrigation-controller |
| Subscribers | notification-service, sensor-simulator |
| Payload format | JSON |

**Payload example:**
```json
{
  "zone_id": "2",
  "status": "completed",
  "volume": 1833.68,
  "completed_at": "2026-05-03T13:17:18.000000"
}
```

---

## 6. Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        AIRFLOW DAG (scheduled daily)                                │
│                                                                                     │
│  1. Fetch active zones from sensor_metadata                                        │
│  2. Get latest sensor readings for each zone                                       │
│  3. Call model-server for predictions                                              │
│  4. Store predictions in model_predictions table                                   │
│  5. PUBLISH to Redis channel: predictions:new                                    │
└────────────────────────────────┬────────────────────────────────────────────────────┘
                                 │
                                 │ Redis message
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    IRRIGATION-CONTROLLER Service                                   │
│                                                                                     │
│  1. SUBSCRIBE to Redis channel: predictions:new                                  │
│  2. Parse prediction payload                                                       │
│  3. Fetch zone thresholds (moisture_min, moisture_max)                            │
│  4. IF prediction >= moisture_min: SKIP (no irrigation needed)                  │
│  5. Check for recent events in last 10 minutes (deduplication)                   │
│     IF exists: SKIP                                                                │
│  6. Calculate deficit: max(0, moisture_min - prediction)                         │
│  7. Calculate volume: deficit * 100                                               │
│  8. INSERT into irrigation_events (status='pending')                              │
│  9. ASYNC TASK: _execute_irrigation()                                              │
└────────────────────────────────┬────────────────────────────────────────────────────┘
                                 │
                                 │ asyncio.create_task
                                 ▼ (after 5 seconds)
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                   Autonomous Execution                                             │
│                                                                                     │
│  1. Wait 5 seconds (simulated execution)                                          │
│  2. UPDATE irrigation_events: status='completed'                                  │
│     - actual_volume = recommended_volume                                          │
│     - duration_seconds = 300                                                      │
│     - completed_at = NOW()                                                        │
│  3. PUBLISH to Redis channel: irrigation:triggered                               │
└────────────────────────────────┬────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
    ┌──────────────────────┐    ┌──────────────────────┐
    │  SENSOR-SIMULATOR    │    │ NOTIFICATION-SERVICE │
    │                      │    │                      │
    │ Listens for          │    │ Listens for           │
    │ irrigation:triggered │    │ irrigation:triggered │
    │ Increases simulated  │    │ Sends alert/notify   │
    │ moisture readings    │    │ users                │
    └──────────────────────┘    └──────────────────────┘
```

---

## 7. Event Lifecycle

### State Diagram

```
[Prediction Received from Redis]
          │
          ▼
    ┌───────────┐
    │ Evaluate │ ──No──> [Skip: Above threshold]
    │ Threshold│
    └─────┬─────┘
          │Yes
          ▼
    ┌───────────┐
    │ Check     │ ──Yes──> [Skip: Recent event exists]
    │ Recent    │         (Deduplication)
    │ Events   │
    └─────┬─────┘
          │No
          ▼
    ┌─────────────────┐
    │ INSERT Event    │ ──> Status: 'pending'
    │ (store_event)   │
    └─────┬───────────┘
          │
          │ asyncio.create_task
          ▼ (5 second delay)
    ┌───────────────────┐
    │ UPDATE to         │ ──> Status: 'completed'
    │ 'completed'       │       actual_volume set
    └─────┬─────────────┘
          │
          ▼
    ┌─────────────────────┐
    │ PUBLISH to Redis:   │
    │ irrigation:triggered│
    └─────────────────────┘
```

### Event Timeline

| Time | Action | Status |
|------|--------|--------|
| T+0 | Prediction received from Redis | - |
| T+0 | Threshold evaluation passes | - |
| T+0 | Event inserted | `pending` |
| T+0 | Async task started | `pending` |
| T+5 | Execution simulated complete | - |
| T+5 | Event updated | `completed` |
| T+5 | Published to `irrigation:triggered` | `completed` |

---

## 8. Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://irrigation_user:changeme@timescaledb:5432/irrigation_db` | Database connection |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `REDIS_CHANNEL_PREDICTIONS_NEW` | `predictions:new` | Channel for predictions |
| `IRRIGATION_CONTROLLER_PORT` | `8503` | Service port |

### API Endpoints

The irrigation controller exposes these endpoints:

```
GET  /health                    - Health check
GET  /metrics                   - Prometheus metrics
GET  /v1/irrigation/events      - List irrigation events
GET  /v1/irrigation/recent      - List recent events
```

---

## 9. Edge Cases

### 9.1 No Zone Thresholds Found

If zone doesn't exist in the database, the controller logs and skips:

```python
if not thresholds:
    logger.debug(f"No thresholds found for zone {zone_id}")
    return None
```

### 9.2 Prediction Above Threshold

If predicted moisture is above minimum threshold, no irrigation needed:

```python
if prediction >= thresholds["moisture_min"]:
    return None
```

### 9.3 Recent Event Exists (Deduplication)

If irrigation already triggered in last 10 minutes, skip:

```python
if await self._recent_event_exists(zone_id, minutes=10):
    logger.debug(f"Skipping irrigation for zone {zone_id}: recent event exists")
    return None
```

### 9.4 Redis Connection Failure

The controller uses try-except in the message loop to handle errors gracefully:

```python
except Exception as e:
    logger.error(f"Error processing message: {e}")
```

### 9.5 Multiple Sensors per Zone

When zone has multiple sensors (e.g., Zone 2 has 2-s1 and 2-s2):
- Airflow publishes predictions for each sensor
- First prediction triggers irrigation event
- Second prediction is skipped due to deduplication
- Result: 1 event per zone per 10 minutes


═══════════════════════════════════════════════════════════════════

SECTION: ML Pipeline

# MLOps Pipeline: Smart Irrigation

## Overview
The Smart Irrigation System integrates MLOps best practices to ensure models are trained on high-quality data, served reliably, and monitored for performance degradation.

## 1. Feature Store Architecture
We use a **Versioned Feature Store** implemented in TimescaleDB (`feature_references`).
- **Engine**: The `feature-engineering` service computes rolling metrics across windows (30m, 1h, 3h, 24h).
- **Versioning**: Each feature record is tagged with a `model_version` (e.g., `v1`, `v2_candidate`).
- **Consistency**: The same engineering logic is used for both training (batch) and inference (streaming), preventing training-serving skew.

## 2. Model Lifecycle

### Dataset Versioning & Storage
To ensure that models can always be traced back to the data they were trained on, we store every training dataset in **MinIO** (Object Storage).
- **Versioning**: Each training run gets its own unique dataset version stored in the `mlflow-artifacts` bucket.
- **Traceability**: The system automatically tracks which dataset version was used for each model. This allows you to "time travel" and retrain or audit models with the exact same data later.
- **Efficiency**: Downstream tasks pull data directly from MinIO, which is more stable and scalable for large datasets than passing data through temporary memory or databases.

### Scalable Pipeline
The training pipeline is designed to handle large volumes of sensor data without slowing down:
- **Fast Data Preparation**: The logic for building training datasets is optimized to process millions of records efficiently.
- **Traceable Experiments**: We use **MLflow** to track every training attempt, including the exact features used and the resulting performance metrics.
- **Automated Retraining**: Airflow manages the end-to-end flow from data gathering to model registration.

### Experiment Tracking
...

## 3. Data Quality & Malfunction Detection
Before data is used for inference or training, it passes through the **Data Quality Framework**:
- **Plausibility Check**: Hard physical limits (e.g., moisture cannot be > 100%).
- **Malfunction detection**: Identifies stuck sensors or unrealistic jumps that would corrupt ML predictions.
- **Health Filtering**: The system can be configured to ignore readings from sensors marked as `unhealthy` in `v_sensor_health`.

## 4. Monitoring & Drift
- **Shadow Deployment**: New model versions can be deployed in "shadow mode," where they run alongside the champion model. Results are stored in `shadow_predictions` for comparison without affecting irrigation logic.
- **Shadow Comparison**: The `v_shadow_comparison` view calculates deltas between models to validate new candidates.
- **Drift Monitoring**: The `drift-monitor` service (implementation ongoing) tracks statistical changes in input distributions (Moisture Mean Shift) and output residuals.

## 5. Feature Dictionary (Agricultural)
| Feature | Logic | Use Case |
| :--- | :--- | :--- |
| `mean_moisture` | Rolling average | Baseline soil hydration. |
| `roc_moisture` | Rate of change | How fast the soil is drying (evapotranspiration). |
| `std_moisture` | Standard deviation | Sensor stability / noisy data detection. |
| `mean_temp` | Rolling average | Thermal load on crops. |



═══════════════════════════════════════════════════════════════════

SECTION: ML Training Guide

# Model Training Guide: Smart Irrigation

This guide explains when and how model training occurs, the lifecycle of a model candidate, and the specific algorithms used in the Smart Irrigation System.

## 1. Training Schedule (The "When")
Model retraining is fully automated and orchestrated by **Apache Airflow**.

- **Primary Schedule**: The `smart_irrigation_model_training` DAG runs daily at **02:00 AM UTC**.
- **Manual Overrides**: Training can be triggered manually via the Airflow UI or CLI for rapid iteration or emergency retraining after identifying data drift.
- **Automatic Retraining Trigger**: The system is fully autonomous. When the `drift-monitor` service detects significant concept drift or a drop in prediction accuracy, it automatically triggers the Airflow retraining DAG via the REST API. A 1-hour cooldown prevents redundant training cycles.

## 2. Training Workflow (The "How")
The training process follows a "Champion-Challenger" pattern to ensure only superior models reach production.

### Step 1: Dataset Construction
The system fetches raw sensor data and corresponding windowed features from the **TimescaleDB Feature Store**. 

- **Optimized Preparation**: The data gathering logic is optimized to handle millions of records efficiently, significantly reducing the time required to build large training sets.
- **Dataset Versioning**: Once constructed, the training dataset is saved as a versioned artifact (JSON) in **MinIO Object Storage**. 
- **Traceability**: Every training run is linked to a specific dataset version in MLflow. This ensures that you can always pinpoint exactly what data was used to train a specific model, enabling perfect reproducibility.
- **Preprocessing**: It performs **Deduplication**, **Outlier Smoothing**, and **Forward-Filling** for temperature missing values.

### Step 2: Candidate Generation
The pipeline trains and evaluates three distinct types of models:
1. **Linear Regression**: A simple baseline to confirm basic signal presence.
2. **Random Forest**: A robust ensemble model for non-linear relationships.
3. **XGBoost**: A high-performance gradient boosting model.

### Step 3: Hyperparameter Optimization
For the XGBoost candidate, the system uses **Optuna** to perform a Bayesian search for the best hyperparameters:
- `learning_rate`, `max_depth`, `n_estimators`, `subsample`, and `colsample_bytree`.

### Step 4: Time-Aware Evaluation
Models are evaluated using **Time-Aware Cross-Validation** (3 folds). This ensures that we never train on future data to predict the past, maintaining the chronological integrity of the time-series.

### Step 5: Registry & Promotion
The best model (lowest RMSE) is bundled into a **scikit-learn Pipeline** containing a `StandardScaler`.
- **MLflow Registration**: The pipeline is logged to the MLflow Registry.
- **Auto-Promotion**: If the new candidate's RMSE is better than the current Production model by a configurable margin, it is automatically promoted to the `Production` stage.

## 3. Models Used (The "Which")
We prioritize models that offer high accuracy while remaining efficient enough for edge or containerized deployment.

| Model | Role | Strength |
| :--- | :--- | :--- |
| **XGBoost** | Primary Predictor | Excellent at handling complex interactions and missing data. Our current production choice. |
| **Random Forest** | Robust Challenger | Stable, hard to overfit, and provides good baseline metrics. |
| **Linear Regression** | Sanity Check | Lightweight and interpretable; used to detect if the training set has become fundamentally noisy. |

## 4. Serving Logic
Models are served via the `model-server` (FastAPI).
- **Dynamic Reloading**: Every 60 seconds, the server checks MLflow for a new `Production` version and reloads it without downtime.
- **Bundled Scaling**: Because we use Pipelines, the server accepts **raw data** (e.g., moisture = 45.5%) and handles the normalization automatically, preventing "Training-Serving Skew".



═══════════════════════════════════════════════════════════════════

SECTION: ML Exploration

# ML Exploration Report

This file is generated by `python -m mlops.exploration`.

Run the generator against a populated TimescaleDB instance to refresh the report with:

```bash
python -m mlops.exploration
```

The generated report includes:
- dataset coverage and time range
- moisture distribution by soil type
- monthly seasonal patterns
- a sensor reliability snapshot



═══════════════════════════════════════════════════════════════════

SECTION: ML Demo Script

# ML Demo Script

## End-to-End Flow
1. Start the stack with the ML services and monitoring enabled.
2. Show recent `sensor_readings` and the latest `feature_references` rows.
3. Trigger or reference a training run through Airflow and show the resulting MLflow run.
4. Call `POST /v1/predict` on the model server with a recent zone feature vector.
5. Show the new row in `model_predictions`.
6. Show the Redis-driven irrigation event in `irrigation_events`.
7. Open Grafana and highlight prediction throughput, latency, and drift signals.

## Demo Talking Points
- Why soil-specific indices improve agronomic relevance.
- How the model promotion rule prevents regressions.
- How drift alerts surface changing field behavior before silent failures.

## Rehearsal Checklist
- Verify MLflow is reachable.
- Verify `model-server`, `drift-monitor`, and `irrigation-controller` are healthy.
- Verify at least one prediction exists in `model_predictions`.
- Verify the Grafana ML dashboard loads.



═══════════════════════════════════════════════════════════════════

SECTION: Model Card Template

# Soil Moisture Model Card Template

## Training Data
- Sensor source tables:
- Time range:
- Zones included:

## Features Used
- Rolling feature set version:
- Soil-specific indices:
- Excluded columns:

## Evaluation
- RMSE:
- MAE:
- R²:
- Holdout summary:
- Shadow comparison summary:

## Known Limitations
- Sensor quality sensitivity:
- Retraining assumptions:
- Confidence interval caveats:



═══════════════════════════════════════════════════════════════════

SECTION: Jenkins CI/CD

# Jenkins CI/CD Documentation

## Overview

Jenkins automates the CI/CD pipeline for the Smart Irrigation System. It handles:
- Code checkout and preparation
- Linting and type checking
- Unit and integration testing
- Security scanning (OWASP)
- Docker image building
- Publishing to GHCR (GitHub Container Registry)
- Deployment to production

**Location:** `jenkins/` directory

---

## Architecture

### Components

| Component | Purpose | Location |
|-----------|---------|----------|
| Jenkins Controller | Master node, schedules jobs, serves UI | Docker container |
| Python Agent | Lint, test, security scan tasks | Docker container |
| Docker Agent | Build, push, deploy tasks | Docker container |
| Configuration as Code | Declarative setup | `jenkins/casc.yaml` |
| Pipeline Definition | CI/CD stages | `Jenkinsfile` |

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              JENKINS CONTROLLER                                │
│                                                                                 │
│  - Serves UI (port 8081)                                                        │
│  - Schedules jobs                                                              │
│  - Manages agents                                                               │
│  - Configuration as Code (JCasC)                                                │
│  - Zero executors (all work delegated to agents)                               │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
        ┌────────────────────────┴────────────────────────┐
        │              Docker Cloud (dynamic agents)      │
        │                                                 │
        ▼                                                 ▼
┌─────────────────────┐                         ┌─────────────────────┐
│  PYTHON AGENT      │                         │   DOCKER AGENT     │
│                     │                         │                     │
│ - Lint (Ruff)      │                         │ - Docker Build     │
│ - Type Check (mypy)│                         │ - Push to GHCR     │
│ - Unit Tests       │                         │ - Deploy           │
│ - Integration Tests│                         │                     │
│ - Security Scan    │                         │                     │
│ (OWASP)            │                         │                     │
│                     │                         │                     │
│ Max: 4 instances   │                         │ Max: 2 instances   │
└─────────────────────┘                         └─────────────────────┘
```

---

## Configuration as Code (JCasC)

**File:** `jenkins/casc.yaml`

Jenkins is fully configured via YAML - no manual UI setup required.

### Key Settings

```yaml
jenkins:
  # Controller has zero executors - all work goes to agents
  numExecutors: 0
  mode: EXCLUSIVE

  # Security: Local users with admin from env vars
  securityRealm:
    local:
      allowsSignup: false

  # Authorization: Admin has all, anonymous has read
  authorizationStrategy:
    globalMatrix:
      permissions:
        - "Overall/Administer:${JENKINS_ADMIN_USER}"
        - "Overall/Read:anonymous"

  # Docker Cloud: Dynamic agent provisioning
  clouds:
    - docker:
        name: "docker-local"
        dockerApi:
          dockerHost:
            uri: "unix:///var/run/docker.sock"
        templates:
          - name: "python-agent"
            image: "smart-irrigation-python-agent:latest"
            # ... config for python agent

          - name: "docker-agent"
            image: "smart-irrigation-docker-agent:latest"
            # ... config for docker agent
```

### Agent Templates

**Python Agent** (`jenkins/Dockerfile.python-agent`):
- Base: `jenkins/inbound-agent:latest`
- Python 3.11 with venv
- Tools: ruff, mypy, pytest, pytest-cov
- OWASP Dependency-Check
- Max 4 concurrent instances

**Docker Agent** (`jenkins/Dockerfile.docker-agent`):
- Base: `jenkins/inbound-agent:latest`
- Docker CLI + Compose plugin
- Access to host Docker socket
- Max 2 concurrent instances

### Seed Job

Automatically creates the pipeline job on first boot:

```yaml
jobs:
  - script: |
      pipelineJob('smart-irrigation-pipeline') {
        definition {
          cpsScm {
            scm {
              git {
                remote {
                  url("https://github.com/AmineAitLaamim/smart-irrigation.git")
                  credentials('github-creds')
                }
                branches('*/main', '*/develop', '*/devops', '**')
              }
            }
            scriptPath('Jenkinsfile')
          }
        }
        triggers {
          githubPush()
        }
      }
```

---

## Pipeline Stages

**File:** `Jenkinsfile`

### Stage Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           SMART IRRIGATION PIPELINE                              │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐                    │
│  │  CHECKOUT   │───►│  CI CHECKS   │───►│ INTEGRATION     │                    │
│  │             │    │              │    │ TESTS           │                    │
│  └─────────────┘    └──────┬───────┘    └────────┬────────┘                    │
│                            │                       │                             │
│                     ┌──────┴───────┐              │                             │
│                     │ Parallel:    │              │                             │
│                     │ - Ruff      │              │                             │
│                     │ - mypy      │              │                             │
│                     │ - Unit Tests│              │                             │
│                     │ - Security  │              │                             │
│                     └─────────────┘              │                             │
│                                                   ▼                             │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐    ┌───────────┐ │
│  │   DEPLOY    │◄───│   PUBLISH   │◄───│ DOCKER BUILD    │◄───│ SECURITY  │ │
│  │  (main only)│    │  (main only) │    │ (all branches)  │    │  SCAN     │ │
│  └─────────────┘    └──────────────┘    └─────────────────┘    └───────────┘ │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Stage Details

#### 1. Checkout
```groovy
stage('Checkout') {
    agent { label 'python' }
    steps {
        checkout scm
        stash includes: '**', name: 'source'
    }
}
```
- Pulls code from GitHub
- Stashes for use by subsequent stages

#### 2. CI Checks (Parallel)
Runs on all branches in parallel:

**Ruff (Linting):**
```groovy
stage('Ruff') {
    sh 'ruff check services/ --output-format=junit > ruff-report.xml'
}
```

**mypy (Type Checking):**
```groovy
stage('mypy') {
    sh 'python3 -m mypy services/${svc}/src --ignore-missing-imports'
}
```
- Type-checks all 10 services
- Generates JUnit XML for each

**Unit Tests:**
```groovy
stage('Unit Tests') {
    sh 'python3 -m pytest services/${svc}/tests/unit/ --junitxml="unit-${svc}.xml"'
}
```
- Runs unit tests for all services
- Generates test reports

**Security Scan (OWASP):**
```groovy
stage('Security Scan') {
    sh 'dependency-check.sh --scan services/${svc}/requirements.txt'
}
```
- Scans all requirements.txt files
- Checks for known CVEs

#### 3. Integration Tests
```groovy
stage('Integration Tests') {
    when {
        anyOf {
            branch 'main'
            branch 'develop'
            changeRequest target: 'main'
            changeRequest target: 'develop'
        }
    }
    steps {
        sh 'python3 -m pytest services/${svc}/tests/integration/'
    }
}
```
Runs only on:
- `main` branch
- `develop` branch
- PRs targeting `main` or `develop`

#### 4. Docker Build & Verify
```groovy
stage('Docker Build & Verify') {
    agent { label 'docker' }
    steps {
        sh '''
            for svc in $SERVICES; do
                docker build -t "${IMAGE_BASE}/${svc}:${TAG}" -f "services/${svc}/Dockerfile" .
            done
        '''
    }
}
```
- Builds all 10 service images
- Verifies images exist

#### 5. Publish
```groovy
stage('Publish') {
    when { branch 'main' }
    agent { label 'docker' }
    steps {
        sh '''
            docker login ghcr.io -u ${GHCR_USER} -p ${GHCR_TOKEN}
            docker push "${IMAGE_BASE}/${svc}:${TAG}"
            docker push "${IMAGE_BASE}/${svc}:latest"
        '''
    }
}
```
Runs only on `main` branch:
- Logs into GHCR
- Pushes images with tag `main-{GIT_SHA}` and `latest`

#### 6. Deploy
```groovy
stage('Deploy') {
    when { branch 'main' }
    agent { label 'docker' }
    steps {
        sh '''
            docker compose --env-file .env \
                -f docker/docker-compose.yml \
                -f docker/docker-compose.data.yml \
                -f docker/docker-compose.ml.yml \
                -f docker/docker-compose.app.yml \
                up -d
        '''
    }
}
```
Runs only on `main` branch:
- Pulls latest images from GHCR
- Deploys stack with docker compose

---

## Branch Strategy

| Stage | main | develop | devops | feature/* | PR→main | PR→develop |
|-------|------|---------|--------|-----------|---------|-------------|
| Checkout | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Ruff | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| mypy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Unit Tests | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Security Scan | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Integration Tests | ✓ | ✓ | - | - | ✓ | ✓ |
| Docker Build | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Publish | ✓ | - | - | - | - | - |
| Deploy | ✓ | - | - | - | - | - |

---

## Environment Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `REGISTRY` | Jenkinsfile | Container registry (ghcr.io) |
| `IMAGE_BASE` | Jenkinsfile | Image base URL |
| `SERVICES` | Jenkinsfile | Comma-separated service list |
| `GITHUB_USER` | .env | GitHub username |
| `GITHUB_TOKEN` | .env | GitHub PAT for GHCR |
| `JENKINS_ADMIN_USER` | .env | Jenkins admin username |
| `JENKINS_ADMIN_PASSWORD` | .env | Jenkins admin password |

---

## Services

The pipeline builds and deploys these 10 services:

```
api-gateway, data-ingestion, drift-monitor, feature-engineering,
irrigation-controller, model-server, notification-service,
sensor-simulator, user-service, web-dashboard
```

---

## Running Jenkins

### Start Jenkins
```bash
make jenkins
# Or via full stack
make up
```

### Access UI
- URL: http://localhost:8081
- Credentials: From `.env` (JENKINS_ADMIN_USER, JENKINS_ADMIN_PASSWORD)

### Trigger Pipeline
```bash
# Via UI: Click "Play" on smart-irrigation-pipeline

# Via CLI
docker exec jenkins jenkins-cli trigger smart-irrigation-pipeline
```

### Check Build Status
```bash
docker logs jenkins
```

---

## Build Custom Agents

```bash
make build-jenkins-agents
```

Builds:
- `smart-irrigation-python-agent:latest`
- `smart-irrigation-docker-agent:latest`

---

## Troubleshooting

### Agent Won't Start
```bash
# Check Docker socket permissions
ls -la /var/run/docker.sock

# Check agent logs
docker logs jenkins
```

### Pipeline Stuck
```bash
# Cancel running build
docker exec jenkins jenkins-cli cancel-build smart-irrigation-pipeline
```

### GHCR Push Fails
```bash
# Verify credentials
echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USER --password-stdin
```

---

## Summary

| Feature | Implementation |
|---------|---------------|
| Configuration | JCasC (YAML file) |
| Pipeline | Declarative (Jenkinsfile) |
| Agents | Dynamic Docker containers |
| Trigger | GitHub webhook (push + PR) |
| Linting | Ruff |
| Type Check | mypy |
| Testing | pytest |
| Security | OWASP Dependency-Check |
| Registry | GHCR (GitHub Container Registry) |
| Deployment | docker compose |

The Jenkins pipeline provides automated CI/CD with security scanning, testing, and production deployment all orchestrated through Configuration as Code.


═══════════════════════════════════════════════════════════════════

SECTION: Airflow DAG Pipeline

# Airflow DAG Documentation

## Overview

Apache Airflow orchestrates the MLOps pipeline for the Smart Irrigation System. It handles:
1. Dataset preparation from sensor data
2. Model training (baseline + XGBoost)
3. Model evaluation and promotion to production
4. **Prediction generation** (scheduled, not real-time)

**Location:** `airflow/dags/smart_irrigation_dags.py`

---

## Two Prediction Paths

The system has **two ways** to generate predictions:

### 1. Real-Time Predictions (Primary)

```
Feature Engineering → [features:computed] → Model Server → [predictions:new] → Irrigation Controller
```

- Triggered when new sensor data arrives
- Model Server subscribes to Redis `features:computed`
- Runs inference immediately
- Publishes to `predictions:new` channel

### 2. Scheduled Predictions (Airflow)

```
Airflow DAG: scheduled_zone_predictions → model-server API → [predictions:new] → Irrigation Controller
```

- Runs daily at 2:00 AM UTC
- Queries all active zones from database
- Calls model-server REST API (`/v1/predict`)
- Stores predictions in `model_predictions` table
- Publishes to `predictions:new` channel

| Aspect | Real-Time | Scheduled (Airflow) |
|--------|-----------|---------------------|
| Trigger | New sensor data | Cron (daily 2am) |
| Latency | ~10-15 seconds | Minutes |
| Use Case | Immediate irrigation | Batch predictions |
| Method | Redis subscription | REST API call |

---

## DAG Configuration

```python
with DAG(
    dag_id="smart_irrigation_model_training",
    description="Feature refresh, model training, evaluation, and MLflow promotion.",
    schedule="0 2 * * *",  # Runs daily at 2:00 AM UTC
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["mlops", "training"],
) as dag:
```

| Property | Value | Description |
|----------|-------|-------------|
| dag_id | `smart_irrigation_model_training` | Unique identifier |
| schedule | `0 2 * * *` | Cron: Daily at 2:00 AM UTC |
| catchup | `false` | Don't run missed DAGs |
| retries | 1 | Retry failed tasks once |
| retry_delay | 5 minutes | Wait between retries |

---

## Task Flow

```
┌─────────────────────────┐
│   prepare_dataset       │  ← Build dataset from TimescaleDB sensor data
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  train_candidate_models │  ← Train baseline + XGBoost models
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ evaluate_and_register   │  ← Evaluate, compare with production, promote
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ export_training_summary │  ← Save training results to JSON
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ scheduled_zone_predictions│ ← Generate predictions, publish to Redis
└─────────────────────────┘
```

---

## Task Details

### 1. prepare_dataset

**Purpose:** Fetch sensor data from TimescaleDB and create a training dataset.

```python
def prepare_dataset(**context):
    dataset = asyncio.run(build_dataset_from_database())
    mlflow_info = log_dataset_to_mlflow(dataset)
    
    # Push to XCom for downstream tasks
    context["ti"].xcom_push(key="dataset_run_id", value=mlflow_info["run_id"])
    context["ti"].xcom_push(key="dataset_artifact_path", value=mlflow_info["artifact_path"])
    context["ti"].xcom_push(key="dataset_metadata", value=dataset.metadata)
    context["ti"].xcom_push(key="feature_columns", value=dataset.feature_columns)
```

**What it does:**
1. Calls `build_dataset_from_database()` from `mlops/dataset_pipeline.py`
2. Fetches sensor readings, feature references, and predictions
3. Creates a structured dataset with features and labels
4. Logs the dataset to MLflow as an artifact
5. Passes dataset info via XCom to next task

**Outputs (XCom):**
- `dataset_run_id`: MLflow run ID for the dataset
- `dataset_artifact_path`: Path to dataset artifact
- `dataset_metadata`: Dataset metadata
- `feature_columns`: List of feature column names

---

### 2. train_candidate_models

**Purpose:** Train multiple models and select the best one.

```python
def train_candidate_models(**context):
    dataset = _load_dataset_from_mlflow(run_id, artifact_path, metadata, feature_columns)
    
    baseline_runs = run_baseline_models(dataset)
    xgboost_run = run_xgboost_training(dataset)
    all_runs = [*baseline_runs, xgboost_run]
    best_run = choose_best_run(all_runs)
    
    context["ti"].xcom_push(key="baseline_runs", value=...)
    context["ti"].xcom_push(key="best_run", value=...)
```

**What it does:**
1. Loads dataset from MLflow (created by previous task)
2. Trains baseline models (simple heuristics for comparison)
3. Trains XGBoost model with hyperparameter tuning
4. Compares all models using RMSE metric
5. Selects the best performing model

**Models trained:**
- Baseline models (simple heuristics)
- XGBoost (gradient boosted decision trees)

**Outputs (XCom):**
- `baseline_runs`: Results from all baseline models
- `best_run`: The best performing model result

---

### 3. evaluate_and_register

**Purpose:** Evaluate model against production and promote if better.

```python
def evaluate_and_register(**context):
    production_rmse = load_production_rmse(client, MLFLOW_REGISTERED_MODEL_NAME)
    decision = decide_promotion(best_run.metrics.rmse, production_rmse)
    mlflow_result = log_training_to_mlflow(dataset, baseline_runs, best_run)
    
    if decision.should_promote:
        promote_model(client, MLFLOW_REGISTERED_MODEL_NAME, mlflow_result["version"], decision.target_stage)
```

**What it does:**
1. Loads current production model RMSE from MLflow
2. Compares new model RMSE with production RMSE
3. Decides whether to promote (if new model is better)
4. Logs training results to MLflow
5. Promotes model to appropriate stage (Staging/Production)

**Promotion Logic:**
```
if new_rmse < production_rmse:
    promote to Production
elif new_rmse < production_rmse * 1.1:
    promote to Staging
else:
    don't promote
```

**Outputs (XCom):**
- `promotion_result`: Contains decision, best_run, and MLflow info

---

### 4. export_training_summary

**Purpose:** Save training summary to a JSON file for external access.

```python
def export_training_summary(**context):
    result = context["ti"].xcom_pull(key="promotion_result", task_ids="evaluate_and_register")
    summary_dir = ROOT_DIR / "airflow" / "artifacts"
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / "latest_training_summary.json"
    summary_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return str(summary_path)
```

**What it does:**
1. Retrieves promotion result from previous task
2. Creates `airflow/artifacts` directory if not exists
3. Writes summary JSON to `latest_training_summary.json`

**Output file:** `airflow/artifacts/latest_training_summary.json`

---

### 5. scheduled_zone_predictions

**Purpose:** Generate predictions for all zones and publish to Redis for irrigation controller.

```python
def scheduled_zone_predictions(**context):
    async def _run():
        conn = await asyncpg.connect(DATABASE_URL)
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        
        zones = await conn.fetch("SELECT DISTINCT zone_id, sensor_id FROM sensor_metadata WHERE active = TRUE")
        
        for row in zones:
            # Get latest sensor reading
            latest_reading = await conn.fetchrow(
                "SELECT moisture FROM sensor_readings WHERE zone_id = $1 AND sensor_id = $2 ORDER BY timestamp DESC LIMIT 1",
                row["zone_id"], row["sensor_id"]
            )
            
            # Call model-server for prediction
            response = await client.post(f"{MODEL_SERVER_REST_URL}/v1/predict", json={...})
            payload = response.json()
            
            # Store prediction in database
            await conn.execute("INSERT INTO model_predictions ...")
            
            # PUBLISH to Redis
            await redis_client.publish(REDIS_CHANNEL_PREDICTIONS_NEW, json.dumps({...}))
```

**What it does:**
1. Fetches all active zones and sensors from database
2. For each zone/sensor:
   - Gets latest sensor reading
   - Calls model-server for prediction
   - Stores prediction in `model_predictions` table
   - **Publishes to Redis `predictions:new` channel**

**Key point:** This task bridges ML predictions to the irrigation controller via Redis pub/sub.

**Redis message format:**
```json
{
  "zone_id": "2",
  "sensor_id": "2-s1",
  "prediction": 36.66,
  "model_version": "1",
  "predicted_at": "2026-05-03T02:00:00"
}
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://irrigation_user:changeme@timescaledb:5432/irrigation_db` | Database connection |
| `MLFLOW_TRACKING_URI` | `http://mlflow:5000` | MLflow server URL |
| `MLFLOW_REGISTERED_MODEL_NAME` | `smart-irrigation-soil-moisture` | Model name in MLflow |
| `MODEL_SERVER_REST_URL` | `http://model-server:8501` | Model server API |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `REDIS_CHANNEL_PREDICTIONS_NEW` | `predictions:new` | Channel for predictions |

---

## Running the DAG

### Manual Trigger

```bash
# Via Airflow CLI
docker exec airflow airflow dags trigger smart_irrigation_model_training

# Via Airflow UI
# 1. Open http://localhost:8082
# 2. Find "smart_irrigation_model_training" DAG
# 3. Click "Play" button to trigger
```

### Check DAG Runs

```bash
docker exec airflow airflow dags list-runs -d smart_irrigation_model_training
```

### Test Individual Task

```bash
# Test the predictions task with a specific execution date
docker exec airflow airflow tasks test smart_irrigation_model_training scheduled_zone_predictions 2026-05-03
```

---

## Output Artifacts

### Training Summary JSON

Location: `airflow/artifacts/latest_training_summary.json`

Example content:
```json
{
  "decision": {
    "should_promote": true,
    "target_stage": "Production",
    "new_rmse": 5.2,
    "production_rmse": 6.1
  },
  "best_run": {
    "model_name": "XGBoost",
    "metrics": {"rmse": 5.2, "mae": 3.1, "r2": 0.89},
    "params": {"max_depth": 6, "learning_rate": 0.1}
  },
  "mlflow": {
    "run_id": "abc123",
    "version": 5
  }
}
```

---

## Integration with Other Components

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         AIRFLOW DAG                                        │
│                                                                        │
│  1. prepare_dataset ──► Pulls from:                                     │
│     - sensor_readings (TimescaleDB)                                     │
│     - feature_references (TimescaleDB)                                 │
│     - model_predictions (TimescaleDB)                                   │
│                                                                        │
│  2. train_candidate_models ──► Uses:                                    │
│     - Dataset from prepare_dataset                                      │
│     - MLflow for experiment tracking                                    │
│                                                                        │
│  3. evaluate_and_register ──► Uses:                                     │
│     - MLflow for model registry                                         │
│     - Compares with current production model                           │
│                                                                        │
│  4. scheduled_zone_predictions ──► Publishes to:                         │
│     - Redis: predictions:new                                           │
│     - TimescaleDB: model_predictions                                   │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │
                                 │ Redis: predictions:new
                                 ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                   IRRIGATION-CONTROLLER                                   │
│                                                                        │
│ - Subscribes to predictions:new                                         │
│ - Triggers irrigation based on thresholds                               │
│ - Auto-completes events after 5 seconds                                │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Summary

| Task | Function | Output |
|------|----------|--------|
| prepare_dataset | Build training dataset from DB | Dataset in MLflow |
| train_candidate_models | Train baseline + XGBoost | Best model selection |
| evaluate_and_register | Compare with production, promote | Model promotion |
| export_training_summary | Save summary JSON | JSON file |
| scheduled_zone_predictions | Generate and publish predictions | Redis message |

The Airflow DAG orchestrates the complete ML lifecycle from data preparation to model serving, with the final task bridging to the irrigation controller via Redis. |


═══════════════════════════════════════════════════════════════════

SECTION: Web Dashboard

# Web Dashboard Documentation

## Overview

The Web Dashboard is a React/Next.js application that provides a user-friendly interface for:
- **Authentication** - Login, register, session management
- **Zone Monitoring** - Real-time sensor data visualization
- **Predictions** - Model prediction display
- **Irrigation History** - Historical irrigation events
- **Zone Management** - Create and configure zones

**Location:** `services/web-dashboard/`

**Port:** 3000

---

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         WEB DASHBOARD (Next.js App)                           │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        Next.js Pages                                     │   │
│  │                                                                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │   │
│  │  │ (auth)      │  │ (dashboard)  │  │             │  │            │  │   │
│  │  │             │  │              │  │             │  │            │  │   │
│  │  │ - Login    │  │ - Dashboard │  │ - Zones     │  │ - History  │  │   │
│  │  │ - Register│  │ - Overview  │  │ - Zone [id] │  │ - Settings │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        Custom Hooks                                       │   │
│  │                                                                          │   │
│  │  useZones()          - Zone CRUD operations                              │   │
│  │  useSensorData()    - Sensor readings (moisture, temperature)          │   │
│  │  usePredictions()   - Model predictions                                │   │
│  │  useIrrigationEvents() - Irrigation event history                     │   │
│  │  useZonesOverviewChart() - Chart data for dashboard                   │   │
│  │                                                                          │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        State Management                                  │   │
│  │                                                                          │   │
│  │  authStore   - User authentication state                               │   │
│  │  uiStore     - UI state (sidebar, theme, etc)                         │   │
│  │                                                                          │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            API Layer                                          │
│                                                                                 │
│  lib/api.ts ───► API Client with:                                           │
│  - Auto token refresh                                                        │
│  - Error handling                                                           │
│  - Cookie-based auth                                                        │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        API Gateway (8080)                                     │
│                                                                                 │
│  Proxied to: user-service, irrigation-controller, model-server, etc.         │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Technology | Purpose |
|------------|----------|
| Next.js 14+ | React framework with App Router |
| TypeScript | Type safety |
| Tailwind CSS | Styling |
| Zustand | State management |
| Recharts | Data visualization |
| shadcn/ui | UI components |

---

## Page Structure

### Authentication Pages

```
/login    - User login
/register - User registration
```

### Dashboard Pages

```
/dashboard      - Overview with charts and metrics
/zones          - List all zones
/zones/[id]     - Zone detail with sensor data
/history        - Irrigation event history
/settings       - User settings
```

---

## Custom Hooks

### useZones

```typescript
const { zones, loading, createZone, updateZone, deleteZone } = useZones()
```

**Features:**
- Fetch all zones
- Create new zone
- Update existing zone
- Delete zone (owner only)

### useSensorData

```typescript
const { readings, latest, loading } = useSensorData(zoneId, hours)
```

**Features:**
- Fetch sensor readings for last N hours
- Get latest reading per sensor
- Real-time updates

### usePredictions

```typescript
const { predictions, loading } = usePredictions(zoneId, hours)
```

**Features:**
- Fetch model predictions
- Display prediction confidence

### useIrrigationEvents

```typescript
const { events, loading } = useIrrigationEvents(zoneId, limit)
```

**Features:**
- Fetch irrigation events
- Show trigger reason
- Display status (pending/completed)

### useZonesOverviewChart

```typescript
const { chartData, loading } = useZonesOverviewChart()
```

**Features:**
- Aggregated data for dashboard charts
- Zone comparison

---

## API Client

### lib/api.ts

The API client provides a wrapper around fetch with automatic token refresh:

```typescript
export const api = {
  get:    <T>(path: string) => request<T>(path),
  post:   <T>(path: string, body: unknown) => request<T>(path, { method: "POST", body: ... }),
  put:    <T>(path: string, body: unknown) => request<T>(path, { method: "PUT", body: ... }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
}
```

**Features:**
- Automatic token refresh on 401
- Cookie-based authentication (httpOnly cookies)
- JSON content type
- Error handling

### Token Refresh Flow

```
Request fails with 401
        │
        ▼
POST /api/auth/refresh (uses cookie)
        │
        ├── Success ──► Retry original request
        │
        └── Failure ──► Redirect to /login
```

---

## State Management

### authStore

```typescript
interface AuthState {
  user: User | null
  isAuthenticated: boolean
  login: (email, password) => Promise<void>
  logout: () => Promise<void>
  refreshToken: () => Promise<void>
}
```

### uiStore

```typescript
interface UIState {
  sidebarOpen: boolean
  theme: 'light' | 'dark'
  toggleSidebar: () => void
  setTheme: (theme) => void
}
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | (empty string) | Backend API base URL |

---

## Configuration

### Docker Compose

```yaml
web-dashboard:
  image: web-dashboard:latest
  ports:
    - "3000:3000"
  environment:
    - NEXT_PUBLIC_API_URL=http://api-gateway:8080
  depends_on:
    - api-gateway
```

### Next.js Config (next.config.ts)

```typescript
const nextConfig = {
  // Output: 'standalone' for minimal container size
  // API rewrites for proxying
}
```

---

## Data Visualization

### Dashboard Overview

- Zone status cards (active zones, sensors online)
- Moisture trends chart (line chart)
- Recent irrigation events
- Quick stats (total water used, events today)

### Zone Detail

- Real-time sensor readings
- Temperature and moisture gauges
- Historical data charts
- Irrigation event timeline

### History Page

- Pagination of all irrigation events
- Filter by zone
- Sort by date/status

---

## Authentication Flow

### Login

1. User submits credentials to `/api/auth/login`
2. Backend returns access + refresh tokens (as cookies)
3. Redirect to `/dashboard`

### Protected Routes

All dashboard routes are protected and redirect to `/login` if not authenticated.

### Token Refresh

- Access token expires after 15 minutes
- Automatic refresh via `/api/auth/refresh`
- Refresh token valid for 7 days

---

## Example Usage

### Using the API Client

```typescript
import { api } from '@/lib/api'

// Get zones
const zones = await api.get<Zone[]>('/v1/zones')

// Create zone
await api.post('/v1/zones', {
  zone_name: 'Garden',
  soil_type: 'loam',
  moisture_min: 30,
  moisture_max: 60
})

// Get sensor data
const readings = await api.get<SensorReading[]>(`/v1/zones/${zoneId}/sensors?hours=24`)
```

### Using Hooks

```typescript
import { useZones, useSensorData, useIrrigationEvents } from '@/hooks'

function ZoneDetail({ zoneId }) {
  const { zone, loading } = useZone(zoneId)
  const { readings } = useSensorData(zoneId, 24)
  const { events } = useIrrigationEvents(zoneId, 20)

  return (
    <div>
      <h1>{zone?.zone_name}</h1>
      <Chart data={readings} />
      <EventList events={events} />
    </div>
  )
}
```

---

## Component Library

The dashboard uses shadcn/ui components:
- Button, Card, Input, Select
- Dialog, Dropdown, Popover
- Table, Pagination
- Form components
- Charts (Recharts)

---

## Monitoring

### Development

```bash
npm run dev
# Open http://localhost:3000
```

### Production Build

```bash
npm run build
npm start
```

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Framework | Next.js 14+ (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS |
| State | Zustand |
| Charts | Recharts |
| API | REST via API Gateway |
| Auth | JWT + Cookies |
| Port | 3000 |

The Web Dashboard provides a complete user interface for monitoring and managing the Smart Irrigation System, with real-time sensor data, predictions display, and irrigation history.


═══════════════════════════════════════════════════════════════════

SECTION: Prometheus Monitoring

# Prometheus Monitoring

## Overview

Prometheus collects metrics from all Smart Irrigation services, stores them time-series, and triggers alerts based on configurable rules. It integrates with Grafana for visualization and Alertmanager for alert routing.

**Port:** 9090

**Config:** `configs/monitoring/prometheus.yml`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         SERVICES (Metrics Producers)                          │
│                                                                                 │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐   │
│  │ API Gateway  │ │User Service │ │Notification │ │   Data Ingestion   │   │
│  │   :8080      │ │   :5005     │ │  Service    │ │      :8001         │   │
│  │   /metrics   │ │   /metrics   │ │   :8505     │ │     /metrics       │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────────────────┘   │
│                                                                                 │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐   │
│  │Feature Eng.  │ │ Data Quality │ │ Model Server │ │  Irrigation Ctrl   │   │
│  │   :8004      │ │   :8005      │ │   :8501      │ │      :8503         │   │
│  │   /metrics   │ │   /metrics   │ │   /metrics   │ │     /metrics       │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      PROMETHEUS (:9090)                                        │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    Scrape Configuration                                 │   │
│  │                                                                          │   │
│  │  scrape_interval: 15s                                                   │   │
│  │  evaluation_interval: 15s                                               │   │
│  │  10 jobs (one per service)                                             │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    Alert Rules                                          │   │
│  │                                                                          │   │
│  │  - service-availability  (service down)                               │   │
│  │  - application-health    (latency, errors, drift)                     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    Storage                                              │   │
│  │                                                                          │   │
│  │  retention: 15 days                                                    │   │
│  │  TSDB path: /prometheus                                                │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      ALERTMANAGER (:9093)                                      │
│                                                                                 │
│  Routes alerts based on severity and dispatches via email/webhook            │
└────────────────────────────────────────────────┬────────────────────────────────┘
                                                 │
                                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      GRAFANA (:3001)                                          │
│                                                                                 │
│  Dashboards for system health, sensor metrics, ML performance                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Scrape Configuration

### prometheus.yml

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    project: smart-irrigation

rule_files:
  - /etc/prometheus/alert_rules.yml

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: [prometheus:9090]

  - job_name: api-gateway
    metrics_path: /metrics
    static_configs:
      - targets: [api-gateway:8080]

  - job_name: user-service
    metrics_path: /metrics
    static_configs:
      - targets: [user-service:5005]

  # ... (one job per service)
```

### Service Targets

| Service | Port | Metrics Path |
|---------|------|--------------|
| api-gateway | 8080 | /metrics |
| user-service | 5005 | /metrics |
| notification-service | 8505 | /metrics |
| data-ingestion | 8001 | /metrics |
| feature-engineering | 8004 | /metrics |
| data-quality | 8005 | /metrics |
| model-server | 8501 | /metrics |
| drift-monitor | 8502 | /metrics |
| irrigation-controller | 8503 | /metrics |

---

## Alert Rules

### alert_rules.yml

#### Service Availability

```yaml
- alert: SmartIrrigationServiceDown
  expr: up{job=~"api-gateway|user-service|..."} == 0
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Service {{ $labels.job }} is down"
    description: "Prometheus cannot scrape..."
```

#### Application Health

| Alert | Expression | For | Severity |
|-------|------------|-----|----------|
| ApiGatewayHigh5xxRate | 5xx ratio > 5% | 10m | warning |
| UserServiceHighLatency | p95 > 1s | 10m | warning |
| DataIngestionProcessingStalled | no new readings in 15m | 15m | critical |
| FeatureEngineeringErrorsIncreasing | errors > 0 | 5m | warning |
| ModelServerErrorRateHigh | errors > 5 | 10m | warning |
| DriftSignalExceeded | KL > 0.5 or PH > 50 | 10m | warning |
| UnhealthySensorsDetected | max health status >= 2 | 10m | warning |

---

## Query Examples

### Service Uptime

```promql
up{job="api-gateway"}
```

### Request Rate (API Gateway)

```promql
rate(api_gateway_http_requests_total[5m])
```

### Error Rate (Data Ingestion)

```promql
rate(data_ingestion_errors_total[5m])
```

### Sensor Health Status

```promql
data_quality_sensor_health_status
```

### Model Prediction Latency

```promql
histogram_quantile(0.95, rate(model_server_prediction_duration_seconds_bucket[5m]))
```

---

## Docker Compose

```yaml
prometheus:
  image: prom/prometheus:latest
  ports:
    - "9090:9090"
  command:
    - "--config.file=/etc/prometheus/prometheus.yml"
    - "--storage.tsdb.path=/prometheus"
    - "--storage.tsdb.retention.time=15d"
    - "--web.enable-lifecycle"
  volumes:
    - ../configs/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    - ../configs/monitoring/alert_rules.yml:/etc/prometheus/alert_rules.yml:ro
    - prometheus_data:/prometheus
  networks:
    - irrigation_net
```

---

## Environment Variables

From `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `PROMETHEUS_SCRAPE_INTERVAL` | 15s | Scrape interval |

---

## Accessing Prometheus

**Web UI:** http://localhost:9090

**Graph queries:** http://localhost:9090/graph

**Alerts page:** http://localhost:9090/alerts

---

## Integration

### Alertmanager

Prometheus sends firing alerts to Alertmanager:

```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093
```

### Grafana

Grafana connects to Prometheus as a datasource:

```yaml
# configs/monitoring/grafana/datasources.yml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    access: proxy
```

---

## Metrics by Service

### API Gateway

- `api_gateway_http_requests_total` (counter)
- `api_gateway_request_duration_seconds` (histogram)

### User Service

- `user_service_request_duration_seconds` (histogram)
- `user_service_login_attempts_total` (counter)

### Data Ingestion

- `data_ingestion_total_processed` (gauge)
- `data_ingestion_valid_readings` (gauge)
- `data_ingestion_anomalies_flagged` (gauge)
- `data_ingestion_errors_total` (counter)

### Data Quality

- `data_quality_readings_checked_total` (counter)
- `data_quality_anomalies_detected_total` (counter)
- `data_quality_active_rules` (gauge)
- `data_quality_sensor_health_status` (gauge)

### Model Server

- `model_server_predictions_total` (counter)
- `model_server_prediction_duration_seconds` (histogram)
- `model_server_errors_total` (counter)

### Irrigation Controller

- `irrigation_triggers_total` (counter)
- `irrigation_events_active` (gauge)

### Drift Monitor

- `drift_monitor_kl_divergence` (gauge)
- `drift_monitor_page_hinkley_score` (gauge)

---

## Summary

| Aspect | Value |
|--------|-------|
| Port | 9090 |
| Scrape Interval | 15s |
| Evaluation Interval | 15s |
| Retention | 15 days |
| Alert Rules | `configs/monitoring/alert_rules.yml` |
| Targets | 10 services |
| Integration | Grafana, Alertmanager |

Prometheus provides centralized metrics collection and alerting for all Smart Irrigation services.


═══════════════════════════════════════════════════════════════════

SECTION: Grafana Dashboards

# Grafana Dashboards

## Overview

Grafana provides visualization dashboards for the Smart Irrigation System, connected to Prometheus as the data source. It includes pre-configured dashboards for sensor operations and ML performance monitoring.

**Port:** 3001

**Default credentials:** admin / grafana_dev (from `.env`)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              GRAFANA (:3001)                                   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                       Dashboards                                        │   │
│  │                                                                          │   │
│  │  ┌──────────────────────┐      ┌───────────────────────────────────┐   │   │
│  │  │  Sensor Operations   │      │      ML Performance              │   │   │
│  │  │                      │      │                                   │   │   │
│  │  │ - Sensor health      │      │ - Predictions served            │   │   │
│  │  │ - Ingestion counts   │      │ - Model latency (p95)           │   │   │
│  │  │ - Anomaly detection  │      │ - Drift signals (KL, PH)        │   │   │
│  │  │ - Per-sensor status  │      │ - Irrigation events             │   │   │
│  │  │                      │      │ - Notification deliveries      │   │   │
│  │  └──────────────────────┘      └───────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      PROMETHEUS (:9090)                                        │
│                                                                                 │
│  Datasource: http://prometheus:9090                                           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Dashboards

### Sensor Operations

**UID:** `smart-irrigation-sensors`

**URL:** http://localhost:3001/d/smart-irrigation-sensors

**Panels:**

| Panel | Metric | Description |
|-------|--------|-------------|
| Worst Sensor Health | `max(data_quality_sensor_health_status)` | 0=healthy, 1=degraded, 2=unhealthy |
| Total Ingested Readings | `data_ingestion_total_processed` | Cumulative readings processed |
| Anomaly Detection Rate | `rate(data_quality_anomalies_detected_total[5m])` | Anomalies per second by type |
| Ingestion Pipeline Counters | `data_ingestion_valid_readings`, `data_ingestion_anomalies_flagged` | Valid vs flagged readings |
| Per-Sensor Health Status | `data_quality_sensor_health_status` | Health per zone/sensor |

**Time range:** Last 24 hours (auto-refresh: 30s)

**Tags:** smart-irrigation, sensors

---

### ML Performance

**UID:** `smart-irrigation-ml`

**URL:** http://localhost:3001/d/smart-irrigation-ml

**Panels:**

| Panel | Metric | Description |
|-------|--------|-------------|
| Predictions Served | `model_server_predictions_total` | Total predictions made |
| Current KL Divergence | `drift_monitor_kl_divergence` | Data drift (threshold: 0.2 warning, 0.5 critical) |
| Current Page-Hinkley Score | `drift_monitor_page_hinkley_score` | Concept drift (threshold: 20 warning, 50 critical) |
| Model Server p95 Latency | `histogram_quantile(0.95, ...)` | Prediction latency |
| Drift Signals | `drift_monitor_kl_divergence`, `drift_monitor_mean_error` | Drift over time |
| Irrigation Events | `irrigation_controller_events_total` | Triggered irrigation events |
| Notification Deliveries | `notification_service_deliveries_total` | Email/webhook delivery status |

**Time range:** Last 24 hours (auto-refresh: 30s)

**Tags:** smart-irrigation, ml

---

## Configuration

### datasources.yml

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    uid: prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

### dashboards.yml

```yaml
apiVersion: 1
providers:
  - name: Smart Irrigation Dashboards
    orgId: 1
    folder: Smart Irrigation
    type: file
    disableDeletion: false
    editable: true
    options:
      path: /var/lib/grafana/dashboards
```

### Dashboard Files

| File | Dashboard |
|------|-----------|
| `dashboard_sensors.json` | Sensor Operations |
| `dashboard_ml.json` | ML Performance |

---

## Docker Compose

```yaml
grafana:
  image: grafana/grafana:latest
  ports:
    - "3001:3000"
  environment:
    - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER}
    - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
    - GF_USERS_ALLOW_SIGN_UP=false
  volumes:
    - grafana_data:/var/lib/grafana
    - ../configs/monitoring/grafana/dashboards.yml:/etc/grafana/provisioning/dashboards/dashboards.yml:ro
    - ../configs/monitoring/grafana/datasources.yml:/etc/grafana/provisioning/datasources/datasources.yml:ro
    - ../configs/monitoring/grafana:/var/lib/grafana/dashboards:ro
  networks:
    - irrigation_net
  depends_on:
    prometheus:
      condition: service_healthy
```

---

## Environment Variables

From `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `GRAFANA_ADMIN_USER` | admin | Admin username |
| `GRAFANA_ADMIN_PASSWORD` | grafana_dev | Admin password |

---

## Accessing Grafana

**URL:** http://localhost:3001

**Login:** admin / grafana_dev

**Explore queries:** http://localhost:3001/explore

**Alerting:** http://localhost:3001/alerting

---

## Adding Custom Panels

### Query Examples

**Service uptime:**
```promql
up{job="data-ingestion"}
```

**Data ingestion rate:**
```promql
rate(data_ingestion_total_processed[5m])
```

**Error rate by service:**
```promql
sum by (job) (rate(prometheus_target_scrapes_exceeded_target_limit_total[5m]))
```

**Memory usage (if exposed):**
```promql
container_memory_usage_bytes{container_name="irrigation-controller"}
```

### Panel Types

- **Stat** - Single value with thresholds
- **Time series** - Line/area charts over time
- **Table** - Tabular data
- **Gauge** - Numeric with ranges

---

## Alerts Integration

Grafana can trigger alerts based on panel queries:

1. Open a panel → Click alert icon
2. Configure conditions (e.g., `max > 2` for sensor health)
3. Set notification channel (email, Slack, webhook)
4. Save dashboard

**Note:** Prometheus alerts are defined in `alert_rules.yml` and managed via Alertmanager. Grafana alerts are independent.

---

## Summary

| Aspect | Value |
|--------|-------|
| Port | 3001 |
| Default login | admin / grafana_dev |
| Datasource | Prometheus (http://prometheus:9090) |
| Dashboards | 2 (Sensor Operations, ML Performance) |
| Auto-refresh | 30 seconds |
| Time range | 24 hours |

Grafana provides real-time visibility into sensor health, data pipeline performance, and ML model behavior.


═══════════════════════════════════════════════════════════════════

SECTION: Alertmanager

# Alertmanager

## Overview

Alertmanager handles alerts sent by Prometheus, manages routing and deduplication, and dispatches notifications via webhooks. In the Smart Irrigation System, it forwards alerts to the notification-service which then sends email/webhook notifications.

**Port:** 9093

**Config:** `configs/monitoring/alertmanager.yml`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       PROMETHEUS (:9090)                                       │
│                                                                                 │
│  Evaluates alert_rules.yml                                                     │
│  Fires alerts to Alertmanager                                                  │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     ALERTMANAGER (:9093)                                       │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                       Routing Tree                                       │   │
│  │                                                                          │   │
│  │  All alerts ──────────────────────────────────────────────────────────┐   │   │
│  │                              │                                        │   │
│  │              ┌───────────────┴───────────────┐                        │   │
│  │              │                               │                        │   │
│  │         critical (10s wait)           warning (30s wait)             │   │
│  │              │                               │                        │   │
│  │              └───────────────┬───────────────┘                        │   │
│  │                              │                                        │   │
│  └──────────────────────────────┼───────────────────────────────────────┘   │
│                                 │                                            │
│                                 ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                       Receivers                                         │   │
│  │                                                                          │   │
│  │  - notification-service (webhook)                                      │   │
│  │  - email (via notification-service)                                    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                     Inhibit Rules                                      │   │
│  │                                                                          │   │
│  │  critical alerts inhibit warning alerts for same alertname/job        │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                  NOTIFICATION SERVICE (:8505)                                 │
│                                                                                 │
│  Receives alerts via webhook → sends email/webhook to end users               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Configuration

### alertmanager.yml

```yaml
global:
  resolve_timeout: 5m

route:
  receiver: notification-service
  group_by:
    - alertname
    - job
    - severity
  group_wait: 15s
  group_interval: 1m
  repeat_interval: 4h
  routes:
    - matchers:
        - severity="critical"
      receiver: notification-service
      group_wait: 10s
      repeat_interval: 30m
    - matchers:
        - severity="warning"
      receiver: notification-service
      group_wait: 30s
      repeat_interval: 2h

receivers:
  - name: notification-service
    webhook_configs:
      - url: http://notification-service:8505/alerts/webhook
        send_resolved: true

inhibit_rules:
  - source_matchers:
      - severity="critical"
    target_matchers:
      - severity="warning"
    equal:
      - alertname
      - job
```

### Configuration Explained

| Setting | Value | Description |
|---------|-------|-------------|
| `group_by` | alertname, job, severity | How to group alerts |
| `group_wait` | 15s | Wait before sending first notification |
| `group_interval` | 1m | Interval between grouped alerts |
| `repeat_interval` | 4h | Repeat alert if still firing |
| `group_wait` (critical) | 10s | Faster notification for critical |
| `repeat_interval` (critical) | 30m | More frequent repeats for critical |
| `group_wait` (warning) | 30s | Slower for warnings |
| `repeat_interval` (warning) | 2h | Less frequent for warnings |

---

## Routing

### Severity-Based Routing

```yaml
routes:
  # Critical alerts - faster notifications
  - matchers:
      - severity="critical"
    receiver: notification-service
    group_wait: 10s
    repeat_interval: 30m

  # Warning alerts - slower notifications
  - matchers:
      - severity="warning"
    receiver: notification-service
    group_wait: 30s
    repeat_interval: 2h
```

### Grouping

Alerts are grouped by `alertname`, `job`, and `severity`. Multiple alerts matching the same group are sent together to reduce notification spam.

---

## Inhibit Rules

Prevents warning alerts from firing when a critical alert for the same issue exists:

```yaml
inhibit_rules:
  - source_matchers:
      - severity="critical"
    target_matchers:
      - severity="warning"
    equal:
      - alertname
      - job
```

**Logic:** If a `critical` alert for `HighTemperature` on `irrigation-controller` is firing, suppress any `warning` alerts for `HighTemperature` on `irrigation-controller`.

---

## Receivers

### Webhook (Primary)

```yaml
- name: notification-service
  webhook_configs:
    - url: http://notification-service:8505/alerts/webhook
      send_resolved: true
```

**Endpoint:** `POST http://notification-service:8505/alerts/webhook`

**Payload:**
```json
{
  "receiver": "notification-service",
  "status": "firing",
  "alerts": [
    {
      "status": "firing",
      "labels": {"alertname": "SmartIrrigationServiceDown", "severity": "critical", "job": "data-ingestion"},
      "annotations": {"summary": "Service data-ingestion is down", "description": "..."},
      "startsAt": "2026-05-03T10:00:00Z"
    }
  ],
  "groupLabels": {"alertname": "SmartIrrigationServiceDown"},
  "commonLabels": {"severity": "critical"},
  "commonAnnotations": {}
}
```

---

## Docker Compose

```yaml
alertmanager:
  image: prom/alertmanager:latest
  ports:
    - "9093:9093"
  command:
    - "--config.file=/etc/alertmanager/alertmanager.yml"
    - "--storage.path=/alertmanager"
  volumes:
    - ../configs/monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
  networks:
    - irrigation_net
```

---

## Environment Variables

From `.env` (for notification-service email):

| Variable | Default | Description |
|----------|---------|-------------|
| `ALERTMANAGER_SMTP_HOST` | smtp.example.com | SMTP server |
| `ALERTMANAGER_SMTP_PORT` | 587 | SMTP port |
| `ALERTMANAGER_SMTP_FROM` | alerts@smart-irrigation.local | Sender email |
| `ALERTMANAGER_SMTP_USERNAME` | dev_alerts | SMTP username |
| `ALERTMANAGER_SMTP_PASSWORD` | smtp_dev_pass | SMTP password |
| `ALERTMANAGER_EMAIL_TO` | team@smart-irrigation.local | Recipient email |

---

## Accessing Alertmanager

**Web UI:** http://localhost:9093

**Silent alert:** http://localhost:9093/#/silences

**Status:** http://localhost:9093/api/v1/status

---

## Integration with Prometheus

Prometheus sends alerts to Alertmanager via configuration:

```yaml
# prometheus.yml
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093
```

---

## Alert Flow

```
1. Prometheus evaluates alert_rules.yml every 15s
2. If alert condition met → fires alert to Alertmanager
3. Alertmanager:
   - Groups alerts by alertname/job/severity
   - Waits group_wait before sending
   - Sends to notification-service webhook
4. Notification-service:
   - Receives alert at /alerts/webhook
   - Checks ALERT_SEVERITY_THRESHOLD
   - Sends email (if SMTP configured)
   - Sends webhook (if webhook URL configured)
```

---

## Testing Alerts

### Manually trigger via Prometheus

```bash
# In Prometheus UI: http://localhost:9090/graph
# Execute: up{job="data-ingestion"} = 0
```

### Check Alertmanager status

```bash
curl http://localhost:9093/api/v1/alerts
```

### Check silences

```bash
curl http://localhost:9093/api/v1/silences
```

---

## Summary

| Aspect | Value |
|--------|-------|
| Port | 9093 |
| Config | configs/monitoring/alertmanager.yml |
| Receiver | notification-service webhook |
| Group wait | 15s (default), 10s (critical), 30s (warning) |
| Repeat interval | 4h (default), 30m (critical), 2h (warning) |
| Inhibit rules | Critical suppresses warning for same alert/job |

Alertmanager provides centralized alert routing with intelligent grouping and deduplication before forwarding to the notification-service for delivery.


═══════════════════════════════════════════════════════════════════

SECTION: Notification Service

# Notification Service

## Overview

The Notification Service is an alert routing service that consumes events from Redis and Alertmanager webhooks, then dispatches notifications via email and webhooks based on severity thresholds.

**Location:** `services/notification-service/`

---

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      Alert Sources                                              │
│                                                                                 │
│  ┌──────────────────┐                    ┌────────────────────────┐          │
│  │  Redis Channels  │                    │  Alertmanager Webhook  │          │
│  │                   │                    │                        │          │
│  │ - alerts:anomaly  │──┐                 │  POST /alerts/webhook   │──┐       │
│  │ - irrigation:     │  │                 │                        │  │       │
│  │   triggered        │──┼────────────────▶│                        │  │       │
│  └──────────────────┘  │                 └────────────────────────┘  │       │
│                        │                                             │       │
└────────────────────────┼─────────────────────────────────────────────┼───────┘
                         │                                             │
                         ▼                                             ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    NOTIFICATION SERVICE                                         │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                       AlertHandler                                       │   │
│  │                                                                          │   │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐   │   │
│  │  │   Severity   │    │    Email     │    │       Webhook           │   │   │
│  │  │   Filter     │    │   (SMTP)     │    │       (HTTP POST)       │   │   │
│  │  │              │    │              │    │                          │   │   │
│  │  │ - info       │    │ - TLS        │    │ - Configurable URL     │   │   │
│  │  │ - warning    │    │ - Auth      │    │ - JSON payload        │   │   │
│  │  │ - critical   │    │ - Template  │    │ - Latency metrics     │   │   │
│  │  └──────────────┘    └──────────────┘    └──────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Input Channels

### Redis Channels

| Channel | Description | Example Payload |
|---------|-------------|-----------------|
| `alerts:anomaly` | Data quality anomalies | `{"zone_id": "zone-001", "severity": "warning", "event_type": "above_max_plausible_moisture"}` |
| `irrigation:triggered` | Irrigation events | `{"zone_id": "zone-001", "action": "start", "duration": 300}` |

### Alertmanager Webhook

```
POST /alerts/webhook
```

```json
{
  "receiver": "notifications",
  "status": "firing",
  "alerts": [
    {
      "status": "firing",
      "labels": {"severity": "critical", "alertname": "HighTemperature"},
      "annotations": {"summary": "Temperature exceeded threshold", "description": "Zone 1 at 55°C"},
      "startsAt": "2026-05-03T10:00:00Z"
    }
  ],
  "groupLabels": {},
  "commonLabels": {},
  "commonAnnotations": {}
}
```

---

## Components

### main.py

FastAPI application with Redis listener:

```python
async def redis_listener() -> None:
    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if message:
            data = json.loads(message["data"])
            severity = str(data.get("severity", "info")).lower()
            if not handler.should_dispatch(severity):
                continue
            asyncio.create_task(handler.dispatch_alert({**data, "channel": channel}, "redis"))
```

**Endpoints:**
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `POST /alerts/webhook` - Alertmanager integration

### alert_handler.py

Handles alert dispatch:

```python
async def dispatch_alert(self, payload: dict[str, Any], source: str) -> dict[str, str]:
    severity = str(payload.get("severity", "warning")).lower()
    ALERTS_RECEIVED.labels(source, severity).inc()
    subject = f"[{severity.upper()}] Smart Irrigation Alert"
    body = json.dumps(payload, indent=2)
    await asyncio.gather(self.send_email(subject, body), self.send_webhook(payload))
    return {"status": "accepted", "source": source, "severity": severity}
```

**Features:**
- Severity-based filtering
- Email via SMTP (async, thread pool)
- Webhook delivery (with latency tracking)
- Alertmanager normalization

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | redis://redis:6379/0 | Redis connection |
| `REDIS_CHANNEL_ALERTS_ANOMALY` | alerts:anomaly | Anomaly alerts channel |
| `REDIS_CHANNEL_IRRIGATION_TRIGGERED` | irrigation:triggered | Irrigation events channel |
| `SMTP_HOST` | - | SMTP server hostname |
| `SMTP_PORT` | 587 | SMTP port (TLS) |
| `SMTP_FROM_ADDRESS` | - | Sender email address |
| `SMTP_PASSWORD` | - | SMTP password |
| `NOTIFICATION_WEBHOOK_URL` | - | Webhook URL for HTTP notifications |
| `ALERT_EMAIL_TO` | admin@smart-irrigation.local | Recipient email |
| `ALERT_SEVERITY_THRESHOLD` | warning | Minimum severity to dispatch |

### Severity Levels

| Level | Value | Description |
|-------|-------|-------------|
| `info` | 0 | Informational only |
| `warning` | 1 | Warnings, requires attention |
| `critical` | 2 | Critical alerts, immediate action |

The `ALERT_SEVERITY_THRESHOLD` setting controls which alerts are dispatched:
- `"info"` → dispatch all alerts
- `"warning"` → dispatch warning + critical
- `"critical"` → dispatch only critical

---

## Metrics

Prometheus metrics at `/metrics`:

| Metric | Labels | Description |
|--------|--------|-------------|
| `notification_service_alerts_received_total` | source, severity | Alerts received |
| `notification_service_deliveries_total` | channel, status | Delivery attempts (success/failed/skipped) |
| `notification_service_webhook_delivery_seconds` | - | Webhook latency histogram |

---

## Notification Channels

### Email (SMTP)

- **Transport:** TLS (port 587)
- **Authentication:** Username + password
- **Template:** JSON dump of alert payload as body

```python
def _send_smtp_sync(self, subject: str, body: str) -> None:
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = ALERT_EMAIL_TO
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_FROM, SMTP_PASSWORD)
        server.send_message(msg)
```

### Webhook (HTTP POST)

- **Method:** POST
- **Content-Type:** application/json
- **Timeout:** 10 seconds
- **Payload:** Full alert data as JSON

```python
async def send_webhook(self, payload: dict[str, Any]) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.post(WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
```

---

## Alertmanager Integration

The service normalizes Alertmanager alerts to internal format:

```python
def normalize_alertmanager_alert(self, alert, payload_status):
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    return {
        "source": "alertmanager",
        "status": alert.get("status", payload_status),
        "severity": labels.get("severity", "warning"),
        "alertname": labels.get("alertname", "unknown"),
        "service": labels.get("job") or labels.get("service", "unknown"),
        "summary": annotations.get("summary", ""),
        "description": annotations.get("description", ""),
        "startsAt": alert.get("startsAt"),
        "endsAt": alert.get("endsAt"),
    }
```

---

## Docker Compose

```yaml
notification-service:
  image: notification-service:latest
  ports:
    - "8002:8002"
  environment:
    - REDIS_URL=redis://redis:6379/0
    - REDIS_CHANNEL_ALERTS_ANOMALY=alerts:anomaly
    - REDIS_CHANNEL_IRRIGATION_TRIGGERED=irrigation:triggered
    - SMTP_HOST=smtp.example.com
    - SMTP_PORT=587
    - SMTP_FROM_ADDRESS=alerts@smart-irrigation.local
    - SMTP_PASSWORD=${SMTP_PASSWORD}
    - NOTIFICATION_WEBHOOK_URL=https://hooks.example.com/notify
    - ALERT_EMAIL_TO=admin@example.com
    - ALERT_SEVERITY_THRESHOLD=warning
  depends_on:
    - redis
```

---

## Usage Examples

### Sending a test alert via Redis

```bash
redis-cli PUBLISH alerts:anomaly '{"zone_id": "zone-001", "severity": "warning", "event_type": "high_moisture", "value": 95}'
```

### Alertmanager rule

```yaml
groups:
- name: irrigation
  rules:
  - alert: HighTemperature
    expr: temperature > 45
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High temperature in {{ $labels.zone_id }}"
      description: "Temperature is {{ $value }}°C"
```

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Framework | FastAPI + asyncio |
| Language | Python |
| Input | Redis pubsub + Alertmanager webhook |
| Output | Email (SMTP) + Webhook (HTTP) |
| Filtering | Severity-based threshold |
| Port | 8002 |
| Dependencies | Redis |

The Notification Service provides centralized alerting with configurable thresholds, supporting both real-time Redis events and Prometheus Alertmanager integration.


═══════════════════════════════════════════════════════════════════

SECTION: Deployment Guide

# Deployment Guide

## Overview

This guide covers deploying the Smart Irrigation System to production using Docker Compose. It includes automated deployment scripts, rollback procedures, and verification checks.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              PRODUCTION DEPLOYMENT                              │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                     Deployment Pipeline (Jenkins)                        │   │
│  │                                                                          │   │
│  │  Git Push → Build → Test → Push to Registry → Deploy to Staging/Prod   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         STAGING ENVIRONMENT                                     │
│                                                                                 │
│  Same as production but with limited resources and test data                   │
│  URL: staging.smart-irrigation.local                                          │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         PRODUCTION ENVIRONMENT                                  │
│                                                                                 │
│  Full infrastructure with 19 services                                           │
│  URL: smart-irrigation.local (or custom domain)                                 │
└────────────────────────────────┬────────────────────────────────────────────────┘
```

---

## Prerequisites

### System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 4 cores | 8 cores |
| RAM | 8 GB | 16 GB |
| Disk | 50 GB | 100 GB |
| Docker | 20.10+ | 24.0+ |
| Docker Compose | 2.0+ | 2.20+ |

### Network Requirements

| Port | Service |
|------|---------|
| 80/443 | Web Dashboard, API Gateway |
| 5432 | PostgreSQL (restrict to internal) |
| 6379 | Redis (restrict to internal) |

---

## Pre-Deployment Checklist

```bash
# 1. Verify Docker installation
docker --version
docker compose version

# 2. Verify .env configuration
cp .env.example .env
# Edit .env with production values

# 3. Validate environment variables
make validate-env

# 4. Ensure required ports are available
make check-ports
```

---

## Environment Configuration

### Production .env

```bash
# =============================================================================
# PRODUCTION ENVIRONMENT - UPDATE THESE VALUES
# =============================================================================

# JWT - GENERATE NEW SECRET: openssl rand -hex 32
JWT_SECRET_KEY=your_production_jwt_secret_here

# Database
POSTGRES_PASSWORD=strong_postgres_password_here

# MinIO - GENERATE NEW: openssl rand -hex 32
MINIO_ROOT_PASSWORD=strong_minio_password_here

# SMTP for notifications
SMTP_HOST=smtp.gmail.com
SMTP_FROM_ADDRESS=alerts@yourdomain.com
SMTP_PASSWORD=your_app_password

# Public URLs
DOMAIN_NAME=smart-irrigation.yourdomain.com
CORS_ALLOWED_ORIGINS=https://smart-irrigation.yourdomain.com

# Security
ENV=production
```

---

## Deployment Methods

### 1. Direct Docker Compose (Development/Testing)

```bash
# Clone and setup
git clone https://github.com/your-org/smart-irrigation.git
cd smart-irrigation
cp .env.example .env

# Start all services
docker compose -f docker/docker-compose.yml \
               -f docker/docker-compose.app.yml \
               -f docker/docker-compose.data.yml \
               -f docker/docker-compose.ml.yml up -d
```

### 2. Production Deployment Script

```bash
# From project root
./scripts/deploy.sh production
```

### 3. Jenkins Pipeline (CI/CD)

```bash
# Push to main branch triggers:
# 1. Lint + Unit tests
# 2. Build Docker images
# 3. Push to registry (GHCR)
# 4. Deploy to staging
# 5. Run smoke tests
# 6. Deploy to production (manual approval)
```

---

## Deployment Scripts

### deploy.sh

```bash
#!/bin/bash
set -e

ENVIRONMENT=${1:-staging}

echo "=== Smart Irrigation Deployment: $ENVIRONMENT ==="

# 1. Load environment
source .env

# 2. Pull latest images
echo "Pulling latest images..."
docker compose -f docker/docker-compose.yml pull
docker compose -f docker/docker-compose.app.yml pull
docker compose -f docker/docker-compose.data.yml pull
docker compose -f docker/docker-compose.ml.yml pull
docker compose -f docker/docker-compose.monitoring.yml pull

# 3. Run database migrations
echo "Running migrations..."
docker compose run --rm timescaledb-migration

# 4. Start infrastructure
echo "Starting infrastructure..."
docker compose -f docker/docker-compose.yml up -d

# 5. Wait for healthy services
echo "Waiting for services..."
./scripts/wait-for-health.sh

# 6. Start application services
docker compose -f docker/docker-compose.app.yml up -d
docker compose -f docker/docker-compose.data.yml up -d
docker compose -f docker/docker-compose.ml.yml up -d
docker compose -f docker/docker-compose.monitoring.yml up -d

# 7. Verify deployment
echo "Verifying deployment..."
./scripts/verify-deployment.sh

echo "=== Deployment Complete ==="
```

---

## Rollback Procedures

### Automatic Rollback

If health checks fail after deployment:

```bash
# Rollback to previous version
./scripts/rollback.sh
```

### Manual Rollback

```bash
# 1. List available versions
docker compose ls --format json | jq '.[].ConfigFiles'

# 2. Stop current deployment
docker compose down

# 3. Start specific version (tag)
docker compose -f docker/docker-compose.yml -f docker/docker-compose.app.yml up -d

# 4. Verify rollback
./scripts/smoke_test.sh
```

### Database Rollback

```bash
# Restore from backup
docker compose exec -T timescaledb psql -U irrigation_user -d irrigation_db < backups/irrigation_db_backup.sql

# Or use point-in-time recovery (PITR)
docker compose exec timescaledb pg_restore -U irrigation_user -d irrigation_db backup_file.dump
```

---

## Blue-Green Deployment

### Architecture

```
┌─────────────┐     ┌─────────────┐
│   BLUE      │     │   GREEN     │
│  (current)  │     │  (new)      │
│             │     │             │
│  :8080      │◄────│  :8081      │
└─────────────┘     └─────────────┘
       │                   ▲
       │    Nginx          │
       └───────────────────┘
```

### deploy-blue-green.sh

```bash
#!/bin/bash

# 1. Deploy to green (staging)
echo "Deploying to green..."
docker compose -f docker/docker-compose.yml up -d green

# 2. Run smoke tests
./scripts/smoke_test.sh green

# 3. Switch traffic
docker compose -f docker/docker-compose.yml exec nginx nginx -s reload

# 4. Monitor
./scripts/monitor.sh 5m

# 5. If issues, rollback
if [ $? -ne 0 ]; then
    echo "Rolling back to blue..."
    ./scripts/rollback.sh blue
fi
```

---

## Canary Deployment

### Strategy

- Deploy new version to 10% of traffic
- Monitor error rates and latency
- Gradually increase to 50%, 100%
- Rollback if issues detected

### Implementation

```bash
# Canary deployment with Traefik
# traefik.yml
services:
  irrigation-controller:
    deploy:
      labels:
        - "traefik.http.services.irrigation-controller.weight=10"
```

---

## Deployment Verification

### verify-deployment.sh

```bash
#!/bin/bash

echo "=== Verifying Deployment ==="

FAILED=0

# 1. Check all containers are running
echo "Checking containers..."
docker compose ps | grep -q "Up" || { echo "❌ Containers not running"; FAILED=1; }

# 2. Health checks
echo "Checking health endpoints..."

# API Gateway
curl -sf http://localhost:8080/health || { echo "❌ API Gateway"; FAILED=1; }

# User Service
curl -sf http://localhost:5005/health || { echo "❌ User Service"; FAILED=1; }

# Data Ingestion
curl -sf http://localhost:8001/health || { echo "❌ Data Ingestion"; FAILED=1; }

# Model Server
curl -sf http://localhost:8501/health || { echo "❌ Model Server"; FAILED=1; }

# 3. Check data flow
echo "Checking data flow..."
redis-cli ping > /dev/null 2>&1 || { echo "❌ Redis"; FAILED=1; }
docker compose exec -T timescaledb pg_isready -U irrigation_user || { echo "❌ PostgreSQL"; FAILED=1; }

# 4. Check Grafana
curl -sf http://localhost:3001/api/health || { echo "❌ Grafana"; FAILED=1; }

# 5. Run smoke tests
echo "Running smoke tests..."
./scripts/smoke_test.sh || { echo "❌ Smoke tests failed"; FAILED=1; }

if [ $FAILED -eq 0 ]; then
    echo "✅ Deployment verified successfully!"
else
    echo "❌ Deployment verification failed"
    exit 1
fi
```

### smoke_test.sh

```bash
#!/bin/bash

echo "=== Running Smoke Tests ==="

# Test 1: User registration
curl -sf -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123","full_name":"Test"}' \
  || { echo "User registration failed"; exit 1; }

# Test 2: Login
TOKEN=$(curl -sf -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123"}' \
  | jq -r '.access_token')

# Test 3: Create zone
curl -sf -X POST http://localhost:8080/v1/zones \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"zone_name":"Test Zone","soil_type":"loam","crop_type":"wheat","moisture_min":30,"moisture_max":70}' \
  || { echo "Zone creation failed"; exit 1; }

# Test 4: Sensor data ingestion
redis-cli PUBLISH sensor:data '{"zone_id":"zone-001","sensor_id":"sensor-001","moisture":45,"temperature":22}' \
  || { echo "Sensor data publish failed"; exit 1; }

# Test 5: Dashboard loads
curl -sf http://localhost:3000 > /dev/null || { echo "Dashboard failed"; exit 1; }

echo "✅ All smoke tests passed"
```

---

## Monitoring Deployment

### Health Check Script

```bash
#!/bin/bash

# Run continuously, alert on failures
while true; do
    if ! curl -sf http://localhost:8080/health > /dev/null; then
        echo "ALERT: API Gateway unhealthy at $(date)"
        # Send alert to notification service
    fi
    sleep 30
done
```

### Metrics to Watch

| Metric | Threshold | Action |
|--------|------------|--------|
| Container status | Any down | Immediate alert |
| API latency p95 | > 1s | Investigate |
| Error rate | > 5% | Rollback |
| Memory usage | > 80% | Scale up |
| Disk usage | > 80% | Cleanup |

---

## Troubleshooting

### Service won't start

```bash
# View logs
docker compose logs -f <service-name>

# Common fixes
docker compose down -v        # Remove volumes
docker compose build --no-cache <service>
docker system prune -a        # Cleanup unused images
```

### Database connection issues

```bash
# Check DB is ready
docker compose exec timescaledb pg_isready -U irrigation_user

# Check connection string
docker compose exec user-service env | grep DATABASE_URL
```

### Out of disk space

```bash
# Clean up
docker system df
docker image prune -a
docker volume prune
```

---

## Production Checklist

- [ ] Generate new JWT_SECRET_KEY
- [ ] Set strong database passwords
- [ ] Configure SMTP for notifications
- [ ] Set ENV=production in .env
- [ ] Configure CORS_ALLOWED_ORIGINS
- [ ] Enable firewall rules
- [ ] Configure domain DNS
- [ ] Setup SSL/TLS certificates
- [ ] Enable backup schedule
- [ ] Configure monitoring alerts

---

## Summary

| Step | Command |
|------|---------|
| Validate env | `make validate-env` |
| Deploy | `./scripts/deploy.sh production` |
| Verify | `./scripts/verify-deployment.sh` |
| Rollback | `./scripts/rollback.sh` |
| Monitor | `./scripts/monitor.sh` |

This deployment guide provides automated, repeatable deployments with rollback capability for the Smart Irrigation System.

---

## Exposing Services Externally with Ngrok

### Overview

Ngrok creates a secure tunnel from your local server to the internet, allowing clients on different networks to access the Smart Irrigation System without port forwarding or cloud deployment.

### Quick Start

```bash
# Start tunnel for web dashboard (port 80)
make tunnel-dashboard

# Or for API Gateway directly (port 8080)
make tunnel-api

# Stop tunnel when done
make tunnel-stop
```

### Available Commands

| Command | Description |
|---------|-------------|
| `make tunnel-dashboard` | Expose web dashboard on port 80 |
| `make tunnel-api` | Expose API Gateway on port 8080 |
| `make tunnel-stop` | Stop all ngrok tunnels |

### How It Works

```
Client (any network) → ngrok URL → Your Server (port 80) → Nginx → Services
```

### Access from Anywhere

When ngrok starts, it shows a URL like:
```
https://abc123.ngrok.io
```

Share this URL with clients:

| Path | Service |
|------|---------|
| https://abc123.ngrok.io/ | Web Dashboard |
| https://abc123.ngrok.io/api/ | API Gateway |
| https://abc123.ngrok.io/grafana/ | Grafana |
| https://abc123.ngrok.io/mlflow/ | MLflow |

### Use Cases

- **Development** - Share access with team members
- **Testing** - Allow external testers to access the app
- **Demo** - Show the application to stakeholders
- **Webhook testing** - Receive webhooks from external services

### Security Notes

- Ngrok URLs are temporary and change each session
- For production, use proper domain + SSL instead
- Ngrok Basic auth can be added:
  ```bash
  ngrok http 80 --basic-auth "user:password"
  ```

### Installation

If ngrok is not installed:
```bash
# Windows
Invoke-WebRequest -Uri "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip" -OutFile ngrok.zip
Expand-Archive ngrok.zip -DestinationPath .
# Add to PATH or use full path

# Linux/Mac
brew install ngrok  # or
curl -sL https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tar.gz | tar xz
```

Ngrok provides quick external access for testing and demos without requiring router configuration or cloud deployment.


═══════════════════════════════════════════════════════════════════

SECTION: Testing Guide

# Testing Guide

## Overview

The Smart Irrigation System uses pytest for unit and integration testing across all services. Tests are organized by service with unit tests for core logic and integration tests for API endpoints.

---

## Test Structure

```
services/
├── api-gateway/
│   └── tests/
│       ├── unit/
│       │   ├── test_auth.py
│       │   └── test_routes.py
│       └── integration/
│           └── test_endpoints.py
├── user-service/
│   └── tests/
│       ├── unit/
│       │   ├── test_auth.py
│       │   └── test_routes.py
│       └── integration/
├── model-server/
│   └── tests/
│       ├── unit/
│       │   └── test_model_service.py
│       └── integration/
├── drift-monitor/
│   └── tests/
│       ├── unit/
│       │   └── test_drift_detector.py
│       └── integration/
├── feature-engineering/
│   └── tests/
│       ├── unit/
│       │   └── test_feature_computation.py
│       └── integration/
└── irrigation-controller/
    └── tests/
        └── integration/
```

---

## Running Tests

### Run all tests

```bash
pytest
```

### Run specific service

```bash
pytest services/user-service/
```

### Run unit tests only

```bash
pytest --ignore=tests/integration/
```

### Run with coverage

```bash
pytest --cov=services/user-service --cov-report=html
```

### Run with verbose output

```bash
pytest -v
```

---

## Unit Tests

### user-service - Authentication

**File:** `services/user-service/tests/unit/test_auth.py`

Tests password hashing and JWT token management:

```python
def test_password_hashing():
    password = "secret_password"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)

def test_create_tokens():
    user_id = "test-user-id"
    access_token, refresh_token = create_tokens(user_id)
    access_payload = jwt.decode(access_token, ...)
    assert access_payload["sub"] == user_id
    assert access_payload["type"] == "access"

@pytest.mark.asyncio
async def test_verify_token_valid():
    access_token, _ = create_tokens(user_id)
    payload = await verify_token(access_token, expected_type="access")
    assert payload["sub"] == user_id
```

### drift-monitor - Drift Detection

**File:** `services/drift-monitor/tests/unit/test_drift_detector.py`

Tests drift detection algorithms:

```python
def test_page_hinkley_detects_shift():
    score, detected = page_hinkley([0.1, 0.1, 0.1, 1.0, 1.0], threshold=0.1)
    assert score >= 0
    assert detected is True

def test_kl_divergence_non_negative():
    divergence = kl_divergence([0.1, 0.2, 0.3], [0.3, 0.4, 0.5])
    assert divergence >= 0

def test_summarize_drift_sets_flag():
    summary = summarize_drift([0.1, 0.2, 0.2], [0.8, 0.9, 1.0])
    assert summary.drift_detected is True
```

---

## Integration Tests

Integration tests verify API endpoints work correctly:

### api-gateway - test_endpoints.py

```python
def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_rate_limiting():
    for _ in range(101):
        response = client.get("/health")
    # 101st request should be rate limited
    assert response.status_code == 429
```

---

## Test Configuration

### Dependencies (from requirements.txt)

```
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
httpx>=0.24.0  # For async HTTP testing
```

### Environment Variables

Tests use `.env` variables or sensible defaults:

```python
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev_jwt_secret_key")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://...")
```

---

## Test Categories

### 1. Unit Tests

- **Purpose:** Test individual functions/classes in isolation
- **Location:** `tests/unit/`
- **Mock:** External dependencies (DB, Redis, API calls)
- **Fast:** Run in milliseconds

### 2. Integration Tests

- **Purpose:** Test service endpoints and integrations
- **Location:** `tests/integration/`
- **Real:** Use actual services (PostgreSQL, Redis) or test doubles
- **Coverage:** API contracts, error handling

---

## Writing Tests

### Example: Unit Test

```python
# services/my-service/tests/unit/test_calculator.py
import pytest
from src.calculator import calculate_irrigation_duration

def test_calculate_duration_below_threshold():
    # Given
    moisture = 20
    threshold = 30
    max_duration = 600

    # When
    duration = calculate_irrigation_duration(moisture, threshold, max_duration)

    # Then
    assert duration > 0
    assert duration <= max_duration

def test_calculate_duration_above_threshold():
    # Given
    moisture = 40
    threshold = 30

    # When
    duration = calculate_irrigation_duration(moisture, threshold, 600)

    # Then
    assert duration == 0  # No irrigation needed
```

### Example: API Test

```python
# services/api-gateway/tests/integration/test_zones.py
import pytest

def test_create_zone_authenticated(client, auth_token):
    response = client.post(
        "/v1/zones",
        json={"zone_name": "Test Zone", "soil_type": "loam"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 201
    assert response.json()["zone_name"] == "Test Zone"

def test_create_zone_unauthenticated(client):
    response = client.post(
        "/v1/zones",
        json={"zone_name": "Test Zone"}
    )
    assert response.status_code == 401
```

---

## CI/CD Integration

Tests run in Jenkins pipeline:

```groovy
// Jenkinsfile
stage('Test') {
    steps {
        script {
            sh 'pytest --cov=services/ --cov-report=xml'
        }
        archiveArtifacts artifacts: 'coverage.xml', fingerprint: true
    }
    post {
        always {
            junit '**/test-results/*.xml'
        }
    }
}
```

---

## Coverage Targets

| Type | Target |
|------|--------|
| Unit Tests | 80%+ coverage |
| Integration Tests | Key endpoints covered |
| Critical Paths | 100% coverage |

---

## Running in Docker

```bash
# Run tests in container
docker run --rm smart-irrigation-user-service pytest

# With coverage
docker run --rm smart-irrigation-user-service pytest --cov=src --cov-report=html
```

---

## Troubleshooting

### Tests hang

- Check for unclosed database connections
- Use `pytest --forked` to isolate tests

### Import errors

- Ensure `PYTHONPATH` includes `services/<service>/src`

### Redis connection errors

- Use `fakeredis` for unit tests
- Use Docker containers for integration tests

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Framework | pytest |
| Test Types | Unit, Integration |
| Mocking | unittest.mock, fakeredis |
| Coverage | pytest-cov |
| CI | Jenkins pipeline |

Tests ensure code quality and prevent regressions across all Smart Irrigation services.


═══════════════════════════════════════════════════════════════════

SECTION: Code Review Guidelines

# Code Review Guidelines

## 1. Review Requirements

- Every PR requires **at least one approving review** before merging to `develop`.
- PRs that modify **interface contracts** (Pydantic schemas, Redis channel formats, REST API endpoints) require review from **all affected team members** to ensure backward compatibility.

## 2. CI Checks

Jenkins runs the following on every PR:

| Check | Scope |
|---|---|
| Python linting | `ruff` for all backend services |
| TypeScript/ESLint | `eslint` + `tsc` for web-dashboard |
| Unit tests | `pytest` (Python), `vitest` (TypeScript) |
| Docker build | Build verification for affected services |
| Integration smoke tests | API endpoint smoke tests |

All checks must pass before merge.

## 3. Review Checklist

### Correctness
- [ ] Logic matches the interface contract (Pydantic schema, Redis format, REST spec)
- [ ] Error handling covers failure cases (bad input, DB down, Redis unavailable)
- [ ] No hardcoded secrets or credentials

### Style & Consistency
- [ ] Python code passes `ruff` linting
- [ ] TypeScript code passes ESLint + type-checking
- [ ] Naming conventions match existing code in the service

### Testing
- [ ] Unit tests cover happy path and edge cases
- [ ] New endpoints have integration tests
- [ ] Dockerfile produces a working image

### Safety
- [ ] No secrets in code (use environment variables)
- [ ] SQL uses parameterized queries (no string concatenation)
- [ ] JWT validation on all protected endpoints

## 4. Merge Rules

- **Squash merge** into `develop` for clean history
- **Rebase merges only** — no merge commits
- Delete feature branch after merge
- Tag release candidates on `main` only after full E2E smoke test passes

## 5. Conflict Resolution

- Each team member owns their service directory exclusively (see ownership tags)
- Database migrations are numbered and immutable — conflicts prevented by design
- Shared files (docker-compose, zone configs, tests) require coordination before modification
- Daily sync meetings to flag potential contract changes early



═══════════════════════════════════════════════════════════════════

SECTION: Branch Naming Convention

# Branch Naming Conventions

```
main
└── develop
    ├── devops
    ├── dataops
    └── mlops
```

## Structure

- **`main`** — production / demo-ready
- **`develop`** — integration branch, all roles merge here
- **`devops` / `dataops` / `mlops`** — role working branches, each member commits directly here
- **`fix/<description>`** — cross-role bug fixes, created from `develop`
- **`chore/<description>`** — maintenance tasks, created from `develop`

## Naming Rules

- Use **kebab-case** for all descriptions
- Keep descriptions concise (3-5 words max)
- Each role commits directly to their branch — no feature branches needed
- `fix/` and `chore/` branches are created from `develop` only when the change affects multiple roles

## Examples

```bash
# DevOps — commit directly
git checkout devops
git commit -m "[DO] init docker-compose with timescaledb and redis"

# DataOps — commit directly
git checkout dataops
git commit -m "[DA] create sensor_readings hypertable migration"

# MLOps — commit directly
git checkout mlops
git commit -m "[ML] train initial XGBoost model with Optuna"

# Cross-role bug fix
git checkout develop
git checkout -b fix/redis-connection-timeout

# Maintenance
git checkout develop
git checkout -b chore/update-dependencies
```

## Merge Flow

```
devops/dataops/mlops ──→ develop ──→ main
fix/*    ────────────────→ develop ──→ main
chore/*  ────────────────→ develop ──→ main
```

- Role branches merge into `develop` at end of sprint via PR
- `fix/*` and `chore/*` merge into `develop` via PR
- `develop` merges into `main` only when fully tested and demo-ready
- `main` is always deployable and demo-ready

## Who Can Merge

| PR | Can merge? |
|---|---|
| `devops` → `develop` | ❌ DevOps approval required |
| `dataops` → `develop` | ❌ DevOps approval required |
| `mlops` → `develop` | ❌ DevOps approval required |
| `fix/*` → `develop` | ❌ DevOps approval required |
| `chore/*` → `develop` | ❌ DevOps approval required |
| `develop` → `main` | ❌ DevOps approval required |


