# =============================================================================
# Unit Tests — auth.py
# Tests JWT token creation, validation, and all auth error paths.
# No external dependencies (no Redis, no DB, no running server).
# =============================================================================

import time
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from auth import (
    create_access_token,
    create_refresh_token,
    refresh_access_token,
    get_current_user,
    optional_auth,
    TokenPayload,
    CurrentUser,
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
)
from jose import jwt


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_request(auth_header: str | None = None) -> MagicMock:
    """Build a minimal fake FastAPI Request with an Authorization header."""
    request = MagicMock()
    headers_dict = {}
    if auth_header is not None:
        headers_dict["Authorization"] = auth_header
    
    # Mock the headers object itself to have a .get() method
    request.headers = MagicMock()
    request.headers.get.side_effect = lambda key, default=None: headers_dict.get(key, default)
    return request


# ─────────────────────────────────────────────────────────────────────────────
# create_access_token
# ─────────────────────────────────────────────────────────────────────────────

def test_create_access_token_returns_string():
    token = create_access_token("user-123")
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_access_token_payload():
    user_id = "user-abc"
    token = create_access_token(user_id)
    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

    assert payload["sub"] == user_id
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload


def test_create_access_token_expires_in_15_minutes():
    before = int(time.time())
    token = create_access_token("u1")
    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    after = int(time.time())

    # exp should be roughly iat + 900 seconds (15 min)
    assert 895 <= payload["exp"] - before <= 905


# ─────────────────────────────────────────────────────────────────────────────
# create_refresh_token
# ─────────────────────────────────────────────────────────────────────────────

def test_create_refresh_token_type():
    token = create_refresh_token("user-xyz")
    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    assert payload["type"] == "refresh"


def test_create_refresh_token_expires_in_7_days():
    before = int(time.time())
    token = create_refresh_token("u1")
    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

    expected_ttl = 7 * 24 * 60 * 60
    assert abs((payload["exp"] - before) - expected_ttl) < 5


def test_access_and_refresh_tokens_are_different():
    access = create_access_token("u1")
    refresh = create_refresh_token("u1")
    assert access != refresh


# ─────────────────────────────────────────────────────────────────────────────
# get_current_user — error paths
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_current_user_missing_header():
    request = _make_request(auth_header=None)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request)
    assert exc_info.value.status_code == 401
    assert "Missing" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_invalid_scheme():
    request = _make_request(auth_header="Basic sometoken")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request)
    assert exc_info.value.status_code == 401
    assert "scheme" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_current_user_malformed_header():
    # No space — split() raises ValueError
    request = _make_request(auth_header="BearerNoSpace")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    request = _make_request(auth_header="Bearer notavalidtoken")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request)
    assert exc_info.value.status_code == 401
    assert "Invalid or expired" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_refresh_token_rejected():
    """A refresh token must not be accepted where an access token is expected."""
    refresh = create_refresh_token("user-42")
    request = _make_request(auth_header=f"Bearer {refresh}")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request)
    assert exc_info.value.status_code == 401
    assert "token type" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_current_user_valid_token():
    token = create_access_token("user-99")
    request = _make_request(auth_header=f"Bearer {token}")
    user = await get_current_user(request)
    assert isinstance(user, CurrentUser)
    assert user.user_id == "user-99"


# ─────────────────────────────────────────────────────────────────────────────
# optional_auth
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_optional_auth_returns_none_on_missing_header():
    request = _make_request(auth_header=None)
    result = await optional_auth(request)
    assert result is None


@pytest.mark.asyncio
async def test_optional_auth_returns_user_on_valid_token():
    token = create_access_token("user-77")
    request = _make_request(auth_header=f"Bearer {token}")
    result = await optional_auth(request)
    assert result is not None
    assert result.user_id == "user-77"


# ─────────────────────────────────────────────────────────────────────────────
# refresh_access_token
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_access_token_returns_new_tokens():
    refresh = create_refresh_token("user-55")
    new_access, new_refresh = await refresh_access_token(refresh)

    access_payload = jwt.decode(new_access, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    refresh_payload = jwt.decode(new_refresh, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

    assert access_payload["type"] == "access"
    assert access_payload["sub"] == "user-55"
    assert refresh_payload["type"] == "refresh"
    assert refresh_payload["sub"] == "user-55"


@pytest.mark.asyncio
async def test_refresh_access_token_rejects_access_token():
    """An access token must not be usable as a refresh token."""
    access = create_access_token("user-55")
    with pytest.raises(HTTPException) as exc_info:
        await refresh_access_token(access)
    assert exc_info.value.status_code == 401
    assert "refresh" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_refresh_access_token_rejects_garbage():
    with pytest.raises(HTTPException) as exc_info:
        await refresh_access_token("garbage.token.value")
    assert exc_info.value.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# TokenPayload model
# ─────────────────────────────────────────────────────────────────────────────

def test_token_payload_defaults():
    payload = TokenPayload(sub="user-1", exp=9999999999)
    assert payload.type == "access"
    assert payload.iat is None


def test_token_payload_custom_type():
    payload = TokenPayload(sub="user-1", exp=9999999999, type="refresh")
    assert payload.type == "refresh"
