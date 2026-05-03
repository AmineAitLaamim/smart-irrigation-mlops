import os
import sys
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from uuid import uuid4, UUID

# Setup sys.path to find src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

# Mock redis and database before importing app
with patch("redis.asyncio.from_url", return_value=MagicMock()):
    with patch("src.database.db.connect", new_callable=AsyncMock):
        from main import app
        from auth import create_tokens

from src.database import get_db_conn

@pytest_asyncio.fixture
async def client(mock_conn):
    async def override_get_db_conn():
        yield mock_conn
    
    app.dependency_overrides[get_db_conn] = override_get_db_conn
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
def mock_conn():
    conn = AsyncMock()
    return conn

@pytest.mark.asyncio
async def test_get_me(client, mock_conn):
    user_id = str(uuid4())
    access_token, _ = create_tokens(user_id)
    
    mock_user = {
        "user_id": user_id,
        "email": "test@example.com",
        "full_name": "Test User",
        "is_admin": False,
        "created_at": "2023-01-01T00:00:00"
    }
    
    mock_conn.fetchrow.return_value = mock_user
    
    response = await client.get("/users/me", headers={"Authorization": f"Bearer {access_token}"})
    
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
    assert response.json()["user_id"] == user_id

@pytest.mark.asyncio
async def test_update_me(client, mock_conn):
    user_id = str(uuid4())
    access_token, _ = create_tokens(user_id)
    
    mock_user = {
        "user_id": user_id,
        "email": "updated@example.com",
        "full_name": "Updated User",
        "is_admin": False,
        "created_at": "2023-01-01T00:00:00"
    }
    
    # First call for get_current_user
    mock_conn.fetchrow.side_effect = [
        {
            "user_id": user_id,
            "email": "test@example.com",
            "full_name": "Test User",
            "is_admin": False,
            "created_at": "2023-01-01T00:00:00"
        },
        mock_user # Second call for update
    ]
    
    response = await client.put(
        "/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"full_name": "Updated User", "email": "updated@example.com"}
    )
    
    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated User"
    assert response.json()["email"] == "updated@example.com"

@pytest.mark.asyncio
async def test_list_users_admin(client, mock_conn):
    user_id = str(uuid4())
    access_token, _ = create_tokens(user_id)
    
    mock_users = [
        {
            "user_id": user_id,
            "email": "admin@example.com",
            "full_name": "Admin User",
            "is_admin": True,
            "created_at": "2023-01-01T00:00:00"
        },
        {
            "user_id": str(uuid4()),
            "email": "user@example.com",
            "full_name": "Regular User",
            "is_admin": False,
            "created_at": "2023-01-02T00:00:00"
        }
    ]
    
    # First call for get_current_user (get_admin_user depends on it)
    mock_conn.fetchrow.return_value = mock_users[0]
    # Second call for list users
    mock_conn.fetch.return_value = mock_users
    
    response = await client.get("/users", headers={"Authorization": f"Bearer {access_token}"})
    
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["email"] == "admin@example.com"

@pytest.mark.asyncio
async def test_list_users_non_admin(client, mock_conn):
    user_id = str(uuid4())
    access_token, _ = create_tokens(user_id)
    
    mock_user = {
        "user_id": user_id,
        "email": "user@example.com",
        "full_name": "Regular User",
        "is_admin": False,
        "created_at": "2023-01-01T00:00:00"
    }
    
    mock_conn.fetchrow.return_value = mock_user
    
    response = await client.get("/users", headers={"Authorization": f"Bearer {access_token}"})
    
    assert response.status_code == 403
    assert "Admin privileges required" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_user_admin(client, mock_conn):
    admin_id = str(uuid4())
    target_id = str(uuid4())
    access_token, _ = create_tokens(admin_id)
    
    mock_conn.fetchrow.side_effect = [
        {
            "user_id": admin_id,
            "email": "admin@example.com",
            "full_name": "Admin User",
            "is_admin": True,
            "created_at": "2023-01-01T00:00:00"
        },
        {"exists": 1} # For check if user exists
    ]
    mock_conn.execute.return_value = "DELETE 1"
    
    response = await client.delete(f"/users/{target_id}", headers={"Authorization": f"Bearer {access_token}"})
    
    assert response.status_code == 204
    mock_conn.execute.assert_called_with("DELETE FROM users WHERE user_id = $1", UUID(target_id))

@pytest.mark.asyncio
async def test_delete_zone(client, mock_conn):
    zone_id = "test_zone"
    mock_conn.execute.return_value = "DELETE 1"
    
    response = await client.delete(f"/v1/zones/{zone_id}")
    
    assert response.status_code == 204
    mock_conn.execute.assert_called_with("DELETE FROM zones WHERE zone_id = $1", zone_id)

@pytest.mark.asyncio
async def test_delete_zone_not_found(client, mock_conn):
    zone_id = "non_existent"
    mock_conn.execute.return_value = "DELETE 0"
    
    response = await client.delete(f"/v1/zones/{zone_id}")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Zone not found"
