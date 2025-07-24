#!/usr/bin/env python3
"""
Tests for APIToken model (SCRUM-136)
Test-driven development for TCP client authentication tokens.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from server.auth.models import Base, User, APIToken


@pytest.fixture
def test_db():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def test_user(test_db):
    """Create a test user."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        password_hash="hashed_password",
        email_verified=True,
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    return user


class TestAPITokenModel:
    """Test cases for APIToken model."""
    
    def test_create_api_token(self, test_db, test_user):
        """Test creating a new API token."""
        # Create token
        token = APIToken(
            user_id=test_user.id,
            name="My TCP Client",
            token_hash=APIToken.hash_token("test-token-123")
        )
        
        # Save to database
        test_db.add(token)
        test_db.commit()
        
        # Verify token was created
        assert token.id is not None
        assert token.user_id == test_user.id
        assert token.name == "My TCP Client"
        assert token.token_hash != "test-token-123"  # Should be hashed
        assert token.is_active is True
        assert token.expires_at is None
        assert token.created_at is not None
        assert token.updated_at is not None
    
    def test_token_hash_verification(self, test_db, test_user):
        """Test token hashing and verification."""
        plain_token = "my-secret-token-123"
        
        # Create token with hashed value
        token = APIToken(
            user_id=test_user.id,
            name="Test Token",
            token_hash=APIToken.hash_token(plain_token)
        )
        
        # Verify correct token
        assert token.verify_token(plain_token) is True
        
        # Verify incorrect token
        assert token.verify_token("wrong-token") is False
        
        # Verify hash is not reversible
        assert token.token_hash != plain_token
        assert len(token.token_hash) > len(plain_token)
    
    def test_token_expiration(self, test_db, test_user):
        """Test token expiration logic."""
        # Create non-expiring token
        token1 = APIToken(
            user_id=test_user.id,
            name="Non-expiring Token",
            token_hash=APIToken.hash_token("token1"),
            expires_at=None,
            is_active=True  # Explicitly set for test
        )
        assert token1.is_valid() is True
        
        # Create expired token
        token2 = APIToken(
            user_id=test_user.id,
            name="Expired Token",
            token_hash=APIToken.hash_token("token2"),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            is_active=True  # Explicitly set for test
        )
        assert token2.is_valid() is False
        
        # Create future expiring token
        token3 = APIToken(
            user_id=test_user.id,
            name="Future Token",
            token_hash=APIToken.hash_token("token3"),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            is_active=True  # Explicitly set for test
        )
        assert token3.is_valid() is True
    
    def test_token_deactivation(self, test_db, test_user):
        """Test token deactivation."""
        # Create active token
        token = APIToken(
            user_id=test_user.id,
            name="Active Token",
            token_hash=APIToken.hash_token("active-token"),
            is_active=True
        )
        assert token.is_valid() is True
        
        # Deactivate token
        token.is_active = False
        assert token.is_valid() is False
    
    def test_token_usage_tracking(self, test_db, test_user):
        """Test token usage tracking fields."""
        token = APIToken(
            user_id=test_user.id,
            name="Tracked Token",
            token_hash=APIToken.hash_token("tracked-token")
        )
        
        # Initially no usage
        assert token.last_used_at is None
        assert token.last_used_ip is None
        
        # Update usage
        token.last_used_at = datetime.now(timezone.utc)
        token.last_used_ip = "192.168.1.100"
        
        test_db.add(token)
        test_db.commit()
        
        # Verify updates
        assert token.last_used_at is not None
        assert token.last_used_ip == "192.168.1.100"
    
    def test_token_user_relationship(self, test_db, test_user):
        """Test relationship between token and user."""
        # Create tokens
        token1 = APIToken(
            user_id=test_user.id,
            name="Token 1",
            token_hash=APIToken.hash_token("token1")
        )
        token2 = APIToken(
            user_id=test_user.id,
            name="Token 2",
            token_hash=APIToken.hash_token("token2")
        )
        
        test_db.add(token1)
        test_db.add(token2)
        test_db.commit()
        
        # Refresh user to load relationships
        test_db.refresh(test_user)
        
        # Verify user has tokens
        assert len(test_user.tcp_tokens) == 2
        assert token1 in test_user.tcp_tokens
        assert token2 in test_user.tcp_tokens
        
        # Verify tokens have user reference
        assert token1.user == test_user
        assert token2.user == test_user
    
    def test_token_constraints(self, test_db, test_user):
        """Test database constraints."""
        # Test unique token_hash constraint
        token1 = APIToken(
            user_id=test_user.id,
            name="Token 1",
            token_hash="same_hash"
        )
        test_db.add(token1)
        test_db.commit()
        
        # Try to create another token with same hash
        token2 = APIToken(
            user_id=test_user.id,
            name="Token 2",
            token_hash="same_hash"
        )
        test_db.add(token2)
        
        with pytest.raises(Exception):  # Should raise IntegrityError
            test_db.commit()
    
    def test_token_cascade_delete(self, test_db, test_user):
        """Test that tokens are deleted when user is deleted."""
        # Create token
        token = APIToken(
            user_id=test_user.id,
            name="Test Token",
            token_hash=APIToken.hash_token("test-token")
        )
        test_db.add(token)
        test_db.commit()
        
        token_id = token.id
        
        # Delete user
        test_db.delete(test_user)
        test_db.commit()
        
        # Verify token is also deleted
        deleted_token = test_db.query(APIToken).filter(APIToken.id == token_id).first()
        assert deleted_token is None
    
    def test_token_timestamps(self, test_db, test_user):
        """Test automatic timestamp handling."""
        # Create token
        token = APIToken(
            user_id=test_user.id,
            name="Timestamp Token",
            token_hash=APIToken.hash_token("timestamp-token")
        )
        
        # Save token
        test_db.add(token)
        test_db.commit()
        
        # Verify timestamps are set
        assert token.created_at is not None
        assert token.updated_at is not None
        # Allow small time difference (microseconds)
        time_diff = abs((token.updated_at - token.created_at).total_seconds())
        assert time_diff < 0.01  # Less than 10ms difference
        
        # Update token
        import time
        time.sleep(0.1)  # Sleep to ensure time difference
        original_updated = token.updated_at
        token.name = "Updated Token"
        test_db.commit()
        
        # Verify updated_at changed
        assert token.updated_at > original_updated
        assert token.created_at < token.updated_at