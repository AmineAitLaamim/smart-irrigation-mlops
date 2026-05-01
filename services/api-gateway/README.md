# API Gateway

## Overview
The API Gateway is the entry point for all external requests. It provides routing, rate limiting, and core security enforcement for the Smart Irrigation System.

## Features Implemented
### 1. Zone Ownership Enforcement
The gateway now enforces physical resource ownership at the middleware level:
- **Isolation**: For `PUT` and `DELETE` requests on `/v1/zones/{zone_id}`, the gateway validates that the authenticated user is the assigned `owner_id` of the zone.
- **Read-Only Zones**: Zones created via the system configuration (`source='yaml'`) are protected and cannot be modified or deleted through the API.
- **Admin Override**: Users with the `is_admin` claim in their JWT automatically bypass ownership checks, allowing maintenance across all zones.

### 2. JWT Claim Inspection
- Implemented `get_current_user_payload` to decode and inspect JWT claims (like `user_id` and `is_admin`) directly at the gateway.
- This architectural decision eliminates redundant upstream calls to the User Service for authorization checks, reducing latency.

### 3. Dynamic Routing
Routes are proxied to internal microservices based on path prefixes:
- `/auth`, `/users`, `/v1/zones` → **User Service**
- `/v1/sensors`, `/v1/predictions` → **Model Server**
- `/v1/drift` → **Drift Monitor**
- `/v1/irrigation` → **Irrigation Controller**

## Technical Stack
- **Framework**: FastAPI
- **HTTP Client**: `httpx` (async proxying)
- **Database**: TimescaleDB (for ownership lookups)
- **Security**: `python-jose` (JWT)
