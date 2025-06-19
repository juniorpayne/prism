#!/usr/bin/env python3
"""
Enhanced SMTP email provider with connection pooling, retry logic, and circuit breaker.
"""

import asyncio
import logging
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Optional

import aiosmtplib
from aiosmtplib import SMTPException

from .base import EmailMessage, EmailProvider, EmailResult
from .circuit_breaker import CircuitBreaker
from .config import SMTPEmailConfig
from .retry import RetryConfig, with_retry
from .smtp import SMTPErrorHandler
from .smtp_pool import SMTPConnectionPool

logger = logging.getLogger(__name__)


class EnhancedSMTPEmailProvider(EmailProvider):
    """
    Enhanced SMTP email provider with advanced features.

    Features:
    - Connection pooling for better performance
    - Automatic retry with exponential backoff
    - Circuit breaker to prevent cascading failures
    - Improved error handling and recovery
    """

    def __init__(self, config: SMTPEmailConfig):
        """
        Initialize enhanced SMTP email provider.

        Args:
            config: SMTP configuration with pool and retry settings
        """
        self.config = config
        self.logger = logger

        # Initialize connection pool
        self.pool = SMTPConnectionPool(
            config=config,
            max_size=config.pool_size,
        )
        self.pool.max_idle_time = config.pool_max_idle_time

        # Initialize retry configuration
        self.retry_config = RetryConfig(
            max_attempts=config.retry_max_attempts,
            initial_delay=config.retry_initial_delay,
            max_delay=config.retry_max_delay,
            exponential_base=config.retry_exponential_base,
        )

        # Initialize circuit breaker if enabled
        if config.circuit_breaker_enabled:
            self.circuit_breaker = CircuitBreaker(
                failure_threshold=config.circuit_breaker_threshold,
                recovery_timeout=config.circuit_breaker_timeout,
                expected_exception=SMTPException,
            )
        else:
            self.circuit_breaker = None

    async def send_email(self, message: EmailMessage) -> EmailResult:
        """
        Send email via SMTP with retry and circuit breaker.

        Args:
            message: Email message to send

        Returns:
            EmailResult with success status and details
        """
        try:
            # Send through circuit breaker if enabled
            if self.circuit_breaker:
                result = await self.circuit_breaker.call(self._send_with_retry, message)
            else:
                result = await self._send_with_retry(message)

            return result

        except Exception as e:
            # Handle circuit breaker open
            if "Circuit breaker is OPEN" in str(e):
                self.logger.error("Circuit breaker is open, email sending disabled")
                return EmailResult(
                    success=False,
                    error="Email service temporarily unavailable",
                    provider="smtp",
                    metadata={"circuit_breaker": "open"},
                )

            # Other errors
            self.logger.error(f"Failed to send email: {e}")
            return EmailResult(
                success=False,
                error=SMTPErrorHandler.get_user_friendly_error(e),
                provider="smtp",
            )

    async def _send_with_retry(self, message: EmailMessage) -> EmailResult:
        """
        Send email with retry logic.

        Args:
            message: Email message to send

        Returns:
            EmailResult
        """
        last_exception = None

        for attempt in range(self.retry_config.max_attempts):
            try:
                return await self._send_email_internal(message)
            except Exception as e:
                last_exception = e

                if attempt == self.retry_config.max_attempts - 1:
                    raise

                # Calculate delay
                delay = min(
                    self.retry_config.initial_delay * (self.retry_config.exponential_base**attempt),
                    self.retry_config.max_delay,
                )

                # Add jitter
                if self.retry_config.jitter:
                    import random

                    delay *= 0.5 + random.random()

                self.logger.warning(
                    f"Attempt {attempt + 1} failed: {e}. " f"Retrying in {delay:.2f} seconds..."
                )

                await asyncio.sleep(delay)

        raise last_exception

    async def _send_email_internal(self, message: EmailMessage) -> EmailResult:
        """
        Internal method to send email using connection pool.

        Args:
            message: Email message to send

        Returns:
            EmailResult
        """
        async with self.pool.get_connection() as smtp:
            # Create MIME message
            mime_message = self._create_mime_message(message)

            # Send using pooled connection
            response = await self._send_smtp_pooled(smtp, mime_message, message.to)

            return EmailResult(
                success=True,
                message_id=response.get("message_id"),
                provider="smtp",
                metadata={
                    "smtp_response": str(response),
                    "pool_status": repr(self.pool),
                },
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

    async def _send_smtp_pooled(
        self,
        smtp: aiosmtplib.SMTP,
        message: MIMEMultipart,
        recipients: list,
    ) -> dict:
        """
        Send message using pooled SMTP connection.

        Args:
            smtp: Pooled SMTP connection
            message: MIME message to send
            recipients: List of recipient addresses

        Returns:
            SMTP response dictionary
        """
        # Send message using the pooled connection
        response = await smtp.send_message(
            message,
            sender=message["From"],
            recipients=recipients,
        )

        return response

    async def verify_configuration(self) -> bool:
        """
        Verify SMTP configuration by testing a connection.

        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            # Try to create a connection
            async with self.pool.get_connection() as smtp:
                self.logger.info("SMTP configuration verified successfully")
                return True
        except Exception as e:
            self.logger.error(f"SMTP configuration verification failed: {e}")
            return False

    async def close(self) -> None:
        """Close the connection pool and cleanup resources."""
        await self.pool.close()
        if self.circuit_breaker:
            self.circuit_breaker.reset()

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "smtp"

    def get_status(self) -> dict:
        """
        Get provider status information.

        Returns:
            Status dictionary
        """
        status = {
            "provider": "smtp",
            "pool": repr(self.pool),
            "circuit_breaker": None,
        }

        if self.circuit_breaker:
            status["circuit_breaker"] = {
                "state": self.circuit_breaker.state.value,
                "failures": self.circuit_breaker.failure_count,
                "threshold": self.circuit_breaker.failure_threshold,
            }

        return status

    def __repr__(self) -> str:
        """String representation."""
        return f"<EnhancedSMTPEmailProvider host={self.config.host}:{self.config.port} {self.pool}>"
