#!/usr/bin/env python3
"""
Tests for Authentication Required Behavior (SCRUM-141)
Test-driven development for ensuring all TCP clients must authenticate.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from server.auth.models import APIToken, User
from server.registration_processor import RegistrationProcessor, RegistrationResult


# Test fixtures
@pytest.fixture
def test_config():
    """Test configuration."""
    return {
        "registration": {
            "enable_validation": True,
        },
        "database": {
            "path": ":memory:"
        }
    }


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


class TestAuthenticationRequired:
    """Test that authentication is always required."""

    @pytest.mark.asyncio
    async def test_registration_without_token_fails(self, test_config):
        """Test that registrations without tokens are rejected."""
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
    async def test_registration_with_empty_token_fails(self, test_config):
        """Test that empty auth tokens are rejected."""
        processor = RegistrationProcessor(test_config)
        
        # Process registration with empty token
        result = await processor.process_registration(
            hostname="test.example.com",
            client_ip="192.168.1.100",
            message_timestamp="2024-01-01T00:00:00Z",
            auth_token=""
        )
        
        assert not result.success
        assert result.result_type == "auth_required"
        assert "Authentication required" in result.message

    @pytest.mark.asyncio
    async def test_registration_with_invalid_token_fails(self, test_config):
        """Test that invalid tokens are rejected."""
        processor = RegistrationProcessor(test_config)
        
        # Mock token validation failure
        with patch.object(processor, '_validate_token') as mock_validate:
            mock_validate.return_value = {'valid': False, 'reason': 'token_not_found'}
            
            result = await processor.process_registration(
                hostname="test.example.com",
                client_ip="192.168.1.100",
                message_timestamp="2024-01-01T00:00:00Z",
                auth_token="invalid-token-xyz"
            )
            
            assert not result.success
            assert result.result_type == "invalid_token"
            assert "Invalid authentication token" in result.message
            assert "token_not_found" in result.message

    @pytest.mark.asyncio
    async def test_registration_with_valid_token_succeeds(self, test_config, test_user, valid_token):
        """Test that valid tokens allow registration."""
        processor = RegistrationProcessor(test_config)
        
        # Mock successful token validation
        with patch.object(processor, '_validate_token') as mock_validate:
            mock_validate.return_value = {
                'valid': True,
                'user_id': str(test_user.id),
                'token_id': str(valid_token.id)
            }
            
            # Mock host operations
            with patch.object(processor.host_ops, 'get_host_by_hostname') as mock_get:
                mock_get.return_value = None  # New host
                
                with patch.object(processor.host_ops, 'create_host') as mock_create:
                    mock_host = Mock()
                    mock_create.return_value = mock_host
                    
                    # Process registration
                    result = await processor.process_registration(
                        hostname="test.example.com",
                        client_ip="192.168.1.100",
                        message_timestamp="2024-01-01T00:00:00Z",
                        auth_token="valid-token-123"
                    )
                    
                    assert result.success
                    assert result.auth_status == "authenticated"
                    assert result.result_type == "new_registration"
                    
                    # Verify host was created with correct user ID
                    mock_create.assert_called_with(
                        "test.example.com",
                        "192.168.1.100",
                        str(test_user.id)
                    )

    @pytest.mark.asyncio
    async def test_expired_token_fails(self, test_config):
        """Test that expired tokens are rejected."""
        processor = RegistrationProcessor(test_config)
        
        # Mock expired token validation
        with patch.object(processor, '_validate_token') as mock_validate:
            mock_validate.return_value = {'valid': False, 'reason': 'token_expired'}
            
            result = await processor.process_registration(
                hostname="test.example.com",
                client_ip="192.168.1.100",
                message_timestamp="2024-01-01T00:00:00Z",
                auth_token="expired-token-123"
            )
            
            assert not result.success
            assert result.result_type == "invalid_token"
            assert "token_expired" in result.message

    @pytest.mark.asyncio
    async def test_inactive_token_fails(self, test_config):
        """Test that inactive/revoked tokens are rejected."""
        processor = RegistrationProcessor(test_config)
        
        # Mock inactive token validation
        with patch.object(processor, '_validate_token') as mock_validate:
            mock_validate.return_value = {'valid': False, 'reason': 'token_inactive'}
            
            result = await processor.process_registration(
                hostname="test.example.com",
                client_ip="192.168.1.100",
                message_timestamp="2024-01-01T00:00:00Z",
                auth_token="revoked-token-123"
            )
            
            assert not result.success
            assert result.result_type == "invalid_token"
            assert "token_inactive" in result.message

    @pytest.mark.asyncio
    async def test_auth_failure_metrics(self, test_config):
        """Test that authentication failures are tracked in metrics."""
        processor = RegistrationProcessor(test_config)
        
        # Initial metrics
        assert processor._stats["failed_auth_registrations"] == 0
        
        # Test missing token
        await processor.process_registration(
            hostname="test1.example.com",
            client_ip="192.168.1.100",
            message_timestamp="2024-01-01T00:00:00Z"
        )
        assert processor._stats["failed_auth_registrations"] == 1
        
        # Test invalid token
        with patch.object(processor, '_validate_token') as mock_validate:
            mock_validate.return_value = {'valid': False, 'reason': 'invalid'}
            
            await processor.process_registration(
                hostname="test2.example.com",
                client_ip="192.168.1.101",
                message_timestamp="2024-01-01T00:00:01Z",
                auth_token="bad-token"
            )
            assert processor._stats["failed_auth_registrations"] == 2

    @pytest.mark.asyncio
    async def test_successful_auth_metrics(self, test_config, test_user):
        """Test that successful authentications are tracked."""
        processor = RegistrationProcessor(test_config)
        
        with patch.object(processor, '_validate_token') as mock_validate:
            mock_validate.return_value = {
                'valid': True,
                'user_id': str(test_user.id)
            }
            
            with patch.object(processor.host_ops, 'get_host_by_hostname') as mock_get:
                mock_get.return_value = None
                
                with patch.object(processor.host_ops, 'create_host') as mock_create:
                    mock_create.return_value = Mock()
                    
                    await processor.process_registration(
                        hostname="test.example.com",
                        client_ip="192.168.1.100",
                        message_timestamp="2024-01-01T00:00:00Z",
                        auth_token="valid-token"
                    )
                    
                    assert processor._stats["authenticated_registrations"] == 1
                    assert processor._stats["failed_auth_registrations"] == 0


class TestConnectionHandlerAuth:
    """Test connection handler authentication requirements."""

    @pytest.mark.asyncio
    async def test_connection_handler_requires_processor(self):
        """Test that connection handler requires registration processor."""
        from server.connection_handler import ConnectionHandler
        
        # Mock reader/writer
        reader = Mock()
        writer = Mock()
        writer.get_extra_info.return_value = ("192.168.1.100", 12345)
        writer.is_closing.return_value = False
        writer.write = Mock()
        writer.drain = AsyncMock()
        
        # Create handler without registration processor
        config = {"database": {"path": ":memory:"}}
        handler = ConnectionHandler(reader, writer, config)
        handler.registration_processor = None  # Simulate missing processor
        
        # Test message
        message = {
            "type": "registration",
            "hostname": "test.example.com",
            "timestamp": "2024-01-01T00:00:00Z",
            "auth_token": "test-token-123"
        }
        
        await handler._handle_registration(message)
        
        # Should send error response
        writer.write.assert_called()
        sent_data = writer.write.call_args[0][0]
        assert b"error" in sent_data
        assert b"Server configuration error" in sent_data

    @pytest.mark.asyncio
    async def test_connection_handler_passes_auth_token(self):
        """Test that connection handler extracts and passes auth token."""
        from server.connection_handler import ConnectionHandler
        
        # Mock reader/writer
        reader = Mock()
        writer = Mock()
        writer.get_extra_info.return_value = ("192.168.1.100", 12345)
        writer.is_closing.return_value = False
        writer.write = Mock()
        writer.drain = AsyncMock()
        
        # Create handler with proper config
        config = {
            "registration": {},
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
        
        # Verify processor was called with token
        mock_processor.process_registration.assert_called_with(
            hostname="test.example.com",
            client_ip="192.168.1.100",
            message_timestamp="2024-01-01T00:00:00Z",
            auth_token="test-token-123"
        )


class TestNoAnonymousSupport:
    """Test that anonymous/system user support has been removed."""

    def test_no_system_user_manager(self):
        """Test that SystemUserManager doesn't exist."""
        with pytest.raises(ImportError):
            from server.auth.system_user import SystemUserManager

    def test_no_migration_tools(self):
        """Test that migration tools don't exist."""
        with pytest.raises(ImportError):
            from server.commands.migrate_hosts import migrate_anonymous_hosts

    def test_registration_config_no_anonymous_options(self):
        """Test that anonymous config options are removed."""
        from server.registration_processor import RegistrationConfig
        
        config = {"registration": {}}
        reg_config = RegistrationConfig(config)
        
        # These attributes should not exist
        assert not hasattr(reg_config, 'auth_required')
        assert not hasattr(reg_config, 'allow_anonymous')
        assert not hasattr(reg_config, 'auth_warning_interval')