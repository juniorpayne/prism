#!/usr/bin/env python3
"""
Test email command for validating email configuration.

This command sends a test email to verify that email configuration
is working correctly.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

import click
from pydantic import ValidationError

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from server.auth.email_providers.base import EmailMessage
from server.auth.email_providers.config import EmailProviderType
from server.auth.email_providers.config_loader import EmailConfigLoader
from server.auth.email_providers.factory import EmailProviderFactory
from server.auth.email_providers.smtp_validator import SMTPConfigValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@click.command()
@click.option(
    "--to",
    prompt="Recipient email",
    help="Email address to send test to",
)
@click.option(
    "--provider",
    type=click.Choice(["console", "smtp", "aws_ses"]),
    help="Override configured provider",
)
@click.option(
    "--validate-only",
    is_flag=True,
    help="Only validate configuration without sending",
)
@click.option(
    "--config-file",
    help="Path to configuration file (default: from environment)",
)
def test_email(to: str, provider: str, validate_only: bool, config_file: str):
    """Send a test email to verify configuration."""
    click.echo("🔧 Prism DNS Email Configuration Test")
    click.echo("=" * 40)

    try:
        # Load configuration
        click.echo("\n📋 Loading email configuration...")
        config_loader = EmailConfigLoader(config_file)
        config = config_loader.load_config()

        # Override provider if specified
        if provider:
            click.echo(f"   Overriding provider to: {provider}")
            # Create new config with different provider
            if provider == "console":
                from server.auth.email_providers.config import ConsoleEmailConfig

                config = ConsoleEmailConfig(
                    provider=EmailProviderType.CONSOLE,
                    from_email=config.from_email,
                    from_name=config.from_name,
                )
            elif provider == "aws_ses":
                click.echo("   ⚠️  AWS SES provider requires full configuration")
                return

        click.echo(f"\n📧 Email Configuration:")
        click.echo(f"   Provider: {config.provider}")
        click.echo(f"   From: {config.from_name} <{config.from_email}>")
        click.echo(f"   To: {to}")

        # Validate SMTP configuration if applicable
        if config.provider == EmailProviderType.SMTP:
            click.echo(f"\n🔍 SMTP Server Details:")
            click.echo(f"   Host: {config.host}")
            click.echo(f"   Port: {config.port}")
            click.echo(f"   TLS: {config.use_tls}")
            click.echo(f"   SSL: {config.use_ssl}")
            click.echo(f"   Auth: {'Yes' if config.username else 'No'}")

            if validate_only or click.confirm("\nValidate SMTP configuration?", default=True):
                click.echo("\n🔍 Validating SMTP configuration...")
                validator = SMTPConfigValidator(config)
                success, results = asyncio.run(validator.validate())

                for result in results:
                    click.echo(f"   {result}")

                if not success:
                    click.echo("\n❌ Configuration validation failed!")
                    if not click.confirm("Continue anyway?", default=False):
                        return

        if validate_only:
            click.echo("\n✅ Validation complete (no email sent)")
            return

        # Create test email message
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        message = EmailMessage(
            to=[to],
            subject=f"Prism DNS - Test Email ({timestamp})",
            text_body=(
                f"This is a test email from Prism DNS.\n\n"
                f"Timestamp: {timestamp}\n"
                f"Provider: {config.provider}\n\n"
                f"If you received this email, your email configuration is working correctly!\n\n"
                f"---\n"
                f"Prism DNS - Managed DNS Solution\n"
                f"https://prism.thepaynes.ca"
            ),
            html_body=(
                f"<html><body style='font-family: Arial, sans-serif;'>"
                f"<h2>Test Email from Prism DNS</h2>"
                f"<p>This is a test email to verify your email configuration.</p>"
                f"<table style='border: 1px solid #ddd; padding: 10px;'>"
                f"<tr><td><strong>Timestamp:</strong></td><td>{timestamp}</td></tr>"
                f"<tr><td><strong>Provider:</strong></td><td>{config.provider}</td></tr>"
                f"<tr><td><strong>Status:</strong></td><td style='color: green;'>✅ Working</td></tr>"
                f"</table>"
                f"<p>If you received this email, your email configuration is working correctly!</p>"
                f"<hr>"
                f"<p><small>Prism DNS - Managed DNS Solution<br>"
                f"<a href='https://prism.thepaynes.ca'>https://prism.thepaynes.ca</a></small></p>"
                f"</body></html>"
            ),
        )

        # Send test email
        click.echo(f"\n📮 Sending test email to {to}...")
        provider_instance = EmailProviderFactory.create_provider(config)
        result = asyncio.run(provider_instance.send_email(message))

        if result.success:
            click.echo("\n✅ Test email sent successfully!")
            if result.message_id:
                click.echo(f"   Message ID: {result.message_id}")
            if config.provider == EmailProviderType.CONSOLE:
                click.echo("\n📋 Check the console output above for the email content.")
            elif config.provider == EmailProviderType.SMTP and config.host == "mailhog":
                click.echo("\n🌐 View the email at: http://localhost:8025")
        else:
            click.echo(f"\n❌ Failed to send test email: {result.error}")
            if result.metadata:
                click.echo(f"   Details: {result.metadata}")

    except ValidationError as e:
        click.echo(f"\n❌ Configuration error: {e}")
        click.echo("\n💡 Check your environment variables or configuration file.")
    except FileNotFoundError as e:
        click.echo(f"\n❌ Configuration file not found: {e}")
    except Exception as e:
        click.echo(f"\n❌ Unexpected error: {type(e).__name__}: {e}")
        import traceback

        if click.confirm("Show full traceback?", default=False):
            traceback.print_exc()


if __name__ == "__main__":
    test_email()
