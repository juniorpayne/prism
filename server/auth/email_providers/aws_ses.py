#!/usr/bin/env python3
"""
AWS SES email provider implementation.

Supports sending emails through Amazon Simple Email Service (SES)
with IAM role support for EC2 instances and explicit credentials
for development environments.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from .base import EmailMessage, EmailProvider, EmailResult
from .config import AWSSESConfig

logger = logging.getLogger(__name__)


class AWSSESEmailProvider(EmailProvider):
    """
    AWS SES email provider for sending emails through Amazon SES.

    Supports:
    - Standard SMTP-like send_email API
    - IAM role authentication (for EC2)
    - Explicit credentials (for development)
    - Configuration sets for tracking
    - Async sending with proper error handling
    """

    def __init__(self, config: AWSSESConfig):
        """
        Initialize AWS SES email provider.

        Args:
            config: AWS SES configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._client = None

    @property
    def client(self):
        """Lazy load SES client."""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _create_client(self):
        """
        Create SES client with appropriate credentials.

        Returns:
            boto3 SES client

        Raises:
            BotoCoreError: If client creation fails
        """
        session_kwargs = {"region_name": self.config.region}

        # Use explicit credentials if provided and not using IAM role
        if not self.config.use_iam_role:
            if self.config.access_key_id and self.config.secret_access_key:
                session_kwargs.update(
                    {
                        "aws_access_key_id": self.config.access_key_id,
                        "aws_secret_access_key": self.config.secret_access_key,
                    }
                )
                if self.config.session_token:
                    session_kwargs["aws_session_token"] = self.config.session_token

        session = boto3.Session(**session_kwargs)

        # Create client with custom endpoint if specified (for testing)
        client_kwargs = {}
        if self.config.endpoint_url:
            client_kwargs["endpoint_url"] = self.config.endpoint_url
        if not self.config.verify_ssl:
            client_kwargs["verify"] = False

        return session.client("ses", **client_kwargs)

    async def send_email(self, message: EmailMessage) -> EmailResult:
        """
        Send email via AWS SES with suppression check.

        Args:
            message: Email message to send

        Returns:
            EmailResult with success status and details
        """
        try:
            # Check suppression list first
            suppressed_emails = await self._check_suppressions(message.to)
            if suppressed_emails:
                self.logger.warning(f"Email(s) suppressed: {', '.join(suppressed_emails)}")
                return EmailResult(
                    success=False,
                    error=f"Recipients are suppressed: {', '.join(suppressed_emails)}",
                    provider="aws_ses",
                    metadata={"suppressed_emails": suppressed_emails},
                )

            # Prepare SES parameters
            ses_params = self._prepare_ses_params(message)

            # Send email asynchronously
            response = await self._send_ses_email(ses_params)

            return EmailResult(
                success=True,
                message_id=response["MessageId"],
                provider="aws_ses",
                metadata={
                    "ses_message_id": response["MessageId"],
                    "request_id": response["ResponseMetadata"]["RequestId"],
                },
            )

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            self.logger.error(f"SES ClientError: {error_code} - {error_message}")

            return EmailResult(
                success=False,
                error=self._get_user_friendly_error(error_code, error_message),
                provider="aws_ses",
                metadata={"error_code": error_code},
            )

        except Exception as e:
            self.logger.error(f"Unexpected error sending SES email: {e}")
            return EmailResult(
                success=False,
                error=f"Failed to send email: {str(e)}",
                provider="aws_ses",
            )

    def _prepare_ses_params(self, message: EmailMessage) -> Dict[str, Any]:
        """
        Prepare parameters for SES send_email API.

        Args:
            message: Email message

        Returns:
            Dictionary of SES parameters
        """
        # Use message from_email/from_name or fall back to config
        from_email = message.from_email or self.config.from_email
        from_name = message.from_name or self.config.from_name

        params = {
            "Source": f"{from_name} <{from_email}>" if from_name else from_email,
            "Destination": {"ToAddresses": message.to},
            "Message": {
                "Subject": {"Data": message.subject, "Charset": "UTF-8"},
                "Body": {},
            },
        }

        # Add CC recipients
        if message.cc:
            params["Destination"]["CcAddresses"] = message.cc

        # Add body parts
        if message.text_body:
            params["Message"]["Body"]["Text"] = {
                "Data": message.text_body,
                "Charset": "UTF-8",
            }

        if message.html_body:
            params["Message"]["Body"]["Html"] = {
                "Data": message.html_body,
                "Charset": "UTF-8",
            }

        # Add configuration set if specified
        if self.config.configuration_set:
            params["ConfigurationSetName"] = self.config.configuration_set

        # Add reply-to
        if message.reply_to:
            params["ReplyToAddresses"] = [message.reply_to]

        # Add custom headers as tags (SES limitation)
        if message.headers:
            params["Tags"] = [{"Name": k, "Value": v} for k, v in message.headers.items()]

        return params

    async def _send_ses_email(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send email using SES client.

        Args:
            params: SES send_email parameters

        Returns:
            SES response dictionary

        Raises:
            ClientError: If SES API call fails
        """
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.client.send_email(**params))

    def _get_user_friendly_error(self, error_code: str, error_message: str) -> str:
        """
        Convert SES errors to user-friendly messages.

        Args:
            error_code: AWS error code
            error_message: AWS error message

        Returns:
            User-friendly error message
        """
        error_map = {
            "MessageRejected": "Email was rejected. Please check the content.",
            "MailFromDomainNotVerified": "Sender domain is not verified in SES.",
            "ConfigurationSetDoesNotExist": "SES configuration set not found.",
            "AccountSendingPausedException": "Email sending is paused for this account.",
            "SendingQuotaExceeded": "Daily email sending limit reached.",
            "MaxSendingRateExceeded": "Sending emails too quickly. Please slow down.",
        }

        return error_map.get(error_code, f"SES Error: {error_message}")

    async def verify_configuration(self) -> bool:
        """
        Verify SES configuration by checking access and configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            # Try to describe configuration set if specified
            if self.config.configuration_set:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.describe_configuration_set(
                        ConfigurationSetName=self.config.configuration_set
                    ),
                )
            else:
                # Otherwise just check send quota
                await asyncio.get_event_loop().run_in_executor(None, self.client.get_send_quota)

            self.logger.info("SES configuration verified successfully")
            return True

        except ClientError as e:
            self.logger.error(f"SES configuration verification failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error verifying SES configuration: {e}")
            return False

    async def _check_suppressions(self, recipients: list[str]) -> list[str]:
        """
        Check if any recipients are in suppression list.

        Args:
            recipients: List of email addresses to check

        Returns:
            List of suppressed email addresses
        """
        try:
            # Import the models directly by file path to avoid import conflicts
            import importlib.util
            import os
            from datetime import datetime, timezone

            from sqlalchemy import or_, select

            spec = importlib.util.spec_from_file_location(
                "email_events",
                os.path.join(
                    os.path.dirname(os.path.dirname(__file__)), "models", "email_events.py"
                ),
            )
            email_events = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(email_events)
            EmailSuppression = email_events.EmailSuppression

            from server.database.connection import get_async_db

            suppressed = []
            async for db in get_async_db():
                # Check for active suppressions
                result = await db.execute(
                    select(EmailSuppression.email).where(
                        EmailSuppression.email.in_([r.lower() for r in recipients]),
                        or_(
                            EmailSuppression.expires_at.is_(None),
                            EmailSuppression.expires_at > datetime.now(timezone.utc),
                        ),
                    )
                )
                rows = result.fetchall()
                suppressed = [row[0] for row in rows]
                break  # Only need one iteration

            return suppressed
        except Exception as e:
            # Log error but don't fail sending - suppressions are optional
            self.logger.error(f"Error checking suppressions: {e}")
            return []

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "aws_ses"

    def __repr__(self) -> str:
        """String representation."""
        return f"<AWSSESEmailProvider region={self.config.region}>"
