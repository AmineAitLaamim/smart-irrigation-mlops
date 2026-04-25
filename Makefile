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
	@echo ""
	@echo "  Development"
	@echo "    make ps             Show running containers and health status"
	@echo "    make logs           Tail logs from all containers"
	@echo "    make logs s=NAME    Tail logs from a specific service (e.g. make logs s=api-gateway)"
	@echo "    make logs-jenkins   Tail logs from the Jenkins container"
	@echo "    make build          Build all custom service images"
	@echo "    make build s=NAME   Build a specific service image"
	@echo "    make restart s=NAME Restart a specific service"
	@echo ""
	@echo "  Database"
	@echo "    make migrate        Run pending database migrations"
	@echo "    make psql           Open psql shell in timescaledb container"
	@echo ""
	@echo "  Testing"
	@echo "    make test           Run unit + integration tests"
	@echo "    make smoke          Run end-to-end smoke test"
	@echo ""
	@echo "  Utilities"
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
build:
ifdef s
	$(COMPOSE_ALL) build $(s)
else
	$(COMPOSE_ALL) build
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
	@export $$(grep -v '^\s*#' .env | grep -v '^\s*$$' | xargs); \
	docker exec -i timescaledb psql -U $${POSTGRES_USER} -d $${POSTGRES_DB} \
		-f /docker-entrypoint-initdb.d/run_migrations.sql
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

.PHONY: smoke
smoke:
	@bash scripts/smoke_test.sh

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------
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
