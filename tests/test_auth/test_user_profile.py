#!/usr/bin/env python3
"""
Tests for user profile management endpoints.
"""

import json
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.jwt_handler import get_jwt_handler
from server.auth.models import RefreshToken, TokenBlacklist, User, UserActivity
from server.auth.service import AuthService
from server.auth.utils import hash_password

# Configure pytest-asyncio
pytestmark = pytest.mark.asyncio


class TestUserProfile:
    """Test user profile endpoints."""

    @pytest_asyncio.fixture
    async def authenticated_user(self, db_session: AsyncSession):
        """Create and return an authenticated user with tokens."""
        auth_service = AuthService()
        
        # Create verified user
        user = User(
            email="profiletest@example.com",
            username="profileuser",
            password_hash=hash_password("TestPassword123!"),
            email_verified=True,
            email_verified_at=datetime.now(timezone.utc),
            full_name="Test User",
            bio="Test bio",
            avatar_url="https://example.com/avatar.jpg",
            settings=json.dumps({"theme": "dark", "newsletter": True})
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Generate tokens
        jwt_handler = get_jwt_handler()
        access_token = jwt_handler.create_access_token({
            "user_id": str(user.id),
            "email": user.email,
            "username": user.username,
            "email_verified": user.email_verified
        })
        
        return user, access_token
    
    async def test_get_profile_success(
        self, async_client: AsyncClient, authenticated_user
    ):
        """Test successful profile retrieval."""
        user, token = authenticated_user
        
        response = await async_client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(user.id)
        assert data["email"] == user.email
        assert data["username"] == user.username
        assert data["full_name"] == "Test User"
        assert data["bio"] == "Test bio"
        assert data["avatar_url"] == "https://example.com/avatar.jpg"
        assert data["email_verified"] is True
        assert data["settings"]["theme"] == "dark"
        assert data["settings"]["newsletter"] is True
    
    async def test_get_profile_unauthenticated(self, async_client: AsyncClient):
        """Test profile retrieval without authentication."""
        response = await async_client.get("/api/users/me")
        assert response.status_code == 403
        assert "Not authenticated" in response.json()["detail"]
    
    async def test_get_profile_unverified_email(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test profile retrieval with unverified email."""
        # Create unverified user
        auth_service = AuthService()
        user = User(
            email="unverified@example.com",
            username="unverifieduser",
            password_hash=hash_password("TestPassword123!"),
            email_verified=False
        )
        db_session.add(user)
        await db_session.commit()
        
        # Generate token
        jwt_handler = get_jwt_handler()
        access_token = jwt_handler.create_access_token({
            "user_id": str(user.id),
            "email": user.email,
            "username": user.username,
            "email_verified": False
        })
        
        response = await async_client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 403
        assert "Email not verified" in response.json()["detail"]
    
    async def test_update_profile_success(
        self, async_client: AsyncClient, authenticated_user, db_session: AsyncSession
    ):
        """Test successful profile update."""
        user, token = authenticated_user
        
        update_data = {
            "full_name": "Updated Name",
            "bio": "Updated bio text",
            "avatar_url": "https://example.com/new-avatar.jpg"
        }
        
        response = await async_client.put(
            "/api/users/me",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["bio"] == "Updated bio text"
        assert data["avatar_url"] == "https://example.com/new-avatar.jpg"
        
        # Verify in database
        await db_session.refresh(user)
        assert user.full_name == "Updated Name"
        assert user.bio == "Updated bio text"
        assert user.avatar_url == "https://example.com/new-avatar.jpg"
        
        # Check activity was logged
        result = await db_session.execute(
            select(UserActivity).where(
                UserActivity.user_id == user.id,
                UserActivity.activity_type == "profile_updated"
            )
        )
        activity = result.scalar_one_or_none()
        assert activity is not None
        assert "full_name, bio, avatar_url" in activity.activity_description
    
    async def test_update_profile_partial(
        self, async_client: AsyncClient, authenticated_user, db_session: AsyncSession
    ):
        """Test partial profile update."""
        user, token = authenticated_user
        
        response = await async_client.put(
            "/api/users/me",
            json={"bio": "Only bio updated"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["bio"] == "Only bio updated"
        assert data["full_name"] == "Test User"  # Unchanged
        assert data["avatar_url"] == "https://example.com/avatar.jpg"  # Unchanged
    
    async def test_update_profile_invalid_avatar_url(
        self, async_client: AsyncClient, authenticated_user
    ):
        """Test profile update with invalid avatar URL."""
        user, token = authenticated_user
        
        response = await async_client.put(
            "/api/users/me",
            json={"avatar_url": "not-a-url"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422
        assert "Avatar URL must be a valid HTTP/HTTPS URL" in str(response.json())
    
    async def test_update_profile_field_too_long(
        self, async_client: AsyncClient, authenticated_user
    ):
        """Test profile update with field exceeding max length."""
        user, token = authenticated_user
        
        response = await async_client.put(
            "/api/users/me",
            json={"bio": "x" * 501},  # Max is 500
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422
    
    async def test_change_password_success(
        self, async_client: AsyncClient, authenticated_user, db_session: AsyncSession
    ):
        """Test successful password change."""
        user, token = authenticated_user
        
        response = await async_client.put(
            "/api/users/me/password",
            json={
                "current_password": "TestPassword123!",
                "new_password": "NewSecurePass456!"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert "Password changed successfully" in response.json()["message"]
        
        # Verify password was changed
        await db_session.refresh(user)
        auth_service = AuthService()
        assert auth_service.verify_password("NewSecurePass456!", user.password_hash)
        assert not auth_service.verify_password("TestPassword123!", user.password_hash)
        
        # Check activity was logged
        result = await db_session.execute(
            select(UserActivity).where(
                UserActivity.user_id == user.id,
                UserActivity.activity_type == "password_changed"
            )
        )
        activity = result.scalar_one_or_none()
        assert activity is not None
    
    async def test_change_password_incorrect_current(
        self, async_client: AsyncClient, authenticated_user
    ):
        """Test password change with incorrect current password."""
        user, token = authenticated_user
        
        response = await async_client.put(
            "/api/users/me/password",
            json={
                "current_password": "WrongPassword123!",
                "new_password": "NewSecurePass456!"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        assert "Current password is incorrect" in response.json()["detail"]
    
    async def test_change_password_weak_new_password(
        self, async_client: AsyncClient, authenticated_user
    ):
        """Test password change with weak new password."""
        user, token = authenticated_user
        
        response = await async_client.put(
            "/api/users/me/password",
            json={
                "current_password": "TestPassword123!",
                "new_password": "weak"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422
        assert "validation_errors" in response.json()
    
    async def test_delete_account_success(
        self, async_client: AsyncClient, authenticated_user, db_session: AsyncSession
    ):
        """Test successful account deletion."""
        user, token = authenticated_user
        
        response = await async_client.delete(
            "/api/users/me",
            json={
                "password": "TestPassword123!",
                "confirmation": "DELETE MY ACCOUNT"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert "account has been deleted successfully" in response.json()["message"]
        
        # Verify account is soft deleted
        await db_session.refresh(user)
        assert user.is_active is False
        
        # Check activity was logged
        result = await db_session.execute(
            select(UserActivity).where(
                UserActivity.user_id == user.id,
                UserActivity.activity_type == "account_deleted"
            )
        )
        activity = result.scalar_one_or_none()
        assert activity is not None
    
    async def test_delete_account_wrong_password(
        self, async_client: AsyncClient, authenticated_user
    ):
        """Test account deletion with wrong password."""
        user, token = authenticated_user
        
        response = await async_client.delete(
            "/api/users/me",
            json={
                "password": "WrongPassword123!",
                "confirmation": "DELETE MY ACCOUNT"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        assert "Password is incorrect" in response.json()["detail"]
    
    async def test_delete_account_wrong_confirmation(
        self, async_client: AsyncClient, authenticated_user
    ):
        """Test account deletion with wrong confirmation text."""
        user, token = authenticated_user
        
        response = await async_client.delete(
            "/api/users/me",
            json={
                "password": "TestPassword123!",
                "confirmation": "delete my account"  # Wrong case
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422
    
    async def test_get_activity_log(
        self, async_client: AsyncClient, authenticated_user, db_session: AsyncSession
    ):
        """Test getting user activity log."""
        user, token = authenticated_user
        
        # Create some activities
        activities = [
            UserActivity(
                user_id=user.id,
                activity_type="login",
                activity_description="User logged in",
                ip_address="127.0.0.1",
                activity_metadata=json.dumps({"method": "password"})
            ),
            UserActivity(
                user_id=user.id,
                activity_type="profile_updated",
                activity_description="Updated profile",
                ip_address="127.0.0.1",
                activity_metadata=json.dumps({"fields": ["bio"]})
            )
        ]
        db_session.add_all(activities)
        await db_session.commit()
        
        response = await async_client.get(
            "/api/users/me/activity",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["activity_type"] == "profile_updated"  # Most recent first
        assert data[1]["activity_type"] == "login"
    
    async def test_get_activity_log_pagination(
        self, async_client: AsyncClient, authenticated_user, db_session: AsyncSession
    ):
        """Test activity log pagination."""
        user, token = authenticated_user
        
        # Create 25 activities
        for i in range(25):
            activity = UserActivity(
                user_id=user.id,
                activity_type="test_activity",
                activity_description=f"Test activity {i}",
                activity_metadata=json.dumps({"index": i})
            )
            db_session.add(activity)
        await db_session.commit()
        
        # Get first page
        response = await async_client.get(
            "/api/users/me/activity?page=1&limit=10",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10
        
        # Get second page
        response = await async_client.get(
            "/api/users/me/activity?page=2&limit=10",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10
    
    async def test_get_settings(
        self, async_client: AsyncClient, authenticated_user
    ):
        """Test getting user settings."""
        user, token = authenticated_user
        
        response = await async_client.get(
            "/api/users/me/settings",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "dark"  # From fixture
        assert data["newsletter"] is True  # From fixture
        assert data["email_notifications"] is True  # Default
        assert data["session_timeout"] == 30  # Default
    
    async def test_update_settings(
        self, async_client: AsyncClient, authenticated_user, db_session: AsyncSession
    ):
        """Test updating user settings."""
        user, token = authenticated_user
        
        response = await async_client.put(
            "/api/users/me/settings",
            json={
                "theme": "light",
                "email_notifications": False,
                "session_timeout": 60
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "light"
        assert data["email_notifications"] is False
        assert data["session_timeout"] == 60
        assert data["newsletter"] is True  # Unchanged
        
        # Verify in database
        await db_session.refresh(user)
        settings = json.loads(user.settings)
        assert settings["theme"] == "light"
        assert settings["email_notifications"] is False
        
        # Check activity was logged
        result = await db_session.execute(
            select(UserActivity).where(
                UserActivity.user_id == user.id,
                UserActivity.activity_type == "settings_updated"
            )
        )
        activity = result.scalar_one_or_none()
        assert activity is not None
    
    async def test_update_settings_invalid_theme(
        self, async_client: AsyncClient, authenticated_user
    ):
        """Test updating settings with invalid theme."""
        user, token = authenticated_user
        
        response = await async_client.put(
            "/api/users/me/settings",
            json={"theme": "invalid"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422
    
    async def test_update_settings_invalid_timeout(
        self, async_client: AsyncClient, authenticated_user
    ):
        """Test updating settings with invalid session timeout."""
        user, token = authenticated_user
        
        response = await async_client.put(
            "/api/users/me/settings",
            json={"session_timeout": 2000},  # Max is 1440
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422
    
    async def test_token_invalidation_after_password_change(
        self, async_client: AsyncClient, authenticated_user, db_session: AsyncSession
    ):
        """Test that tokens are invalidated after password change."""
        user, token = authenticated_user
        auth_service = AuthService()
        
        # Create a refresh token
        refresh_token = RefreshToken(
            user_id=user.id,
            token="test_refresh_token",
            expires_at=datetime.now(timezone.utc),
            is_active=True
        )
        db_session.add(refresh_token)
        await db_session.commit()
        
        # Change password
        response = await async_client.put(
            "/api/users/me/password",
            json={
                "current_password": "TestPassword123!",
                "new_password": "NewSecurePass456!"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        
        # Verify refresh token is invalidated
        await db_session.refresh(refresh_token)
        assert refresh_token.is_active is False
        
        # Verify token is blacklisted
        result = await db_session.execute(
            select(TokenBlacklist).where(
                TokenBlacklist.token == "test_refresh_token"
            )
        )
        blacklist_entry = result.scalar_one_or_none()
        assert blacklist_entry is not None
        assert blacklist_entry.reason == "password_changed"