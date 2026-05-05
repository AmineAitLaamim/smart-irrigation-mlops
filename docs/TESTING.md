# Testing Guide

## Overview

The Smart Irrigation System uses pytest for unit and integration testing across all services. Tests are organized by service with unit tests for core logic and integration tests for API endpoints.

---

## Test Structure

```
services/
├── api-gateway/
│   └── tests/
│       ├── unit/
│       │   ├── test_auth.py
│       │   └── test_routes.py
│       └── integration/
│           └── test_endpoints.py
├── user-service/
│   └── tests/
│       ├── unit/
│       │   ├── test_auth.py
│       │   └── test_routes.py
│       └── integration/
├── model-server/
│   └── tests/
│       ├── unit/
│       │   └── test_model_service.py
│       └── integration/
├── drift-monitor/
│   └── tests/
│       ├── unit/
│       │   └── test_drift_detector.py
│       └── integration/
├── feature-engineering/
│   └── tests/
│       ├── unit/
│       │   └── test_feature_computation.py
│       └── integration/
└── irrigation-controller/
    └── tests/
        └── integration/
```

---

## Running Tests

### Run all tests

```bash
pytest
```

### Run specific service

```bash
pytest services/user-service/
```

### Run unit tests only

```bash
pytest --ignore=tests/integration/
```

### Run with coverage

```bash
pytest --cov=services/user-service --cov-report=html
```

### Run with verbose output

```bash
pytest -v
```

---

## Unit Tests

### user-service - Authentication

**File:** `services/user-service/tests/unit/test_auth.py`

Tests password hashing and JWT token management:

```python
def test_password_hashing():
    password = "secret_password"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)

def test_create_tokens():
    user_id = "test-user-id"
    access_token, refresh_token = create_tokens(user_id)
    access_payload = jwt.decode(access_token, ...)
    assert access_payload["sub"] == user_id
    assert access_payload["type"] == "access"

@pytest.mark.asyncio
async def test_verify_token_valid():
    access_token, _ = create_tokens(user_id)
    payload = await verify_token(access_token, expected_type="access")
    assert payload["sub"] == user_id
```

### drift-monitor - Drift Detection

**File:** `services/drift-monitor/tests/unit/test_drift_detector.py`

Tests drift detection algorithms:

```python
def test_page_hinkley_detects_shift():
    score, detected = page_hinkley([0.1, 0.1, 0.1, 1.0, 1.0], threshold=0.1)
    assert score >= 0
    assert detected is True

def test_kl_divergence_non_negative():
    divergence = kl_divergence([0.1, 0.2, 0.3], [0.3, 0.4, 0.5])
    assert divergence >= 0

def test_summarize_drift_sets_flag():
    summary = summarize_drift([0.1, 0.2, 0.2], [0.8, 0.9, 1.0])
    assert summary.drift_detected is True
```

---

## Integration Tests

Integration tests verify API endpoints work correctly:

### api-gateway - test_endpoints.py

```python
def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_rate_limiting():
    for _ in range(101):
        response = client.get("/health")
    # 101st request should be rate limited
    assert response.status_code == 429
```

---

## Test Configuration

### Dependencies (from requirements.txt)

```
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
httpx>=0.24.0  # For async HTTP testing
```

### Environment Variables

Tests use `.env` variables or sensible defaults:

```python
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev_jwt_secret_key")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://...")
```

---

## Test Categories

### 1. Unit Tests

- **Purpose:** Test individual functions/classes in isolation
- **Location:** `tests/unit/`
- **Mock:** External dependencies (DB, Redis, API calls)
- **Fast:** Run in milliseconds

### 2. Integration Tests

- **Purpose:** Test service endpoints and integrations
- **Location:** `tests/integration/`
- **Real:** Use actual services (PostgreSQL, Redis) or test doubles
- **Coverage:** API contracts, error handling

---

## Writing Tests

### Example: Unit Test

```python
# services/my-service/tests/unit/test_calculator.py
import pytest
from src.calculator import calculate_irrigation_duration

def test_calculate_duration_below_threshold():
    # Given
    moisture = 20
    threshold = 30
    max_duration = 600

    # When
    duration = calculate_irrigation_duration(moisture, threshold, max_duration)

    # Then
    assert duration > 0
    assert duration <= max_duration

def test_calculate_duration_above_threshold():
    # Given
    moisture = 40
    threshold = 30

    # When
    duration = calculate_irrigation_duration(moisture, threshold, 600)

    # Then
    assert duration == 0  # No irrigation needed
```

### Example: API Test

```python
# services/api-gateway/tests/integration/test_zones.py
import pytest

def test_create_zone_authenticated(client, auth_token):
    response = client.post(
        "/v1/zones",
        json={"zone_name": "Test Zone", "soil_type": "loam"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 201
    assert response.json()["zone_name"] == "Test Zone"

def test_create_zone_unauthenticated(client):
    response = client.post(
        "/v1/zones",
        json={"zone_name": "Test Zone"}
    )
    assert response.status_code == 401
```

---

## CI/CD Integration

Tests run in Jenkins pipeline:

```groovy
// Jenkinsfile
stage('Test') {
    steps {
        script {
            sh 'pytest --cov=services/ --cov-report=xml'
        }
        archiveArtifacts artifacts: 'coverage.xml', fingerprint: true
    }
    post {
        always {
            junit '**/test-results/*.xml'
        }
    }
}
```

---

## Coverage Targets

| Type | Target |
|------|--------|
| Unit Tests | 80%+ coverage |
| Integration Tests | Key endpoints covered |
| Critical Paths | 100% coverage |

---

## Running in Docker

```bash
# Run tests in container
docker run --rm smart-irrigation-user-service pytest

# With coverage
docker run --rm smart-irrigation-user-service pytest --cov=src --cov-report=html
```

---

## Troubleshooting

### Tests hang

- Check for unclosed database connections
- Use `pytest --forked` to isolate tests

### Import errors

- Ensure `PYTHONPATH` includes `services/<service>/src`

### Redis connection errors

- Use `fakeredis` for unit tests
- Use Docker containers for integration tests

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Framework | pytest |
| Test Types | Unit, Integration |
| Mocking | unittest.mock, fakeredis |
| Coverage | pytest-cov |
| CI | Jenkins pipeline |

Tests ensure code quality and prevent regressions across all Smart Irrigation services.