#!/usr/bin/env python3
"""
Unit tests for SMTP email provider.
"""

import asyncio
from email.mime.multipart import MIMEMultipart
from unittest.mock import AsyncMock, MagicMock, patch

import aiosmtplib
import pytest

from server.auth.email_providers import EmailMessage
from server.auth.email_providers.config import EmailProviderType, SMTPEmailConfig
from server.auth.email_providers.smtp import SMTPEmailProvider, SMTPErrorHandler


class TestSMTPEmailProvider:
    """Test SMTP email provider functionality."""

    @pytest.fixture
    def smtp_config(self):
        """Create test SMTP configuration."""
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
        )

    @pytest.fixture
    def email_message(self):
        """Create test email message."""
        return EmailMessage(
            to=["recipient@example.com"],
            subject="Test Email",
            text_body="This is a test email.",
            html_body="<p>This is a test email.</p>",
            from_email="test@example.com",
            from_name="Test App",
        )

    @pytest.mark.asyncio
    async def test_send_email_success(self, smtp_config, email_message):
        """Test successful email sending."""
        provider = SMTPEmailProvider(smtp_config)

        # Mock aiosmtplib.send
        mock_response = {
            "message_id": "test-message-id",
            "rejected": {},
        }

        with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = mock_response

            result = await provider.send_email(email_message)

            assert result.success is True
            assert result.message_id == "test-message-id"
            assert result.provider == "smtp"
            assert "smtp_response" in result.metadata

            # Verify send was called with correct parameters
            mock_send.assert_called_once()
            call_args = mock_send.call_args

            # Check recipients
            assert call_args.kwargs["recipients"] == ["recipient@example.com"]

            # Check host and port
            assert call_args.kwargs["hostname"] == "smtp.example.com"
            assert call_args.kwargs["port"] == 587

            # Check TLS settings
            assert call_args.kwargs["use_tls"] is False
            assert call_args.kwargs["start_tls"] is True

            # Check authentication
            assert call_args.kwargs["username"] == "test_user"
            assert call_args.kwargs["password"] == "test_pass"

    @pytest.mark.asyncio
    async def test_send_email_smtp_exception(self, smtp_config, email_message):
        """Test handling of SMTP exceptions."""
        provider = SMTPEmailProvider(smtp_config)

        with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = aiosmtplib.SMTPException("Authentication failed")

            result = await provider.send_email(email_message)

            assert result.success is False
            assert "Authentication failed" in result.error
            assert result.provider == "smtp"

    @pytest.mark.asyncio
    async def test_send_email_general_exception(self, smtp_config, email_message):
        """Test handling of general exceptions."""
        provider = SMTPEmailProvider(smtp_config)

        with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = Exception("Network error")

            result = await provider.send_email(email_message)

            assert result.success is False
            assert "Network error" in result.error
            assert result.provider == "smtp"

    def test_create_mime_message(self, smtp_config, email_message):
        """Test MIME message creation."""
        provider = SMTPEmailProvider(smtp_config)

        mime_msg = provider._create_mime_message(email_message)

        assert isinstance(mime_msg, MIMEMultipart)
        assert mime_msg["Subject"] == "Test Email"
        assert mime_msg["To"] == "recipient@example.com"
        assert "Test App" in mime_msg["From"]
        assert "test@example.com" in mime_msg["From"]

        # Check that both text and HTML parts are attached
        parts = list(mime_msg.walk())
        assert len(parts) > 1  # Should have multipart container and parts

    def test_create_mime_message_with_cc_and_reply_to(self, smtp_config):
        """Test MIME message with CC and Reply-To headers."""
        provider = SMTPEmailProvider(smtp_config)

        message = EmailMessage(
            to=["recipient@example.com"],
            cc=["cc@example.com"],
            subject="Test",
            text_body="Test",
            html_body="<p>Test</p>",
            reply_to="reply@example.com",
            headers={"X-Custom": "value"},
        )

        mime_msg = provider._create_mime_message(message)

        assert mime_msg["CC"] == "cc@example.com"
        assert mime_msg["Reply-To"] == "reply@example.com"
        assert mime_msg["X-Custom"] == "value"

    @pytest.mark.asyncio
    async def test_send_smtp_ssl_configuration(self, email_message):
        """Test SSL configuration for SMTP."""
        # Create SSL config
        ssl_config = SMTPEmailConfig(
            provider=EmailProviderType.SMTP,
            from_email="test@example.com",
            from_name="Test App",
            host="smtp.example.com",
            port=465,
            use_ssl=True,
            use_tls=False,
        )

        provider = SMTPEmailProvider(ssl_config)

        with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"message_id": "test"}

            await provider.send_email(email_message)

            # Check SSL settings
            call_args = mock_send.call_args
            assert call_args.kwargs["use_tls"] is True
            assert call_args.kwargs["start_tls"] is False

    @pytest.mark.asyncio
    async def test_verify_configuration_success(self, smtp_config):
        """Test successful configuration verification."""
        provider = SMTPEmailProvider(smtp_config)

        mock_smtp = AsyncMock()
        mock_smtp.starttls = AsyncMock()
        mock_smtp.login = AsyncMock()

        with patch("aiosmtplib.SMTP") as mock_smtp_class:
            mock_smtp_class.return_value.__aenter__.return_value = mock_smtp

            result = await provider.verify_configuration()

            assert result is True
            mock_smtp.starttls.assert_called_once()
            mock_smtp.login.assert_called_once_with("test_user", "test_pass")

    @pytest.mark.asyncio
    async def test_verify_configuration_failure(self, smtp_config):
        """Test configuration verification failure."""
        provider = SMTPEmailProvider(smtp_config)

        with patch("aiosmtplib.SMTP") as mock_smtp_class:
            mock_smtp_class.side_effect = Exception("Connection refused")

            result = await provider.verify_configuration()

            assert result is False

    @pytest.mark.asyncio
    async def test_no_authentication(self):
        """Test SMTP without authentication."""
        config = SMTPEmailConfig(
            provider=EmailProviderType.SMTP,
            from_email="test@example.com",
            from_name="Test App",
            host="localhost",
            port=1025,
            use_tls=False,
            use_ssl=False,
        )

        provider = SMTPEmailProvider(config)
        message = EmailMessage(
            to=["test@example.com"],
            subject="Test",
            text_body="Test",
            html_body="<p>Test</p>",
        )

        with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"message_id": "test"}

            result = await provider.send_email(message)

            # Should be successful
            assert result.success is True

            # Should not include auth parameters
            call_args = mock_send.call_args
            assert call_args is not None
            assert "username" not in call_args.kwargs
            assert "password" not in call_args.kwargs


class TestSMTPErrorHandler:
    """Test SMTP error handler."""

    def test_authentication_error_message(self):
        """Test authentication error handling."""
        error = Exception("535 Authentication failed")
        message = SMTPErrorHandler.get_user_friendly_error(error)
        assert "authentication failed" in message.lower()

    def test_connection_error_message(self):
        """Test connection error handling."""
        error = Exception("Connection timeout")
        message = SMTPErrorHandler.get_user_friendly_error(error)
        assert "connect to email server" in message.lower()

    def test_relay_denied_error_message(self):
        """Test relay denied error handling."""
        error = Exception("550 Relay access denied")
        message = SMTPErrorHandler.get_user_friendly_error(error)
        assert "rejected by server" in message.lower()

    def test_tls_error_message(self):
        """Test TLS error handling."""
        error = Exception("TLS negotiation failed")
        message = SMTPErrorHandler.get_user_friendly_error(error)
        assert "security negotiation failed" in message.lower()

    def test_generic_error_message(self):
        """Test generic error handling."""
        error = Exception("Some unexpected error")
        message = SMTPErrorHandler.get_user_friendly_error(error)
        assert "Some unexpected error" in message
