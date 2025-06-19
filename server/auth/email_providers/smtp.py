#!/usr/bin/env python3
"""
SMTP email provider implementation using aiosmtplib.
"""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Dict, Optional

import aiosmtplib
from aiosmtplib import SMTPException

from .base import EmailMessage, EmailProvider, EmailResult
from .config import SMTPEmailConfig


class SMTPErrorHandler:
    """Handle SMTP errors and provide user-friendly messages."""

    @staticmethod
    def get_user_friendly_error(error: Exception) -> str:
        """Convert SMTP errors to user-friendly messages."""
        error_str = str(error).lower()

        if "authentication" in error_str or "535" in error_str:
            return "Email authentication failed. Please check SMTP credentials."
        elif "connection" in error_str or "timeout" in error_str:
            return "Could not connect to email server. Please check SMTP settings."
        elif "550" in error_str:
            return "Email rejected by server. Please verify sender address."
        elif "tls" in error_str or "ssl" in error_str:
            return "Email security negotiation failed. Check TLS/SSL settings."
        else:
            return f"Email sending failed: {error}"


class SMTPEmailProvider(EmailProvider):
    """
    SMTP email provider for sending emails through SMTP servers.

    Supports:
    - Standard SMTP servers (Gmail, SendGrid, etc.)
    - TLS and SSL encryption
    - Authentication
    - Async sending
    """

    def __init__(self, config: SMTPEmailConfig):
        """
        Initialize SMTP email provider.

        Args:
            config: SMTP configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

    async def send_email(self, message: EmailMessage) -> EmailResult:
        """
        Send email via SMTP.

        Args:
            message: Email message to send

        Returns:
            EmailResult with success status and details
        """
        try:
            # Create MIME message
            mime_message = self._create_mime_message(message)

            # Send email
            response = await self._send_smtp(mime_message, message.to)

            return EmailResult(
                success=True,
                message_id=response.get("message_id"),
                provider="smtp",
                metadata={"smtp_response": str(response)},
            )

        except SMTPException as e:
            self.logger.error(f"SMTP error: {e}")
            return EmailResult(
                success=False,
                error=f"SMTP error: {str(e)}",
                provider="smtp",
            )
        except Exception as e:
            self.logger.error(f"Unexpected error sending email: {e}")
            return EmailResult(
                success=False,
                error=f"Failed to send email: {str(e)}",
                provider="smtp",
            )

    def _create_mime_message(self, message: EmailMessage) -> MIMEMultipart:
        """
        Create MIME message from EmailMessage.

        Args:
            message: Email message

        Returns:
            MIME multipart message
        """
        msg = MIMEMultipart("alternative")

        # Set headers
        msg["Subject"] = message.subject

        # Use message from_email/from_name or fall back to config
        from_email = message.from_email or self.config.from_email
        from_name = message.from_name or self.config.from_name
        msg["From"] = formataddr((from_name, from_email))
        msg["To"] = ", ".join(message.to)

        if message.cc:
            msg["CC"] = ", ".join(message.cc)

        if message.reply_to:
            msg["Reply-To"] = message.reply_to

        # Add custom headers
        if message.headers:
            for key, value in message.headers.items():
                msg[key] = value

        # Add text and HTML parts
        if message.text_body:
            text_part = MIMEText(message.text_body, "plain", "utf-8")
            msg.attach(text_part)

        if message.html_body:
            html_part = MIMEText(message.html_body, "html", "utf-8")
            msg.attach(html_part)

        return msg

    async def _send_smtp(self, message: MIMEMultipart, recipients: list) -> dict:
        """
        Send message via SMTP.

        Args:
            message: MIME message to send
            recipients: List of recipient email addresses

        Returns:
            SMTP response dictionary
        """
        # Configure connection
        kwargs = {
            "hostname": self.config.host,
            "port": self.config.port,
            "timeout": self.config.timeout,
        }

        # Add TLS/SSL settings
        if self.config.use_ssl:
            kwargs["use_tls"] = True
            kwargs["start_tls"] = False
        elif self.config.use_tls:
            kwargs["use_tls"] = False
            kwargs["start_tls"] = True

        # Add authentication
        if self.config.username and self.config.password:
            kwargs["username"] = self.config.username
            kwargs["password"] = self.config.password

        # Send email
        response = await aiosmtplib.send(
            message,
            recipients=recipients,
            sender=message["From"],
            **kwargs,
        )

        return response

    async def verify_configuration(self) -> bool:
        """
        Verify SMTP configuration by connecting to server.

        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            async with aiosmtplib.SMTP(
                hostname=self.config.host,
                port=self.config.port,
                timeout=10,
            ) as smtp:
                # Try to connect
                if self.config.use_tls:
                    await smtp.starttls()

                # Try to authenticate if credentials provided
                if self.config.username and self.config.password:
                    await smtp.login(self.config.username, self.config.password)

                self.logger.info("SMTP configuration verified successfully")
                return True

        except Exception as e:
            self.logger.error(f"SMTP configuration verification failed: {e}")
            return False

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "smtp"

    def __repr__(self) -> str:
        """String representation."""
        return f"<SMTPEmailProvider host={self.config.host}:{self.config.port}>"
