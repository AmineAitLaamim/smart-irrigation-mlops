# =============================================================================
# Integration Tests — HTTP endpoints
# Tests real HTTP responses from the FastAPI app using httpx.AsyncClient.
# No external services required (Redis mocked, no upstream proxying tested).
# =============================================================================

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from httpx import AsyncClient, ASGITransport

with patch("redis.from_url", return_value=MagicMock()):
    from main import app
    from auth import create_access_token, create_refresh_token


# ─────────────────────────────────────────────────────────────────────────────
# Fixture: async HTTP client against the real FastAPI app (no live server)
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ─────────────────────────────────────────────────────────────────────────────
# GET /health
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "api-gateway"


# ─────────────────────────────────────────────────────────────────────────────
# GET /
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_root_endpoint(client):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "API Gateway" in data["message"]
    assert data["version"] == "1.0.0"


# ─────────────────────────────────────────────────────────────────────────────
# POST /auth/refresh — token refresh endpoint
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_endpoint_missing_body(client):
    response = await client.post("/auth/refresh", json={})
    assert response.status_code == 400
    assert "Missing" in response.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_endpoint_invalid_token(client):
    response = await client.post("/auth/refresh", json={"refresh_token": "garbage"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_endpoint_with_access_token_rejected(client):
    """Passing an access token to the refresh endpoint must fail."""
    access = create_access_token("user-1")
    response = await client.post("/auth/refresh", json={"refresh_token": access})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_endpoint_valid_refresh_token(client):
    refresh = create_refresh_token("user-42")
    response = await client.post("/auth/refresh", json={"refresh_token": refresh})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


# ─────────────────────────────────────────────────────────────────────────────
# Gateway proxy — unknown route
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unknown_route_returns_404(client):
    response = await client.get("/nonexistent/endpoint")
    assert response.status_code == 404
    assert "Route not found" in response.json()["detail"]


# ─────────────────────────────────────────────────────────────────────────────
# Gateway proxy — upstream service unreachable → 502
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_known_route_unreachable_upstream_returns_502(client):
    """When the upstream is down, the gateway should return 502 Bad Gateway."""
    import httpx
    with patch("main.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.request = AsyncMock(
            side_effect=httpx.RequestError("Connection refused")
        )
        mock_client_cls.return_value = mock_client

        response = await client.get("/v1/drift/status")
        assert response.status_code == 502
