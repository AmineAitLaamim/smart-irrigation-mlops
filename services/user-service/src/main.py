import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Response
from asyncpg import Connection
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    yield
    await db.disconnect()

app = FastAPI(title="User Authentication Service", lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

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
    return row

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
    return row

@app.get("/users", response_model=List[UserResponse])
async def list_users(admin_user = Depends(get_admin_user), conn: Connection = Depends(get_db_conn)):
    rows = await conn.fetch("SELECT user_id, email, full_name, is_admin, created_at FROM users")
    return rows

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
    
    # Get user to check is_admin status
    user = await conn.fetchrow("SELECT is_admin FROM users WHERE user_id = $1", UUID(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Blacklist the old refresh token (rotation)
    from datetime import datetime, timezone
    now_ts = int(datetime.now(timezone.utc).timestamp())
    expire_seconds = exp - now_ts
    if expire_seconds > 0:
        await blacklist_token(jti, expire_seconds)
    
    access_token, new_refresh_token = create_tokens(user_id, is_admin=user["is_admin"])
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

# --- Zone Management ---

@app.post("/v1/zones", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
async def create_zone(zone_in: ZoneCreate, current_user = Depends(get_current_user), conn: Connection = Depends(get_db_conn)):
    # Check if zone_id exists
    existing = await conn.fetchrow("SELECT 1 FROM zones WHERE zone_id = $1", zone_in.zone_id)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Zone ID already exists")
    
    row = await conn.fetchrow(
        """
        INSERT INTO zones (zone_id, zone_name, soil_type, crop_type, moisture_min, moisture_max, active, owner_id, source)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'api')
        RETURNING zone_id, zone_name, soil_type, crop_type, moisture_min, moisture_max, active, owner_id, source, created_at, updated_at
        """,
        zone_in.zone_id, zone_in.zone_name, zone_in.soil_type, zone_in.crop_type,
        zone_in.moisture_min, zone_in.moisture_max, zone_in.active, current_user["user_id"]
    )
    return row

@app.get("/v1/zones", response_model=List[ZoneResponse])
async def list_zones(conn: Connection = Depends(get_db_conn)):
    rows = await conn.fetch("SELECT * FROM zones")
    return rows

@app.get("/v1/zones/{zone_id}", response_model=ZoneResponse)
async def get_zone(zone_id: str, conn: Connection = Depends(get_db_conn)):
    row = await conn.fetchrow("SELECT * FROM zones WHERE zone_id = $1", zone_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    return row

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
    return row

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
    return row
