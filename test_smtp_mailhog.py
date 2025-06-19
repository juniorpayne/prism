#!/usr/bin/env python3
"""
Test script for SMTP email provider with MailHog.

Run this with MailHog:
1. docker compose --profile development up -d mailhog
2. python test_smtp_mailhog.py
3. View emails at http://localhost:8025
"""

import asyncio
import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.auth.email_providers import EmailMessage
from server.auth.email_providers.config import EmailProviderType, SMTPEmailConfig
from server.auth.email_providers.smtp import SMTPEmailProvider


async def test_smtp_with_mailhog():
    """Test SMTP provider with MailHog."""
    print("🧪 Testing SMTP Email Provider with MailHog\n")

    # Create SMTP configuration for MailHog
    config = SMTPEmailConfig(
        provider=EmailProviderType.SMTP,
        from_email="noreply@prism.local",
        from_name="Prism DNS",
        host="localhost",
        port=1025,
        use_tls=False,
        use_ssl=False,
        # MailHog doesn't require authentication
    )

    print(f"📧 SMTP Configuration:")
    print(f"   Host: {config.host}:{config.port}")
    print(f"   From: {config.from_name} <{config.from_email}>")
    print(f"   TLS: {config.use_tls}, SSL: {config.use_ssl}")
    print()

    # Create SMTP provider
    provider = SMTPEmailProvider(config)

    # Test 1: Send a verification email
    print("📮 Test 1: Sending verification email...")
    verification_email = EmailMessage(
        to=["user@example.com"],
        subject="Verify your email address",
        text_body="""
Hello!

Please verify your email address by clicking the link below:

http://localhost:8090/verify-email?token=abc123xyz789

This link will expire in 24 hours.

Thanks,
Prism DNS Team
        """.strip(),
        html_body="""
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <h2>Verify your email address</h2>
    <p>Hello!</p>
    <p>Please verify your email address by clicking the link below:</p>
    <p style="margin: 20px 0;">
        <a href="http://localhost:8090/verify-email?token=abc123xyz789" 
           style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            Verify Email
        </a>
    </p>
    <p>Or copy this link: http://localhost:8090/verify-email?token=abc123xyz789</p>
    <p>This link will expire in 24 hours.</p>
    <p>Thanks,<br>Prism DNS Team</p>
</body>
</html>
        """.strip(),
    )

    result = await provider.send_email(verification_email)
    if result.success:
        print(f"   ✅ Email sent successfully! Message ID: {result.message_id}")
    else:
        print(f"   ❌ Failed to send: {result.error}")
    print()

    # Test 2: Send a password reset email
    print("📮 Test 2: Sending password reset email...")
    reset_email = EmailMessage(
        to=["user@example.com"],
        subject="Reset your password",
        text_body="""
Password Reset Request

We received a request to reset your password. Click the link below to create a new password:

http://localhost:8090/reset-password?token=reset456token

If you didn't request this, please ignore this email.

This link will expire in 1 hour.

Prism DNS Security Team
        """.strip(),
        html_body="""
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <h2>Password Reset Request</h2>
    <p>We received a request to reset your password. Click the link below to create a new password:</p>
    <p style="margin: 20px 0;">
        <a href="http://localhost:8090/reset-password?token=reset456token" 
           style="background-color: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            Reset Password
        </a>
    </p>
    <p>If you didn't request this, please ignore this email.</p>
    <p><strong>This link will expire in 1 hour.</strong></p>
    <hr style="margin: 20px 0;">
    <p style="font-size: 12px; color: #666;">
        Prism DNS Security Team<br>
        This is an automated message, please do not reply.
    </p>
</body>
</html>
        """.strip(),
    )

    result = await provider.send_email(reset_email)
    if result.success:
        print(f"   ✅ Email sent successfully! Message ID: {result.message_id}")
    else:
        print(f"   ❌ Failed to send: {result.error}")
    print()

    # Test 3: Test configuration verification
    print("🔍 Test 3: Verifying SMTP configuration...")
    is_valid = await provider.verify_configuration()
    if is_valid:
        print("   ✅ Configuration is valid!")
    else:
        print("   ❌ Configuration verification failed!")
    print()

    # Test 4: Send email with CC and custom headers
    print("📮 Test 4: Sending email with CC and custom headers...")
    advanced_email = EmailMessage(
        to=["primary@example.com"],
        cc=["manager@example.com"],
        subject="Weekly Report",
        text_body="Please find the weekly report attached.",
        html_body="""
<html>
<body>
    <h3>Weekly Report</h3>
    <p>Please find the weekly report attached.</p>
    <p>Best regards,<br>Reporting Team</p>
</body>
</html>
        """,
        reply_to="reports@prism.local",
        headers={
            "X-Priority": "1",
            "X-Report-Type": "Weekly",
        },
    )

    result = await provider.send_email(advanced_email)
    if result.success:
        print(f"   ✅ Email sent successfully! Message ID: {result.message_id}")
    else:
        print(f"   ❌ Failed to send: {result.error}")
    print()

    print("✨ All tests completed!")
    print(f"\n🌐 View emails at: http://localhost:8025")
    print(
        "   (Make sure MailHog is running with: docker compose --profile development up -d mailhog)"
    )


if __name__ == "__main__":
    asyncio.run(test_smtp_with_mailhog())
