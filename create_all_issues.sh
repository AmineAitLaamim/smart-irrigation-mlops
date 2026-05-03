#!/bin/bash

REPO="AmineAitLaamim/smart-irrigation"

echo "Creating labels..."

gh label create "devops" --color "E4761B" --description "DevOps tasks" --repo $REPO 2>/dev/null
gh label create "mlops" --color "28A745" --description "MLOps tasks" --repo $REPO 2>/dev/null
gh label create "dataops" --color "0075CA" --description "DataOps tasks" --repo $REPO 2>/dev/null
gh label create "shared" --color "6F42C1" --description "Shared tasks" --repo $REPO 2>/dev/null
gh label create "sprint-1" --color "FFC107" --description "Sprint 1" --repo $REPO 2>/dev/null
gh label create "sprint-2" --color "FFC107" --description "Sprint 2" --repo $REPO 2>/dev/null
gh label create "sprint-3" --color "FFC107" --description "Sprint 3" --repo $REPO 2>/dev/null
gh label create "sprint-4" --color "FFC107" --description "Sprint 4" --repo $REPO 2>/dev/null
gh label create "critical" --color "D73A4A" --description "Critical priority" --repo $REPO 2>/dev/null
gh label create "high" --color "E99695" --description "High priority" --repo $REPO 2>/dev/null
gh label create "medium" --color "F9D0C4" --description "Medium priority" --repo $REPO 2>/dev/null
gh label create "critical-path" --color "B60205" --description "Critical path task" --repo $REPO 2>/dev/null

echo "Labels created."
echo ""

# ============================================================
# DATAOPS TASKS (DA-01 to DA-07)
# ============================================================
echo "Creating DataOps issues..."

gh issue create --repo $REPO \
  --title "DA-01: Database Schema Design and Initial Setup" \
  --label "dataops,sprint-1,critical,critical-path" \
  --body "## Description
Design the complete database schema including all tables, indexes, constraints, and hypertable configurations.

## Deliverables
- Create migration 001 (init_timescaledb.sql) with sensor_readings hypertable, zones table, sensor_metadata table, irrigation_events hypertable
- Configure TimescaleDB chunk intervals (1 day for sensor_readings, 1 week for irrigation_events)
- Set up connection pooling parameters
- Define initial database roles and permissions for each service

## Priority
CRITICAL

## Dependencies
None"
echo "DA-01 created"

gh issue create --repo $REPO \
  --title "DA-02: Sensor Data Ingestion Pipeline (Redis Pub/Sub)" \
  --label "dataops,sprint-1,critical,critical-path" \
  --body "## Description
Build the data-ingestion service that subscribes to the sensor:data Redis channel and processes incoming sensor readings.

## Deliverables
- Implement validation logic against zone-specific plausibility bounds (min_plausible and max_plausible)
- Write valid readings to sensor_readings hypertable
- Flag anomalies to data_quality_events hypertable
- Set up connection pooling with asyncpg
- Expose health check endpoint on port 8001 reporting ingestion statistics

## Priority
CRITICAL

## Dependencies
DA-01"
echo "DA-02 created"

gh issue create --repo $REPO \
  --title "DA-03: ETL Pipeline Development" \
  --label "dataops,sprint-2,high" \
  --body "## Description
Develop extract-transform-load pipelines that process raw sensor data into analysis-ready formats.

## Deliverables
- Transformation logic for data cleaning (deduplication, null handling, outlier smoothing)
- Aggregation (hourly and daily rollups)
- Feature computation triggers
- Configurable through environment variables
- Support both batch and streaming execution modes
- Integration with the feature-engineering service

## Priority
HIGH

## Dependencies
DA-01, DA-02"
echo "DA-03 created"

gh issue create --repo $REPO \
  --title "DA-04: Data Quality and Validation Framework" \
  --label "dataops,sprint-2,high" \
  --body "## Description
Implement a comprehensive data quality framework that validates sensor readings and detects sensor malfunctions.

## Deliverables
- Validate sensor readings against zone-specific plausibility bounds
- Detect sensor malfunctions (stuck values, sudden jumps)
- Generate quality reports
- Write anomalous readings to data_quality_events hypertable with anomaly classification
- Create configurable quality rules updatable without code changes
- Integrate quality metrics with Grafana monitoring stack

## Priority
HIGH

## Dependencies
DA-01, DA-02"
echo "DA-04 created"

gh issue create --repo $REPO \
  --title "DA-05: Database Migration Management" \
  --label "dataops,sprint-2,high" \
  --body "## Description
Set up the database migration management system including tracking table, execution scripts, and rollback procedures.

## Deliverables
- Set up schema_migrations tracking table
- Create migrations 001 through 005 with proper up/down functions
- Implement migration runner that applies pending migrations in order at container startup
- Document migration conventions and create templates for future migrations
- Ensure migrations are idempotent and safely re-runnable

## Priority
HIGH

## Dependencies
DA-01"
echo "DA-05 created"

gh issue create --repo $REPO \
  --title "DA-06: ML Feature Store Setup" \
  --label "dataops,sprint-1,high" \
  --body "## Description
Design and implement the feature_references table and supporting infrastructure for the ML feature store.

## Deliverables
- Define schema for storing computed features with zone references, timestamps, and model version tags
- Create the feature engineering service scaffold for MLOps
- Set up Redis channel contracts (ingestion:processed, features:computed)
- Document the feature computation pipeline
- Provide sample feature definitions for common agricultural metrics

## Priority
HIGH

## Dependencies
DA-01"
echo "DA-06 created"

gh issue create --repo $REPO \
  --title "DA-07: Data Backup and Recovery Strategy" \
  --label "dataops,sprint-3,high" \
  --body "## Description
Implement automated database backup and recovery procedures using pg_dump and pg_restore.

## Deliverables
- Create scripts/backup.sh with daily full backups (7-day retention) and hourly WAL archiving
- Configure backup verification that restores latest backup to a test database
- Run integrity checks after restore
- Document recovery procedures
- RTO: 30 minutes, RPO: 1 hour

## Priority
HIGH

## Dependencies
DA-01"
echo "DA-07 created"

echo "DataOps issues done."
echo ""

# ============================================================
# MLOPS TASKS (ML-01 to ML-15)
# ============================================================
echo "Creating MLOps issues..."

gh issue create --repo $REPO \
  --title "ML-01: ML Environment Setup and Data Exploration" \
  --label "mlops,sprint-1,high,critical-path" \
  --body "## Description
Set up the ML development environment and explore existing sensor data from TimescaleDB.

## Deliverables
- Set up Python 3.11 with XGBoost, scikit-learn, Optuna, pandas, numpy, matplotlib
- Configure MLflow for experiment tracking and model registry
- Explore sensor data (distributions, correlations, quality patterns)
- Generate initial data analysis reports (moisture distribution by soil type, seasonal patterns, sensor reliability)
- Document findings in an ML exploration notebook

## Priority
HIGH

## Dependencies
DA-01"
echo "ML-01 created"

gh issue create --repo $REPO \
  --title "ML-02: Data Preparation Pipeline Integration" \
  --label "mlops,sprint-1,high,critical-path" \
  --body "## Description
Build the data preparation pipeline that fetches raw sensor readings and produces training-ready datasets.

## Deliverables
- Fetch raw sensor readings from TimescaleDB and apply cleaning and normalization
- Integrate with feature store (feature_references table)
- Implement train/validation/test splitting with time-aware cross-validation to prevent data leakage
- Create data versioning using MLflow datasets

## Priority
HIGH

## Dependencies
ML-01, DA-02"
echo "ML-02 created"

gh issue create --repo $REPO \
  --title "ML-03: Soil Moisture Prediction Model (XGBoost)" \
  --label "mlops,sprint-2,critical,critical-path" \
  --body "## Description
Train the XGBoost soil moisture prediction model using prepared datasets.

## Deliverables
- Perform feature selection from sensor and engineered features
- Use Optuna for hyperparameter optimization with time-series cross-validation
- Evaluate using RMSE, MAE, and R-squared metrics
- Compare XGBoost against baseline models (linear regression, random forest)
- Document performance comparison
- Register best model in MLflow with a model card

## Priority
CRITICAL

## Dependencies
ML-02, DA-06"
echo "ML-03 created"

gh issue create --repo $REPO \
  --title "ML-04: Model Training Pipeline Automation" \
  --label "mlops,sprint-2,high" \
  --body "## Description
Automate the model training pipeline using Apache Airflow DAGs.

## Deliverables
- Airflow DAG that fetches latest data, runs feature computation, trains with Optuna
- Evaluate performance against current production model
- Promote to production only if new model outperforms baseline by configured margin
- Configure MLflow model registry stages (None, Staging, Production, Archived) with automated transition rules

## Priority
HIGH

## Dependencies
ML-03"
echo "ML-04 created"

gh issue create --repo $REPO \
  --title "ML-05: Model Evaluation and Validation" \
  --label "mlops,sprint-2,high" \
  --body "## Description
Implement comprehensive model evaluation including cross-validation, holdout validation, and shadow mode testing.

## Deliverables
- Cross-validation and holdout validation
- Production shadow mode (new model runs alongside production without affecting irrigation decisions)
- Compare predictions using statistical tests (paired t-test, Diebold-Mariano test)
- Create evaluation reports with confidence intervals and failure case analysis

## Priority
HIGH

## Dependencies
ML-03, ML-04"
echo "ML-05 created"

gh issue create --repo $REPO \
  --title "ML-06: Prediction API Development" \
  --label "mlops,sprint-3,critical,critical-path" \
  --body "## Description
Build the model-server service exposing the XGBoost model through gRPC and REST endpoints.

## Deliverables
- gRPC endpoint on port 5001 for low-latency inter-service communication
- REST endpoint on port 8501 for API Gateway integration
- /v1/predict endpoint returning predicted moisture with confidence intervals
- Model metadata endpoints (/v1/model/info, /v1/model/version)
- Model hot-reloading from MLflow registry when new production model is promoted
- Prometheus metrics for prediction latency, throughput, and error rates

## Priority
CRITICAL

## Dependencies
ML-05, DA-06"
echo "ML-06 created"

gh issue create --repo $REPO \
  --title "ML-07: Anomaly Detection Module" \
  --label "mlops,sprint-3,high" \
  --body "## Description
Implement drift monitoring using Page-Hinkley test statistic and KL divergence.

## Deliverables
- Page-Hinkley test statistic computation
- Kullback-Leibler divergence metrics
- Prediction error distribution metrics on a rolling basis
- Publish alerts to Redis when drift exceeds configured thresholds
- Store drift statistics in shadow_model_predictions table
- REST API endpoint at /v1/drift/status

## Priority
HIGH

## Dependencies
ML-06"
echo "ML-07 created"

gh issue create --repo $REPO \
  --title "ML-08: Model Monitoring and Performance Tracking" \
  --label "mlops,sprint-3,high" \
  --body "## Description
Implement model monitoring and performance tracking with Prometheus and Grafana dashboards.

## Deliverables
- Track prediction accuracy over time
- Report performance degradation through Prometheus metrics
- Grafana dashboards for ML performance (prediction accuracy, drift metrics, model latency)
- Coordinate with DevOps for dashboard JSON configuration

## Priority
HIGH

## Dependencies
ML-06"
echo "ML-08 created"

gh issue create --repo $REPO \
  --title "ML-09: Prediction Scheduling Service" \
  --label "mlops,sprint-3,high" \
  --body "## Description
Build prediction scheduling service integrated with Airflow.

## Deliverables
- Airflow DAG for scheduled predictions per zone
- Integration with model server REST endpoint
- Store prediction results in model_predictions hypertable
- Publish prediction events to predictions:new Redis channel

## Priority
HIGH

## Dependencies
ML-06"
echo "ML-09 created"

gh issue create --repo $REPO \
  --title "ML-10: ML Pipeline Containerization" \
  --label "mlops,sprint-3,high" \
  --body "## Description
Containerize all ML pipeline services with optimized Dockerfiles.

## Deliverables
- Optimized Dockerfiles for model-server, drift-monitor, irrigation-controller, feature-engineering
- Multi-stage builds to minimize image size
- Health check commands in each Dockerfile
- Add all ML services to docker-compose.ml.yml
- Verify all containers start and connect correctly

## Priority
HIGH

## Dependencies
ML-06"
echo "ML-10 created"

gh issue create --repo $REPO \
  --title "ML-11: Feature Engineering Enhancement" \
  --label "mlops,sprint-2,high" \
  --body "## Description
Enhance feature engineering with soil-specific indices and additional derived features.

## Deliverables
- Rolling averages (30-minute, 1-hour, 3-hour, 24-hour windows)
- Rate of change metrics and moisture variance
- Soil-type-specific indices
- Store computed features in feature_references table with timestamps, zone references, and model version tags

## Priority
HIGH

## Dependencies
DA-06, ML-02"
echo "ML-11 created"

gh issue create --repo $REPO \
  --title "ML-12: Irrigation Optimization Algorithm" \
  --label "mlops,sprint-3,high" \
  --body "## Description
Build the irrigation controller that evaluates soil moisture predictions against zone thresholds.

## Deliverables
- Evaluate predictions against zone-specific thresholds (moisture_min, moisture_max)
- Trigger irrigation events when moisture predicted to fall below minimum threshold
- Log events to irrigation_events hypertable (zone_id, trigger reason, recommended volume, timestamps)
- Subscribe to prediction events via Redis Pub/Sub with periodic evaluation loop as fallback
- REST API endpoint at /v1/irrigation/events
- Consider recent rainfall data and soil saturation to prevent overwatering

## Priority
HIGH

## Dependencies
ML-05"
echo "ML-12 created"

gh issue create --repo $REPO \
  --title "ML-13: ML API Integration Testing" \
  --label "mlops,sprint-3,medium" \
  --body "## Description
Write and run integration tests for all ML API endpoints against the API Gateway.

## Deliverables
- Test /v1/predict endpoint with valid and invalid inputs
- Test /v1/model/info and /v1/model/version endpoints
- Test /v1/drift/status endpoint
- Test /v1/irrigation/events endpoint
- Verify all responses match Pydantic schema contracts
- Target 80% code coverage for model-server service

## Priority
MEDIUM

## Dependencies
ML-06"
echo "ML-13 created"

gh issue create --repo $REPO \
  --title "ML-14: ML Documentation and Model Cards" \
  --label "mlops,sprint-4,medium" \
  --body "## Description
Write comprehensive ML documentation and model cards for the XGBoost model.

## Deliverables
- Model card: training data, features used, evaluation metrics, known limitations
- Feature engineering documentation explaining each feature and its agricultural significance
- Drift detection documentation explaining Page-Hinkley test and KL divergence thresholds
- API usage documentation for model-server endpoints

## Priority
MEDIUM

## Dependencies
ML-05"
echo "ML-14 created"

gh issue create --repo $REPO \
  --title "ML-15: ML Demo and Presentation Preparation" \
  --label "mlops,sprint-4,medium" \
  --body "## Description
Prepare demo script and presentation materials for the ML components.

## Deliverables
- Demo script showing end-to-end ML pipeline (sensor → features → prediction → irrigation)
- Presentation slides covering model selection rationale, feature engineering, drift detection
- Rehearse demo at least 3 times
- Coordinate with team for integrated system demo

## Priority
MEDIUM

## Dependencies
All ML tasks"
echo "ML-15 created"

echo "MLOps issues done."
echo ""

# ============================================================
# DEVOPS — INFRASTRUCTURE TASKS (DO-01 to DO-11)
# ============================================================
echo "Creating DevOps Infrastructure issues..."

gh issue create --repo $REPO \
  --title "DO-01: Docker Environment Setup and Compose Configuration" \
  --label "devops,sprint-1,critical,critical-path" \
  --body "## Description
Create the complete Docker Compose stack with all core services and networking configuration.

## Deliverables
- docker/docker-compose.yml with timescaledb, redis, mlflow, minio
- Named volumes for persistent data (db_data, redis_data, mlflow_data, airflow_data)
- Resource limits per container to prevent resource starvation
- docker-compose.dev.yml overlay with bind-mounts and debug ports
- .env.example with all required environment variables documented
- Verify 'docker compose up' brings up all infrastructure services successfully

## Priority
CRITICAL

## Dependencies
None"
echo "DO-01 created"

gh issue create --repo $REPO \
  --title "DO-02: CI/CD Pipeline with Jenkins" \
  --label "devops,sprint-1,high" \
  --body "## Description
Set up Jenkins with Configuration as Code and build the main CI pipeline.

## Deliverables
- Jenkins Docker container with Docker CLI installed and socket mounted
- jenkins/jcasc.yml defining security realm, authorization, tool installations, plugin list
- Plugins: Docker Pipeline, Pipeline Utility Steps, Timestamper, Blue Ocean, Cobertura, OWASP Dependency-Check
- Main Jenkinsfile with stages: Checkout, Lint (Ruff + mypy), Unit Tests, Integration Tests, Security Scan, Docker Build Verify
- Pipeline runs on every push and PR
- Branch-specific behavior: all branches get CI, only main gets CD

## Priority
HIGH

## Dependencies
DO-01"
echo "DO-02 created"

gh issue create --repo $REPO \
  --title "DO-03: Monitoring and Alerting Stack" \
  --label "devops,sprint-2,high" \
  --body "## Description
Create docker-compose.monitoring.yml with prometheus, grafana, alertmanager, loki containers.

## Deliverables
- Configure prometheus.yml with scrape configs for all service /metrics endpoints
- Create alert_rules.yml: NoSensorReadings, DataQualityDrop, ModelLatencyHigh, ContainerCPUHigh, ContainerMemoryHigh, ContainerRestart
- Configure Grafana provisioning (datasources.yml auto-configures Prometheus + Loki)
- Build system_overview and data_pipeline Grafana dashboards
- Verify metrics flow from services to Prometheus to Grafana

## Priority
HIGH

## Dependencies
DO-01"
echo "DO-03 created"

gh issue create --repo $REPO \
  --title "DO-04: Infrastructure Security Hardening" \
  --label "devops,sprint-3,high" \
  --body "## Description
Implement security hardening across the Docker infrastructure and Jenkins pipeline.

## Deliverables
- Trivy filesystem scan on all service directories (CVEs in Python dependencies)
- Bandit for Python security issues (SQL injection, hardcoded passwords)
- detect-secrets for accidentally committed credentials
- Fail build on critical CVEs (CVSS >= 9.0)
- Create .pre-commit-config.yaml with ruff, mypy, and detect-secrets hooks
- Publish Trivy and Bandit reports as Jenkins build artifacts

## Priority
HIGH

## Dependencies
DO-01, DO-07"
echo "DO-04 created"

gh issue create --repo $REPO \
  --title "DO-05: Logging Infrastructure" \
  --label "devops,sprint-2,medium" \
  --body "## Description
Configure Loki log aggregation for all services.

## Deliverables
- Configure Loki to receive structured JSON logs from all services via Promtail or direct HTTP push
- Create infra/alertmanager/config.yml with alert routing by zone and severity
- Inhibition rules (suppress data quality alerts during known maintenance)
- Verify logs are searchable from Grafana

## Priority
MEDIUM

## Dependencies
DO-01"
echo "DO-05 created"

gh issue create --repo $REPO \
  --title "DO-06: Backup and Disaster Recovery Infrastructure" \
  --label "devops,sprint-3,medium" \
  --body "## Description
Implement automated backup and disaster recovery infrastructure.

## Deliverables
- Jenkins scheduled build (cron: daily at 02:00) for pg_dump of TimescaleDB
- Rotate old backups (keep last 7)
- Disk space check (alert if > 90%)
- Docker system prune (remove dangling images and containers)
- System health report as build artifact

## Priority
MEDIUM

## Dependencies
DO-01"
echo "DO-06 created"

gh issue create --repo $REPO \
  --title "DO-07: API Gateway Implementation" \
  --label "devops,sprint-2,critical,critical-path" \
  --body "## Description
Build the API Gateway as the single external entry point for all client requests on port 8080.

## Deliverables
- JWT validation (access tokens 15-minute expiry, refresh token rotation)
- Request rate limiting (100 requests per minute per IP)
- CORS configuration for web dashboard
- Path-based routing: /auth/*, /users/* → user-service | /v1/sensors/*, /v1/predictions/* → model-server | /v1/zones/* → zone handler | /v1/drift/* → drift-monitor | /v1/irrigation/* → irrigation-controller | /dashboard/* → web-dashboard
- Zone ownership validation for PUT and DELETE operations

## Priority
CRITICAL

## Dependencies
DO-01, US-01"
echo "DO-07 created"

gh issue create --repo $REPO \
  --title "DO-08: Health Check and Service Discovery" \
  --label "devops,sprint-2,medium" \
  --body "## Description
Implement health check aggregation and service discovery across all 19 containers.

## Deliverables
- GET /health endpoint on API Gateway aggregating all service health statuses
- Health check commands in each Dockerfile
- Service discovery via internal Docker DNS
- Prometheus alert for any service health check failure
- Verify all 19 containers report healthy within 30 seconds of startup

## Priority
MEDIUM

## Dependencies
DO-01"
echo "DO-08 created"

gh issue create --repo $REPO \
  --title "DO-09: Performance Optimization and Load Testing" \
  --label "devops,sprint-3,medium" \
  --body "## Description
Profile and optimize system performance under load.

## Deliverables
- Load testing scripts for API Gateway endpoints
- Identify bottlenecks in the sensor → Redis → ingestion → TimescaleDB pipeline
- Connection pool tuning for TimescaleDB (PgBouncer configuration)
- Redis memory optimization (AOF persistence, allkeys-lru eviction, 256MB limit)
- Document performance benchmarks and tuning decisions

## Priority
MEDIUM

## Dependencies
All services"
echo "DO-09 created"

gh issue create --repo $REPO \
  --title "DO-10: Environment Configuration Management" \
  --label "devops,sprint-1,medium" \
  --body "## Description
Centralize and document all environment configuration across the 19-container stack.

## Deliverables
- Complete .env.example with all required environment variables documented
- Environment-specific overrides (dev, staging, prod)
- No hardcoded secrets anywhere in the codebase
- Document which services consume which environment variables
- Validate required env vars are present at container startup

## Priority
MEDIUM

## Dependencies
None"
echo "DO-10 created"

gh issue create --repo $REPO \
  --title "DO-11: Deployment Automation" \
  --label "devops,sprint-3,high" \
  --body "## Description
Create full deployment automation including Nginx reverse proxy and one-command setup script.

## Deliverables
- Jenkinsfile.deploy: build production images, tag with SHA+version, push to local registry, rolling deploy
- infra/nginx/nginx.conf routing: / → Grafana | /api/* → API gateway | /jenkins → Jenkins | /mlflow → MLflow
- scripts/setup.sh (one-command project initialization: create networks, volumes, run migrations, seed data)
- scripts/teardown.sh (clean removal)
- Verify 'git clone + setup.sh + docker compose up' produces a fully working system

## Priority
HIGH

## Dependencies
DO-02"
echo "DO-11 created"

echo "DevOps Infrastructure issues done."
echo ""

# ============================================================
# DEVOPS — USER SERVICE TASKS (US-01 to US-04)
# ============================================================
echo "Creating DevOps User Service issues..."

gh issue create --repo $REPO \
  --title "US-01: User Authentication Service (JWT/bcrypt)" \
  --label "devops,sprint-1,critical,critical-path" \
  --body "## Description
Build the user-service FastAPI application with JWT-based authentication on port 5005.

## Deliverables
- User registration with bcrypt password hashing (12 rounds)
- Login with JWT access token (15-minute expiry) and refresh token (7-day expiry) issuance
- Token refresh with rotation
- asyncpg connection pooling for users table
- Pydantic v2 schemas: UserCreate, UserResponse, TokenResponse, LoginRequest
- Redis for refresh token blacklist and rate limiting counters
- Failed login tracking: 5-attempt lockout with 15-minute cooldown
- Health check endpoint on port 5005

## Priority
CRITICAL

## Dependencies
DO-01, DA-01"
echo "US-01 created"

gh issue create --repo $REPO \
  --title "US-02: User Management CRUD Operations" \
  --label "devops,sprint-2,high" \
  --body "## Description
Implement full user management endpoints on the user-service.

## Deliverables
- GET /users/me — authenticated user profile retrieval
- PUT /users/me — profile update
- GET /users — admin user listing
- DELETE /users/{id} — admin user deletion
- All endpoints use bcrypt, asyncpg, and Pydantic v2 validation

## Priority
HIGH

## Dependencies
US-01"
echo "US-02 created"

gh issue create --repo $REPO \
  --title "US-03: Zone Ownership and Permission System" \
  --label "devops,sprint-2,high" \
  --body "## Description
Implement the zone ownership model enforced at the API Gateway middleware level.

## Deliverables
- owner_id foreign key on zones table referencing users table
- API-created zones (source=api) assigned authenticated user as owner
- YAML-loaded zones (source=yaml) have owner_id=NULL and are read-only
- PUT and DELETE on /v1/zones/{zone_id} validate authenticated user matches zone owner_id
- Admin users have override access to all zone operations
- POST /v1/zones/{zone_id}/assign for admin zone reassignment

## Priority
HIGH

## Dependencies
US-01, DA-01"
echo "US-03 created"

gh issue create --repo $REPO \
  --title "US-04: User Service Testing and Validation" \
  --label "devops,sprint-3,medium" \
  --body "## Description
Write comprehensive tests for all user service endpoints and authentication flows.

## Deliverables
- Unit tests for registration, login, token refresh, logout
- Integration tests for JWT validation at the API Gateway
- Test zone ownership enforcement (owner can modify, non-owner cannot, admin can override)
- Test token blacklist on logout
- Test rate limiting and lockout after 5 failed attempts
- Target 80% code coverage for user-service

## Priority
MEDIUM

## Dependencies
US-01, US-02, US-03"
echo "US-04 created"

echo "DevOps User Service issues done."
echo ""

# ============================================================
# DEVOPS — WEB DASHBOARD TASKS (WD-01 to WD-03)
# ============================================================
echo "Creating DevOps Web Dashboard issues..."

gh issue create --repo $REPO \
  --title "WD-01: Dashboard Frontend Scaffold and Layout" \
  --label "devops,sprint-2,high,critical-path" \
  --body "## Description
Scaffold the Next.js 15 web dashboard with TypeScript, Tailwind CSS 4, and shadcn/ui.

## Deliverables
- Responsive layout: navigation bar, sidebar for zone navigation, main content area
- Client-side authentication using JWT tokens in httpOnly cookies with automatic refresh
- Login page, dashboard overview page, zone list/detail page layouts
- API client library (api.ts) communicating exclusively through the API Gateway
- Error handling and token refresh logic in api.ts

## Priority
HIGH

## Dependencies
DO-07, US-01"
echo "WD-01 created"

gh issue create --repo $REPO \
  --title "WD-02: Real-Time Data Visualization (REST Polling)" \
  --label "devops,sprint-3,high,critical-path" \
  --body "## Description
Build interactive data visualization components using REST polling every 10 seconds.

## Deliverables
- SensorChart component: moisture levels over time with threshold markers (moisture_min/max lines)
- PredictionChart component: predicted vs actual moisture comparison
- IrrigationEventLog component: recent irrigation triggers
- All components use Recharts or Chart.js
- No WebSocket connections — all real-time updates via periodic REST polling

## Priority
HIGH

## Dependencies
WD-01, DO-07"
echo "WD-02 created"

gh issue create --repo $REPO \
  --title "WD-03: Zone Configuration and Irrigation Management UI" \
  --label "devops,sprint-3,medium" \
  --body "## Description
Build the zone CRUD interface and irrigation management views.

## Deliverables
- ZoneCard component for listing zones
- Zone creation form (name, soil type, crop type, moisture thresholds, plausibility bounds, description)
- Zone detail/edit view and deletion confirmation
- Irrigation event history view with filtering by zone and date range
- Admin zone assignment feature (reassign zone ownership through UI)
- Client-side validation matching Pydantic schema contracts

## Priority
MEDIUM

## Dependencies
WD-01, US-03"
echo "WD-03 created"

echo "DevOps Web Dashboard issues done."
echo ""

# ============================================================
# DEVOPS — PROJECT COORDINATION TASKS (PC-01 to PC-05)
# ============================================================
echo "Creating DevOps Coordination issues..."

gh issue create --repo $REPO \
  --title "PC-01: Project Repository Setup and Standards" \
  --label "devops,sprint-1,high" \
  --body "## Description
Set up the project repository structure and define team development standards.

## Deliverables
- Repository structure matching the smart-irrigation/ directory tree
- .gitignore rules for Python, Node.js, Docker, and ML artifacts
- Branch naming conventions: do/, da/, ml/, fix/, chore/
- Pull request template with description, testing steps, and interface contract changes sections
- Code review guidelines
- Pre-commit hooks for linting and formatting

## Priority
HIGH

## Dependencies
None"
echo "PC-01 created"

gh issue create --repo $REPO \
  --title "PC-02: Sprint Planning and Daily Coordination" \
  --label "devops,sprint-1,medium" \
  --body "## Description
Ongoing sprint planning and daily team coordination throughout the 8-week project.

## Deliverables
- Sprint planning sessions at the start of each sprint (Sprints 1-4)
- Daily standup coordination to identify blockers early
- Track progress on GitHub Projects board
- Adjust sprint plan when tasks take longer than expected
- Communicate cross-domain dependency delays early

## Priority
MEDIUM

## Dependencies
None"
echo "PC-02 created"

gh issue create --repo $REPO \
  --title "PC-03: Code Review and Integration Oversight" \
  --label "devops,sprint-2,medium" \
  --body "## Description
Review pull requests from all team members and oversee cross-domain integration.

## Deliverables
- Review all PRs from DataOps and MLOps team members
- Focus on architectural consistency, code quality, test coverage, security issues
- Verify adherence to project conventions and interface contracts
- After each sprint, verify cross-domain integrations work end-to-end
- Identify integration issues before they compound into blocking problems

## Priority
MEDIUM

## Dependencies
All tasks"
echo "PC-03 created"

gh issue create --repo $REPO \
  --title "PC-04: API Documentation Generation" \
  --label "devops,sprint-4,medium" \
  --body "## Description
Generate complete API documentation for all endpoints exposed through the API Gateway.

## Deliverables
- FastAPI auto-generated OpenAPI docs at /docs and /redoc
- Document all 20 API endpoints with request/response schemas
- Include authentication requirements and ownership rules for each endpoint
- Export OpenAPI JSON spec
- README section explaining how to access and use the API docs

## Priority
MEDIUM

## Dependencies
All services"
echo "PC-04 created"

gh issue create --repo $REPO \
  --title "PC-05: Final Documentation and Handoff Review" \
  --label "devops,sprint-4,medium" \
  --body "## Description
Review and finalize all project documentation for handoff and thesis submission.

## Deliverables
- Review all team member documentation sections for consistency
- Finalize README.md with complete setup instructions
- Verify scripts/setup.sh works on a clean machine
- Ensure all IaC files are version-controlled and documented
- Final review of all Architecture Decision Records (ADRs)

## Priority
MEDIUM

## Dependencies
All tasks"
echo "PC-05 created"

echo "DevOps Coordination issues done."
echo ""

# ============================================================
# SHARED TASKS (SH-01, TSK-SMOKE)
# ============================================================
echo "Creating Shared issues..."

gh issue create --repo $REPO \
  --title "SH-01: Shared Repository Standards and Git Workflow" \
  --label "shared,sprint-1,high" \
  --body "## Description
Define and document the Git workflow and repository standards for all team members.

## Deliverables
- Repository structure documentation
- .gitignore rules for Python, Node.js, Docker, ML artifacts
- Branch naming conventions: do/, da/, ml/, fix/, chore/
- Pull request template
- Code review guidelines
- Pre-commit hooks for linting and formatting (ruff, mypy)
- Jenkins shared library with reusable pipeline functions
- Contribution workflow guide so all members can work independently without conflicts

## Priority
HIGH

## Dependencies
PC-01"
echo "SH-01 created"

gh issue create --repo $REPO \
  --title "TSK-SMOKE: End-to-End Smoke Testing" \
  --label "shared,sprint-4,high" \
  --body "## Description
Write and execute the scripts/smoke_test.sh script that verifies the complete system is operational.

## Deliverables
- Verify all 19 containers are running and healthy
- Verify sensor data flows through the pipeline (sensor → Redis → ingestion → TimescaleDB)
- Verify model server responds to prediction requests
- Verify user registration and login works
- Verify zone CRUD operations work with ownership validation
- Verify web dashboard loads and displays data
- Smoke test must pass before any release or demo

## Priority
HIGH

## Dependencies
All services"
echo "TSK-SMOKE created"

echo ""
echo "All 47 issues created successfully!"
echo "Go to https://github.com/smart-irrigation-mlops/smart-irrigation/issues to verify."
echo "Then open your GitHub Project board to organize them."
