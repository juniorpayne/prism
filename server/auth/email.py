#!/usr/bin/env python3
"""
Email service for sending verification and password reset emails.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import EmailStr

from server.auth.config import get_settings

logger = logging.getLogger(__name__)


# Email configuration
def get_mail_config() -> ConnectionConfig:
    """Get email configuration from settings."""
    settings = get_settings()

    return ConnectionConfig(
        MAIL_USERNAME=settings.get("email_username", ""),
        MAIL_PASSWORD=settings.get("email_password", ""),
        MAIL_FROM=settings.get("email_from", "noreply@prismdns.com"),
        MAIL_PORT=int(settings.get("email_port", 587)),
        MAIL_SERVER=settings.get("email_host", "smtp.gmail.com"),
        MAIL_FROM_NAME=settings.get("email_from_name", "Prism DNS"),
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
        TEMPLATE_FOLDER=Path(__file__).parent / "templates",
    )


class EmailService:
    """Service for sending emails."""

    def __init__(self):
        """Initialize email service."""
        self.config = get_mail_config()
        self.fastmail = FastMail(self.config)

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

        message = MessageSchema(
            subject="Verify your Prism DNS account",
            recipients=[email],
            body=html,
            subtype=MessageType.html,
        )

        try:
            await self.fastmail.send_message(message)
            logger.info(f"Verification email sent to {email}")
        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {e}")
            # Don't raise exception to avoid exposing email sending issues

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

        message = MessageSchema(
            subject="Reset your Prism DNS password",
            recipients=[email],
            body=html,
            subtype=MessageType.html,
        )

        try:
            await self.fastmail.send_message(message)
            logger.info(f"Password reset email sent to {email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {e}")
            # Don't raise exception to avoid exposing email sending issues

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

        message = MessageSchema(
            subject="Your Prism DNS password has been changed",
            recipients=[email],
            body=html,
            subtype=MessageType.html,
        )

        try:
            await self.fastmail.send_message(message)
            logger.info(f"Password changed email sent to {email}")
        except Exception as e:
            logger.error(f"Failed to send password changed email to {email}: {e}")


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
