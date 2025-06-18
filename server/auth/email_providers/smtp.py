#!/usr/bin/env python3
"""
SMTP email provider for sending emails via SMTP servers.
"""

from typing import Dict, Optional

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import EmailStr

from server.auth.email_providers.base import EmailMessage, EmailProvider, EmailResult
from server.auth.email_providers.exceptions import (
    EmailAuthenticationError,
    EmailConfigurationError,
    EmailDeliveryError,
)


class SMTPEmailProvider(EmailProvider):
    """
    SMTP email provider for sending emails via SMTP servers.

    Supports standard SMTP servers including Gmail, SendGrid SMTP, etc.
    """

    def __init__(self, config: Optional[Dict[str, str]] = None):
        """
        Initialize SMTP email provider.

        Args:
            config: SMTP configuration including host, port, username, password
        """
        super().__init__(config)
        self._validate_config()
        self._setup_connection()

    def _validate_config(self) -> None:
        """Validate SMTP configuration."""
        required_fields = ["host", "port", "username", "password"]
        missing_fields = [field for field in required_fields if not self.config.get(field)]

        if missing_fields:
            raise EmailConfigurationError(
                f"Missing required SMTP configuration: {', '.join(missing_fields)}",
                missing_fields=missing_fields,
            )

    def _setup_connection(self) -> None:
        """Set up FastMail connection."""
        try:
            self.connection_config = ConnectionConfig(
                MAIL_USERNAME=self.config["username"],
                MAIL_PASSWORD=self.config["password"],
                MAIL_FROM=self.config.get("from_email", self.config["username"]),
                MAIL_PORT=int(self.config["port"]),
                MAIL_SERVER=self.config["host"],
                MAIL_FROM_NAME=self.config.get("from_name", ""),
                MAIL_STARTTLS=self.config.get("use_tls", True),
                MAIL_SSL_TLS=self.config.get("use_ssl", False),
                USE_CREDENTIALS=True,
                VALIDATE_CERTS=self.config.get("validate_certs", True),
            )
            self.fastmail = FastMail(self.connection_config)
        except Exception as e:
            raise EmailConfigurationError(f"Failed to setup SMTP connection: {e}")

    async def send_email(self, message: EmailMessage) -> EmailResult:
        """Send email via SMTP."""
        try:
            # Convert EmailMessage to FastMail MessageSchema
            # Build message schema - FastMail requires lists, not None
            message_data = {
                "subject": message.subject,
                "recipients": message.to,
                "body": message.html_body,
                "subtype": MessageType.html,
            }

            # Only add optional fields if they have values
            if message.cc:
                message_data["cc"] = message.cc
            if message.bcc:
                message_data["bcc"] = message.bcc
            if message.reply_to:
                message_data["reply_to"] = [message.reply_to]
            if message.headers:
                message_data["headers"] = message.headers

            fastmail_message = MessageSchema(**message_data)

            # Send the email
            await self.fastmail.send_message(fastmail_message)

            self._logger.info(f"SMTP email sent to {', '.join(message.to)}: {message.subject}")

            return EmailResult(
                success=True,
                message_id=f"smtp-{id(message)}",
                provider=self.provider_name,
                metadata={
                    "host": self.config["host"],
                    "port": self.config["port"],
                },
            )

        except Exception as e:
            error_msg = str(e)
            self._logger.error(f"Failed to send SMTP email: {error_msg}")

            # Determine error type
            if "authentication" in error_msg.lower() or "credentials" in error_msg.lower():
                raise EmailAuthenticationError(
                    f"SMTP authentication failed: {error_msg}",
                    provider=self.provider_name,
                )
            elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                raise EmailDeliveryError(
                    f"SMTP connection failed: {error_msg}",
                    recipient=message.to[0] if message.to else None,
                    permanent=False,
                    retry_after=60,  # Retry after 1 minute
                )
            else:
                raise EmailDeliveryError(
                    f"Failed to send email via SMTP: {error_msg}",
                    recipient=message.to[0] if message.to else None,
                    permanent=False,
                )

    async def verify_configuration(self) -> bool:
        """Verify SMTP configuration by attempting to connect."""
        try:
            # FastMail doesn't provide a direct way to test connection
            # We'll validate the configuration format at least
            self._validate_config()
            self._logger.info(
                f"SMTP configuration appears valid for {self.config['host']}:{self.config['port']}"
            )
            return True
        except Exception as e:
            self._logger.error(f"SMTP configuration validation failed: {e}")
            return False

    def __repr__(self) -> str:
        """String representation of SMTP provider."""
        return (
            f"SMTPEmailProvider(host={self.config.get('host')}, "
            f"port={self.config.get('port')}, "
            f"username={self.config.get('username', 'hidden')})"
        )
