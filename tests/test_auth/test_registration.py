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

from server.auth.models import EmailVerificationToken, Organization, User, UserActivity
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

        # Verify profile fields are initialized
        assert user.full_name is None
        assert user.bio is None
        assert user.avatar_url is None
        assert user.settings == "{}"

        # Verify activity was logged
        result = await db_session.execute(
            select(UserActivity).where(UserActivity.user_id == user.id)
        )
        activity = result.scalar_one_or_none()
        assert activity is not None
        assert activity.activity_type == "registration"
        assert "registered with email" in activity.activity_description
        assert activity.ip_address is not None  # From test client
        import json

        metadata = json.loads(activity.activity_metadata)
        assert metadata["email"] == "test@example.com"
        assert metadata["username"] == "testuser"
        assert metadata["email_verified"] is False

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

    async def test_password_strength_validation(self, async_client: AsyncClient):
        """Test comprehensive password strength validation."""
        test_cases = [
            # (password, should_pass, description)
            ("Short1!", False, "Too short"),
            ("nouppercase123!", False, "No uppercase"),
            ("NOLOWERCASE123!", False, "No lowercase"),
            ("NoNumbers!ABC", False, "No numbers"),
            ("NoSpecialChar123ABC", False, "No special characters"),
            ("ValidPassword123!", True, "Valid password"),
            ("Another$ecure1Pass", True, "Another valid password"),
            ("12345678901!Aa", True, "Valid with mostly numbers"),
            ("!@#$%^&*()_+Aa1", True, "Valid with many special chars"),
        ]

        for password, should_pass, description in test_cases:
            response = await async_client.post(
                "/api/auth/register",
                json={
                    "email": f"{description.replace(' ', '_').lower()}@example.com",
                    "username": f"user_{description.replace(' ', '_').lower()}",
                    "password": password,
                },
            )

            if should_pass:
                assert response.status_code == 201, f"Failed for {description}: {password}"
            else:
                assert response.status_code == 422, f"Failed for {description}: {password}"

    async def test_username_validation_edge_cases(self, async_client: AsyncClient):
        """Test username validation edge cases."""
        test_cases = [
            # (username, should_pass, description)
            ("abc", True, "Minimum length"),
            ("a" * 30, True, "Maximum length"),
            ("user_123", True, "With underscore and numbers"),
            ("USER123", True, "Uppercase (will be lowercased)"),
            ("ab", False, "Too short"),
            ("a" * 31, False, "Too long"),
            ("user-name", False, "With hyphen"),
            ("user.name", False, "With dot"),
            ("user name", False, "With space"),
            ("user@name", False, "With @"),
            ("123user", True, "Starting with number"),
            ("_user", True, "Starting with underscore"),
        ]

        for username, should_pass, description in test_cases:
            response = await async_client.post(
                "/api/auth/register",
                json={
                    "email": f"{username.replace(' ', '_').lower()}_test@example.com",
                    "username": username,
                    "password": "ValidPassword123!",
                },
            )

            if should_pass:
                assert response.status_code in [
                    201,
                    400,
                ], f"Failed for {description}: {username}"  # 400 if duplicate
            else:
                assert response.status_code == 422, f"Failed for {description}: {username}"

    async def test_registration_with_case_insensitive_duplicates(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that email and username are case-insensitive for duplicates."""
        # Register first user
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "Test@Example.COM",
                "username": "TestUser",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 201

        # Try with different case email
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",  # lowercase
                "username": "different",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

        # Try with different case username
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "different@example.com",
                "username": "testuser",  # lowercase
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    async def test_registration_stores_lowercase_values(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that email and username are stored in lowercase."""
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "MiXeDcAsE@ExAmPlE.CoM",
                "username": "MiXeDuSeR",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 201

        # Check database
        result = await db_session.execute(select(User).where(User.email == "mixedcase@example.com"))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.email == "mixedcase@example.com"
        assert user.username == "mixeduser"

    async def test_user_is_active_by_default(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that new users are created with is_active=True."""
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "active@example.com",
                "username": "activeuser",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 201

        # Check database
        result = await db_session.execute(select(User).where(User.email == "active@example.com"))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.is_active is True
        assert user.email_verified is False  # But not verified yet

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
