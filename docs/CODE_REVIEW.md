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
