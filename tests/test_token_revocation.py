"""Test cases for API token revocation functionality."""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4, UUID
from unittest.mock import Mock, patch, AsyncMock
import json
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.models import APIToken, User, UserActivity
from server.database.connection import get_async_db


@pytest.fixture
def test_user():
    """Create a test user."""
    return User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        password_hash="hashed",
        email_verified=True,
        is_active=True
    )


@pytest.fixture
def test_token(test_user):
    """Create a test API token."""
    return APIToken(
        id=uuid4(),
        user_id=test_user.id,
        name="Test Token",
        token_hash=APIToken.hash_token("test-token-123"),
        is_active=True
    )


class TestTokenRevocation:
    """Test token revocation endpoints."""
    
    @pytest.mark.asyncio
    async def test_revoke_token_success(self, client: AsyncClient, test_user: User, db: AsyncSession):
        """Test successful token revocation."""
        # Create a test token
        token = APIToken(
            user_id=test_user.id,
            name="Test Token",
            token_hash=APIToken.hash_token("test-token-123"),
            is_active=True
        )
        db.add(token)
        await db.commit()
        
        # Revoke the token
        response = await authenticated_client.delete(f"/api/v1/tokens/{token.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Token revoked successfully"
        assert data["token_id"] == str(token.id)
        assert "revoked_at" in data
        
        # Verify token is revoked in database
        db_session.refresh(token)
        assert not token.is_active
        assert token.revoked_at is not None
        assert token.revoked_by == test_user.id
        
    @pytest.mark.asyncio
    async def test_revoke_token_not_found(self, authenticated_client: TestClient):
        """Test revoking non-existent token returns 404."""
        fake_id = str(uuid4())
        response = await authenticated_client.delete(f"/api/v1/tokens/{fake_id}")
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Token not found"
        
    @pytest.mark.asyncio
    async def test_revoke_token_invalid_uuid(self, authenticated_client: TestClient):
        """Test revoking token with invalid UUID format."""
        response = await authenticated_client.delete("/api/v1/tokens/invalid-uuid")
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid token ID format"
        
    @pytest.mark.asyncio
    async def test_cannot_revoke_already_revoked(self, authenticated_client: TestClient, test_user: User, db_session):
        """Test cannot revoke an already revoked token."""
        # Create a revoked token
        token = APIToken(
            user_id=test_user.id,
            name="Already Revoked",
            token_hash=APIToken.hash_token("revoked-token"),
            is_active=False,
            revoked_at=datetime.now(timezone.utc),
            revoked_by=test_user.id
        )
        db_session.add(token)
        db_session.commit()
        
        # Try to revoke again
        response = await authenticated_client.delete(f"/api/v1/tokens/{token.id}")
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Token is already revoked"
        
    @pytest.mark.asyncio
    async def test_cannot_revoke_other_users_token(self, authenticated_client: TestClient, test_user: User, db_session):
        """Test user cannot revoke another user's token."""
        # Create another user and their token
        other_user = create_test_user("other@example.com", "otheruser")
        db_session.add(other_user)
        
        token = APIToken(
            user_id=other_user.id,
            name="Other User Token",
            token_hash=APIToken.hash_token("other-token"),
            is_active=True
        )
        db_session.add(token)
        db_session.commit()
        
        # Try to revoke other user's token
        response = await authenticated_client.delete(f"/api/v1/tokens/{token.id}")
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Token not found"
        
    @pytest.mark.asyncio
    async def test_revoke_all_tokens(self, authenticated_client: TestClient, test_user: User, db_session):
        """Test bulk revocation of all user's tokens."""
        # Create multiple tokens
        tokens = []
        for i in range(3):
            token = APIToken(
                user_id=test_user.id,
                name=f"Token {i}",
                token_hash=APIToken.hash_token(f"token-{i}"),
                is_active=True
            )
            db_session.add(token)
            tokens.append(token)
        
        # Add one already revoked token (should not be counted)
        revoked_token = APIToken(
            user_id=test_user.id,
            name="Already Revoked",
            token_hash=APIToken.hash_token("revoked"),
            is_active=False
        )
        db_session.add(revoked_token)
        db_session.commit()
        
        # Revoke all tokens
        response = await authenticated_client.post("/api/v1/tokens/revoke-all")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Revoked 3 tokens"
        assert data["revoked_count"] == 3
        
        # Verify all active tokens are revoked
        for token in tokens:
            db_session.refresh(token)
            assert not token.is_active
            assert token.revoked_at is not None
            assert token.revoked_by == test_user.id
            
    @pytest.mark.asyncio
    async def test_revoke_all_rate_limiting(self, authenticated_client: TestClient):
        """Test rate limiting on bulk revocation endpoint."""
        # Mock rate limit check to return False
        with patch('server.api.routes.tokens.check_rate_limit', return_value=False):
            response = await authenticated_client.post("/api/v1/tokens/revoke-all")
            
            assert response.status_code == 429
            assert "once per hour" in response.json()["detail"]
            
    @pytest.mark.asyncio
    async def test_token_validation_after_revocation(self, test_user: User, db_session):
        """Test that revoked tokens fail validation."""
        # Create an active token
        token = APIToken(
            user_id=test_user.id,
            name="Test Token",
            token_hash=APIToken.hash_token("test-token"),
            is_active=True
        )
        db_session.add(token)
        db_session.commit()
        
        # Token should be valid initially
        assert token.is_valid()
        
        # Revoke the token
        token.is_active = False
        token.revoked_at = datetime.now(timezone.utc)
        db_session.commit()
        
        # Token should no longer be valid
        assert not token.is_valid()
        
    @pytest.mark.asyncio
    async def test_revocation_creates_audit_log(self, authenticated_client: TestClient, test_user: User, db_session):
        """Test that token revocation creates an audit log entry."""
        # Create a token
        token = APIToken(
            user_id=test_user.id,
            name="Audit Test Token",
            token_hash=APIToken.hash_token("audit-token"),
            is_active=True
        )
        db_session.add(token)
        db_session.commit()
        
        # Revoke the token
        response = await authenticated_client.delete(f"/api/v1/tokens/{token.id}")
        assert response.status_code == 200
        
        # Check for audit log entry
        activity = db_session.query(UserActivity).filter(
            UserActivity.user_id == test_user.id,
            UserActivity.activity_type == "token_revoked"
        ).first()
        
        assert activity is not None
        assert activity.activity_description == f"Revoked API token: {token.name}"
        
        # Verify metadata contains token info
        metadata = json.loads(activity.activity_metadata)
        assert metadata["token_id"] == str(token.id)
        assert metadata["token_name"] == token.name
        
    @pytest.mark.asyncio
    async def test_bulk_revocation_audit_log(self, authenticated_client: TestClient, test_user: User, db_session):
        """Test that bulk revocation creates appropriate audit log."""
        # Create tokens
        for i in range(2):
            token = APIToken(
                user_id=test_user.id,
                name=f"Token {i}",
                token_hash=APIToken.hash_token(f"token-{i}"),
                is_active=True
            )
            db_session.add(token)
        db_session.commit()
        
        # Mock rate limit to allow request
        with patch('server.api.routes.tokens.check_rate_limit', return_value=True):
            response = await authenticated_client.post("/api/v1/tokens/revoke-all")
            assert response.status_code == 200
        
        # Check audit log
        activity = db_session.query(UserActivity).filter(
            UserActivity.user_id == test_user.id,
            UserActivity.activity_type == "all_tokens_revoked"
        ).first()
        
        assert activity is not None
        assert "Revoked all 2 API tokens" in activity.activity_description
        
        metadata = json.loads(activity.activity_metadata)
        assert metadata["revoked_count"] == 2
        
    @pytest.mark.asyncio
    async def test_email_notification_on_revocation(self, authenticated_client: TestClient, test_user: User, db_session):
        """Test that email notification is sent when token is revoked."""
        # Set user as email verified
        test_user.email_verified = True
        db_session.commit()
        
        # Create a token
        token = APIToken(
            user_id=test_user.id,
            name="Email Test Token",
            token_hash=APIToken.hash_token("email-token"),
            is_active=True
        )
        db_session.add(token)
        db_session.commit()
        
        # Mock email service
        with patch('server.api.routes.tokens.send_token_revoked_email', new_callable=AsyncMock) as mock_email:
            response = await authenticated_client.delete(f"/api/v1/tokens/{token.id}")
            assert response.status_code == 200
            
            # Verify email was called
            mock_email.assert_called_once_with(test_user, token)
            
    @pytest.mark.asyncio
    async def test_no_email_if_not_verified(self, authenticated_client: TestClient, test_user: User, db_session):
        """Test that no email is sent if user email is not verified."""
        # Ensure user email is not verified
        test_user.email_verified = False
        db_session.commit()
        
        # Create a token
        token = APIToken(
            user_id=test_user.id,
            name="No Email Token",
            token_hash=APIToken.hash_token("no-email-token"),
            is_active=True
        )
        db_session.add(token)
        db_session.commit()
        
        # Mock email service
        with patch('server.api.routes.tokens.send_token_revoked_email', new_callable=AsyncMock) as mock_email:
            response = await authenticated_client.delete(f"/api/v1/tokens/{token.id}")
            assert response.status_code == 200
            
            # Verify email was NOT called
            mock_email.assert_not_called()


class TestTokenModelRevocation:
    """Test APIToken model revocation methods."""
    
    def test_is_valid_with_revoked_at(self, db_session):
        """Test that tokens with revoked_at timestamp are invalid."""
        token = APIToken(
            user_id=uuid4(),
            name="Test Token",
            token_hash=APIToken.hash_token("test"),
            is_active=True,  # Still marked active
            revoked_at=datetime.now(timezone.utc)  # But has revocation timestamp
        )
        
        assert not token.is_valid()
        
    def test_is_valid_checks_multiple_conditions(self, db_session):
        """Test is_valid checks all conditions."""
        base_time = datetime.now(timezone.utc)
        
        # Active, not revoked, not expired - VALID
        token1 = APIToken(
            user_id=uuid4(),
            name="Valid Token",
            token_hash=APIToken.hash_token("valid"),
            is_active=True,
            revoked_at=None,
            expires_at=base_time + timedelta(days=1)
        )
        assert token1.is_valid()
        
        # Not active - INVALID
        token2 = APIToken(
            user_id=uuid4(),
            name="Inactive Token",
            token_hash=APIToken.hash_token("inactive"),
            is_active=False
        )
        assert not token2.is_valid()
        
        # Revoked - INVALID
        token3 = APIToken(
            user_id=uuid4(),
            name="Revoked Token",
            token_hash=APIToken.hash_token("revoked"),
            is_active=True,
            revoked_at=base_time
        )
        assert not token3.is_valid()
        
        # Expired - INVALID
        token4 = APIToken(
            user_id=uuid4(),
            name="Expired Token",
            token_hash=APIToken.hash_token("expired"),
            is_active=True,
            expires_at=base_time - timedelta(days=1)
        )
        assert not token4.is_valid()