"""Unit tests for API token revocation functionality in the model."""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from server.auth.models import APIToken


class TestAPITokenRevocation:
    """Test APIToken model revocation methods."""
    
    def test_token_is_valid_when_active(self):
        """Test that active tokens are valid."""
        token = APIToken(
            user_id=uuid4(),
            name="Test Token",
            token_hash=APIToken.hash_token("test"),
            is_active=True,
            revoked_at=None,
            expires_at=None
        )
        
        assert token.is_valid() is True
        
    def test_token_invalid_when_revoked_at_set(self):
        """Test that tokens with revoked_at timestamp are invalid."""
        token = APIToken(
            user_id=uuid4(),
            name="Test Token",
            token_hash=APIToken.hash_token("test"),
            is_active=True,  # Still marked active
            revoked_at=datetime.now(timezone.utc),  # But has revocation timestamp
            expires_at=None
        )
        
        assert token.is_valid() is False
        
    def test_token_invalid_when_inactive(self):
        """Test that inactive tokens are invalid."""
        token = APIToken(
            user_id=uuid4(),
            name="Test Token",
            token_hash=APIToken.hash_token("test"),
            is_active=False,
            revoked_at=None,
            expires_at=None
        )
        
        assert token.is_valid() is False
        
    def test_token_invalid_when_expired(self):
        """Test that expired tokens are invalid."""
        token = APIToken(
            user_id=uuid4(),
            name="Test Token",
            token_hash=APIToken.hash_token("test"),
            is_active=True,
            revoked_at=None,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1)  # Expired yesterday
        )
        
        assert token.is_valid() is False
        
    def test_token_valid_when_not_yet_expired(self):
        """Test that tokens not yet expired are valid."""
        token = APIToken(
            user_id=uuid4(),
            name="Test Token",
            token_hash=APIToken.hash_token("test"),
            is_active=True,
            revoked_at=None,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1)  # Expires tomorrow
        )
        
        assert token.is_valid() is True
        
    def test_is_valid_checks_all_conditions(self):
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
        assert token1.is_valid() is True
        
        # Not active - INVALID
        token2 = APIToken(
            user_id=uuid4(),
            name="Inactive Token",
            token_hash=APIToken.hash_token("inactive"),
            is_active=False,
            revoked_at=None,
            expires_at=None
        )
        assert token2.is_valid() is False
        
        # Revoked - INVALID
        token3 = APIToken(
            user_id=uuid4(),
            name="Revoked Token",
            token_hash=APIToken.hash_token("revoked"),
            is_active=True,
            revoked_at=base_time,
            expires_at=None
        )
        assert token3.is_valid() is False
        
        # Expired - INVALID
        token4 = APIToken(
            user_id=uuid4(),
            name="Expired Token",
            token_hash=APIToken.hash_token("expired"),
            is_active=True,
            revoked_at=None,
            expires_at=base_time - timedelta(days=1)
        )
        assert token4.is_valid() is False