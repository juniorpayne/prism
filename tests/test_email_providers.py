#!/usr/bin/env python3
"""
Unit tests for specific email provider implementations.
"""

import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.auth.email_providers import (
    ConsoleEmailProvider,
    EmailDeliveryError,
    EmailMessage,
    EmailResult,
    SMTPEmailProvider,
)


class TestConsoleEmailProvider:
    """Test cases for ConsoleEmailProvider."""

    @pytest.fixture
    def console_provider(self):
        """Create a console email provider instance."""
        return ConsoleEmailProvider({"format": "pretty", "highlight_links": True})

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
    def mock_fastmail(self):
        """Create a mock FastMail instance."""
        return MagicMock()

    @pytest.fixture
    def smtp_provider(self, mock_fastmail):
        """Create an SMTP email provider instance."""
        with patch("server.auth.email_providers.smtp.FastMail", return_value=mock_fastmail):
            config = {
                "host": "smtp.example.com",
                "port": "587",
                "username": "test@example.com",
                "password": "password",
            }
            return SMTPEmailProvider(config)

    @pytest.mark.asyncio
    async def test_send_email_success(self, smtp_provider, mock_fastmail):
        """Test successful email sending via SMTP."""
        # Configure mock to succeed
        mock_fastmail.send_message = AsyncMock(return_value=None)

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
        assert result.provider == "SMTP"

        # Verify send_message was called
        mock_fastmail.send_message.assert_called_once()

        # Check the message that was sent
        call_args = mock_fastmail.send_message.call_args[0][0]
        assert call_args.subject == "Test Subject"
        assert "test@example.com" in str(call_args.recipients)
        assert call_args.body == "<p>Test content</p>"

    @pytest.mark.asyncio
    async def test_send_email_failure(self, smtp_provider, mock_fastmail):
        """Test email sending failure via SMTP."""
        # Configure mock to raise exception
        mock_fastmail.send_message = AsyncMock(side_effect=Exception("SMTP connection failed"))

        # Create email message
        message = EmailMessage(
            to=["test@example.com"],
            subject="Test Subject",
            html_body="<p>Test content</p>",
        )

        # Send email - should raise EmailDeliveryError
        with pytest.raises(EmailDeliveryError) as exc_info:
            await smtp_provider.send_email(message)

        # Check that it's an SMTP-related error
        error_message = str(exc_info.value)
        assert "SMTP" in error_message
        assert "connection failed" in error_message.lower()

        # Verify send_message was called
        mock_fastmail.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_email_service_uses_console_provider():
    """Test that email service uses console provider when SMTP is not configured."""
    with patch("server.auth.email.get_settings") as mock_settings:
        with patch("server.auth.email.get_email_provider_from_env") as mock_env:
            # Configure settings to disable email
            mock_settings.return_value = {
                "email_enabled": False,
                "email_username": "",
                "email_password": "",
                "frontend_url": "http://localhost:8090",
            }

            # Mock env to return console config
            mock_env.return_value = {
                "provider": "console",
                "format": "pretty",
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
    with patch("server.auth.email.get_settings") as mock_settings:
        with patch("server.auth.email.get_email_provider_from_env") as mock_env:
            with patch("server.auth.email_providers.smtp.FastMail"):
                # Configure settings to enable email
                mock_settings.return_value = {
                    "email_enabled": True,
                    "email_username": "test@example.com",
                    "email_password": "password123",
                    "email_host": "smtp.example.com",
                    "email_port": 587,
                    "email_from": "noreply@example.com",
                    "email_from_name": "Test App",
                    "frontend_url": "http://localhost:8090",
                }

                # Mock env to return SMTP config
                mock_env.return_value = {
                    "provider": "smtp",
                    "host": "smtp.example.com",
                    "port": "587",
                    "username": "test@example.com",
                    "password": "password123",
                }

                # Import after patching
                from server.auth.email import EmailService

                # Create service
                service = EmailService()

                # Check that SMTP provider is used
                assert isinstance(service.provider, SMTPEmailProvider)
