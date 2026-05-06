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
                  url("https://github.com/AmineAitLaamim/smart-irrigation-mlops.git")
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