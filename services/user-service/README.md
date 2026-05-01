# User Service

## Overview
The User Service handles authentication, authorization, and user profile management. It is the central authority for identity in the Smart Irrigation System.

## Features Implemented
### 1. Full User CRUD
- **GET /users/me**: Retrieve the profile of the authenticated user.
- **PUT /users/me**: Update profile details (email, full name, password). Supports partial updates.
- **GET /users**: (Admin only) List all registered users in the system.
- **DELETE /users/{id}**: (Admin only) Permanently remove a user account.
- **POST /register**: Register new users. Now includes `is_admin` status in the response.

### 2. Role-Based Access Control (RBAC)
- Introduced the `is_admin` boolean field on the user model.
- Admins have elevated privileges, allowing them to view/delete any user and override zone ownership checks.

### 3. Enhanced Authentication
- **JWT Claims**: Tokens now include the `is_admin` claim to allow the API Gateway to make authorization decisions without upstream database calls.
- **Token Rotation**: Implemented refresh token rotation with blacklisting (via Redis) to ensure session security.
- **Password Hashing**: Uses `bcrypt` with configurable rounds for secure credential storage.

## Technical Stack
- **Framework**: FastAPI (Python)
- **Database**: TimescaleDB (via `asyncpg` for high-performance async access)
- **Cache/Security**: Redis (Token blacklisting and failed login lockout)
- **Validation**: Pydantic v2

## Testing
Comprehensive unit tests are located in `tests/unit/test_routes.py`, covering:
- Profile retrieval and updates.
- Admin-only endpoint enforcement.
- Input validation (Pydantic).
- Mocking of database and Redis dependencies.
