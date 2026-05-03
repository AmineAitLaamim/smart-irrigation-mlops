# API Gateway Documentation

## Overview

The API Gateway is the central entry point for all client requests to the Smart Irrigation System. It provides:
- **Authentication** - JWT-based auth with access/refresh tokens
- **Authorization** - Zone-level ownership validation
- **Rate Limiting** - Redis-based per-IP rate limiting
- **Routing** - Proxy requests to backend services
- **Monitoring** - Prometheus metrics for all requests
- **CORS** - Cross-origin request handling

**Location:** `services/api-gateway/src/`

**Port:** 8080

---

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY                                         │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        FastAPI Application                              │   │
│  │                                                                          │   │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │   │
│  │  │                     Middleware Stack                             │  │   │
│  │  │                                                                   │  │   │
│  │  │  1. CORS Middleware (allow_origins)                               │  │   │
│  │  │  2. Rate Limit Middleware (per IP, 100/min)                      │  │   │
│  │  │  3. Prometheus Metrics Middleware                                │  │   │
│  │  │  4. Authentication Middleware                                     │  │   │
│  │  │  5. Zone Ownership Validation                                     │  │   │
│  │  │  6. Proxy to Upstream Services                                    │  │   │
│  │  │                                                                   │  │   │
│  │  └──────────────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Clients      │    │    Redis        │    │  PostgreSQL     │
│                 │    │                 │    │  (zones data)   │
│ - Web Browser   │    │  Rate limiting  │    │                 │
│ - Mobile App    │    │  - rate_limit:  │    │  Ownership      │
│ - External APIs │    │    {client_ip}  │    │  validation     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         UPSTREAM SERVICES                                      │
│                                                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │User Service │ │Model Server │ │Drift Monitor│ │Irrigation   │            │
│  │   (5005)    │ │   (8501)    │ │   (8502)    │ │ Controller  │            │
│  │             │ │             │ │             │ │   (8503)    │            │
│  │ - /auth/*   │ │ - /v1/predict│ │ - /v1/drift │ │ - /v1/      │            │
│  │ - /users/*  │ │ - /v1/model  │ │             │ │   irrigation│            │
│  │ - /v1/zones │ │             │ │             │ │             │            │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘            │
│                                                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                             │
│  │Notification │ │Data Quality │ │Web Dashboard│                             │
│  │ Service     │ │  Service    │ │   (3000)   │                             │
│  │   (8505)    │ │   (8005)    │ │             │                             │
│  │             │ │             │ │             │                             │
│  │/v1/notif.*  │ │  /quality/* │ │ /dashboard/*│                             │
│  └─────────────┘ └─────────────┘ └─────────────┘                             │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Routing

### Route Mapping

The gateway maps incoming paths to upstream services:

```python
ROUTES = {
    "/auth":           USER_SERVICE_URL,         # Strip /auth prefix
    "/users":         USER_SERVICE_URL,
    "/v1/predict":    MODEL_SERVER_URL,
    "/v1/model":      MODEL_SERVER_URL,
    "/v1/zones":      USER_SERVICE_URL,
    "/v1/drift":      DRIFT_MONITOR_URL,
    "/v1/irrigation": IRRIGATION_CONTROLLER_URL,
    "/v1/notifications": NOTIFICATION_SERVICE_URL,
    "/quality":       DATA_QUALITY_URL,
    "/dashboard":     WEB_DASHBOARD_URL,
}
```

### Example Translations

| Client Request | Upstream Service | Upstream Path |
|----------------|------------------|---------------|
| `GET /auth/login` | User Service | `/login` (stripped `/auth`) |
| `GET /users/me` | User Service | `/users/me` |
| `POST /v1/predict` | Model Server | `/v1/predict` |
| `GET /v1/zones` | User Service | `/v1/zones` |
| `GET /v1/drift/status` | Drift Monitor | `/v1/drift/status` |
| `GET /v1/irrigation/events` | Irrigation Controller | `/v1/irrigation/events` |

---

## Authentication

### JWT Tokens

The gateway handles JWT-based authentication:

**Access Token:**
- Expiry: 15 minutes
- Purpose: API authentication
- Payload: `{"sub": "user_id", "type": "access", "iat": ..., "exp": ...}`

**Refresh Token:**
- Expiry: 7 days
- Purpose: Get new access token
- Payload: `{"sub": "user_id", "type": "refresh", "iat": ..., "exp": ...}`

### Token Flow

```
1. Client sends credentials to /auth/login
                   │
                   ▼
2. User Service validates and returns tokens
                   │
                   ▼
3. Client includes in Authorization header:
   Authorization: Bearer {access_token}
                   │
                   ▼
4. Gateway validates token (auth.py)
                   │
                   ├── Valid ──► Proxy to service
                   │
                   └── Invalid ──► 401 Unauthorized
```

### Token Refresh

```bash
POST /auth/refresh
{
  "refresh_token": "eyJ..."
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

---

## Authorization

### Protected Routes

These routes require authentication:

```python
# Routes requiring auth
if path.startswith(("auth/", "users/", "v1/zones/", "v1/irrigation/", "v1/notifications/", "quality/")):
    require_auth = True

# Exception: public auth endpoints
if path in ("auth/login", "auth/register", "auth/auth_refresh"):
    require_auth = False
```

### Zone Ownership Validation

When users modify zones, the gateway validates ownership:

```python
async def validate_zone_ownership(request: Request, zone_id: str):
    user_payload = await get_current_user_payload(request)
    user_id = user_payload.get("sub")
    is_admin = user_payload.get("is_admin", False)

    # Admin can do anything
    if is_admin:
        return

    # Check zone ownership
    row = await conn.fetchrow(
        "SELECT owner_id, source FROM zones WHERE zone_id = $1",
        zone_id,
    )

    is_owner = row["owner_id"] and str(row["owner_id"]) == user_id

    # System zones (yaml, no owner) are read-only
    if row["source"] == "yaml" and not row["owner_id"]:
        raise 403 Forbidden

    # Only owner can modify
    if not is_owner:
        raise 403 Forbidden
```

**Ownership Rules:**
| Zone Source | Has Owner | Can User Modify? |
|-------------|-----------|-------------------|
| `yaml` | No (system) | ❌ No (read-only) |
| `yaml` | Yes | ✅ Yes (if owner) |
| `api` | Yes | ✅ Yes (if owner) |
| `api` | No | ❌ No (orphan) |

---

## Rate Limiting

### Configuration

Rate limiting is Redis-based with sliding window:

```python
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "100"))
```

Default: 100 requests per minute per IP

### How It Works

```python
async def check_rate_limit(client_ip: str) -> bool:
    key = f"rate_limit:{client_ip}"
    current_time = int(time.time())
    window_start = current_time - 60  # 1 minute window

    # Remove old entries
    redis.zremrangebyscore(key, "-inf", str(window_start))

    # Count current entries
    request_count = redis.zcard(key)

    # Add new entry
    redis.zadd(key, {str(current_time): current_time})
    redis.expire(key, 60)

    return request_count < 100
```

### Response Headers

When rate limited, returns:
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
```

---

## Middleware Stack

### 1. CORS Middleware

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # From env var
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. Rate Limit Middleware

Applies to all requests except testing environment.

### 3. Prometheus Metrics Middleware

Tracks request count and latency.

### 4. Authentication Middleware

Validates JWT for protected routes.

### 5. Proxy Middleware

Forwards requests to upstream services.

---

## API Endpoints

### Health Check

```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "api-gateway"
}
```

### Metrics

```bash
GET /metrics
```

**Prometheus metrics:**
- `api_gateway_http_requests_total` - Total requests by method, path, status
- `api_gateway_request_duration_seconds` - Request latency histogram

### Root

```bash
GET /
```

**Response:**
```json
{
  "message": "Smart Irrigation API Gateway",
  "version": "1.0.0"
}
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_GATEWAY_PORT` | `8080` | Gateway port |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` | Allowed CORS origins |
| `USER_SERVICE_URL` | `http://user-service:5005` | User service URL |
| `MODEL_SERVER_URL` | `http://model-server:8501` | Model server URL |
| `DRIFT_MONITOR_URL` | `http://drift-monitor:8502` | Drift monitor URL |
| `IRRIGATION_CONTROLLER_URL` | `http://irrigation-controller:8503` | Irrigation controller URL |
| `NOTIFICATION_SERVICE_URL` | `http://notification-service:8505` | Notification service URL |
| `DATA_QUALITY_URL` | `http://data-quality:8005` | Data quality service URL |
| `WEB_DASHBOARD_URL` | `http://web-dashboard:3000` | Web dashboard URL |
| `RATE_LIMIT_PER_MIN` | `100` | Requests per minute per IP |
| `JWT_SECRET_KEY` | `dev_jwt_secret_key...` | JWT signing key |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `REDIS_URL` | `redis://redis:6379/0` | Redis for rate limiting |

### Docker Configuration

```yaml
api-gateway:
  image: api-gateway:latest
  ports:
    - "8080:8080"
  environment:
    - CORS_ALLOWED_ORIGINS=http://localhost:3000
    - RATE_LIMIT_PER_MIN=100
    - JWT_SECRET_KEY=${JWT_SECRET_KEY}
  depends_on:
    - redis
    - user-service
```

---

## Security Features

### 1. Token Validation

- JWT signature verification
- Token type checking (access vs refresh)
- Expiration validation

### 2. Zone-Level Authorization

- Users can only modify their own zones
- System zones (yaml, no owner) are read-only
- Admins can modify any zone

### 3. Rate Limiting

- Prevents abuse and DoS attacks
- Per-IP sliding window
- Configurable limits

### 4. CORS Protection

- Only allowed origins can access
- Configurable via environment

### 5. Request Sanitization

- Headers forwarded with original client IP
- X-Forwarded-For header added

---

## Monitoring

### Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `api_gateway_http_requests_total` | Counter | method, path, status | Total requests |
| `api_gateway_request_duration_seconds` | Histogram | method, path | Request latency |

### Health Check

```bash
curl http://localhost:8080/health
```

### Grafana Integration

Import the API Gateway dashboard to visualize:
- Requests per second
- Error rate
- Latency percentiles
- Top endpoints

---

## Example Usage

### Authentication Flow

```bash
# 1. Register
curl -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secret", "full_name": "John"}'

# 2. Login
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secret"}'

# Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}

# 3. Use access token
curl http://localhost:8080/v1/zones \
  -H "Authorization: Bearer eyJ..."

# 4. Refresh token (when access expires)
curl -X POST http://localhost:8080/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJ..."}'
```

### Making Predictions

```bash
curl -X POST http://localhost:8080/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "zone_id": "2",
    "sensor_id": "2-s1",
    "features": [45.2, 22.5]
  }'
```

### Managing Zones

```bash
# Get zones (requires auth)
curl http://localhost:8080/v1/zones \
  -H "Authorization: Bearer {access_token}"

# Create zone (requires auth)
curl -X POST http://localhost:8080/v1/zones \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{"zone_name": "Garden", "soil_type": "loam", "crop_type": "tomatoes", "moisture_min": 30, "moisture_max": 60}'
```

---

## Error Handling

| Error | Status Code | Description |
|-------|-------------|-------------|
| Invalid token | 401 | JWT expired or invalid |
| Missing auth | 401 | No Authorization header |
| Rate limited | 429 | Too many requests |
| Zone access denied | 403 | Not zone owner |
| System zone modify | 403 | System zone is read-only |
| Route not found | 404 | Unknown path |
| Service unavailable | 502 | Upstream service error |

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Framework | FastAPI + Uvicorn |
| Authentication | JWT (access + refresh tokens) |
| Authorization | Zone-level ownership |
| Rate Limiting | Redis sliding window (100/min) |
| Routing | Path-based proxy to 9 services |
| CORS | Configurable allowed origins |
| Monitoring | Prometheus metrics |
| Port | 8080 |

The API Gateway provides a unified entry point with authentication, authorization, and rate limiting for all Smart Irrigation services.