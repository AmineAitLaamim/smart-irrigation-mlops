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
