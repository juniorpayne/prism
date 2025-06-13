#!/usr/bin/env python3
"""
Tests for JWT authentication functionality.
"""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.jwt_handler import get_jwt_handler
from server.auth.models import RefreshToken, User
from server.auth.utils import hash_password


class TestJWTAuthentication:
    """Test JWT authentication endpoints."""

    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient, verified_user: User):
        """Test successful login with valid credentials."""
        response = await async_client.post(
            "/api/auth/login",
            json={"username": verified_user.username, "password": "TestPassword123!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] == 900

    @pytest.mark.asyncio
    async def test_login_with_email(self, async_client: AsyncClient, verified_user: User):
        """Test login using email instead of username."""
        response = await async_client.post(
            "/api/auth/login",
            json={"username": verified_user.email, "password": "TestPassword123!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, async_client: AsyncClient, verified_user: User):
        """Test login with invalid password."""
        response = await async_client.post(
            "/api/auth/login",
            json={"username": verified_user.username, "password": "WrongPassword123!"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials"

    @pytest.mark.asyncio
    async def test_login_unverified_email(self, async_client: AsyncClient, unverified_user: User):
        """Test login with unverified email."""
        response = await async_client.post(
            "/api/auth/login",
            json={"username": unverified_user.username, "password": "TestPassword123!"},
        )

        assert response.status_code == 400
        assert "Email not verified" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_access_protected_endpoint(self, async_client: AsyncClient, auth_headers: dict):
        """Test accessing protected endpoint with valid token."""
        response = await async_client.get("/api/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "username" in data

    @pytest.mark.asyncio
    async def test_access_protected_endpoint_no_token(self, async_client: AsyncClient):
        """Test accessing protected endpoint without token."""
        response = await async_client.get("/api/auth/me")

        assert response.status_code == 403  # FastAPI returns 403 for missing credentials

    @pytest.mark.asyncio
    async def test_access_protected_endpoint_invalid_token(self, async_client: AsyncClient):
        """Test accessing protected endpoint with invalid token."""
        response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid authentication credentials"

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self, async_client: AsyncClient, verified_user: User, db_session: AsyncSession
    ):
        """Test refreshing access token with valid refresh token."""
        # First login to get tokens
        login_response = await async_client.post(
            "/api/auth/login",
            json={"username": verified_user.username, "password": "TestPassword123!"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Use refresh token to get new access token
        response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] == 900

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, async_client: AsyncClient):
        """Test refresh with invalid token."""
        response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid_refresh_token"},
        )

        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_logout_success(self, async_client: AsyncClient, auth_headers: dict):
        """Test successful logout."""
        response = await async_client.post("/api/auth/logout", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"

    @pytest.mark.asyncio
    async def test_logout_invalidates_refresh_tokens(
        self, async_client: AsyncClient, verified_user: User, db_session: AsyncSession
    ):
        """Test that logout invalidates all user's refresh tokens."""
        # Login to get tokens
        login_response = await async_client.post(
            "/api/auth/login",
            json={"username": verified_user.username, "password": "TestPassword123!"},
        )
        if login_response.status_code == 429:
            pytest.skip("Rate limit exceeded - skipping test")
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        refresh_token = login_response.json()["refresh_token"]

        # Logout
        await async_client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Try to use refresh token after logout
        response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_access_token(self, async_client: AsyncClient, verified_user: User):
        """Test that expired access token is rejected."""
        # Create an expired token
        jwt_handler = get_jwt_handler()
        jwt_handler.access_token_expire = timedelta(seconds=-1)  # Expired

        expired_token = jwt_handler.create_access_token(
            {
                "id": str(verified_user.id),
                "email": verified_user.email,
                "username": verified_user.username,
                "organizations": [],
            }
        )

        response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401
        # The error is caught and returned as a generic invalid credentials error
        assert response.json()["detail"] == "Invalid authentication credentials"

    @pytest.mark.asyncio
    async def test_jwt_token_claims(self, async_client: AsyncClient, verified_user_with_org: tuple):
        """Test that JWT token contains correct claims."""
        user, org = verified_user_with_org

        # Reset JWT handler to ensure it has correct expiration times
        import server.auth.jwt_handler

        server.auth.jwt_handler._jwt_handler = None

        response = await async_client.post(
            "/api/auth/login",
            json={"username": user.username, "password": "TestPassword123!"},
        )

        assert response.status_code == 200
        access_token = response.json()["access_token"]

        # Decode token to check claims
        jwt_handler = get_jwt_handler()
        payload = jwt_handler.decode_token(access_token)

        assert payload["sub"] == str(user.id)
        assert payload["email"] == user.email
        assert payload["username"] == user.username
        assert payload["type"] == "access"
        assert len(payload["organizations"]) == 1
        assert payload["organizations"][0]["id"] == str(org.id)
        assert payload["organizations"][0]["role"] == "owner"
