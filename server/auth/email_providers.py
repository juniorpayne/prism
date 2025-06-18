#!/usr/bin/env python3
"""
Email providers for different environments.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from pydantic import EmailStr

logger = logging.getLogger(__name__)


class EmailProvider(ABC):
    """Abstract base class for email providers."""

    @abstractmethod
    async def send_email(
        self,
        to_email: EmailStr,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """
        Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text email body (optional)

        Returns:
            True if email was sent successfully, False otherwise
        """
        pass


class ConsoleEmailProvider(EmailProvider):
    """
    Console email provider for development.
    Prints email content to console instead of sending.
    """

    async def send_email(
        self,
        to_email: EmailStr,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """Print email to console."""
        # Extract important links from HTML content
        import re

        # Find verification/reset links
        link_pattern = r'href="([^"]+(?:verify-email|reset-password)[^"]+)"'
        links = re.findall(link_pattern, html_content)

        # Extract token from verification URL
        token_pattern = r'token=([^"&\s]+)'
        tokens = re.findall(token_pattern, html_content)

        print("\n" + "=" * 80)
        print("📧 EMAIL CONSOLE OUTPUT (Development Mode)")
        print("=" * 80)
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print("-" * 80)

        if "verify-email" in subject.lower() or (links and "verify-email" in links[0]):
            print("🔐 EMAIL VERIFICATION")
            print(f"Verification Token: {tokens[0] if tokens else 'No token found'}")
            if links:
                print(f"Verification Link: {links[0]}")
            print("\nTo verify this email, use one of these methods:")
            print("1. Click the link above in your browser")
            print("2. Use the API endpoint:")
            print(f"   GET /api/auth/verify-email/{tokens[0] if tokens else '<token>'}")
            if tokens:
                print("\n3. Or manually update the database:")
                print("   docker compose exec server sqlite3 /app/data/prism.db")
                print(
                    f'   UPDATE users SET email_verified = 1, email_verified_at = datetime("now") WHERE email = "{to_email}";'
                )

        elif "reset-password" in subject.lower() or (links and "reset-password" in links[0]):
            print("🔑 PASSWORD RESET")
            print(f"Reset Token: {tokens[0] if tokens else 'No token found'}")
            if links:
                print(f"Reset Link: {links[0]}")
            print("\nTo reset password, visit the link above in your browser")

        elif "password" in subject.lower() and "changed" in subject.lower():
            print("✅ PASSWORD CHANGED NOTIFICATION")
            print("This is a security notification that the password was changed.")

        else:
            print("📨 GENERAL EMAIL")
            # For other emails, show first few lines of content
            text_preview = re.sub(r"<[^>]+>", "", html_content)[:200]
            print(f"Preview: {text_preview}...")

        print("=" * 80 + "\n")

        logger.info(f"Console email sent to {to_email}: {subject}")
        return True


class SMTPEmailProvider(EmailProvider):
    """
    SMTP email provider for production.
    Uses fastapi-mail to send emails via SMTP.
    """

    def __init__(self, fastmail_instance):
        """Initialize with FastMail instance."""
        self.fastmail = fastmail_instance

    async def send_email(
        self,
        to_email: EmailStr,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """Send email via SMTP."""
        from fastapi_mail import MessageSchema, MessageType

        message = MessageSchema(
            subject=subject,
            recipients=[to_email],
            body=html_content,
            subtype=MessageType.html,
        )

        try:
            await self.fastmail.send_message(message)
            logger.info(f"SMTP email sent to {to_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMTP email to {to_email}: {e}")
            return False
