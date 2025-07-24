#!/usr/bin/env python3
"""
Tests for Server-Side Token Validation (SCRUM-140)
Test-driven development for token validation in TCP registration messages.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

from server.auth.models import APIToken, User
from server.registration_processor import RegistrationProcessor, RegistrationResult


# Test fixtures
@pytest.fixture
def test_user():
    """Create a test user."""
    return User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        password_hash="hashed",
        email_verified=True
    )


@pytest.fixture
def valid_token(test_user):
    """Create a valid API token."""
    return APIToken(
        id=uuid4(),
        user_id=test_user.id,
        name="Test TCP Client",
        token_hash=APIToken.hash_token("valid-token-123"),
        is_active=True
    )


@pytest.fixture
def expired_token(test_user):
    """Create an expired API token."""
    return APIToken(
        id=uuid4(),
        user_id=test_user.id,
        name="Expired Token",
        token_hash=APIToken.hash_token("expired-token-123"),
        is_active=True,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )


@pytest.fixture
def test_config():
    """Test configuration."""
    return {
        "registration": {
            "enable_validation": True,
            "system_user_id": "00000000-0000-0000-0000-000000000000"
        },
        "database": {
            "path": ":memory:"
        }
    }


class TestTokenValidation:
    """Test token validation in registration processor."""

    @pytest.mark.asyncio
    async def test_registration_with_valid_token(self, test_config, test_user, valid_token):
        """Test registration with valid API token."""
        processor = RegistrationProcessor(test_config)
        
        # Mock database operations
        with patch.object(processor, '_validate_token') as mock_validate:
            mock_validate.return_value = {
                'valid': True,
                'user_id': str(test_user.id),
                'token_id': str(valid_token.id)
            }
            
            # Process registration
            result = await processor.process_registration(
                hostname="test.example.com",
                client_ip="192.168.1.100",
                message_timestamp="2024-01-01T00:00:00Z",
                auth_token="valid-token-123"
            )
            
            assert result.success
            assert result.auth_status == "authenticated"
            assert mock_validate.called
            mock_validate.assert_called_with("valid-token-123", "192.168.1.100")

    @pytest.mark.asyncio
    async def test_registration_with_invalid_token(self, test_config):
        """Test registration with invalid token is rejected."""
        processor = RegistrationProcessor(test_config)
        
        # Mock database operations
        with patch.object(processor, '_validate_token') as mock_validate:
            mock_validate.return_value = {
                'valid': False,
                'reason': 'token_not_found'
            }
            
            # Process registration
            result = await processor.process_registration(
                hostname="test.example.com",
                client_ip="192.168.1.100",
                message_timestamp="2024-01-01T00:00:00Z",
                auth_token="invalid-token-xyz"
            )
            
            assert not result.success  # Should fail
            assert result.result_type == "invalid_token"
            assert "token_not_found" in result.message
            assert mock_validate.called

    @pytest.mark.asyncio
    async def test_registration_without_token(self, test_config):
        """Test registration without token is rejected."""
        processor = RegistrationProcessor(test_config)
        
        # Process registration without token
        result = await processor.process_registration(
            hostname="test.example.com",
            client_ip="192.168.1.100",
            message_timestamp="2024-01-01T00:00:00Z"
        )
        
        assert not result.success
        assert result.result_type == "auth_required"
        assert "Authentication required" in result.message

    @pytest.mark.asyncio
    async def test_token_validation_with_database(self, test_config, test_user, valid_token):
        """Test actual token validation against database."""
        processor = RegistrationProcessor(test_config)
        
        # Mock the database manager's get_session method
        mock_session = Mock()
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = [valid_token]
        mock_session.query.return_value = mock_query
        mock_session.commit = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        
        with patch.object(processor.db_manager, 'get_session', return_value=mock_session):
            result = await processor._validate_token("valid-token-123", "192.168.1.100")
            
            assert result['valid'] is True
            assert result['user_id'] == str(test_user.id)
            assert result['token_id'] == str(valid_token.id)
            
            # Verify token usage was updated
            assert valid_token.last_used_at is not None
            assert valid_token.last_used_ip == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_expired_token_validation(self, test_config, test_user, expired_token):
        """Test that expired tokens are rejected."""
        processor = RegistrationProcessor(test_config)
        
        # Mock the database manager's get_session method
        mock_session = Mock()
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = [expired_token]
        mock_session.query.return_value = mock_query
        mock_session.commit = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        
        with patch.object(processor.db_manager, 'get_session', return_value=mock_session):
            result = await processor._validate_token("expired-token-123", "192.168.1.100")
            
            assert result['valid'] is False
            assert result['reason'] == 'token_expired'

    @pytest.mark.asyncio
    async def test_token_caching(self, test_config, test_user, valid_token):
        """Test token validation caching."""
        processor = RegistrationProcessor(test_config)
        
        # Mock the database manager's get_session method
        mock_session = Mock()
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = [valid_token]
        mock_session.query.return_value = mock_query
        mock_session.commit = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        
        with patch.object(processor.db_manager, 'get_session') as mock_get_session:
            mock_get_session.return_value = mock_session
            
            # First call - should hit database
            result1 = await processor._validate_token("valid-token-123", "192.168.1.100")
            assert mock_get_session.called
            
            # Reset mock
            mock_get_session.reset_mock()
            
            # Second call - should use cache
            result2 = await processor._validate_token("valid-token-123", "192.168.1.100")
            assert not mock_get_session.called  # Cache hit, no DB call
            
            assert result1 == result2

    @pytest.mark.asyncio
    async def test_registration_metrics(self, test_config):
        """Test that registration metrics are tracked."""
        processor = RegistrationProcessor(test_config)
        
        # Mock host operations for successful registration
        with patch.object(processor.host_ops, 'get_host_by_hostname') as mock_get:
            mock_get.return_value = None
            with patch.object(processor.host_ops, 'create_host') as mock_create:
                mock_create.return_value = Mock()
                
                # Mock token validation
                with patch.object(processor, '_validate_token') as mock_validate:
                    # Authenticated registration
                    mock_validate.return_value = {'valid': True, 'user_id': 'user-123'}
                    await processor.process_registration(
                        hostname="auth.example.com",
                        client_ip="192.168.1.100",
                        message_timestamp="2024-01-01T00:00:00Z",
                        auth_token="valid-token"
                    )
                    
                    # No token registration (should fail)
                    await processor.process_registration(
                        hostname="anon.example.com",
                        client_ip="192.168.1.101",
                        message_timestamp="2024-01-01T00:00:00Z"
                    )
                    
                    # Invalid token registration
                    mock_validate.return_value = {'valid': False, 'reason': 'invalid'}
                    await processor.process_registration(
                        hostname="invalid.example.com",
                        client_ip="192.168.1.102",
                        message_timestamp="2024-01-01T00:00:00Z",
                        auth_token="bad-token"
                    )
                    
                    # Check metrics
                    assert processor._stats.get('authenticated_registrations', 0) == 1
                    assert processor._stats.get('failed_auth_registrations', 0) == 2


class TestConnectionHandlerIntegration:
    """Test connection handler integration with token validation."""

    @pytest.mark.asyncio
    async def test_connection_handler_passes_token(self):
        """Test that connection handler extracts and passes auth token."""
        from server.connection_handler import ConnectionHandler
        
        # Mock reader/writer
        reader = Mock()
        writer = Mock()
        writer.get_extra_info.return_value = ("192.168.1.100", 12345)
        writer.is_closing.return_value = False
        writer.write = Mock()
        writer.drain = AsyncMock()
        
        # Create handler with proper config including database section
        config = {
            "registration": {"system_user_id": "system"},
            "database": {"path": ":memory:"},
            "powerdns": {"enabled": False}
        }
        handler = ConnectionHandler(reader, writer, config)
        
        # Mock registration processor
        mock_processor = AsyncMock()
        mock_processor.process_registration.return_value = RegistrationResult(
            success=True,
            result_type="authenticated",
            message="Registration successful",
            hostname="test.example.com",
            ip_address="192.168.1.100",
            auth_status="authenticated"
        )
        handler.registration_processor = mock_processor
        
        # Test message with auth token
        message = {
            "type": "registration",
            "hostname": "test.example.com",
            "timestamp": "2024-01-01T00:00:00Z",
            "auth_token": "test-token-123"
        }
        
        await handler._handle_registration(message)
        
        # Verify processor was called with token using keyword arguments
        mock_processor.process_registration.assert_called_with(
            hostname="test.example.com",
            client_ip="192.168.1.100",
            message_timestamp="2024-01-01T00:00:00Z",
            auth_token="test-token-123"
        )