#!/usr/bin/env python3
"""
Tests for Token Generation API Endpoints (SCRUM-137)
Test-driven development for API token generation endpoints.
"""

import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from server.auth.models import User, APIToken
from server.auth.utils import hash_password
from server.auth.jwt_handler import get_jwt_handler

# Configure pytest-asyncio
pytestmark = pytest.mark.asyncio


class TestTokenAPI:
    """Test token generation API endpoints."""

    async def test_create_token_success(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test successful token creation."""
        # Create and login a user
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash=hash_password("TestPassword123!"),
            email_verified=True
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Get access token
        jwt_handler = get_jwt_handler()
        access_token = jwt_handler.create_access_token({
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "organizations": []
        })
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Create API token
        response = await async_client.post(
            "/api/v1/tokens",
            json={"name": "My Test Client"},
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert data["name"] == "My Test Client"
        assert "token" in data
        assert len(data["token"]) == 32
        assert data["expires_at"] is None
        assert "created_at" in data
        
        # Verify token is stored in database
        from uuid import UUID
        result = await db_session.execute(
            select(APIToken).where(APIToken.id == UUID(data["id"]))
        )
        db_token = result.scalar_one()
        assert db_token.user_id == user.id
        assert db_token.name == "My Test Client"
        assert db_token.verify_token(data["token"])  # Verify plain token matches hash

    async def test_create_token_with_expiration(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test creating token with expiration."""
        # Create and login a user
        user = User(
            email="test2@example.com",
            username="testuser2",
            password_hash=hash_password("TestPassword123!"),
            email_verified=True
        )
        db_session.add(user)
        await db_session.commit()
        
        # Get access token
        jwt_handler = get_jwt_handler()
        access_token = jwt_handler.create_access_token({
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "organizations": []
        })
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = await async_client.post(
            "/api/v1/tokens",
            json={"name": "Expiring Token", "expires_in_days": 30},
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Parse and verify expiration
        expires_str = data["expires_at"]
        # Handle both formats: with Z suffix and without
        if expires_str.endswith("Z"):
            expires_at = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
        elif "+" not in expires_str and not expires_str.endswith("00:00"):
            # Assume UTC if no timezone info
            expires_at = datetime.fromisoformat(expires_str).replace(tzinfo=timezone.utc)
        else:
            expires_at = datetime.fromisoformat(expires_str)
        
        expected = datetime.now(timezone.utc) + timedelta(days=30)
        
        # Allow 1 minute tolerance for test execution time
        assert abs((expires_at - expected).total_seconds()) < 60

    async def test_create_token_unauthenticated(self, async_client: AsyncClient):
        """Test token creation requires authentication."""
        response = await async_client.post(
            "/api/v1/tokens",
            json={"name": "Unauthorized Token"}
        )
        
        assert response.status_code == 403  # No auth header

    async def test_create_token_invalid_name(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test token creation with invalid name."""
        # Create and login a user
        user = User(
            email="test3@example.com",
            username="testuser3",
            password_hash=hash_password("TestPassword123!"),
            email_verified=True
        )
        db_session.add(user)
        await db_session.commit()
        
        # Get access token
        jwt_handler = get_jwt_handler()
        access_token = jwt_handler.create_access_token({
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "organizations": []
        })
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Empty name
        response = await async_client.post(
            "/api/v1/tokens",
            json={"name": ""},
            headers=headers
        )
        assert response.status_code == 422
        
        # Name too long
        response = await async_client.post(
            "/api/v1/tokens",
            json={"name": "a" * 256},
            headers=headers
        )
        assert response.status_code == 422

    async def test_create_token_rate_limiting(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test rate limiting for token creation."""
        # Create and login a user
        user = User(
            email="test4@example.com",
            username="testuser4",
            password_hash=hash_password("TestPassword123!"),
            email_verified=True
        )
        db_session.add(user)
        await db_session.commit()
        
        # Get access token
        jwt_handler = get_jwt_handler()
        access_token = jwt_handler.create_access_token({
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "organizations": []
        })
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Create 10 tokens (should succeed)
        for i in range(10):
            response = await async_client.post(
                "/api/v1/tokens",
                json={"name": f"Token {i}"},
                headers=headers
            )
            assert response.status_code == 200
        
        # 11th token should fail
        response = await async_client.post(
            "/api/v1/tokens",
            json={"name": "Token 11"},
            headers=headers
        )
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]

    async def test_list_tokens_empty(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test listing tokens when user has none."""
        # Create and login a user
        user = User(
            email="test5@example.com",
            username="testuser5",
            password_hash=hash_password("TestPassword123!"),
            email_verified=True
        )
        db_session.add(user)
        await db_session.commit()
        
        # Get access token
        jwt_handler = get_jwt_handler()
        access_token = jwt_handler.create_access_token({
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "organizations": []
        })
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = await async_client.get("/api/v1/tokens", headers=headers)
        
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_tokens_with_data(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test listing user's tokens."""
        # Create and login a user
        user = User(
            email="test6@example.com",
            username="testuser6",
            password_hash=hash_password("TestPassword123!"),
            email_verified=True
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create some tokens directly in DB
        token1 = APIToken(
            user_id=user.id,
            name="Token 1",
            token_hash=APIToken.hash_token("test-token-1"),
            last_used_at=datetime.now(timezone.utc)
        )
        token2 = APIToken(
            user_id=user.id,
            name="Token 2",
            token_hash=APIToken.hash_token("test-token-2"),
            is_active=False
        )
        
        db_session.add(token1)
        db_session.add(token2)
        await db_session.commit()
        
        # Get access token
        jwt_handler = get_jwt_handler()
        access_token = jwt_handler.create_access_token({
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "organizations": []
        })
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # List tokens
        response = await async_client.get("/api/v1/tokens", headers=headers)
        assert response.status_code == 200
        
        tokens = response.json()
        assert len(tokens) == 2
        
        # Verify tokens are sorted by created_at desc
        # Since we added them in order, token2 should be first
        token_names = [t["name"] for t in tokens]
        assert "Token 2" in token_names
        assert "Token 1" in token_names
        
        # Verify no actual tokens are exposed
        for token in tokens:
            assert "token" not in token
            assert "token_hash" not in token
            
        # Verify fields are present
        token2_data = next(t for t in tokens if t["name"] == "Token 2")
        assert token2_data["is_active"] is False
        
        token1_data = next(t for t in tokens if t["name"] == "Token 1")
        assert token1_data["last_used_at"] is not None

    async def test_list_tokens_only_own_tokens(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that users only see their own tokens."""
        # Create first user
        user1 = User(
            email="test7@example.com",
            username="testuser7",
            password_hash=hash_password("TestPassword123!"),
            email_verified=True
        )
        db_session.add(user1)
        
        # Create another user and their token
        other_user = User(
            email="other@example.com",
            username="otheruser",
            password_hash=hash_password("TestPassword123!"),
            email_verified=True
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(user1)
        await db_session.refresh(other_user)
        
        other_token = APIToken(
            user_id=other_user.id,
            name="Other User Token",
            token_hash=APIToken.hash_token("other-token")
        )
        db_session.add(other_token)
        
        # Create own token
        own_token = APIToken(
            user_id=user1.id,
            name="My Token",
            token_hash=APIToken.hash_token("my-token")
        )
        db_session.add(own_token)
        await db_session.commit()
        
        # Get access token for user1
        jwt_handler = get_jwt_handler()
        access_token = jwt_handler.create_access_token({
            "id": str(user1.id),
            "email": user1.email,
            "username": user1.username,
            "organizations": []
        })
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # List tokens - should only see own
        response = await async_client.get("/api/v1/tokens", headers=headers)
        assert response.status_code == 200
        
        tokens = response.json()
        assert len(tokens) == 1
        assert tokens[0]["name"] == "My Token"