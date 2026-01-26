"""
Authentication tests for BlackRoad OS API.

Tests cover:
- User registration
- User login
- JWT token creation and verification
- Password hashing
- Protected endpoint access
"""
import pytest
import jwt
import time
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (
    hash_password,
    create_token,
    verify_token,
    SECRET_KEY,
    JWT_ALGORITHM,
    users_db,
)


class TestPasswordHashing:
    """Tests for password hashing functionality."""

    def test_hash_password_returns_hex_string(self):
        """Hash should return a hex string."""
        result = hash_password("testpassword")
        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 produces 64 hex characters

    def test_hash_password_deterministic(self):
        """Same password should produce same hash."""
        password = "mypassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 == hash2

    def test_hash_password_different_passwords_produce_different_hashes(self):
        """Different passwords should produce different hashes."""
        hash1 = hash_password("password1")
        hash2 = hash_password("password2")
        assert hash1 != hash2

    def test_hash_password_empty_string(self):
        """Empty string should still produce valid hash."""
        result = hash_password("")
        assert isinstance(result, str)
        assert len(result) == 64


class TestJWTTokens:
    """Tests for JWT token creation and verification."""

    def test_create_token_returns_string(self):
        """Token should be a string."""
        token = create_token("user-123")
        assert isinstance(token, str)

    def test_create_token_is_valid_jwt(self):
        """Token should be a valid JWT that can be decoded."""
        user_id = "user-123"
        token = create_token(user_id)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        assert payload["user_id"] == user_id

    def test_create_token_has_expiration(self):
        """Token should have expiration time."""
        token = create_token("user-123")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        assert "exp" in payload

    def test_create_token_has_issued_at(self):
        """Token should have issued at time."""
        token = create_token("user-123")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        assert "iat" in payload

    def test_verify_token_returns_user_id(self):
        """Verify token should return the user_id."""
        user_id = "user-456"
        token = create_token(user_id)
        result = verify_token(token)
        assert result == user_id

    def test_verify_token_invalid_token(self):
        """Invalid token should return None."""
        result = verify_token("invalid-token")
        assert result is None

    def test_verify_token_wrong_secret(self):
        """Token signed with wrong secret should fail verification."""
        payload = {
            "user_id": "user-123",
            "exp": datetime.utcnow() + timedelta(hours=24),
        }
        token = jwt.encode(payload, "wrong-secret", algorithm=JWT_ALGORITHM)
        result = verify_token(token)
        assert result is None

    def test_verify_token_expired(self):
        """Expired token should fail verification."""
        payload = {
            "user_id": "user-123",
            "exp": datetime.utcnow() - timedelta(hours=1),  # Expired
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)
        result = verify_token(token)
        assert result is None

    def test_verify_token_malformed(self):
        """Malformed token should return None."""
        result = verify_token("not.a.valid.token.at.all")
        assert result is None


class TestUserRegistration:
    """Tests for user registration endpoint."""

    def test_register_success(self, client, test_user):
        """Successful registration should return token and user info."""
        response = client.post("/api/auth/register", json=test_user)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user["email"]

    def test_register_returns_valid_token(self, client, test_user):
        """Registration should return a valid JWT token."""
        response = client.post("/api/auth/register", json=test_user)
        data = response.json()
        user_id = verify_token(data["access_token"])
        assert user_id is not None
        assert user_id == data["user"]["id"]

    def test_register_duplicate_email(self, client, test_user):
        """Registering with existing email should fail."""
        client.post("/api/auth/register", json=test_user)
        response = client.post("/api/auth/register", json=test_user)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_register_invalid_email(self, client):
        """Invalid email format should fail."""
        response = client.post("/api/auth/register", json={
            "email": "invalid-email",
            "password": "password123"
        })
        assert response.status_code == 422

    def test_register_missing_password(self, client):
        """Missing password should fail."""
        response = client.post("/api/auth/register", json={
            "email": "test@example.com"
        })
        assert response.status_code == 422

    def test_register_without_name_uses_email_prefix(self, client):
        """Registration without name should use email prefix."""
        response = client.post("/api/auth/register", json={
            "email": "john@example.com",
            "password": "password123"
        })
        data = response.json()
        assert data["user"]["name"] == "john"

    def test_register_with_name(self, client):
        """Registration with name should use provided name."""
        response = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "password123",
            "name": "John Doe"
        })
        data = response.json()
        assert data["user"]["name"] == "John Doe"

    def test_register_sets_free_tier(self, client, test_user):
        """New users should start with free tier."""
        client.post("/api/auth/register", json=test_user)
        assert users_db[test_user["email"]]["subscription_tier"] == "free"


class TestUserLogin:
    """Tests for user login endpoint."""

    def test_login_success(self, client, test_user, registered_user):
        """Successful login should return token."""
        response = client.post("/api/auth/login", json={
            "email": test_user["email"],
            "password": test_user["password"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user, registered_user):
        """Wrong password should fail."""
        response = client.post("/api/auth/login", json={
            "email": test_user["email"],
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """Login with nonexistent user should fail."""
        response = client.post("/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "password123"
        })
        assert response.status_code == 401

    def test_login_invalid_email_format(self, client):
        """Invalid email format should fail validation."""
        response = client.post("/api/auth/login", json={
            "email": "not-an-email",
            "password": "password123"
        })
        assert response.status_code == 422


class TestCurrentUser:
    """Tests for get current user endpoint."""

    def test_get_current_user_authenticated(self, client, auth_headers, test_user):
        """Authenticated user should get their info."""
        response = client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user["email"]

    def test_get_current_user_unauthenticated(self, client):
        """Unauthenticated request should fail."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client):
        """Invalid token should fail."""
        response = client.get("/api/auth/me", headers={
            "Authorization": "Bearer invalid-token"
        })
        assert response.status_code == 401

    def test_get_current_user_malformed_header(self, client):
        """Malformed authorization header should fail."""
        response = client.get("/api/auth/me", headers={
            "Authorization": "NotBearer token"
        })
        assert response.status_code == 401

    def test_get_current_user_returns_subscription_tier(self, client, auth_headers):
        """Response should include subscription tier."""
        response = client.get("/api/auth/me", headers=auth_headers)
        data = response.json()
        assert "subscription_tier" in data
        assert data["subscription_tier"] == "free"
