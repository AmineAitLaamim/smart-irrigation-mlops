import os
import sys
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client):
    # Test the health endpoint
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_model_info_endpoint(client):
    # Test the model info endpoint
    response = await client.get("/v1/model/info")
    assert response.status_code == 200
    assert "version" in response.json()


@pytest.mark.asyncio
async def test_predict_endpoint(client):
    # Test the predict endpoint
    response = await client.post(
        "/v1/predict",
        json={"zone_id": "zone_a", "sensor_id": "sensor_a1", "features": [1.0, 2.0, 3.0]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "predicted_moisture" in data
    assert len(data["confidence_interval"]) == 2
