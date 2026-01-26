"""
API endpoint tests for BlackRoad OS API.

Tests cover:
- Health check endpoints
- AI Chat endpoints
- Agent management endpoints
- Blockchain endpoints
- Payment endpoints
- System stats endpoints
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import agents_db, conversations_db, blockchain_db, sessions_db


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self, client):
        """Health endpoint should return healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "blackroad-os-api"
        assert "timestamp" in data

    def test_readiness_check(self, client):
        """Readiness endpoint should return ready status."""
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["version"] == "1.0.0"


class TestAIChatEndpoints:
    """Tests for AI chat endpoints."""

    def test_chat_creates_conversation(self, client, auth_headers, sample_chat_message):
        """Chat should create a new conversation if none specified."""
        response = client.post(
            "/api/ai-chat/chat",
            json=sample_chat_message,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert data["conversation_id"].startswith("conv-")

    def test_chat_returns_ai_response(self, client, auth_headers, sample_chat_message):
        """Chat should return an AI response."""
        response = client.post(
            "/api/ai-chat/chat",
            json=sample_chat_message,
            headers=auth_headers
        )
        data = response.json()
        assert "message" in data
        assert len(data["message"]) > 0

    def test_chat_continues_existing_conversation(self, client, auth_headers):
        """Chat should continue existing conversation."""
        # Start conversation
        response1 = client.post(
            "/api/ai-chat/chat",
            json={"message": "First message"},
            headers=auth_headers
        )
        conv_id = response1.json()["conversation_id"]

        # Continue conversation
        response2 = client.post(
            "/api/ai-chat/chat",
            json={"message": "Second message", "conversation_id": conv_id},
            headers=auth_headers
        )
        data = response2.json()
        assert data["conversation_id"] == conv_id
        assert len(data["messages"]) == 4  # 2 user + 2 assistant

    def test_chat_stores_messages(self, client, auth_headers, sample_chat_message):
        """Chat should store messages in conversation."""
        response = client.post(
            "/api/ai-chat/chat",
            json=sample_chat_message,
            headers=auth_headers
        )
        data = response.json()
        assert "messages" in data
        assert len(data["messages"]) == 2  # user + assistant
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"

    def test_chat_without_auth(self, client, sample_chat_message):
        """Chat without auth should still work (user_id will be None)."""
        response = client.post("/api/ai-chat/chat", json=sample_chat_message)
        assert response.status_code == 200

    def test_list_conversations(self, client, auth_headers):
        """Should list user conversations."""
        # Create a conversation first
        client.post(
            "/api/ai-chat/chat",
            json={"message": "Test"},
            headers=auth_headers
        )
        response = client.get("/api/ai-chat/conversations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data
        assert len(data["conversations"]) >= 1


class TestAgentEndpoints:
    """Tests for agent management endpoints."""

    def test_spawn_agent(self, client, auth_headers, sample_agent_data):
        """Should spawn a new agent."""
        response = client.post(
            "/api/agents/spawn",
            json=sample_agent_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "agent_id" in data
        assert data["status"] == "spawned"
        assert data["agent"]["role"] == sample_agent_data["role"]

    def test_spawn_agent_generates_unique_id(self, client, auth_headers, sample_agent_data):
        """Each spawned agent should have unique ID."""
        response1 = client.post("/api/agents/spawn", json=sample_agent_data, headers=auth_headers)
        response2 = client.post("/api/agents/spawn", json=sample_agent_data, headers=auth_headers)
        assert response1.json()["agent_id"] != response2.json()["agent_id"]

    def test_spawn_agent_sets_active_status(self, client, auth_headers, sample_agent_data):
        """Spawned agent should be active."""
        response = client.post("/api/agents/spawn", json=sample_agent_data, headers=auth_headers)
        assert response.json()["agent"]["status"] == "active"

    def test_spawn_agent_stores_capabilities(self, client, auth_headers, sample_agent_data):
        """Agent should store capabilities."""
        response = client.post("/api/agents/spawn", json=sample_agent_data, headers=auth_headers)
        agent = response.json()["agent"]
        assert agent["capabilities"] == sample_agent_data["capabilities"]

    def test_list_agents(self, client, auth_headers, sample_agent_data):
        """Should list user agents."""
        # Spawn an agent
        client.post("/api/agents/spawn", json=sample_agent_data, headers=auth_headers)

        response = client.get("/api/agents/list", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert data["user_agents"] >= 1

    def test_list_agents_filters_by_user(self, client, auth_headers, another_auth_headers, sample_agent_data):
        """Each user should only see their own agents."""
        # User 1 creates agent
        client.post("/api/agents/spawn", json=sample_agent_data, headers=auth_headers)

        # User 2 lists agents
        response = client.get("/api/agents/list", headers=another_auth_headers)
        data = response.json()
        assert data["user_agents"] == 0

    def test_get_agent_by_id(self, client, auth_headers, sample_agent_data):
        """Should get specific agent by ID."""
        spawn_response = client.post("/api/agents/spawn", json=sample_agent_data, headers=auth_headers)
        agent_id = spawn_response.json()["agent_id"]

        response = client.get(f"/api/agents/{agent_id}")
        assert response.status_code == 200
        assert response.json()["id"] == agent_id

    def test_get_agent_not_found(self, client):
        """Should return 404 for nonexistent agent."""
        response = client.get("/api/agents/nonexistent-id")
        assert response.status_code == 404

    def test_terminate_agent(self, client, auth_headers, sample_agent_data):
        """Should terminate agent."""
        spawn_response = client.post("/api/agents/spawn", json=sample_agent_data, headers=auth_headers)
        agent_id = spawn_response.json()["agent_id"]

        response = client.delete(f"/api/agents/{agent_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "terminated"

    def test_terminate_agent_not_found(self, client, auth_headers):
        """Should return 404 when terminating nonexistent agent."""
        response = client.delete("/api/agents/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404

    def test_terminate_agent_unauthorized(self, client, auth_headers, another_auth_headers, sample_agent_data):
        """User should not terminate another user's agent."""
        # User 1 creates agent
        spawn_response = client.post("/api/agents/spawn", json=sample_agent_data, headers=auth_headers)
        agent_id = spawn_response.json()["agent_id"]

        # User 2 tries to terminate
        response = client.delete(f"/api/agents/{agent_id}", headers=another_auth_headers)
        assert response.status_code == 403


class TestBlockchainEndpoints:
    """Tests for blockchain endpoints."""

    def test_get_blocks_empty(self, client):
        """Should return empty blocks list initially."""
        response = client.get("/api/blockchain/blocks")
        assert response.status_code == 200
        data = response.json()
        assert data["blocks"] == []
        assert data["total_blocks"] == 0

    def test_get_blocks_with_limit(self, client):
        """Should respect limit parameter."""
        response = client.get("/api/blockchain/blocks?limit=5")
        assert response.status_code == 200

    def test_create_transaction(self, client, auth_headers, sample_transaction_data):
        """Should create a transaction."""
        response = client.post(
            "/api/blockchain/transaction",
            json=sample_transaction_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "transaction_id" in data
        assert data["status"] == "pending"

    def test_create_transaction_stores_details(self, client, auth_headers, sample_transaction_data):
        """Transaction should store all details."""
        response = client.post(
            "/api/blockchain/transaction",
            json=sample_transaction_data,
            headers=auth_headers
        )
        tx = response.json()["transaction"]
        assert tx["from"] == sample_transaction_data["from_address"]
        assert tx["to"] == sample_transaction_data["to_address"]
        assert tx["amount"] == sample_transaction_data["amount"]
        assert tx["currency"] == sample_transaction_data["currency"]

    def test_get_transactions(self, client, auth_headers, sample_transaction_data):
        """Should list transactions."""
        # Create a transaction
        client.post(
            "/api/blockchain/transaction",
            json=sample_transaction_data,
            headers=auth_headers
        )

        response = client.get("/api/blockchain/transactions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["transactions"]) >= 1


class TestPaymentEndpoints:
    """Tests for payment endpoints."""

    def test_create_checkout_session(self, client):
        """Should create a checkout session."""
        response = client.post(
            "/api/payments/create-checkout-session",
            json={"amount": 4900, "tier": "starter"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "sessionId" in data
        assert "url" in data
        assert data["sessionId"].startswith("cs_test_")

    def test_create_checkout_session_default_values(self, client):
        """Checkout should use default values if not provided."""
        response = client.post(
            "/api/payments/create-checkout-session",
            json={}
        )
        data = response.json()
        assert data["sessionId"].startswith("cs_test_")

    def test_verify_payment_success(self, client, auth_headers):
        """Should verify payment and update tier."""
        # Create session first
        create_response = client.post(
            "/api/payments/create-checkout-session",
            json={"tier": "pro"}
        )
        session_id = create_response.json()["sessionId"]

        # Verify payment
        response = client.post(
            "/api/payments/verify-payment",
            json={"session_id": session_id},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tier"] == "pro"

    def test_verify_payment_invalid_session(self, client, auth_headers):
        """Should fail for invalid session."""
        response = client.post(
            "/api/payments/verify-payment",
            json={"session_id": "invalid-session"},
            headers=auth_headers
        )
        data = response.json()
        assert data["success"] is False


class TestFilesEndpoints:
    """Tests for files endpoints."""

    def test_list_files(self, client, auth_headers):
        """Should list user files (empty initially)."""
        response = client.get("/api/files/list", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["files"] == []
        assert data["total_files"] == 0
        assert "storage_limit" in data


class TestSocialEndpoints:
    """Tests for social endpoints."""

    def test_get_social_feed(self, client):
        """Should return social feed (empty initially)."""
        response = client.get("/api/social/feed")
        assert response.status_code == 200
        data = response.json()
        assert data["posts"] == []


class TestSystemEndpoints:
    """Tests for system endpoints."""

    def test_get_system_stats(self, client):
        """Should return system stats."""
        response = client.get("/api/system/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "total_agents" in data
        assert "active_agents" in data
        assert "version" in data

    def test_system_stats_reflect_data(self, client, auth_headers, sample_agent_data):
        """Stats should reflect actual data."""
        # Spawn an agent
        client.post("/api/agents/spawn", json=sample_agent_data, headers=auth_headers)

        response = client.get("/api/system/stats")
        data = response.json()
        assert data["total_agents"] >= 1
        assert data["active_agents"] >= 1
