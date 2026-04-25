import pytest
from src.auth import hash_password, verify_password, create_tokens, verify_token
import jwt
import os

def test_password_hashing():
    password = "secret_password"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)

def test_create_tokens():
    user_id = "test-user-id"
    access_token, refresh_token = create_tokens(user_id)
    
    # Verify access token
    access_payload = jwt.decode(access_token, os.getenv("JWT_SECRET_KEY", "dev_jwt_secret_key"), algorithms=["HS256"])
    assert access_payload["sub"] == user_id
    assert access_payload["type"] == "access"
    
    # Verify refresh token
    refresh_payload = jwt.decode(refresh_token, os.getenv("JWT_SECRET_KEY", "dev_jwt_secret_key"), algorithms=["HS256"])
    assert refresh_payload["sub"] == user_id
    assert refresh_payload["type"] == "refresh"
    assert "jti" in refresh_payload

@pytest.mark.asyncio
async def test_verify_token_valid():
    user_id = "test-user-id"
    access_token, _ = create_tokens(user_id)
    payload = await verify_token(access_token, expected_type="access")
    assert payload["sub"] == user_id

@pytest.mark.asyncio
async def test_verify_token_invalid_type():
    from fastapi import HTTPException
    user_id = "test-user-id"
    access_token, _ = create_tokens(user_id)
    with pytest.raises(HTTPException) as excinfo:
        await verify_token(access_token, expected_type="refresh")
    assert excinfo.value.status_code == 401
