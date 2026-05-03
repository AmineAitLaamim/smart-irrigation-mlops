# User Service Documentation

## Overview

The User Service provides:
- **User Authentication** - Registration, login, JWT tokens
- **Zone Management** - CRUD operations for irrigation zones
- **Data APIs** - Sensor readings, predictions, irrigation events
- **Access Control** - Role-based permissions (admin vs user)

**Location:** `services/user-service/src/`

**Port:** 5005

---

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              USER SERVICE                                       │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        FastAPI Application                             │   │
│  │                                                                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │   │
│  │  │   Auth      │  │   Users     │  │   Zones     │  │  Data     │  │   │
│  │  │  Endpoints  │  │  Endpoints  │  │  Endpoints  │  │  APIs     │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │   │
│  │                                                                          │   │
│  │  ┌──────────────────────────────────────────────────────────────────┐   │   │
│  │  │                    Authentication Layer                         │   │   │
│  │  │  - Password hashing (bcrypt)                                    │   │   │
│  │  │  - JWT token creation/validation                              │   │   │
│  │  │  - Token blacklist (Redis)                                    │   │   │
│  │  │  - Account lockout                                            │   │   │
│  │  └──────────────────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                    Prometheus Metrics                                    │   │
│  │                                                                          │   │
│  │  user_service_http_requests_total                                      │   │
│  │  user_service_request_duration_seconds                                 │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    PostgreSQL   │    │     Redis      │    │    API Gateway │
│                 │    │                 │    │                │
│  - users       │    │  - Token       │    │  - Proxied     │
│  - zones       │    │    blacklist   │    │    requests    │
│  - sensor_*    │    │  - Auth        │    │                │
│  - model_*     │    │    lockouts    │    │                │
│  - irrigation_ │    │                 │    │                │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## Authentication

### Registration

```bash
POST /register
{
  "email": "user@example.com",
  "password": "secretpassword",
  "full_name": "John Doe"
}
```

**Response:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_admin": false,
  "created_at": "2026-05-03T12:00:00"
}
```

### Login

```bash
POST /login
{
  "email": "user@example.com",
  "password": "secretpassword"
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

### Token Refresh

```bash
POST /refresh
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

### Security Features

#### Password Hashing
- Algorithm: bcrypt
- Rounds: 12 (configurable)

#### JWT Tokens

| Token Type | Expiry | Purpose |
|------------|--------|---------|
| Access | 15 minutes | API authentication |
| Refresh | 7 days | Get new access token |

#### Account Lockout
- Max failed attempts: 5 (configurable)
- Lockout duration: 15 minutes (configurable)
- Stored in Redis with TTL

#### Token Blacklist
- Used for token rotation
- Stored in separate Redis DB
- Automatically expires when token expires

---

## User Management

### Get Current User

```bash
GET /users/me
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_admin": false,
  "created_at": "2026-05-03T12:00:00"
}
```

### Update Current User

```bash
PUT /users/me
{
  "full_name": "Jane Doe",
  "password": "newpassword"
}
```

### List Users (Admin only)

```bash
GET /users
Authorization: Bearer {admin_access_token}
```

### Delete User (Admin only)

```bash
DELETE /users/{user_id}
```

---

## Zone Management

### Create Zone

```bash
POST /v1/zones
Authorization: Bearer {access_token}
{
  "zone_name": "Garden",
  "soil_type": "loam",
  "crop_type": "tomatoes",
  "moisture_min": 30,
  "moisture_max": 60
}
```

**Or with custom zone_id:**
```json
{
  "zone_id": "garden-1",
  "zone_name": "Garden",
  ...
}
```

### List Zones

```bash
GET /v1/zones
```

### Get Zone

```bash
GET /v1/zones/{zone_id}
```

### Update Zone

```bash
PUT /v1/zones/{zone_id}
{
  "zone_name": "Updated Name",
  "moisture_min": 25
}
```

### Delete Zone

```bash
DELETE /v1/zones/{zone_id}
```

### Assign Zone to User (Admin only)

```bash
POST /v1/zones/{zone_id}/assign
{
  "owner_id": "user-uuid"
}
```

---

## Data APIs

### Sensor Readings

```bash
# Last 24 hours
GET /v1/zones/{zone_id}/sensors

# Last N hours
GET /v1/zones/{zone_id}/sensors?hours=48
```

**Response:**
```json
[
  {
    "timestamp": "2026-05-03T12:00:00",
    "sensor_id": "2-s1",
    "moisture": 45.2,
    "temperature": 22.5
  },
  ...
]
```

### Latest Sensor Readings

```bash
GET /v1/zones/{zone_id}/sensors/latest
```

### Predictions

```bash
GET /v1/zones/{zone_id}/predictions
```

### Irrigation Events

```bash
# Zone events
GET /v1/zones/{zone_id}/irrigation

# Recent events (all zones)
GET /v1/irrigation/recent
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | `dev_jwt_secret_key` | JWT signing key |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_ACCESS_EXPIRE_MIN` | `15` | Access token expiry (minutes) |
| `JWT_REFRESH_EXPIRE_DAYS` | `7` | Refresh token expiry (days) |
| `BCRYPT_ROUNDS` | `12` | Password hashing rounds |
| `AUTH_MAX_ATTEMPTS` | `5` | Max failed login attempts |
| `AUTH_LOCKOUT_MINUTES` | `15` | Lockout duration |
| `REDIS_URL` | `redis://redis:6379/0` | Main Redis DB |
| `REDIS_TOKEN_BLACKLIST_URL` | `redis://redis:6379/1` | Token blacklist DB |

### Docker Configuration

```yaml
user-service:
  image: user-service:latest
  ports:
    - "5005:5005"
  environment:
    - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    - REDIS_URL=redis://redis:6379/0
    - REDIS_TOKEN_BLACKLIST_URL=redis://redis:6379/1
  depends_on:
    - timescaledb
    - redis
```

---

## Database Schema

### users Table

```sql
CREATE TABLE users (
    user_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email        VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name    VARCHAR(255),
    is_admin     BOOLEAN DEFAULT FALSE,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
```

### zones Table

```sql
CREATE TABLE zones (
    zone_id       VARCHAR(50) PRIMARY KEY,
    zone_name    VARCHAR(200) NOT NULL,
    soil_type    VARCHAR(50) NOT NULL,
    crop_type    VARCHAR(50),
    owner_id     UUID REFERENCES users(user_id),
    source       VARCHAR(20) NOT NULL,  -- 'api' or 'yaml'
    moisture_min FLOAT NOT NULL,
    moisture_max FLOAT NOT NULL,
    active       BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Access Control

### Role-Based Permissions

| Action | User | Admin |
|--------|------|-------|
| Register | ✅ | - |
| Login | ✅ | - |
| View own profile | ✅ | ✅ |
| Update own profile | ✅ | ✅ |
| List all users | - | ✅ |
| Delete user | - | ✅ |
| Create zone | ✅ | ✅ |
| Update own zones | ✅ | ✅ |
| Update any zone | - | ✅ |
| Delete zone | ✅ (own) | ✅ |
| Assign zone | - | ✅ |
| View zone data | ✅ (own) | ✅ |

### Ownership Validation

- Users can only modify zones they own
- System zones (source='yaml', no owner) are read-only
- Admin can modify any zone

---

## Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `user_service_http_requests_total` | Counter | Total requests by method, path, status |
| `user_service_request_duration_seconds` | Histogram | Request latency |

---

## API Endpoints Summary

### Authentication
| Method | Endpoint | Auth | Description |
|--------|-----------|------|-------------|
| POST | /register | No | Register new user |
| POST | /login | No | Login, get tokens |
| POST | /refresh | No | Refresh tokens |

### Users
| Method | Endpoint | Auth | Description |
|--------|-----------|------|-------------|
| GET | /users/me | Yes | Get current user |
| PUT | /users/me | Yes | Update current user |
| GET | /users | Admin | List all users |
| DELETE | /users/{id} | Admin | Delete user |

### Zones
| Method | Endpoint | Auth | Description |
|--------|-----------|------|-------------|
| POST | /v1/zones | Yes | Create zone |
| GET | /v1/zones | No | List zones |
| GET | /v1/zones/{id} | No | Get zone |
| PUT | /v1/zones/{id} | Owner | Update zone |
| DELETE | /v1/zones/{id} | Owner | Delete zone |
| POST | /v1/zones/{id}/assign | Admin | Assign zone to user |

### Data
| Method | Endpoint | Description |
|--------|-----------|-------------|
| GET | /v1/zones/{id}/sensors | Sensor readings |
| GET | /v1/zones/{id}/sensors/latest | Latest readings |
| GET | /v1/zones/{id}/predictions | Model predictions |
| GET | /v1/zones/{id}/irrigation | Irrigation events |
| GET | /v1/irrigation/recent | Recent events |

---

## Example Usage

### Register and Login

```bash
# Register
curl -X POST http://localhost:5005/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secret", "full_name": "John"}'

# Login
curl -X POST http://localhost:5005/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secret"}'

# Get access token from response, use in subsequent requests
export TOKEN="eyJ..."

# Get own profile
curl http://localhost:5005/users/me -H "Authorization: Bearer $TOKEN"
```

### Zone Management

```bash
# Create zone
curl -X POST http://localhost:5005/v1/zones \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"zone_name": "Garden", "soil_type": "loam", "crop_type": "tomatoes", "moisture_min": 30, "moisture_max": 60}'

# Get zone data
curl http://localhost:5005/v1/zones/garden-1/sensors?hours=24

# Get predictions
curl http://localhost:5005/v1/zones/garden-1/predictions

# Get irrigation events
curl http://localhost:5005/v1/zones/garden-1/irrigation
```

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| Framework | FastAPI |
| Auth | JWT + bcrypt |
| Token Storage | Redis (blacklist + lockout) |
| Database | PostgreSQL (users, zones) |
| Rate Limiting | Redis-based lockout |
| Port | 5005 |

The User Service provides complete user authentication, zone management, and data access APIs for the Smart Irrigation System.