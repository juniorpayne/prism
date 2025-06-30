#!/usr/bin/env python3
"""
Unit tests for specific email provider implementations.
"""

import os
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiosmtplib import SMTPException

from server.auth.email_providers import (
    ConsoleEmailProvider,
    EmailDeliveryError,
    EmailMessage,
    EmailResult,
    SMTPEmailProvider,
)
from server.auth.email_providers.config import SMTPEmailConfig


class TestConsoleEmailProvider:
    """Test cases for ConsoleEmailProvider."""

    @pytest.fixture
    def console_provider(self):
        """Create a console email provider instance."""
        return ConsoleEmailProvider(
            {"format": "pretty", "highlight_links": True, "enhanced_formatting": False}
        )

    @pytest.mark.asyncio
    async def test_send_verification_email(self, console_provider, capsys):
        """Test sending verification email to console."""
        # Create email message
        message = EmailMessage(
            to=["test@example.com"],
            subject="Verify your Prism DNS account",
            html_body="""
        <html>
        <body>
            <h2>Welcome to Prism DNS!</h2>
            <p>Hi testuser,</p>
            <p>Please verify your email address by clicking the link below:</p>
            <a href="http://localhost:8090/verify-email?token=abc123def456">
                Verify Email Address
            </a>
        </body>
        </html>
        """,
        )

        # Send email
        result = await console_provider.send_email(message)

        # Check result
        assert result.success is True
        assert result.provider == "Console"

        # Capture console output
        captured = capsys.readouterr()

        # Verify console output contains expected elements
        assert "EMAIL CONSOLE OUTPUT" in captured.out
        assert "test@example.com" in captured.out
        assert "Verify your Prism DNS account" in captured.out
        assert "EMAIL VERIFICATION" in captured.out
        assert "Verification Token: abc123def456" in captured.out
        assert "verify-email?token=abc123def456" in captured.out

    @pytest.mark.asyncio
    async def test_send_password_reset_email(self, console_provider, capsys):
        """Test sending password reset email to console."""
        # Create email message
        message = EmailMessage(
            to=["test@example.com"],
            subject="Reset your Prism DNS password",
            html_body="""
        <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>Hi testuser,</p>
            <p>Reset your password using the link below:</p>
            <a href="http://localhost:8090/reset-password?token=xyz789rst456">
                Reset Password
            </a>
        </body>
        </html>
        """,
        )

        # Send email
        result = await console_provider.send_email(message)

        # Check result
        assert result.success is True

        # Capture console output
        captured = capsys.readouterr()

        # Verify console output contains expected elements
        assert "EMAIL CONSOLE OUTPUT" in captured.out
        assert "PASSWORD RESET" in captured.out
        assert "Reset Token: xyz789rst456" in captured.out
        assert "reset-password?token=xyz789rst456" in captured.out

    @pytest.mark.asyncio
    async def test_send_general_email(self, console_provider, capsys):
        """Test sending general email to console."""
        # Create email message
        message = EmailMessage(
            to=["test@example.com"],
            subject="Account Updated",
            html_body="""
        <html>
        <body>
            <h2>Account Update</h2>
            <p>Your account has been updated successfully.</p>
        </body>
        </html>
        """,
        )

        # Send email
        result = await console_provider.send_email(message)

        # Check result
        assert result.success is True

        # Capture console output
        captured = capsys.readouterr()

        # Verify console output contains expected elements
        assert "EMAIL CONSOLE OUTPUT" in captured.out
        assert "GENERAL EMAIL" in captured.out
        assert "Account Update" in captured.out

    @pytest.mark.asyncio
    async def test_extract_multiple_tokens(self, console_provider, capsys):
        """Test extraction of multiple tokens from email."""
        # Create email message
        message = EmailMessage(
            to=["test@example.com"],
            subject="Test Email",
            html_body="""
        <html>
        <body>
            <a href="http://localhost:8090/verify-email?token=token1">Verify</a>
            <a href="http://localhost:8090/reset-password?token=token2">Reset</a>
        </body>
        </html>
        """,
        )

        # Send email
        await console_provider.send_email(message)

        # Capture console output
        captured = capsys.readouterr()

        # Should display first matching link
        assert "token1" in captured.out or "token2" in captured.out

    @pytest.mark.asyncio
    async def test_password_changed_notification(self, console_provider, capsys):
        """Test password changed notification email."""
        # Create email message
        message = EmailMessage(
            to=["test@example.com"],
            subject="Your Prism DNS password has been changed",
            html_body="""
        <html>
        <body>
            <h2>Password Changed Successfully</h2>
            <p>Your password has been changed.</p>
        </body>
        </html>
        """,
        )

        # Send email
        result = await console_provider.send_email(message)

        # Check result
        assert result.success is True

        # Capture console output
        captured = capsys.readouterr()

        # Verify console output
        assert "PASSWORD CHANGED NOTIFICATION" in captured.out
        assert "security notification" in captured.out


class TestSMTPEmailProvider:
    """Test cases for SMTPEmailProvider."""

    @pytest.fixture
    def smtp_provider(self):
        """Create an SMTP email provider instance."""
        config = SMTPEmailConfig(
            provider="smtp",
            from_email="test@example.com",
            from_name="Test App",
            host="smtp.example.com",
            port=587,
            username="test@example.com",
            password="password",
            use_tls=True,
        )
        return SMTPEmailProvider(config)

    @pytest.mark.asyncio
    async def test_send_email_success(self, smtp_provider):
        """Test successful email sending via SMTP."""
        # Mock aiosmtplib.send
        with patch("server.auth.email_providers.smtp.aiosmtplib.send") as mock_send:
            # Configure mock to succeed
            mock_send.return_value = {"message_id": "test-message-id"}

            # Create email message
            message = EmailMessage(
                to=["test@example.com"],
                subject="Test Subject",
                html_body="<p>Test content</p>",
            )

            # Send email
            result = await smtp_provider.send_email(message)

            # Check result
            assert result.success is True
            assert result.provider == "smtp"  # Note: lowercase now due to provider_name property

            # Verify send was called
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args[1]
            assert call_kwargs["hostname"] == "smtp.example.com"
            assert call_kwargs["port"] == 587
            assert call_kwargs["username"] == "test@example.com"
            assert call_kwargs["password"] == "password"

    @pytest.mark.asyncio
    async def test_send_email_failure(self, smtp_provider):
        """Test email sending failure via SMTP."""
        # Mock aiosmtplib.send to raise exception
        with patch("server.auth.email_providers.smtp.aiosmtplib.send") as mock_send:
            # Configure mock to raise exception
            mock_send.side_effect = SMTPException("SMTP connection failed")

            # Create email message
            message = EmailMessage(
                to=["test@example.com"],
                subject="Test Subject",
                html_body="<p>Test content</p>",
            )

            # Send email - should return failure result
            result = await smtp_provider.send_email(message)

            # Check result
            assert result.success is False
            assert "connection failed" in result.error.lower()
            assert result.provider == "smtp"

            # Verify send was called
            mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_email_service_uses_console_provider():
    """Test that email service uses console provider when SMTP is not configured."""
    # Clear email service singleton
    from server.auth import email

    email._email_service = None

    with patch("server.auth.email.get_settings") as mock_settings:
        with patch.dict(
            os.environ, {"EMAIL_PROVIDER": "console", "EMAIL_FROM_ADDRESS": "test@example.com"}
        ):
            # Configure settings
            mock_settings.return_value = {
                "email_from": "test@example.com",
                "frontend_url": "http://localhost:8090",
            }

            # Import after patching
            from server.auth.email import EmailService

            # Create service
            service = EmailService()

            # Check that console provider is used
            assert isinstance(service.provider, ConsoleEmailProvider)


@pytest.mark.asyncio
async def test_email_service_uses_smtp_provider():
    """Test that email service uses SMTP provider when configured."""
    # Clear email service singleton and config loader
    from server.auth import email

    email._email_service = None

    # Clear the config loader singleton
    from server.auth.email_providers import config_loader

    config_loader._config_loader = None

    with patch("server.auth.email.get_settings") as mock_settings:
        with patch.dict(
            os.environ,
            {
                "EMAIL_PROVIDER": "smtp",
                "EMAIL_FROM_ADDRESS": "noreply@example.com",
                "EMAIL_FROM_NAME": "Test App",
                "SMTP_HOST": "smtp.example.com",
                "SMTP_PORT": "587",
                "SMTP_USERNAME": "test@example.com",
                "SMTP_PASSWORD": "password123",
                "SMTP_USE_TLS": "true",
                "SMTP_USE_SSL": "false",
            },
            clear=True,  # Clear all env vars to avoid conflicts
        ):
            with patch("server.auth.email_providers.smtp.aiosmtplib"):
                # Configure settings
                mock_settings.return_value = {
                    "email_from": "noreply@example.com",
                    "frontend_url": "http://localhost:8090",
                }

                # Import after patching
                from server.auth.email import EmailService

                # Create service
                service = EmailService()

                # Check that SMTP provider is used
                assert isinstance(service.provider, SMTPEmailProvider)
