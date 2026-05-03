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
