"""Test cases for API token revocation endpoints."""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4
import json

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from server.api.routes.tokens import revoke_token, revoke_all_tokens
from server.auth.models import APIToken, User, UserActivity


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    user.username = "testuser"
    user.email_verified = True
    return user


@pytest.fixture
def mock_token(mock_user):
    """Create a mock API token."""
    token = MagicMock(spec=APIToken)
    token.id = uuid4()
    token.user_id = mock_user.id
    token.name = "Test Token"
    token.is_active = True
    token.revoked_at = None
    token.revoked_by = None
    return token


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock(spec=AsyncSession)
    return db


class TestRevokeTokenEndpoint:
    """Test the DELETE /api/v1/tokens/{token_id} endpoint."""
    
    @pytest.mark.asyncio
    async def test_revoke_token_success(self, mock_user, mock_token, mock_db):
        """Test successful token revocation."""
        # Setup mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_token
        mock_db.execute.return_value = mock_result
        
        # Call the endpoint function directly
        result = await revoke_token(
            token_id=str(mock_token.id),
            current_user=mock_user,
            db=mock_db
        )
        
        # Verify the token was revoked
        assert mock_token.is_active is False
        assert mock_token.revoked_at is not None
        assert mock_token.revoked_by == mock_user.id
        
        # Verify response
        assert result["message"] == "Token revoked successfully"
        assert result["token_id"] == str(mock_token.id)
        assert "revoked_at" in result
        
        # Verify activity was logged
        mock_db.add.assert_called_once()
        activity = mock_db.add.call_args[0][0]
        assert isinstance(activity, UserActivity)
        assert activity.user_id == mock_user.id
        assert activity.activity_type == "token_revoked"
        
        # Verify commit was called
        mock_db.commit.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_revoke_token_invalid_uuid(self, mock_user, mock_db):
        """Test revoking token with invalid UUID format."""
        with pytest.raises(HTTPException) as exc_info:
            await revoke_token(
                token_id="invalid-uuid",
                current_user=mock_user,
                db=mock_db
            )
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Invalid token ID format"
        
    @pytest.mark.asyncio
    async def test_revoke_token_not_found(self, mock_user, mock_db):
        """Test revoking non-existent token."""
        # Setup mock query result with no token
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await revoke_token(
                token_id=str(uuid4()),
                current_user=mock_user,
                db=mock_db
            )
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Token not found"
        
    @pytest.mark.asyncio
    async def test_revoke_already_revoked_token(self, mock_user, mock_token, mock_db):
        """Test revoking an already revoked token."""
        # Setup token as already revoked
        mock_token.is_active = False
        
        # Setup mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_token
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await revoke_token(
                token_id=str(mock_token.id),
                current_user=mock_user,
                db=mock_db
            )
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Token is already revoked"


class TestRevokeAllTokensEndpoint:
    """Test the POST /api/v1/tokens/revoke-all endpoint."""
    
    @pytest.mark.asyncio
    async def test_revoke_all_tokens_success(self, mock_user, mock_db):
        """Test successful bulk token revocation."""
        # Create mock tokens
        mock_tokens = []
        for i in range(3):
            token = MagicMock(spec=APIToken)
            token.id = uuid4()
            token.user_id = mock_user.id
            token.name = f"Token {i}"
            token.is_active = True
            mock_tokens.append(token)
        
        # Setup mock query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_tokens
        mock_db.execute.return_value = mock_result
        
        # Mock rate limit check
        with patch('server.api.routes.tokens.check_rate_limit', return_value=True):
            result = await revoke_all_tokens(
                current_user=mock_user,
                db=mock_db
            )
        
        # Verify all tokens were revoked
        for token in mock_tokens:
            assert token.is_active is False
            assert token.revoked_at is not None
            assert token.revoked_by == mock_user.id
        
        # Verify response
        assert result["message"] == "Revoked 3 tokens"
        assert result["revoked_count"] == 3
        
        # Verify activity was logged
        mock_db.add.assert_called_once()
        activity = mock_db.add.call_args[0][0]
        assert isinstance(activity, UserActivity)
        assert activity.user_id == mock_user.id
        assert activity.activity_type == "all_tokens_revoked"
        
        # Verify commit was called
        mock_db.commit.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_revoke_all_tokens_rate_limited(self, mock_user, mock_db):
        """Test rate limiting on bulk revocation."""
        # Mock rate limit check to fail
        with patch('server.api.routes.tokens.check_rate_limit', return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await revoke_all_tokens(
                    current_user=mock_user,
                    db=mock_db
                )
        
        assert exc_info.value.status_code == 429
        assert "once per hour" in exc_info.value.detail
        
    @pytest.mark.asyncio
    async def test_revoke_all_no_tokens(self, mock_user, mock_db):
        """Test bulk revocation when user has no tokens."""
        # Setup mock query result with no tokens
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        # Mock rate limit check
        with patch('server.api.routes.tokens.check_rate_limit', return_value=True):
            result = await revoke_all_tokens(
                current_user=mock_user,
                db=mock_db
            )
        
        # Verify response
        assert result["message"] == "Revoked 0 tokens"
        assert result["revoked_count"] == 0
        
        # Verify no activity was logged (since no tokens were revoked)
        mock_db.add.assert_not_called()
        
        # Verify commit was still called
        mock_db.commit.assert_called_once()