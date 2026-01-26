"""
Pytest fixtures and configuration for BlackRoad OS API tests.
"""
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (
    app,
    users_db,
    sessions_db,
    agents_db,
    blockchain_db,
    conversations_db,
    hash_password,
    create_token,
    SECRET_KEY,
)


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_databases():
    """Clear all in-memory databases before each test."""
    users_db.clear()
    sessions_db.clear()
    agents_db.clear()
    blockchain_db["blocks"] = []
    blockchain_db["transactions"] = []
    conversations_db.clear()
    yield
    # Cleanup after test
    users_db.clear()
    sessions_db.clear()
    agents_db.clear()
    blockchain_db["blocks"] = []
    blockchain_db["transactions"] = []
    conversations_db.clear()


@pytest.fixture
def test_user():
    """Create a test user and return user data."""
    user_data = {
        "email": "test@example.com",
        "password": "testpassword123",
        "name": "Test User"
    }
    return user_data


@pytest.fixture
def registered_user(client, test_user):
    """Register a test user and return the response data."""
    response = client.post("/api/auth/register", json=test_user)
    return response.json()


@pytest.fixture
def auth_headers(registered_user):
    """Get authorization headers with valid token."""
    token = registered_user["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def another_user():
    """Create another test user data."""
    return {
        "email": "another@example.com",
        "password": "anotherpassword123",
        "name": "Another User"
    }


@pytest.fixture
def registered_another_user(client, another_user):
    """Register another test user."""
    response = client.post("/api/auth/register", json=another_user)
    return response.json()


@pytest.fixture
def another_auth_headers(registered_another_user):
    """Get authorization headers for another user."""
    token = registered_another_user["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_agent_data():
    """Sample agent spawn data."""
    return {
        "role": "guardian",
        "capabilities": ["audit", "verify", "protect"],
        "pack": "security"
    }


@pytest.fixture
def sample_transaction_data():
    """Sample blockchain transaction data."""
    return {
        "from_address": "0x1234567890abcdef",
        "to_address": "0xfedcba0987654321",
        "amount": 100.0,
        "currency": "RoadCoin"
    }


@pytest.fixture
def sample_chat_message():
    """Sample chat message data."""
    return {
        "message": "Hello, BlackRoad!"
    }
