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