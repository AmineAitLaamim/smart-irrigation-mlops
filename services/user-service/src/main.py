import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Response
from asyncpg import Connection
from .database import db, get_db_conn
from .models import UserCreate, UserResponse, TokenResponse, LoginRequest, RefreshRequest
from .auth import (
    hash_password, verify_password, create_tokens, verify_token,
    check_lockout, increment_failed_login, reset_failed_login,
    blacklist_token
)

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
        RETURNING user_id, email, full_name, created_at
        """,
        user_in.email, hashed_pwd, user_in.full_name
    )
    return row

@app.post("/login", response_model=TokenResponse)
async def login(login_in: LoginRequest, conn: Connection = Depends(get_db_conn)):
    await check_lockout(login_in.email)
    
    user = await conn.fetchrow(
        "SELECT user_id, hashed_password FROM users WHERE email = $1",
        login_in.email
    )
    
    if not user or not verify_password(login_in.password, user["hashed_password"]):
        await increment_failed_login(login_in.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    
    await reset_failed_login(login_in.email)
    
    access_token, refresh_token = create_tokens(str(user["user_id"]))
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@app.post("/refresh", response_model=TokenResponse)
async def refresh(refresh_in: RefreshRequest):
    payload = await verify_token(refresh_in.refresh_token, expected_type="refresh")
    user_id = payload.get("sub")
    jti = payload.get("jti")
    exp = payload.get("exp")
    
    # Blacklist the old refresh token (rotation)
    # exp is a timestamp
    now = 1640995200 # Dummy now, real now is needed for expire calculation
    from datetime import datetime, timezone
    now_ts = int(datetime.now(timezone.utc).timestamp())
    expire_seconds = exp - now_ts
    if expire_seconds > 0:
        await blacklist_token(jti, expire_seconds)
    
    access_token, new_refresh_token = create_tokens(user_id)
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }
