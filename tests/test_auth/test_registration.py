#!/usr/bin/env python3
"""
Tests for user registration and email verification.
"""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.models import EmailVerificationToken, Organization, User
from server.auth.service import AuthService

# Configure pytest-asyncio
pytestmark = pytest.mark.asyncio


class TestUserRegistration:
    """Test user registration functionality."""

    async def test_successful_registration(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test successful user registration."""
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "user" in data
        assert data["user"]["email"] == "test@example.com"
        assert data["user"]["username"] == "testuser"
        assert data["user"]["email_verified"] is False
        assert "message" in data

        # Verify user was created in database
        result = await db_session.execute(select(User).where(User.email == "test@example.com"))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.username == "testuser"
        assert user.email_verified is False

        # Verify email verification token was created
        result = await db_session.execute(
            select(EmailVerificationToken).where(EmailVerificationToken.user_id == user.id)
        )
        token = result.scalar_one_or_none()
        assert token is not None
        assert token.used_at is None

    async def test_duplicate_email(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test registration with duplicate email."""
        # Create first user
        auth_service = AuthService()
        user1, _ = await auth_service.register_user(
            db=db_session, email="existing@example.com", username="user1", password="SecurePass123!"
        )

        # Try to register with same email
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "existing@example.com",
                "username": "user2",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    async def test_duplicate_username(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test registration with duplicate username."""
        # Create first user
        auth_service = AuthService()
        user1, _ = await auth_service.register_user(
            db=db_session,
            email="user1@example.com",
            username="existinguser",
            password="SecurePass123!",
        )

        # Try to register with same username
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "user2@example.com",
                "username": "existinguser",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    async def test_invalid_email_format(self, async_client: AsyncClient):
        """Test registration with invalid email format."""
        response = await async_client.post(
            "/api/auth/register",
            json={"email": "invalid-email", "username": "testuser", "password": "SecurePass123!"},
        )

        assert response.status_code == 422
        assert "validation_errors" in response.json()

    async def test_invalid_username_format(self, async_client: AsyncClient):
        """Test registration with invalid username format."""
        # Too short
        response = await async_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "username": "ab", "password": "SecurePass123!"},
        )
        assert response.status_code == 422

        # Too long
        response = await async_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "username": "a" * 31, "password": "SecurePass123!"},
        )
        assert response.status_code == 422

        # Invalid characters
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "username": "user@name",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 422

    async def test_weak_password(self, async_client: AsyncClient):
        """Test registration with weak password."""
        # Too short
        response = await async_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "username": "testuser", "password": "weak"},
        )
        assert response.status_code == 422

        # No uppercase
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "weakpassword123!",
            },
        )
        assert response.status_code == 422

        # No number
        response = await async_client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "username": "testuser", "password": "WeakPassword!"},
        )
        assert response.status_code == 422

        # No special character
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "WeakPassword123",
            },
        )
        assert response.status_code == 422

    # async def test_rate_limiting(self, async_client: AsyncClient):
    #     """Test rate limiting on registration endpoint."""
    #     # Make 5 requests (limit)
    #     for i in range(5):
    #         response = await async_client.post("/api/auth/register", json={
    #             "email": f"test{i}@example.com",
    #             "username": f"testuser{i}",
    #             "password": "SecurePass123!"
    #         })
    #         assert response.status_code in [201, 400]  # Some might fail due to duplicates

    #     # 6th request should be rate limited
    #     response = await async_client.post("/api/auth/register", json={
    #         "email": "test6@example.com",
    #         "username": "testuser6",
    #         "password": "SecurePass123!"
    #     })
    #     assert response.status_code == 429


class TestEmailVerification:
    """Test email verification functionality."""

    async def test_successful_verification(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test successful email verification."""
        # Register user
        auth_service = AuthService()
        user, token = await auth_service.register_user(
            db=db_session,
            email="verify@example.com",
            username="verifyuser",
            password="SecurePass123!",
        )

        # Verify email
        response = await async_client.get(f"/api/auth/verify-email/{token.token}")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "successfully" in data["message"]
        assert data["user"]["email_verified"] is True

        # Check database
        await db_session.refresh(user)
        assert user.email_verified is True
        assert user.email_verified_at is not None

        # Check token is marked as used
        await db_session.refresh(token)
        assert token.used_at is not None

        # Check default organization was created
        result = await db_session.execute(
            select(Organization).where(Organization.owner_id == user.id)
        )
        org = result.scalar_one_or_none()
        assert org is not None
        assert org.name == f"{user.username}'s Organization"

    async def test_invalid_token(self, async_client: AsyncClient):
        """Test email verification with invalid token."""
        response = await async_client.get("/api/auth/verify-email/invalid-token")

        assert response.status_code == 400
        assert "Invalid verification token" in response.json()["detail"]

    async def test_expired_token(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test email verification with expired token."""
        # Create user with expired token
        from datetime import datetime, timedelta, timezone

        auth_service = AuthService()
        user = User(
            email="expired@example.com",
            username="expireduser",
            password_hash=auth_service.hash_password("SecurePass123!"),
        )
        db_session.add(user)
        await db_session.flush()  # Get user ID

        # Create expired token
        token = EmailVerificationToken(
            user_id=user.id,
            token="expired-token",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=25),  # Expired
        )
        db_session.add(token)
        await db_session.commit()

        # Try to verify
        response = await async_client.get("/api/auth/verify-email/expired-token")

        assert response.status_code == 400
        assert "expired" in response.json()["detail"]

    async def test_already_used_token(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test email verification with already used token."""
        # Register and verify user
        auth_service = AuthService()
        user, token = await auth_service.register_user(
            db=db_session, email="used@example.com", username="useduser", password="SecurePass123!"
        )

        # Verify once
        await auth_service.verify_email(db=db_session, token=token.token)

        # Try to verify again
        response = await async_client.get(f"/api/auth/verify-email/{token.token}")

        assert response.status_code == 400
        assert "already been used" in response.json()["detail"]

    async def test_already_verified_user(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test email verification for already verified user."""
        # Create already verified user
        auth_service = AuthService()
        user, token = await auth_service.register_user(
            db=db_session,
            email="verified@example.com",
            username="verifieduser",
            password="SecurePass123!",
        )

        # Manually mark as verified
        user.email_verified = True
        user.email_verified_at = datetime.now(timezone.utc)
        await db_session.commit()

        # Try to verify
        response = await async_client.get(f"/api/auth/verify-email/{token.token}")

        assert response.status_code == 400
        assert "already verified" in response.json()["detail"]
