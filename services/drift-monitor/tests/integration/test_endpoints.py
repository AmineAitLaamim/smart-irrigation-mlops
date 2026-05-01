import os
import sys
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from main import app, monitor


@pytest_asyncio.fixture
async def client():
    monitor.connect = AsyncMock()
    monitor.disconnect = AsyncMock()
    monitor.run = AsyncMock()
    monitor.status = AsyncMock(return_value={"page_hinkley_score": 0.1, "kl_divergence": 0.01, "mean_error": 0.0, "drift_detected": False})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "drift-monitor"


@pytest.mark.asyncio
async def test_drift_status_endpoint(client):
    response = await client.get("/v1/drift/status")
    assert response.status_code == 200
    assert "drift_detected" in response.json()
