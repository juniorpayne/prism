#!/usr/bin/env python3
"""
Email service for sending verification and password reset emails.
"""

import logging
from datetime import datetime
from typing import Optional

from pydantic import EmailStr

from server.auth.config import get_settings
from server.auth.email_providers import (
    EmailMessage,
    EmailPriority,
    EmailProvider,
    EmailProviderFactory,
    EmailResult,
)
from server.auth.email_providers.config import EmailProviderType
from server.auth.email_providers.config_loader import get_config_loader
from server.auth.email_providers.validators import validate_config_for_environment
from server.auth.email_templates import get_template_service

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails."""

    def __init__(self):
        """Initialize email service."""
        self.settings = get_settings()

        # Get configuration loader
        config_loader = get_config_loader()

        # Load email configuration
        try:
            email_config = config_loader.load_config()

            # Validate configuration for current environment
            warnings = validate_config_for_environment(email_config, config_loader.env)
            for warning in warnings:
                logger.warning(f"Email config warning: {warning}")

            # Log configuration info
            config_info = config_loader.get_config_info()
            logger.info(f"Email configuration loaded: {config_info}")

        except Exception as e:
            logger.error(f"Failed to load email configuration: {e}")
            # Fall back to console provider
            from server.auth.email_providers.config import ConsoleEmailConfig

            email_config = ConsoleEmailConfig(
                provider=EmailProviderType.CONSOLE,
                from_email=self.settings.get("email_from", "noreply@prism.local"),
                from_name=self.settings.get("email_from_name", "Prism DNS"),
                reply_to=self.settings.get("email_reply_to"),
            )
            logger.info("Using fallback console email provider")

        # Create provider using factory
        self.provider = EmailProviderFactory.create_from_email_config(email_config)

        # Store config for later use
        self.email_config = email_config
        # Ensure provider is an EmailProviderType enum
        if isinstance(self.email_config.provider, str):
            self.email_config.provider = EmailProviderType(self.email_config.provider)

        # Initialize template service
        self.template_service = get_template_service()

        logger.info(f"Email service initialized with {self.provider.provider_name} provider")

        # Log email configuration details
        logger.info("Email Configuration Details:")
        logger.info(f"  Provider: {self.email_config.provider}")
        logger.info(f"  From Address: {self.email_config.from_email}")
        if self.email_config.from_name:
            logger.info(f"  From Name: {self.email_config.from_name}")
        if self.email_config.reply_to:
            logger.info(f"  Reply To: {self.email_config.reply_to}")
        if hasattr(self.email_config, "host"):
            logger.info(f"  SMTP Host: {self.email_config.host}:{self.email_config.port}")
        if hasattr(self.email_config, "region"):
            logger.info(f"  AWS Region: {self.email_config.region}")
        logger.info("-------------------------------------")

    async def send_verification_email(self, email: EmailStr, username: str, token: str) -> None:
        """
        Send email verification email.

        Args:
            email: Recipient email
            username: Username
            token: Verification token
        """
        settings = get_settings()
        frontend_url = settings.get("frontend_url", "http://localhost:8090")
        verification_url = f"{frontend_url}/verify-email?token={token}"

        # Render email template
        html_body, text_body = await self.template_service.render_email(
            "email_verification/verify_email",
            {
                "username": username,
                "verification_url": verification_url,
                "expiry_hours": 24,
            },
        )

        # Create email message
        message = EmailMessage(
            to=[email],
            subject="Verify your Prism DNS account",
            html_body=html_body,
            text_body=text_body,
            from_email=self.email_config.from_email,
            from_name=self.email_config.from_name,
            reply_to=self.email_config.reply_to,
        )

        # Send email
        result = await self.provider.send_email(message)

        if not result.success:
            logger.error(f"Failed to send verification email: {result.error}")

    async def send_password_reset_email(
        self,
        email: EmailStr,
        username: str,
        token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Send password reset email.

        Args:
            email: Recipient email
            username: Username
            token: Reset token
            ip_address: Request IP address
            user_agent: Request user agent
        """
        settings = get_settings()
        frontend_url = settings.get("frontend_url", "http://localhost:8090")
        reset_url = f"{frontend_url}/reset-password?token={token}"

        # Render email template
        html_body, text_body = await self.template_service.render_email(
            "password_reset/reset_request",
            {
                "username": username,
                "reset_url": reset_url,
                "expiry_hours": 1,
                "request_ip": ip_address or "Unknown",
            },
        )

        # Create email message
        message = EmailMessage(
            to=[email],
            subject="Reset your Prism DNS password",
            html_body=html_body,
            text_body=text_body,
            from_email=self.email_config.from_email,
            from_name=self.email_config.from_name,
            reply_to=self.email_config.reply_to,
            metadata={
                "ip_address": ip_address,
                "user_agent": user_agent,
            },
        )

        # Send email
        result = await self.provider.send_email(message)

        if not result.success:
            logger.error(f"Failed to send password reset email: {result.error}")

    async def send_password_changed_email(
        self,
        email: EmailStr,
        username: str,
        ip_address: Optional[str] = None,
        device_info: Optional[str] = None,
    ) -> None:
        """
        Send password changed confirmation email.

        Args:
            email: Recipient email
            username: Username
            ip_address: IP address where change was made
            device_info: Device/browser information
        """
        change_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

        # Render email template
        html_body, text_body = await self.template_service.render_email(
            "password_reset/reset_success",
            {
                "username": username,
                "change_date": change_date,
                "change_ip": ip_address or "Unknown",
                "device_info": device_info or "Unknown device",
            },
        )

        # Create email message
        message = EmailMessage(
            to=[email],
            subject="Your Prism DNS password has been changed",
            html_body=html_body,
            text_body=text_body,
            from_email=self.email_config.from_email,
            from_name=self.email_config.from_name,
            reply_to=self.email_config.reply_to,
            priority=EmailPriority.HIGH,  # Security notifications are high priority
        )

        # Send email
        result = await self.provider.send_email(message)

        if not result.success:
            logger.error(f"Failed to send password changed email: {result.error}")

    async def send_welcome_email(self, email: EmailStr, username: str) -> None:
        """
        Send welcome email after successful verification.

        Args:
            email: Recipient email
            username: Username
        """
        # Render email template
        html_body, text_body = await self.template_service.render_email(
            "welcome/welcome",
            {
                "username": username,
            },
        )

        # Create email message
        message = EmailMessage(
            to=[email],
            subject=f"Welcome to {self.template_service.app_name}!",
            html_body=html_body,
            text_body=text_body,
            from_email=self.email_config.from_email,
            from_name=self.email_config.from_name,
            reply_to=self.email_config.reply_to,
        )

        # Send email
        result = await self.provider.send_email(message)

        if not result.success:
            logger.error(f"Failed to send welcome email: {result.error}")

    async def send_security_alert_email(
        self,
        email: EmailStr,
        username: str,
        login_date: str,
        device_info: str,
        browser_info: str,
        login_ip: str,
        location: Optional[str] = None,
    ) -> None:
        """
        Send security alert for new device login.

        Args:
            email: Recipient email
            username: Username
            login_date: Date/time of login
            device_info: Device information
            browser_info: Browser information
            login_ip: IP address of login
            location: Location of login (if available)
        """
        # Render email template
        html_body, text_body = await self.template_service.render_email(
            "security/new_device",
            {
                "username": username,
                "login_date": login_date,
                "device_info": device_info,
                "browser_info": browser_info,
                "login_ip": login_ip,
                "location": location or "Unknown location",
            },
        )

        # Create email message
        message = EmailMessage(
            to=[email],
            subject="Security Alert - New Device Login",
            html_body=html_body,
            text_body=text_body,
            from_email=self.email_config.from_email,
            from_name=self.email_config.from_name,
            reply_to=self.email_config.reply_to,
            priority=EmailPriority.HIGH,  # Security alerts are high priority
        )

        # Send email
        result = await self.provider.send_email(message)

        if not result.success:
            logger.error(f"Failed to send security alert email: {result.error}")

    async def send_account_deletion_email(
        self,
        email: EmailStr,
        username: str,
        deletion_date: str,
        request_ip: Optional[str] = None,
    ) -> None:
        """
        Send account deletion confirmation email.

        Args:
            email: Recipient email
            username: Username
            deletion_date: Date of deletion
            request_ip: IP address that requested deletion
        """
        # Render email template
        html_body, text_body = await self.template_service.render_email(
            "account/deletion_confirm",
            {
                "username": username,
                "email": email,
                "deletion_date": deletion_date,
                "request_ip": request_ip or "Unknown",
            },
        )

        # Create email message
        message = EmailMessage(
            to=[email],
            subject="Account Deleted - Prism DNS",
            html_body=html_body,
            text_body=text_body,
            from_email=self.email_config.from_email,
            from_name=self.email_config.from_name,
            reply_to=self.email_config.reply_to,
        )

        # Send email
        result = await self.provider.send_email(message)

        if not result.success:
            logger.error(f"Failed to send account deletion email: {result.error}")


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
