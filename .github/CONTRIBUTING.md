# Contributing Guide

## Table of Contents
1. [Branch Structure](#branch-structure)
2. [Branch Naming](#branch-naming)
3. [Commit Message Convention](#commit-message-convention)
4. [Pull Request Process](#pull-request-process)
5. [Code Review Guidelines](#code-review-guidelines)
6. [Pre-commit Hooks](#pre-commit-hooks)
7. [Interface Contract Changes](#interface-contract-changes)
8. [Conflict Prevention](#conflict-prevention)

---

## Branch Structure

```
main
└── develop
    ├── devops     ← DevOps commits directly here
    ├── dataops    ← DataOps commits directly here
    └── mlops      ← MLOps commits directly here
```

| Branch | Purpose | Who commits here |
|---|---|---|
| `main` | Production ready, demo ready | Nobody directly — only via PR from `develop` |
| `develop` | Integration branch | Nobody directly — only via PR from role branches |
| `devops` | DevOps working branch | DevOps only — commits directly |
| `dataops` | DataOps working branch | DataOps only — commits directly |
| `mlops` | MLOps working branch | MLOps only — commits directly |
| `fix/*` | Cross-role bug fix | Anyone — created from `develop` when needed |
| `chore/*` | Maintenance | Anyone — created from `develop` when needed |

Each role owns their branch completely. No feature branches needed inside role branches — just commit directly.

---

## Branch Naming

Each role commits directly to their branch:

```bash
# DevOps — commit directly to devops
git checkout devops
git commit -m "[DO] init docker-compose with timescaledb and redis"
git push origin devops

# DataOps — commit directly to dataops
git checkout dataops
git commit -m "[DA] create sensor_readings hypertable migration"
git push origin dataops

# MLOps — commit directly to mlops
git checkout mlops
git commit -m "[ML] train initial XGBoost model with Optuna"
git push origin mlops
```

**Fix and chore branches** are the only short-lived branches — created from `develop` for cross-role issues:

```bash
git checkout develop
git checkout -b fix/redis-connection-timeout
git checkout -b chore/update-dependencies
```

Fix and chore branch names should be short and descriptive:

```
fix/redis-connection-timeout    ✓
fix/jwt-token-expiry            ✓
fix/zone-ownership-bug          ✓
chore/update-dependencies       ✓
chore/cleanup-dockerfiles       ✓

fix/DO-04-redis-fix             ✗  task ID not needed here
fix/the-bug                     ✗  too vague
```

---

## Commit Message Convention

### Format

```
[TAG] short description of what you did
```

### Tags

| Tag | When to use |
|---|---|
| `[DO]` | DevOps work |
| `[DA]` | DataOps work |
| `[ML]` | MLOps work |
| `[FIX]` | Bug fix |
| `[CHORE]` | Maintenance, no new features |
| `[SHARED]` | Shared work (smoke tests, git workflow) |

### Good examples

```bash
[DO] init docker-compose with timescaledb and redis
[DO] add named volumes and resource limits to compose
[DO] add Jenkinsfile with lint and test stages
[DO] configure Prometheus scrape intervals for all services
[DO] implement JWT validation in API gateway middleware
[DO] scaffold Next.js 15 dashboard with Tailwind and shadcn
[DA] create sensor_readings hypertable migration
[DA] implement Redis Pub/Sub ingestion pipeline
[DA] add plausibility bounds validation for sensor readings
[DA] set up Great Expectations quality suites
[ML] set up MLflow experiment tracking and model registry
[ML] train initial XGBoost model with Optuna optimization
[ML] expose prediction REST endpoint on port 8501
[ML] implement Page-Hinkley drift detection
[FIX] resolve redis connection timeout on startup
[FIX] fix zone ownership validation for admin users
[CHORE] update ruff to v0.5.0
[CHORE] remove unused debug print statements
[SHARED] add end-to-end smoke test script
```

### Bad examples

```bash
fix stuff                          ✗  too vague
update                             ✗  too vague
[DO] fixed the docker thing        ✗  too vague, use present tense
devops: init docker-compose        ✗  wrong format
DO-01: init docker-compose         ✗  task ID belongs in PR description not commit
[DO] Added jenkins pipeline.       ✗  past tense, has period at end
```

### Rules

- Keep it under 72 characters
- Use present tense — "add" not "added", "fix" not "fixed"
- Describe *what* you did, not *how* you did it
- No period at the end
- One logical change per commit — do not bundle unrelated changes

### Filtering commits by role

```bash
git log --oneline | grep "\[DO\]"      # DevOps commits only
git log --oneline | grep "\[DA\]"      # DataOps commits only
git log --oneline | grep "\[ML\]"      # MLOps commits only
git log --oneline | grep "\[FIX\]"     # all fixes
```

---

## Pull Request Process

### Who reviews what

| PR | Author | Reviewer | Can merge? |
|---|---|---|---|
| `dataops` → `develop` | DataOps | **DevOps** | ❌ Needs DevOps approval |
| `mlops` → `develop` | MLOps | **DevOps** | ❌ Needs DevOps approval |
| `devops` → `develop` | DevOps | **DevOps** | ❌ Needs DevOps approval |
| `develop` → `main` | DevOps | **DevOps** | ❌ Needs DevOps approval |
| `fix/*` → `develop` | Anyone | **DevOps** | ❌ Needs DevOps approval |
| `chore/*` → `develop` | Anyone | **DevOps** | ❌ Needs DevOps approval |

**DevOps is the sole reviewer for anything merging into `develop` or `main`.**
DataOps and MLOps commit freely to their own branches with no review required.

### Daily work — commit directly to your role branch

```bash
# DataOps working on DA-01
git checkout dataops
git commit -m "[DA] create sensor_readings hypertable migration"
git push origin dataops

# MLOps working on ML-03
git checkout mlops
git commit -m "[ML] train initial XGBoost model with Optuna"
git push origin mlops

# DevOps working on DO-01
git checkout devops
git commit -m "[DO] init docker-compose with timescaledb and redis"
git push origin devops
```

### Role branch → develop (end of sprint — DevOps review required)

1. Open PR: `dataops` → `develop` or `mlops` → `develop` or `devops` → `develop`
2. Fill in the PR template
3. **DevOps must review and approve**
4. CI checks must pass (Jenkins lint + tests)
5. Run smoke test on `develop` after all roles merge
6. Fix any integration issues with a `fix/*` branch

### develop → main (DevOps review required)

1. Open PR: `develop` → `main`
2. **DevOps must review and approve**
3. Smoke test must pass on `develop`
4. Merge only when the system is fully working end-to-end

### Fix and chore branches

```bash
# bug fix — created from develop, affects multiple roles
git checkout develop
git checkout -b fix/redis-connection-timeout
git commit -m "[FIX] resolve redis connection timeout on startup"
git push origin fix/redis-connection-timeout
# PR: fix/redis-connection-timeout → develop
# DevOps must approve before merge

# maintenance — same flow
git checkout develop
git checkout -b chore/update-dependencies
git commit -m "[CHORE] update ruff to v0.5.0"
git push origin chore/update-dependencies
# PR: chore/update-dependencies → develop
# DevOps must approve before merge
```

---

## Code Review Guidelines

### Who reviews

**DevOps is the sole reviewer** for all PRs targeting `develop` or `main`.
DataOps and MLOps do not need a review to merge within their own branches.

### DevOps — as reviewer, check for

- Code follows project conventions (naming, structure, formatting)
- Tests are added or updated for the changes
- No hardcoded secrets, passwords, or API keys
- `.env.example` is updated if new environment variables are added
- Interface contracts are respected (Pydantic schemas, Redis channel formats, API endpoints)
- Docker-related changes do not break the compose stack
- No unnecessary dependencies added

### DataOps and MLOps — as authors, before opening a PR to develop

- Self-review your own diff before requesting review
- Make sure pre-commit hooks pass locally
- Run relevant tests locally before pushing
- Keep PRs focused — one task per PR
- Write a clear PR description explaining what changed and why

### Review turnaround

- DevOps responds to review requests within **24 hours**
- If a PR is blocked for more than 24 hours, raise it in the daily standup

---

## Pre-commit Hooks

Install once after cloning the repository:

```bash
./scripts/setup.sh
```

Or manually:

```bash
pip install pre-commit
pre-commit install
```

Hooks run automatically on every `git commit`:

| Hook | What it does |
|---|---|
| `ruff` | Python linting — catches errors, unused imports, bad style. Auto-fixes minor issues |
| `ruff-format` | Python code formatting — consistent spacing and indentation |
| `mypy` | Python type checking — catches type errors before runtime |
| `detect-secrets` | Scans for accidentally committed passwords, API keys, tokens |

If a hook fails, the commit is **blocked** until you fix the issue:

```bash
git commit -m "[DO] add docker-compose services"

# ruff finds an unused import → commit blocked
# fix the import → run git commit again → passes → commit goes through
```

To run hooks manually without committing:

```bash
pre-commit run --all-files
```

---

## Interface Contract Changes

Some changes affect multiple team members and require coordination before merging.

If your PR modifies any of the following, you **must notify all affected team members** before merging:

| Contract | Affects | How to notify |
|---|---|---|
| Pydantic schemas (ZoneCreate, UserCreate, etc.) | All services consuming the API | Comment in PR + mention in standup |
| Redis channel format (sensor:data, features:computed, etc.) | Producer and consumer services | Comment in PR + mention in standup |
| API endpoints (new route, changed response) | web-dashboard, API gateway | Comment in PR + mention in standup |
| Database schema (new table, new column) | All services using that table | Comment in PR + mention in standup |
| Docker Compose (new service, changed port) | All team members | Comment in PR + mention in standup |

PRs that modify interface contracts **must be reviewed and approved by DevOps** before merging, regardless of which role authored them.

---

## Conflict Prevention

### Ownership boundaries

Each team member owns their service directories exclusively:

| Role | Owns |
|---|---|
| DevOps | `api-gateway/`, `user-service/`, `web-dashboard/`, `notification-service/`, `docker/`, `jenkins/`, `configs/monitoring/` |
| DataOps | `sensor-simulator/`, `data-ingestion/`, `migrations/001`, `migrations/002`, `scripts/backup.sh` |
| MLOps | `feature-engineering/`, `model-server/`, `drift-monitor/`, `irrigation-controller/`, `airflow/`, `migrations/003`, `migrations/004` |
| Shared | `configs/zones/zone_config.yaml`, `tests/`, `scripts/smoke_test.sh`, `migrations/005` |

Do not modify files outside your domain without coordinating with the owner first.

### Shared files coordination

| File | Owner | Protocol |
|---|---|---|
| `docker/docker-compose.yml` | DevOps | Notify all members before modifying |
| `configs/zones/zone_config.yaml` | Shared | Any member can add zones, coordinate on schema changes |
| `migrations/001-004` | DataOps/MLOps | Coordinate with DevOps before modifying |
| `migrations/005` | DevOps | Notify DataOps and MLOps of any schema changes |
| `.env.example` | DevOps | All members add their vars, DevOps maintains the file |
| `Makefile` | DevOps | Members can request new targets |
| `tests/integration/` | Shared | All members contribute |

### Daily standup

The team holds a brief daily sync to:
- Share progress on current tasks
- Flag potential interface contract changes early
- Resolve cross-service dependencies before they become blockers
- Update the GitHub Projects board
