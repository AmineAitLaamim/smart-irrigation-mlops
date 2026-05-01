import os
import jwt
import redis.asyncio as redis
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from asyncpg import Connection
from src.database import get_db_conn

# Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev_jwt_secret_key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_EXPIRE_MIN = int(os.getenv("JWT_ACCESS_EXPIRE_MIN", "15"))
JWT_REFRESH_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", "7"))
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
REDIS_TOKEN_BLACKLIST_URL = os.getenv("REDIS_TOKEN_BLACKLIST_URL", "redis://redis:6379/1")

AUTH_MAX_ATTEMPTS = int(os.getenv("AUTH_MAX_ATTEMPTS", "5"))
AUTH_LOCKOUT_MINUTES = int(os.getenv("AUTH_LOCKOUT_MINUTES", "15"))

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=BCRYPT_ROUNDS)

# Redis Clients
redis_client = redis.from_url(REDIS_URL, decode_responses=True)
blacklist_client = redis.from_url(REDIS_TOKEN_BLACKLIST_URL, decode_responses=True)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_tokens(user_id: str, is_admin: bool = False) -> Tuple[str, str]:
    now = datetime.now(timezone.utc)
    
    access_expire = now + timedelta(minutes=JWT_ACCESS_EXPIRE_MIN)
    access_payload = {
        "sub": user_id,
        "exp": access_expire,
        "type": "access",
        "is_admin": is_admin
    }
    access_token = jwt.encode(access_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    refresh_expire = now + timedelta(days=JWT_REFRESH_EXPIRE_DAYS)
    refresh_payload = {
        "sub": user_id,
        "exp": refresh_expire,
        "type": "refresh",
        "jti": os.urandom(16).hex()  # Unique ID for rotation
    }
    refresh_token = jwt.encode(refresh_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    return access_token, refresh_token

async def check_lockout(email: str):
    attempts = await redis_client.get(f"auth_attempts:{email}")
    if attempts and int(attempts) >= AUTH_MAX_ATTEMPTS:
        ttl = await redis_client.ttl(f"auth_attempts:{email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account locked. Try again in {ttl // 60} minutes."
        )

async def increment_failed_login(email: str):
    key = f"auth_attempts:{email}"
    attempts = await redis_client.incr(key)
    if attempts == 1:
        await redis_client.expire(key, AUTH_LOCKOUT_MINUTES * 60)
    
    if attempts >= AUTH_MAX_ATTEMPTS:
        await redis_client.expire(key, AUTH_LOCKOUT_MINUTES * 60)

async def reset_failed_login(email: str):
    await redis_client.delete(f"auth_attempts:{email}")

async def blacklist_token(jti: str, expire_seconds: int):
    await blacklist_client.setex(f"blacklist:{jti}", expire_seconds, "1")

async def is_token_blacklisted(jti: str) -> bool:
    return await blacklist_client.exists(f"blacklist:{jti}")

async def verify_token(token: str, expected_type: str = "access") -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != expected_type:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        
        if expected_type == "refresh":
            jti = payload.get("jti")
            if await is_token_blacklisted(jti):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")
                
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

async def get_current_user(token: str = Depends(oauth2_scheme), conn: Connection = Depends(get_db_conn)):
    payload = await verify_token(token)
    user_id = payload.get("sub")
    try:
        from uuid import UUID
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID in token")
        
    user = await conn.fetchrow("SELECT user_id, email, full_name, is_admin, created_at FROM users WHERE user_id = $1", user_uuid)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

async def get_admin_user(current_user = Depends(get_current_user)):
    if not current_user["is_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user
