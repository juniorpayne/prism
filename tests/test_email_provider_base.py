#!/usr/bin/env python3
"""
Unit tests for email provider base classes and factory.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.auth.email_providers import (
    EmailAttachment,
    EmailConfigurationError,
    EmailDeliveryError,
    EmailMessage,
    EmailPriority,
    EmailProvider,
    EmailProviderFactory,
    EmailResult,
)
from server.auth.email_providers.base import EmailProviderConfig
from server.auth.email_providers.console import ConsoleEmailProvider
from server.auth.email_providers.smtp import SMTPEmailProvider


class TestEmailMessage:
    """Test EmailMessage dataclass."""

    def test_valid_email_message(self):
        """Test creating a valid email message."""
        message = EmailMessage(
            to=["user@example.com"],
            subject="Test Subject",
            html_body="<p>Test HTML</p>",
            text_body="Test text",
        )

        assert message.to == ["user@example.com"]
        assert message.subject == "Test Subject"
        assert message.html_body == "<p>Test HTML</p>"
        assert message.text_body == "Test text"
        assert message.priority == EmailPriority.NORMAL

    def test_email_normalization(self):
        """Test that email addresses are normalized."""
        message = EmailMessage(
            to=["  USER@EXAMPLE.COM  "],
            subject="Test",
            html_body="Test",
            cc=["  CC@EXAMPLE.COM  "],
            bcc=["  BCC@EXAMPLE.COM  "],
        )

        assert message.to == ["user@example.com"]
        assert message.cc == ["cc@example.com"]
        assert message.bcc == ["bcc@example.com"]

    def test_missing_recipient(self):
        """Test that missing recipient raises error."""
        with pytest.raises(ValueError, match="At least one recipient is required"):
            EmailMessage(
                to=[],
                subject="Test",
                html_body="Test",
            )

    def test_missing_subject(self):
        """Test that missing subject raises error."""
        with pytest.raises(ValueError, match="Subject is required"):
            EmailMessage(
                to=["user@example.com"],
                subject="",
                html_body="Test",
            )

    def test_missing_body(self):
        """Test that missing body raises error."""
        with pytest.raises(ValueError, match="Either html_body or text_body is required"):
            EmailMessage(
                to=["user@example.com"],
                subject="Test",
                html_body="",
                text_body="",
            )

    def test_attachments(self):
        """Test email with attachments."""
        attachment = EmailAttachment(
            filename="test.pdf",
            content=b"PDF content",
            content_type="application/pdf",
        )

        message = EmailMessage(
            to=["user@example.com"],
            subject="Test with attachment",
            html_body="See attached",
            attachments=[attachment],
        )

        assert len(message.attachments) == 1
        assert message.attachments[0].filename == "test.pdf"


class TestEmailResult:
    """Test EmailResult dataclass."""

    def test_successful_result(self):
        """Test successful email result."""
        result = EmailResult(
            success=True,
            message_id="msg-123",
            provider="SMTP",
        )

        assert result.success is True
        assert result.message_id == "msg-123"
        assert result.provider == "SMTP"
        assert result.error is None
        assert "success=True" in str(result)

    def test_failed_result(self):
        """Test failed email result."""
        result = EmailResult(
            success=False,
            error="Connection failed",
            error_code="CONN_ERROR",
            provider="SMTP",
            retry_after=60,
        )

        assert result.success is False
        assert result.error == "Connection failed"
        assert result.error_code == "CONN_ERROR"
        assert result.retry_after == 60
        assert "success=False" in str(result)
        assert "Connection failed" in str(result)


class MockEmailProvider(EmailProvider):
    """Mock email provider for testing."""

    async def send_email(self, message: EmailMessage) -> EmailResult:
        """Mock send email."""
        return EmailResult(
            success=True,
            message_id="mock-123",
            provider="Mock",
        )

    async def verify_configuration(self) -> bool:
        """Mock verify configuration."""
        return True


class TestEmailProvider:
    """Test EmailProvider abstract base class."""

    @pytest.fixture
    def mock_provider(self):
        """Create mock provider instance."""
        return MockEmailProvider({"test": "config"})

    @pytest.mark.asyncio
    async def test_provider_initialization(self, mock_provider):
        """Test provider initialization."""
        assert mock_provider.config == {"test": "config"}
        assert mock_provider.provider_name == "Mock"
        assert "Mock" in repr(mock_provider)

    @pytest.mark.asyncio
    async def test_send_bulk_success(self, mock_provider):
        """Test bulk send with all successful."""
        messages = [
            EmailMessage(
                to=[f"user{i}@example.com"],
                subject=f"Test {i}",
                html_body=f"Test {i}",
            )
            for i in range(3)
        ]

        results = await mock_provider.send_bulk(messages)

        assert len(results) == 3
        assert all(r.success for r in results)
        assert all(r.message_id == "mock-123" for r in results)

    @pytest.mark.asyncio
    async def test_send_bulk_with_failure(self, mock_provider):
        """Test bulk send with some failures."""
        # Make second email fail
        mock_provider.send_email = AsyncMock(
            side_effect=[
                EmailResult(success=True, message_id="1", provider="Mock"),
                Exception("Send failed"),
                EmailResult(success=True, message_id="3", provider="Mock"),
            ]
        )

        messages = [
            EmailMessage(
                to=[f"user{i}@example.com"],
                subject=f"Test {i}",
                html_body=f"Test {i}",
            )
            for i in range(3)
        ]

        results = await mock_provider.send_bulk(messages)

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert "Send failed" in results[1].error
        assert results[2].success is True


class TestEmailProviderFactory:
    """Test EmailProviderFactory."""

    def test_create_console_provider(self):
        """Test creating console provider."""
        provider = EmailProviderFactory.create_provider("console", {"format": "json"})

        assert isinstance(provider, ConsoleEmailProvider)
        assert provider.config["format"] == "json"

    def test_create_smtp_provider(self):
        """Test creating SMTP provider."""
        with patch("server.auth.email_providers.smtp.FastMail"):
            config = {
                "host": "smtp.example.com",
                "port": "587",
                "username": "user@example.com",
                "password": "password",
            }
            provider = EmailProviderFactory.create_provider("smtp", config)

            assert isinstance(provider, SMTPEmailProvider)

    def test_create_unknown_provider(self):
        """Test creating unknown provider raises error."""
        with pytest.raises(EmailConfigurationError, match="Unknown email provider: invalid"):
            EmailProviderFactory.create_provider("invalid")

    def test_create_from_config(self):
        """Test creating provider from config dict."""
        config = {
            "provider": "console",
            "format": "pretty",
            "use_colors": True,
        }

        provider = EmailProviderFactory.create_from_config(config)

        assert isinstance(provider, ConsoleEmailProvider)
        # Note: original config is modified (provider key removed)
        assert "provider" not in config

    def test_create_from_config_missing_provider(self):
        """Test error when provider key is missing."""
        with pytest.raises(EmailConfigurationError, match="must include 'provider' key"):
            EmailProviderFactory.create_from_config({"format": "json"})

    def test_register_provider(self):
        """Test registering a new provider."""
        # Register mock provider
        EmailProviderFactory.register_provider("mock", MockEmailProvider)

        # Should be able to create it now
        provider = EmailProviderFactory.create_provider("mock")
        assert isinstance(provider, MockEmailProvider)

        # Clean up
        del EmailProviderFactory._providers["mock"]

    def test_register_invalid_provider(self):
        """Test registering invalid provider class."""

        class NotAProvider:
            pass

        with pytest.raises(ValueError, match="must extend EmailProvider"):
            EmailProviderFactory.register_provider("invalid", NotAProvider)

    def test_get_available_providers(self):
        """Test getting list of available providers."""
        providers = EmailProviderFactory.get_available_providers()

        assert "console" in providers
        assert "smtp" in providers
        assert isinstance(providers, list)

    def test_is_provider_available(self):
        """Test checking if provider is available."""
        assert EmailProviderFactory.is_provider_available("console") is True
        assert EmailProviderFactory.is_provider_available("SMTP") is True  # Case insensitive
        assert EmailProviderFactory.is_provider_available("invalid") is False


class TestEmailProviderConfig:
    """Test EmailProviderConfig class."""

    def test_config_initialization(self):
        """Test config initialization with kwargs."""
        config = EmailProviderConfig(
            host="smtp.example.com",
            port=587,
            username="user@example.com",
        )

        assert config.host == "smtp.example.com"
        assert config.port == 587
        assert config.username == "user@example.com"

    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = EmailProviderConfig(
            host="smtp.example.com",
            port=587,
            _private="should not appear",
        )

        config_dict = config.to_dict()

        assert config_dict == {
            "host": "smtp.example.com",
            "port": 587,
        }
        assert "_private" not in config_dict

    def test_config_validate(self):
        """Test that validate can be called (does nothing by default)."""
        config = EmailProviderConfig()
        config.validate()  # Should not raise
