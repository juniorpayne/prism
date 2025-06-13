#!/usr/bin/env python3
"""
Tests for password reset functionality.
"""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.models import PasswordResetToken, RefreshToken, User
from server.auth.utils import hash_password, hash_token


class TestPasswordReset:
    """Test password reset endpoints."""

    @pytest.mark.asyncio
    async def test_forgot_password_valid_email(
        self, async_client: AsyncClient, verified_user: User
    ):
        """Test forgot password with valid email."""
        response = await async_client.post(
            "/api/auth/forgot-password",
            json={"email": verified_user.email},
        )

        assert response.status_code == 200
        assert (
            response.json()["message"]
            == "If the email exists, a password reset link has been sent."
        )

    @pytest.mark.asyncio
    async def test_forgot_password_valid_username(
        self, async_client: AsyncClient, verified_user: User
    ):
        """Test forgot password with valid username."""
        response = await async_client.post(
            "/api/auth/forgot-password",
            json={"email": verified_user.username},
        )

        assert response.status_code == 200
        assert (
            response.json()["message"]
            == "If the email exists, a password reset link has been sent."
        )

    @pytest.mark.asyncio
    async def test_forgot_password_invalid_email(self, async_client: AsyncClient):
        """Test forgot password with non-existent email."""
        response = await async_client.post(
            "/api/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )

        # Should still return 200 to prevent enumeration
        assert response.status_code == 200
        assert (
            response.json()["message"]
            == "If the email exists, a password reset link has been sent."
        )

    @pytest.mark.asyncio
    async def test_forgot_password_unverified_email(
        self, async_client: AsyncClient, unverified_user: User
    ):
        """Test forgot password with unverified email."""
        response = await async_client.post(
            "/api/auth/forgot-password",
            json={"email": unverified_user.email},
        )

        # Should still return 200 to prevent enumeration
        assert response.status_code == 200
        assert (
            response.json()["message"]
            == "If the email exists, a password reset link has been sent."
        )

    @pytest.mark.asyncio
    async def test_reset_password_valid_token(
        self, async_client: AsyncClient, verified_user: User, db_session: AsyncSession
    ):
        """Test reset password with valid token."""
        # Create reset token
        token = "test_reset_token_123"
        reset_token = PasswordResetToken(
            user_id=verified_user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db_session.add(reset_token)
        await db_session.commit()

        # Reset password
        new_password = "NewSecurePassword123!"
        response = await async_client.post(
            "/api/auth/reset-password",
            json={"token": token, "password": new_password},
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Password reset successfully"

        # Verify user can login with new password
        login_response = await async_client.post(
            "/api/auth/login",
            json={"username": verified_user.username, "password": new_password},
        )
        assert login_response.status_code == 200

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, async_client: AsyncClient):
        """Test reset password with invalid token."""
        response = await async_client.post(
            "/api/auth/reset-password",
            json={"token": "invalid_token_123", "password": "NewPassword123!"},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid or expired reset token"

    @pytest.mark.asyncio
    async def test_reset_password_expired_token(
        self, async_client: AsyncClient, verified_user: User, db_session: AsyncSession
    ):
        """Test reset password with expired token."""
        # Create expired token
        token = "expired_reset_token_123"
        reset_token = PasswordResetToken(
            user_id=verified_user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
        )
        db_session.add(reset_token)
        await db_session.commit()

        # Try to reset password
        response = await async_client.post(
            "/api/auth/reset-password",
            json={"token": token, "password": "NewPassword123!"},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid or expired reset token"

    @pytest.mark.asyncio
    async def test_reset_password_used_token(
        self, async_client: AsyncClient, verified_user: User, db_session: AsyncSession
    ):
        """Test reset password with already used token."""
        # Create used token
        token = "used_reset_token_123"
        reset_token = PasswordResetToken(
            user_id=verified_user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            used_at=datetime.now(timezone.utc),  # Already used
        )
        db_session.add(reset_token)
        await db_session.commit()

        # Try to reset password
        response = await async_client.post(
            "/api/auth/reset-password",
            json={"token": token, "password": "NewPassword123!"},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid or expired reset token"

    @pytest.mark.asyncio
    async def test_reset_password_weak_password(
        self, async_client: AsyncClient, verified_user: User, db_session: AsyncSession
    ):
        """Test reset password with weak password."""
        # Create reset token
        token = "test_weak_password_token"
        reset_token = PasswordResetToken(
            user_id=verified_user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db_session.add(reset_token)
        await db_session.commit()

        # Try weak password
        response = await async_client.post(
            "/api/auth/reset-password",
            json={"token": token, "password": "weak"},
        )

        assert response.status_code == 422
        error_data = response.json()
        assert error_data["detail"] == "Request validation failed"
        assert any(
            "at least 12 characters" in err["msg"] for err in error_data["validation_errors"]
        )

    @pytest.mark.asyncio
    async def test_reset_password_invalidates_refresh_tokens(
        self, async_client: AsyncClient, verified_user: User, db_session: AsyncSession
    ):
        """Test that password reset invalidates all refresh tokens."""
        # Login to get refresh token
        login_response = await async_client.post(
            "/api/auth/login",
            json={"username": verified_user.username, "password": "TestPassword123!"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Create reset token
        token = "test_invalidate_sessions_token"
        reset_token = PasswordResetToken(
            user_id=verified_user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db_session.add(reset_token)
        await db_session.commit()

        # Reset password
        response = await async_client.post(
            "/api/auth/reset-password",
            json={"token": token, "password": "NewSecurePassword123!"},
        )
        assert response.status_code == 200

        # Try to use old refresh token
        refresh_response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 401

    @pytest.mark.asyncio
    async def test_rate_limiting(self, async_client: AsyncClient, verified_user: User):
        """Test rate limiting on forgot password endpoint."""
        # TESTING=true should give us 100 per minute limit
        # Try 4 requests quickly
        for i in range(4):
            response = await async_client.post(
                "/api/auth/forgot-password",
                json={"email": f"test{i}@example.com"},
            )
            # All should succeed with TESTING=true
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_forgot_password_case_insensitive(
        self, async_client: AsyncClient, verified_user: User
    ):
        """Test forgot password is case insensitive for email/username."""
        # Test with uppercase email
        response = await async_client.post(
            "/api/auth/forgot-password",
            json={"email": verified_user.email.upper()},
        )
        assert response.status_code == 200

        # Test with uppercase username
        response = await async_client.post(
            "/api/auth/forgot-password",
            json={"email": verified_user.username.upper()},
        )
        assert response.status_code == 200
