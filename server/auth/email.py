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
from server.auth.email_providers.utils import get_email_provider_from_env
from server.auth.email_templates import get_template_service

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails."""

    def __init__(self):
        """Initialize email service."""
        self.settings = get_settings()

        # Get email configuration from environment or settings
        email_config = get_email_provider_from_env()

        # Override with settings if email is disabled
        if not self.settings.get("email_enabled"):
            email_config["provider"] = "console"
            logger.info("Email disabled in settings, using console provider")

        # Create provider using factory
        self.provider = EmailProviderFactory.create_provider(email_config["provider"], email_config)

        # Initialize template service
        self.template_service = get_template_service()

        logger.info(f"Email service initialized with {self.provider.provider_name} provider")

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
            from_email=self.settings.get("email_from", "noreply@prismdns.com"),
            from_name=self.settings.get("email_from_name", "Prism DNS"),
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
            from_email=self.settings.get("email_from", "noreply@prismdns.com"),
            from_name=self.settings.get("email_from_name", "Prism DNS"),
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
            from_email=self.settings.get("email_from", "noreply@prismdns.com"),
            from_name=self.settings.get("email_from_name", "Prism DNS"),
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
            from_email=self.settings.get("email_from", "noreply@prismdns.com"),
            from_name=self.settings.get("email_from_name", "Prism DNS"),
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
            from_email=self.settings.get("email_from", "noreply@prismdns.com"),
            from_name=self.settings.get("email_from_name", "Prism DNS"),
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
            from_email=self.settings.get("email_from", "noreply@prismdns.com"),
            from_name=self.settings.get("email_from_name", "Prism DNS"),
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
