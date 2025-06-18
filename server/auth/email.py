#!/usr/bin/env python3
"""
Email service for sending verification and password reset emails.
"""

import logging
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

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #4CAF50;">Welcome to Prism DNS!</h2>
                <p>Hi {username},</p>
                <p>Thank you for registering with Prism DNS. To complete your registration, 
                please verify your email address by clicking the button below:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" 
                       style="background-color: #4CAF50; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Verify Email Address
                    </a>
                </div>
                
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #666;">
                    {verification_url}
                </p>
                
                <p><strong>This link will expire in 24 hours.</strong></p>
                
                <p>If you didn't create an account with Prism DNS, you can safely ignore this email.</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="color: #666; font-size: 12px;">
                    This is an automated message from Prism DNS. Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """

        # Create email message
        message = EmailMessage(
            to=[email],
            subject="Verify your Prism DNS account",
            html_body=html,
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

        # Get current time
        from datetime import datetime

        request_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #FF9800;">Password Reset Request</h2>
                <p>Hi {username},</p>
                <p>We received a request to reset your password for your Prism DNS account.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" 
                       style="background-color: #FF9800; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Reset Password
                    </a>
                </div>
                
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #666;">
                    {reset_url}
                </p>
                
                <p><strong>This link will expire in 1 hour.</strong></p>
                
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 0; font-size: 14px;"><strong>Security Information:</strong></p>
                    <ul style="margin: 10px 0 0 0; padding-left: 20px; font-size: 14px;">
                        <li>Time: {request_time}</li>
                        {f'<li>IP Address: {ip_address}</li>' if ip_address else ''}
                        {f'<li>Browser: {user_agent[:50]}...</li>' if user_agent else ''}
                    </ul>
                </div>
                
                <p>If you didn't request this password reset, please ignore this email and your 
                password will remain unchanged. You may want to review your account for any 
                unauthorized access.</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="color: #666; font-size: 12px;">
                    This is an automated message from Prism DNS. Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """

        # Create email message
        message = EmailMessage(
            to=[email],
            subject="Reset your Prism DNS password",
            html_body=html,
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

    async def send_password_changed_email(self, email: EmailStr, username: str) -> None:
        """
        Send password changed confirmation email.

        Args:
            email: Recipient email
            username: Username
        """
        from datetime import datetime

        change_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2196F3;">Password Changed Successfully</h2>
                <p>Hi {username},</p>
                <p>Your password has been successfully changed.</p>
                
                <div style="background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Changed at:</strong> {change_time}</p>
                </div>
                
                <p><strong>Security Notice:</strong> For your security, all devices have been 
                logged out. You'll need to sign in again with your new password.</p>
                
                <p>If you didn't make this change, please contact our support team immediately 
                and consider taking these steps:</p>
                <ul>
                    <li>Reset your password again</li>
                    <li>Review your recent account activity</li>
                    <li>Enable two-factor authentication</li>
                </ul>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="color: #666; font-size: 12px;">
                    This is an automated security notification from Prism DNS. 
                    Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """

        # Create email message
        message = EmailMessage(
            to=[email],
            subject="Your Prism DNS password has been changed",
            html_body=html,
            from_email=self.settings.get("email_from", "noreply@prismdns.com"),
            from_name=self.settings.get("email_from_name", "Prism DNS"),
            priority=EmailPriority.HIGH,  # Security notifications are high priority
        )

        # Send email
        result = await self.provider.send_email(message)

        if not result.success:
            logger.error(f"Failed to send password changed email: {result.error}")


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
