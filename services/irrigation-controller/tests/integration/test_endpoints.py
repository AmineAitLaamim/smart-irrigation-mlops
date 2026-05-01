import os
import sys
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from main import app, controller


@pytest_asyncio.fixture
async def client():
    controller.connect = AsyncMock()
    controller.disconnect = AsyncMock()
    controller.run = AsyncMock()
    controller.list_events = AsyncMock(return_value=[{"zone_id": "zone_a", "recommended_volume": 12.0}])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "irrigation-controller"


@pytest.mark.asyncio
async def test_irrigation_events_endpoint(client):
    response = await client.get("/v1/irrigation/events")
    assert response.status_code == 200
    assert response.json()["events"][0]["zone_id"] == "zone_a"
