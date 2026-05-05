import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Response
from asyncpg import Connection
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from src.database import db, get_db_conn
from src.models import (
    UserCreate, UserResponse, TokenResponse, LoginRequest, RefreshRequest, UserUpdate,
    ZoneCreate, ZoneResponse, ZoneUpdate, ZoneAssignment
)
from src.auth import (
    hash_password, verify_password, create_tokens, verify_token,
    check_lockout, increment_failed_login, reset_failed_login,
    blacklist_token, get_current_user, get_admin_user
)
from typing import List
from uuid import UUID


HTTP_REQUESTS = Counter(
    "user_service_http_requests_total",
    "Total HTTP requests handled by the user service",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "user_service_request_duration_seconds",
    "Request latency observed by the user service",
    ["method", "path"],
)


def _path_label(path: str) -> str:
    if path.startswith("/v1/zones/") and path.endswith("/assign"):
        return "/v1/zones/{zone_id}/assign"
    if path.startswith("/v1/zones/") and path.endswith("/sensors/latest"):
        return "/v1/zones/{zone_id}/sensors/latest"
    if path.startswith("/v1/zones/") and path.endswith("/sensors"):
        return "/v1/zones/{zone_id}/sensors"
    if path.startswith("/v1/zones/") and path.endswith("/predictions"):
        return "/v1/zones/{zone_id}/predictions"
    if path.startswith("/v1/zones/") and path.endswith("/irrigation"):
        return "/v1/zones/{zone_id}/irrigation"
    if path.startswith("/v1/zones/"):
        return "/v1/zones/{zone_id}"
    if path.startswith("/users/"):
        return "/users/{user_id}"
    if path in {"/", ""}:
        return "/"
    return path


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    yield
    await db.disconnect()

app = FastAPI(title="User Authentication Service", lifespan=lifespan)


@app.middleware("http")
async def prometheus_http_metrics(request, call_next):
    start = time.perf_counter()
    path_label = _path_label(request.url.path)
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        REQUEST_LATENCY.labels(request.method, path_label).observe(time.perf_counter() - start)
        HTTP_REQUESTS.labels(request.method, path_label, str(status_code)).inc()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, conn: Connection = Depends(get_db_conn)):
    # Check if user exists
    existing = await conn.fetchrow("SELECT 1 FROM users WHERE email = $1", user_in.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    hashed_pwd = hash_password(user_in.password)
    
    row = await conn.fetchrow(
        """
        INSERT INTO users (email, hashed_password, full_name)
        VALUES ($1, $2, $3)
        RETURNING user_id, email, full_name, is_admin, created_at
        """,
        user_in.email, hashed_pwd, user_in.full_name
    )
    return dict(row)

@app.get("/users/me", response_model=UserResponse)
async def get_me(current_user = Depends(get_current_user)):
    return current_user

@app.put("/users/me", response_model=UserResponse)
async def update_me(user_update: UserUpdate, current_user = Depends(get_current_user), conn: Connection = Depends(get_db_conn)):
    update_data = user_update.model_dump(exclude_unset=True)
    if not update_data:
        return current_user
    
    if "password" in update_data:
        update_data["hashed_password"] = hash_password(update_data.pop("password"))
    
    keys = list(update_data.keys())
    values = list(update_data.values())
    set_clause = ", ".join([f"{key} = ${i+2}" for i, key in enumerate(keys)])
    
    query = f"""
        UPDATE users
        SET {set_clause}
        WHERE user_id = $1
        RETURNING user_id, email, full_name, is_admin, created_at
    """
    
    row = await conn.fetchrow(query, current_user["user_id"], *values)
    return dict(row)

@app.get("/users", response_model=List[UserResponse])
async def list_users(admin_user = Depends(get_admin_user), conn: Connection = Depends(get_db_conn)):
    rows = await conn.fetch("SELECT user_id, email, full_name, is_admin, created_at FROM users")
    return [dict(row) for row in rows]

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: UUID, admin_user = Depends(get_admin_user), conn: Connection = Depends(get_db_conn)):
    # Check if user exists
    existing = await conn.fetchrow("SELECT 1 FROM users WHERE user_id = $1", user_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    await conn.execute("DELETE FROM users WHERE user_id = $1", user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.post("/login", response_model=TokenResponse)
async def login(login_in: LoginRequest, conn: Connection = Depends(get_db_conn)):
    await check_lockout(login_in.email)
    
    user = await conn.fetchrow(
        "SELECT user_id, hashed_password, is_admin FROM users WHERE email = $1",
        login_in.email
    )
    
    if not user or not verify_password(login_in.password, user["hashed_password"]):
        await increment_failed_login(login_in.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    
    await reset_failed_login(login_in.email)
    
    access_token, refresh_token = create_tokens(str(user["user_id"]), is_admin=user["is_admin"])
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@app.post("/refresh", response_model=TokenResponse)
async def refresh(refresh_in: RefreshRequest, conn: Connection = Depends(get_db_conn)):
    payload = await verify_token(refresh_in.refresh_token, expected_type="refresh")
    user_id = payload.get("sub")
    jti = payload.get("jti")
    exp = payload.get("exp")

    if user_id is None or jti is None or exp is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    
    # Get user to check is_admin status
    user = await conn.fetchrow("SELECT is_admin FROM users WHERE user_id = $1", UUID(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Blacklist the old refresh token (rotation)
    from datetime import datetime, timezone
    now_ts = int(datetime.now(timezone.utc).timestamp())
    expire_seconds = int(exp) - now_ts
    if expire_seconds > 0:
        await blacklist_token(str(jti), expire_seconds)
    
    access_token, new_refresh_token = create_tokens(str(user_id), is_admin=user["is_admin"])
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

# --- Zone Management ---

@app.post("/v1/zones", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
async def create_zone(zone_in: ZoneCreate, current_user = Depends(get_current_user), conn: Connection = Depends(get_db_conn)):
    if zone_in.zone_id:
        # Check if zone_id exists
        existing = await conn.fetchrow("SELECT 1 FROM zones WHERE zone_id = $1", zone_in.zone_id)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Zone ID already exists")
    
    if zone_in.zone_id:
        row = await conn.fetchrow(
            """
            INSERT INTO zones (zone_id, zone_name, soil_type, crop_type, moisture_min, moisture_max, active, owner_id, source)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'api')
            RETURNING zone_id, zone_name, soil_type, crop_type, moisture_min, moisture_max, active, owner_id, source, created_at, updated_at
            """,
            zone_in.zone_id, zone_in.zone_name, zone_in.soil_type, zone_in.crop_type,
            zone_in.moisture_min, zone_in.moisture_max, zone_in.active, current_user["user_id"]
        )
    else:
        row = await conn.fetchrow(
            """
            INSERT INTO zones (zone_name, soil_type, crop_type, moisture_min, moisture_max, active, owner_id, source)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'api')
            RETURNING zone_id, zone_name, soil_type, crop_type, moisture_min, moisture_max, active, owner_id, source, created_at, updated_at
            """,
            zone_in.zone_name, zone_in.soil_type, zone_in.crop_type,
            zone_in.moisture_min, zone_in.moisture_max, zone_in.active, current_user["user_id"]
        )
    return dict(row)

@app.get("/v1/zones", response_model=List[ZoneResponse])
async def list_zones(conn: Connection = Depends(get_db_conn)):
    rows = await conn.fetch("SELECT * FROM zones")
    return [dict(row) for row in rows]

@app.get("/v1/zones/{zone_id}", response_model=ZoneResponse)
async def get_zone(zone_id: str, conn: Connection = Depends(get_db_conn)):
    row = await conn.fetchrow("SELECT * FROM zones WHERE zone_id = $1", zone_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    return dict(row)

@app.put("/v1/zones/{zone_id}", response_model=ZoneResponse)
async def update_zone(zone_id: str, zone_update: ZoneUpdate, conn: Connection = Depends(get_db_conn)):
    # Note: Ownership is validated at the API Gateway level
    update_data = zone_update.model_dump(exclude_unset=True)
    if not update_data:
        return await get_zone(zone_id, conn)
    
    keys = list(update_data.keys())
    values = list(update_data.values())
    set_clause = ", ".join([f"{key} = ${i+2}" for i, key in enumerate(keys)])
    
    query = f"""
        UPDATE zones
        SET {set_clause}
        WHERE zone_id = $1
        RETURNING *
    """
    
    row = await conn.fetchrow(query, zone_id, *values)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    return dict(row)

@app.delete("/v1/zones/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(zone_id: str, conn: Connection = Depends(get_db_conn)):
    # Note: Ownership is validated at the API Gateway level
    result = await conn.execute("DELETE FROM zones WHERE zone_id = $1", zone_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.post("/v1/zones/{zone_id}/assign", response_model=ZoneResponse)
async def assign_zone(zone_id: str, assignment: ZoneAssignment, admin_user = Depends(get_admin_user), conn: Connection = Depends(get_db_conn)):
    # Check if target user exists
    user_exists = await conn.fetchrow("SELECT 1 FROM users WHERE user_id = $1", assignment.owner_id)
    if not user_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")
        
    row = await conn.fetchrow(
        "UPDATE zones SET owner_id = $1 WHERE zone_id = $2 RETURNING *",
        assignment.owner_id, zone_id
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    return dict(row)

# ─── Sensor Readings ─────────────────────────────────────────────────────────

@app.get("/v1/zones/{zone_id}/sensors")
async def get_zone_sensor_readings(
    zone_id: str,
    hours: int = 24,
    conn: Connection = Depends(get_db_conn)
):
    """Return sensor readings for the last N hours for a zone."""
    rows = await conn.fetch(
        """
        SELECT timestamp, zone_id, sensor_id, moisture, temperature
        FROM sensor_readings
        WHERE zone_id = $1
          AND timestamp >= NOW() - ($2 || ' hours')::interval
        ORDER BY timestamp ASC
        LIMIT 500
        """,
        zone_id, str(hours)
    )
    return [
        {
            "timestamp": row["timestamp"].isoformat(),
            "sensor_id": row["sensor_id"],
            "moisture": float(row["moisture"]) if row["moisture"] is not None else None,
            "temperature": float(row["temperature"]) if row["temperature"] is not None else None,
        }
        for row in rows
    ]


@app.get("/v1/zones/{zone_id}/sensors/latest")
async def get_zone_latest_sensor(
    zone_id: str,
    conn: Connection = Depends(get_db_conn)
):
    """Return the most recent reading per sensor for a zone."""
    rows = await conn.fetch(
        """
        SELECT DISTINCT ON (sensor_id)
            timestamp, zone_id, sensor_id, moisture, temperature
        FROM sensor_readings
        WHERE zone_id = $1
        ORDER BY sensor_id, timestamp DESC
        """,
        zone_id
    )
    return [
        {
            "timestamp": row["timestamp"].isoformat(),
            "sensor_id": row["sensor_id"],
            "moisture": float(row["moisture"]) if row["moisture"] is not None else None,
            "temperature": float(row["temperature"]) if row["temperature"] is not None else None,
        }
        for row in rows
    ]


# ─── Model Predictions ───────────────────────────────────────────────────────

@app.get("/v1/zones/{zone_id}/predictions")
async def get_zone_predictions(
    zone_id: str,
    hours: int = 24,
    conn: Connection = Depends(get_db_conn)
):
    """Return model predictions for the last N hours for a zone."""
    rows = await conn.fetch(
        """
        SELECT predicted_at, zone_id, prediction, confidence
        FROM model_predictions
        WHERE zone_id = $1
          AND predicted_at >= NOW() - ($2 || ' hours')::interval
        ORDER BY predicted_at ASC
        LIMIT 500
        """,
        zone_id, str(hours)
    )
    return [
        {
            "predicted_at": row["predicted_at"].isoformat(),
            "prediction": float(row["prediction"]) if row["prediction"] is not None else None,
            "confidence": float(row["confidence"]) if row["confidence"] is not None else None,
        }
        for row in rows
    ]


# ─── Irrigation Events ───────────────────────────────────────────────────────

@app.get("/v1/zones/{zone_id}/irrigation")
async def get_zone_irrigation_events(
    zone_id: str,
    limit: int = 20,
    conn: Connection = Depends(get_db_conn)
):
    """Return the most recent irrigation events for a zone."""
    rows = await conn.fetch(
        """
        SELECT triggered_at, zone_id, trigger_reason, recommended_volume, status
        FROM irrigation_events
        WHERE zone_id = $1
        ORDER BY triggered_at DESC
        LIMIT $2
        """,
        zone_id, limit
    )
    return [
        {
            "triggered_at": row["triggered_at"].isoformat(),
            "zone_id": row["zone_id"],
            "trigger_reason": row["trigger_reason"],
            "recommended_volume": float(row["recommended_volume"]) if row["recommended_volume"] is not None else None,
            "status": row["status"],
        }
        for row in rows
    ]


@app.get("/v1/irrigation/recent")
async def get_recent_irrigation_events(
    limit: int = 20,
    conn: Connection = Depends(get_db_conn)
):
    """Return the most recent irrigation events across all zones."""
    rows = await conn.fetch(
        """
        SELECT triggered_at, zone_id, trigger_reason, recommended_volume, status
        FROM irrigation_events
        ORDER BY triggered_at DESC
        LIMIT $1
        """,
        limit
    )
    return [
        {
            "triggered_at": row["triggered_at"].isoformat(),
            "zone_id": row["zone_id"],
            "trigger_reason": row["trigger_reason"],
            "recommended_volume": float(row["recommended_volume"]) if row["recommended_volume"] is not None else None,
            "status": row["status"],
        }
        for row in rows
    ]

