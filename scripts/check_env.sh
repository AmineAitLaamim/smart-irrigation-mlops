#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Smart Irrigation System — Environment Validator
# =============================================================================
# Validates all required environment variables from .env
# Run with: make validate-env
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"

if [[ ! -f "$ENV_FILE" ]]; then
    echo -e "${RED}Error: .env not found — run 'make env' first${NC}"
    exit 1
fi

# Source .env
set -a
source "$ENV_FILE"
set +a

REQUIRED_VARS=(
    # Database
    POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB DATABASE_URL
    DB_POOL_MIN_SIZE DB_POOL_MAX_SIZE
    TIMESCALEDB_SENSOR_CHUNK_INTERVAL TIMESCALEDB_IRRIGATION_CHUNK_INTERVAL
    # Redis
    REDIS_URL REDIS_MAX_MEMORY REDIS_EVICTION_POLICY
    # Auth / JWT
    JWT_SECRET_KEY JWT_ALGORITHM JWT_ACCESS_EXPIRE_MIN JWT_REFRESH_EXPIRE_DAYS
    BCRYPT_ROUNDS REDIS_TOKEN_BLACKLIST_URL AUTH_MAX_ATTEMPTS AUTH_LOCKOUT_MINUTES
    # API Gateway
    API_GATEWAY_PORT RATE_LIMIT_PER_MIN CORS_ALLOWED_ORIGINS
    USER_SERVICE_URL MODEL_SERVER_REST_URL DRIFT_MONITOR_URL NOTIFICATION_SERVICE_URL
    DATA_INGESTION_HEALTH_URL
    # ML Infra
    MLFLOW_TRACKING_URI MLFLOW_S3_ENDPOINT_URL AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
    MLFLOW_ARTIFACT_BUCKET MINIO_ROOT_USER MINIO_ROOT_PASSWORD MLFLOW_PRODUCTION_STAGE
    # Airflow
    AIRFLOW__CORE__FERNET_KEY AIRFLOW__CORE__EXECUTOR AIRFLOW__DATABASE__SQL_ALCHEMY_CONN
    AIRFLOW__WEBSERVER__SECRET_KEY AIRFLOW_ADMIN_USER AIRFLOW_ADMIN_PASSWORD
    # Data Pipeline
    SENSOR_PUBLISH_INTERVAL
    REDIS_CHANNEL_SENSOR_DATA REDIS_CHANNEL_INGESTION_PROCESSED
    REDIS_CHANNEL_FEATURES_COMPUTED REDIS_CHANNEL_PREDICTIONS_NEW
    REDIS_CHANNEL_ALERTS_ANOMALY REDIS_CHANNEL_IRRIGATION_TRIGGERED
    DATA_INGESTION_PORT
    # Model Server
    MODEL_SERVER_GRPC_PORT MODEL_SERVER_REST_PORT
    # User Service
    USER_SERVICE_PORT
    # Web Dashboard
    NEXT_PUBLIC_API_BASE_URL DASHBOARD_PORT NEXT_PUBLIC_POLLING_INTERVAL_MS
    # Monitoring
    GRAFANA_ADMIN_USER GRAFANA_ADMIN_PASSWORD PROMETHEUS_SCRAPE_INTERVAL
    ALERTMANAGER_SMTP_HOST ALERTMANAGER_SMTP_PORT ALERTMANAGER_SMTP_FROM
    ALERTMANAGER_SMTP_USERNAME ALERTMANAGER_SMTP_PASSWORD ALERTMANAGER_EMAIL_TO
    # Notification
    SMTP_FROM_ADDRESS SMTP_PORT SMTP_PASSWORD
    ALERT_SEVERITY_THRESHOLD
    # Jenkins
    JENKINS_ADMIN_USER JENKINS_ADMIN_PASSWORD JENKINS_PORT
    # Env flag
    ENV
)

MISSING=()
CHANGEME=()

for var in "${REQUIRED_VARS[@]}"; do
    val="${!var:-}"
    if [[ -z "$val" ]]; then
        MISSING+=("$var")
    elif [[ "$val" == changeme* ]]; then
        CHANGEME+=("$var")
    fi
done

if [[ ${#MISSING[@]} -gt 0 || ${#CHANGEME[@]} -gt 0 ]]; then
    if [[ ${#MISSING[@]} -gt 0 ]]; then
        echo -e "${RED}Missing required environment variables:${NC}"
        for var in "${MISSING[@]}"; do
            echo -e "  - ${RED}$var${NC}"
        done
    fi
    if [[ ${#CHANGEME[@]} -gt 0 ]]; then
        echo -e "${YELLOW}Placeholder values still set:${NC}"
        for var in "${CHANGEME[@]}"; do
            echo -e "  - ${YELLOW}$var${NC}"
        done
    fi
    echo ""
    echo "Fix: edit .env and set real values for the variables above."
    exit 1
fi

COUNT=${#REQUIRED_VARS[@]}
echo -e "${GREEN}All $COUNT required environment variables are set.${NC}"
