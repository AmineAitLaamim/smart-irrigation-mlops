# =============================================================================
# Smart Irrigation System — Makefile
# =============================================================================

COMPOSE_BASE    := docker compose --env-file .env -f docker/docker-compose.yml
COMPOSE_MON     := $(COMPOSE_BASE) -f docker/docker-compose.monitoring.yml
COMPOSE_ML      := $(COMPOSE_BASE) -f docker/docker-compose.ml.yml
COMPOSE_DATA    := $(COMPOSE_BASE) -f docker/docker-compose.data.yml
COMPOSE_APP     := $(COMPOSE_BASE) -f docker/docker-compose.app.yml
COMPOSE_ALL     := $(COMPOSE_BASE) \
                   -f docker/docker-compose.app.yml \
                   -f docker/docker-compose.data.yml \
                   -f docker/docker-compose.ml.yml \
                   -f docker/docker-compose.monitoring.yml

.DEFAULT_GOAL := help

# -----------------------------------------------------------------------------
# Help
# -----------------------------------------------------------------------------
.PHONY: help
help:
	@echo ""
	@echo "Smart Irrigation System — available targets"
	@echo ""
	@echo "  Setup"
	@echo "    make env            Copy .env.example → .env (first-time setup)"
	@echo "    make check-env      Validate all required env vars are set"
	@echo ""
	@echo "  Startup"
	@echo "    make up             Start all 19 containers"
	@echo "    make up-base        Start base infra only (timescaledb, redis, mlflow, minio)"
	@echo "    make up-data        Start base + data pipeline"
	@echo "    make up-ml          Start base + ML pipeline"
	@echo "    make up-app         Start base + user-facing services"
	@echo "    make up-monitoring  Start base + monitoring + CI/CD"
	@echo "    make jenkins        Start Jenkins service only"
	@echo "    make build-jenkins-agents Build custom Jenkins controller and agent images"
	@echo ""
	@echo "  Teardown"
	@echo "    make down           Stop all containers (keep volumes)"
	@echo "    make down-v         Stop all containers and delete volumes"
	@echo "    make clear-volumes  Stop containers and clear their volumes (same as down-v)"
	@echo ""
	@echo "  Development"
	@echo "    make ps             Show running containers and health status"
	@echo "    make logs           Tail logs from all containers"
	@echo "    make logs s=NAME    Tail logs from a specific service (e.g. make logs s=api-gateway)"
	@echo "    make logs-jenkins   Tail logs from the Jenkins container"
	@echo "    make build          Build all custom service images"
	@echo "    make build s=NAME   Build a specific service image"
	@echo "    make rebuild        Rebuild without cache and recreate all containers"
	@echo "    make rebuild s=NAME Rebuild without cache and recreate a specific service"
	@echo "    make restart s=NAME Restart a specific service"
	@echo ""
	@echo "  Database"
	@echo "    make migrate        Run pending database migrations"
	@echo "    make psql           Open psql shell in timescaledb container"
	@echo ""
	@echo "  Testing"
	@echo "    make test           Run unit + integration tests"
	@echo "    make test-all       Run all unit tests across services using uv"
	@echo "    make smoke          Run end-to-end smoke test"
	@echo ""
	@echo "  Utilities"
	@echo "    make generate-data  Generate a batch of sensor readings (use count=100 interval=30)"
	@echo "    make redis-cli      Open redis-cli shell"
	@echo "    make mlflow         Open MLflow UI in browser"
	@echo "    make grafana        Open Grafana UI in browser"
	@echo "    make tunnel         Expose Jenkins via ngrok"
	@echo ""

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------
.PHONY: env
env:
	@bash scripts/init_env.sh

.PHONY: check-env
check-env:
	@bash scripts/check_env.sh

# -----------------------------------------------------------------------------
# Startup
# -----------------------------------------------------------------------------
.PHONY: up
up: check-env
	$(COMPOSE_ALL) up -d
	@echo ""
	@echo "All 19 containers starting. Run 'make ps' to check health status."

.PHONY: up-base
up-base: check-env
	$(COMPOSE_BASE) up -d

.PHONY: up-data
up-data: check-env
	$(COMPOSE_DATA) up -d

.PHONY: up-ml
up-ml: check-env
	$(COMPOSE_ML) up -d

.PHONY: up-app
up-app: check-env
	$(COMPOSE_APP) up -d

.PHONY: up-monitoring
up-monitoring: check-env
	$(COMPOSE_MON) up -d

.PHONY: jenkins
jenkins: check-env
	$(COMPOSE_MON) up -d jenkins

.PHONY: build-jenkins-agents
build-jenkins-agents: check-env
	docker build -t jenkins-controller:latest -f jenkins/Dockerfile.jenkins jenkins/
	docker build -t smart-irrigation-python-agent:latest -f jenkins/Dockerfile.python-agent jenkins/
	docker build -t smart-irrigation-docker-agent:latest -f jenkins/Dockerfile.docker-agent jenkins/

.PHONY: rebuild-jenkins
rebuild-jenkins: check-env
	@docker network inspect irrigation_net >/dev/null 2>&1 || (echo "Creating irrigation_net..." && docker network create irrigation_net)
	$(COMPOSE_MON) build --no-cache jenkins jenkins-python-agent jenkins-docker-agent
	$(COMPOSE_MON) up -d --force-recreate jenkins

# -----------------------------------------------------------------------------
# Teardown
# -----------------------------------------------------------------------------
.PHONY: down
down:
	$(COMPOSE_ALL) down

.PHONY: down-v
down-v:
	@echo "WARNING: This will delete all volumes including the database. Continue? [y/N]"
	@read ans && [ $${ans:-N} = y ] && $(COMPOSE_ALL) down -v || echo "Aborted."

.PHONY: clear-volumes
clear-volumes: down-v

# -----------------------------------------------------------------------------
# Development
# -----------------------------------------------------------------------------
.PHONY: ps
ps:
	$(COMPOSE_ALL) ps

.PHONY: logs
logs:
ifdef s
	$(COMPOSE_ALL) logs -f $(s)
else
	$(COMPOSE_ALL) logs -f
endif

.PHONY: logs-jenkins
logs-jenkins:
	docker logs -f jenkins

.PHONY: build
build: check-env
ifdef s
	$(COMPOSE_ALL) build $(s)
	$(COMPOSE_ALL) up -d $(s)
else
	$(COMPOSE_ALL) build
	$(COMPOSE_ALL) up -d
endif

.PHONY: rebuild
rebuild: check-env
ifdef s
	$(COMPOSE_ALL) build --no-cache $(s)
	$(COMPOSE_ALL) up -d --force-recreate $(s)
else
	$(COMPOSE_ALL) build --no-cache
	$(COMPOSE_ALL) up -d --force-recreate
endif

.PHONY: restart
restart:
ifndef s
	$(error Usage: make restart s=SERVICE_NAME)
endif
	$(COMPOSE_ALL) restart $(s)

# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------
.PHONY: migrate
migrate:
	@export $$(grep -v '^\s*#' .env | grep -v '^\s*$$' | sed 's/\r$$//' | xargs); \
	docker exec -i timescaledb bash /docker-entrypoint-initdb.d/01_run_migrations.sh
	@echo "Migrations applied."

.PHONY: psql
psql:
	@export $$(grep -v '^\s*#' .env | grep -v '^\s*$$' | xargs); \
	docker exec -it timescaledb psql -U $${POSTGRES_USER} -d $${POSTGRES_DB}

# -----------------------------------------------------------------------------
# Testing
# -----------------------------------------------------------------------------
.PHONY: test
test:
	@echo "Tip: run 'pytest tests/' locally with your virtualenv active."

.PHONY: test-all
test-all:
	@echo "Running all unit and integration tests using uv..."
	@for service in api-gateway data-ingestion drift-monitor feature-engineering irrigation-controller model-server notification-service sensor-simulator user-service; do \
		if find services/$$service/tests -name "test_*.py" | grep -q .; then \
			echo "----------------------------------------------------------------------"; \
			echo "Testing $$service..."; \
			echo "----------------------------------------------------------------------"; \
			PYTHONPATH=services/$$service:services/$$service/src ENV=testing uv run \
				--with pytest --with pytest-asyncio --with fastapi --with httpx --with python-jose --with PyJWT --with passlib --with redis --with asyncpg --with prometheus-client --with "pydantic[email]" \
				pytest services/$$service/tests/ || exit 1; \
		else \
			echo "No tests found for $$service, skipping."; \
		fi; \
	done

.PHONY: test-all-psh
test-all-psh:
	@echo "Running all unit and integration tests using PowerShell..."
	@powershell -NoProfile -Command "$$services = @('api-gateway','data-ingestion','drift-monitor','feature-engineering','irrigation-controller','model-server','notification-service','sensor-simulator','user-service'); $$failed = $$false; foreach ($$service in $$services) { $$testPath = Join-Path 'services' $$service; $$testDir = Join-Path $$testPath 'tests'; if (Test-Path $$testDir) { $$tests = Get-ChildItem -Path $$testDir -Recurse -Filter 'test_*.py'; if ($$tests.Count -gt 0) { Write-Host '----------------------------------------------------------------------'; Write-Host \"Testing $$service...\"; Write-Host '----------------------------------------------------------------------'; $$env:PYTHONPATH = \"services/$$service;services/$$service/src\"; uv run --with pytest --with pytest-asyncio --with fastapi --with httpx --with python-jose --with PyJWT --with passlib --with redis --with asyncpg --with prometheus-client --with 'pydantic[email]' pytest $$testDir; if ($$LASTEXITCODE -ne 0) { $$failed = $$true; break } } else { Write-Host \"No tests found for $$service, skipping.\" } } else { Write-Host \"No tests found for $$service, skipping.\" } }; if ($$failed) { exit 1 }"

.PHONY: smoke
smoke:
	@bash scripts/smoke_test.sh

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------
.PHONY: generate-data
generate-data:
	@echo "Syncing generator script to container..."
	@docker cp services/sensor-simulator/src/batch_generate.py sensor-simulator:/app/src/batch_generate.py
	@echo "Generating batch of sensor readings..."
	@docker exec sensor-simulator python src/batch_generate.py \
		--count $(or $(count),$(or $(n),100)) \
		--interval $(or $(interval),$(or $(i),30))

.PHONY: fast-forward
fast-forward:
	@echo "Syncing generator script to container..."
	@docker cp services/sensor-simulator/src/batch_generate.py sensor-simulator:/app/src/batch_generate.py
	@echo "Simulating 12 hours passing forward (generating 1440 data points per sensor)..."
	@docker exec sensor-simulator python src/batch_generate.py --count 1440 --interval 30 --forward
	@echo "Time travel complete! Future data is being ingested."


.PHONY: redis-cli
redis-cli:
	docker exec -it redis redis-cli

.PHONY: mlflow
mlflow:
	@echo "Opening MLflow at http://localhost:5000"
	@xdg-open http://localhost:5000 2>/dev/null || open http://localhost:5000 2>/dev/null || true

.PHONY: grafana
grafana:
	@echo "Opening Grafana at http://localhost:3001"
	@xdg-open http://localhost:3001 2>/dev/null || open http://localhost:3001 2>/dev/null || true

.PHONY: tunnel
tunnel:
	@echo "Starting ngrok for Jenkins on port $(or $(JENKINS_PORT),8081)..."
	ngrok http $(or $(JENKINS_PORT),8081)

.PHONY: tunnel-dashboard
tunnel-dashboard:
	@echo "Starting ngrok for Web Dashboard on port 80..."
	ngrok http 80

.PHONY: tunnel-api
tunnel-api:
	@echo "Starting ngrok for API Gateway on port 8080..."
	ngrok http 8080

.PHONY: tunnel-stop
tunnel-stop:
	@echo "Stopping all ngrok tunnels..."
	ngrok disconnect || true
	@echo "Ngrok tunnels stopped"
