#!/usr/bin/env python3
"""
Unit tests for enhanced SMTP email provider.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiosmtplib
import pytest

from server.auth.email_providers import EmailMessage
from server.auth.email_providers.circuit_breaker import CircuitState
from server.auth.email_providers.config import EmailProviderType, SMTPEmailConfig
from server.auth.email_providers.smtp_enhanced import EnhancedSMTPEmailProvider


class TestEnhancedSMTPEmailProvider:
    """Test enhanced SMTP email provider functionality."""

    @pytest.fixture
    def smtp_config(self):
        """Create test SMTP configuration with enhanced features."""
        return SMTPEmailConfig(
            provider=EmailProviderType.SMTP,
            from_email="test@example.com",
            from_name="Test App",
            host="smtp.example.com",
            port=587,
            username="test_user",
            password="test_pass",
            use_tls=True,
            use_ssl=False,
            timeout=30,
            # Pool settings
            pool_size=3,
            pool_max_idle_time=300,
            # Retry settings
            retry_max_attempts=3,
            retry_initial_delay=0.1,  # Short for tests
            retry_max_delay=1.0,
            retry_exponential_base=2.0,
            # Circuit breaker settings
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=60,
        )

    @pytest.fixture
    def email_message(self):
        """Create test email message."""
        return EmailMessage(
            to=["recipient@example.com"],
            subject="Test Email",
            text_body="This is a test email.",
            html_body="<p>This is a test email.</p>",
        )

    @pytest.mark.asyncio
    async def test_create_provider(self, smtp_config):
        """Test creating enhanced provider."""
        provider = EnhancedSMTPEmailProvider(smtp_config)

        assert provider.config == smtp_config
        assert provider.pool.max_size == 3
        assert provider.retry_config.max_attempts == 3
        assert provider.circuit_breaker is not None
        assert provider.circuit_breaker.failure_threshold == 3

        # Cleanup
        await provider.close()

    @pytest.mark.asyncio
    async def test_send_email_with_pool(self, smtp_config, email_message):
        """Test sending email using connection pool."""
        provider = EnhancedSMTPEmailProvider(smtp_config)

        # Mock SMTP connection
        mock_smtp = AsyncMock()
        mock_smtp.send_message = AsyncMock(return_value={"message_id": "test-123"})
        mock_smtp.is_connected = True

        # Mock pool to return our mock connection
        with patch.object(provider.pool, "get_connection") as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_smtp

            result = await provider.send_email(email_message)

            assert result.success is True
            assert result.message_id == "test-123"
            assert "pool_status" in result.metadata

            # Verify connection was used
            mock_smtp.send_message.assert_called_once()

        # Cleanup
        await provider.close()

    @pytest.mark.asyncio
    async def test_retry_on_failure(self, smtp_config, email_message):
        """Test retry logic on transient failures."""
        # Create new config with shorter delays for faster tests
        config_dict = smtp_config.model_dump()
        config_dict["retry_initial_delay"] = 0.1  # Minimum allowed
        config_dict["retry_max_delay"] = 1.0
        test_config = SMTPEmailConfig(**config_dict)
        provider = EnhancedSMTPEmailProvider(test_config)

        # Mock SMTP that fails twice then succeeds
        call_count = 0

        async def mock_send_message(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise aiosmtplib.SMTPException("Temporary failure")
            return {"message_id": "success-123"}

        mock_smtp = AsyncMock()
        mock_smtp.send_message = mock_send_message
        mock_smtp.is_connected = True

        with patch.object(provider.pool, "get_connection") as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_smtp

            result = await provider.send_email(email_message)

            assert result.success is True
            assert result.message_id == "success-123"
            assert call_count == 3  # Should have retried twice

        # Cleanup
        await provider.close()

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens(self, smtp_config, email_message):
        """Test circuit breaker opens after failures."""
        smtp_config.circuit_breaker_threshold = 2
        smtp_config.retry_max_attempts = 1  # No retries for this test
        provider = EnhancedSMTPEmailProvider(smtp_config)

        # Mock SMTP that always fails
        mock_smtp = AsyncMock()
        mock_smtp.send_message = AsyncMock(
            side_effect=aiosmtplib.SMTPException("Connection failed")
        )

        with patch.object(provider.pool, "get_connection") as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_smtp

            # First two failures should open circuit
            for i in range(2):
                result = await provider.send_email(email_message)
                assert result.success is False

            # Circuit should be open now
            assert provider.circuit_breaker.state == CircuitState.OPEN

            # Next call should be rejected by circuit breaker
            result = await provider.send_email(email_message)
            assert result.success is False
            assert "temporarily unavailable" in result.error
            assert result.metadata.get("circuit_breaker") == "open"

        # Cleanup
        await provider.close()

    @pytest.mark.asyncio
    async def test_circuit_breaker_disabled(self, smtp_config, email_message):
        """Test provider works without circuit breaker."""
        smtp_config.circuit_breaker_enabled = False
        provider = EnhancedSMTPEmailProvider(smtp_config)

        assert provider.circuit_breaker is None

        # Mock successful send
        mock_smtp = AsyncMock()
        mock_smtp.send_message = AsyncMock(return_value={"message_id": "test-123"})

        with patch.object(provider.pool, "get_connection") as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_smtp

            result = await provider.send_email(email_message)
            assert result.success is True

        # Cleanup
        await provider.close()

    @pytest.mark.asyncio
    async def test_verify_configuration(self, smtp_config):
        """Test configuration verification."""
        provider = EnhancedSMTPEmailProvider(smtp_config)

        # Mock successful connection
        mock_smtp = AsyncMock()
        mock_smtp.is_connected = True

        with patch.object(provider.pool, "get_connection") as mock_get_conn:
            mock_get_conn.return_value.__aenter__.return_value = mock_smtp

            result = await provider.verify_configuration()
            assert result is True

        # Test failed verification
        with patch.object(provider.pool, "get_connection") as mock_get_conn:
            mock_get_conn.side_effect = Exception("Connection failed")

            result = await provider.verify_configuration()
            assert result is False

        # Cleanup
        await provider.close()

    @pytest.mark.asyncio
    async def test_get_status(self, smtp_config):
        """Test getting provider status."""
        provider = EnhancedSMTPEmailProvider(smtp_config)

        status = provider.get_status()

        assert status["provider"] == "smtp"
        assert "pool" in status
        assert status["circuit_breaker"]["state"] == "closed"
        assert status["circuit_breaker"]["failures"] == 0
        assert status["circuit_breaker"]["threshold"] == 3

        # Cleanup
        await provider.close()

    @pytest.mark.asyncio
    async def test_close_provider(self, smtp_config):
        """Test closing provider releases resources."""
        provider = EnhancedSMTPEmailProvider(smtp_config)

        # Create some connections
        mock_smtp = AsyncMock()
        mock_smtp.quit = AsyncMock()

        with patch("aiosmtplib.SMTP", return_value=mock_smtp):
            # Force pool to create connection
            await provider.pool._create_connection()

        # Close provider
        await provider.close()

        # Pool should be closed
        assert provider.pool._closed is True
        # Circuit breaker should be reset
        if provider.circuit_breaker:
            assert provider.circuit_breaker.state == CircuitState.CLOSED
