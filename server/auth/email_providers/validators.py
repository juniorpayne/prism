#!/usr/bin/env python3
"""
Email configuration validators with extended validation logic.
"""

import logging
import re
import socket
from typing import List, Optional, Set

from server.auth.email_providers.config import AWSSESConfig, EmailConfig, SMTPEmailConfig

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Extended configuration validator for email providers."""

    @staticmethod
    def validate_smtp_config(config: SMTPEmailConfig) -> List[str]:
        """
        Validate SMTP configuration with extended checks.

        Args:
            config: SMTP configuration to validate

        Returns:
            List of validation warnings (empty if fully valid)
        """
        warnings = []

        # Check if host is reachable
        if not ConfigValidator._is_host_reachable(config.host, config.port):
            warnings.append(f"SMTP host {config.host}:{config.port} is not reachable")

        # Provider-specific validations
        if "gmail" in config.host.lower():
            warnings.extend(ConfigValidator._validate_gmail_config(config))
        elif "sendgrid" in config.host.lower():
            warnings.extend(ConfigValidator._validate_sendgrid_config(config))
        elif "mailgun" in config.host.lower():
            warnings.extend(ConfigValidator._validate_mailgun_config(config))

        # Check common misconfigurations
        if config.port == 25:
            warnings.append("Port 25 is often blocked by ISPs and cloud providers")

        if not config.use_tls and not config.use_ssl:
            warnings.append("No encryption enabled - emails will be sent in plain text")

        if config.timeout < 10:
            warnings.append(f"Timeout of {config.timeout}s may be too short for slow connections")

        return warnings

    @staticmethod
    def validate_ses_config(config: AWSSESConfig) -> List[str]:
        """
        Validate AWS SES configuration.

        Args:
            config: SES configuration to validate

        Returns:
            List of validation warnings
        """
        warnings = []

        # Check if from_email is verified in SES
        if not config.from_email.endswith(".amazonaws.com"):
            warnings.append("Ensure your from_email address is verified in AWS SES")

        # Region-specific checks
        if config.region == "us-east-1" and config.use_iam_role:
            warnings.append("Consider using a region closer to your application for lower latency")

        # Warn about missing configuration set
        if not config.configuration_set:
            warnings.append(
                "Consider using a configuration set for better tracking and reputation management"
            )

        # Check for sandbox mode indicators
        if config.max_send_rate and config.max_send_rate <= 1.0:
            warnings.append("Low send rate suggests SES account may still be in sandbox mode")

        return warnings

    @staticmethod
    def validate_email_addresses(config: EmailConfig) -> List[str]:
        """
        Validate email addresses in configuration.

        Args:
            config: Email configuration

        Returns:
            List of validation warnings
        """
        warnings = []

        # Check from_email domain
        domain = config.from_email.split("@")[1]

        # Check for common test domains
        test_domains = {"example.com", "test.com", "localhost", "local", "example.test"}
        if domain.lower() in test_domains:
            warnings.append(f"Using test domain '{domain}' - not suitable for production")

        # Check for no-reply patterns
        if config.from_email.lower().startswith(("noreply", "no-reply", "donotreply")):
            if not config.reply_to:
                warnings.append(
                    "Using no-reply address without setting reply_to - "
                    "users cannot respond to emails"
                )

        # Validate domain has MX records (for production)
        if not ConfigValidator._domain_has_mx_records(domain):
            warnings.append(f"Domain '{domain}' has no MX records - emails may be marked as spam")

        return warnings

    @staticmethod
    def _is_host_reachable(host: str, port: int, timeout: float = 5.0) -> bool:
        """Check if host:port is reachable."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except socket.gaierror:
            # Host doesn't exist
            return False
        except Exception as e:
            logger.debug(f"Failed to check host reachability: {e}")
            return False

    @staticmethod
    def _domain_has_mx_records(domain: str) -> bool:
        """Check if domain has MX records."""
        try:
            import dns.resolver

            resolver = dns.resolver.Resolver()
            resolver.timeout = 5.0
            resolver.lifetime = 5.0

            mx_records = resolver.resolve(domain, "MX")
            return len(mx_records) > 0

        except ImportError:
            # dnspython not installed - skip check
            logger.debug("dnspython not installed - skipping MX record check")
            return True
        except Exception:
            # Any DNS resolution error
            return False

    @staticmethod
    def _validate_gmail_config(config: SMTPEmailConfig) -> List[str]:
        """Validate Gmail-specific SMTP configuration."""
        warnings = []

        if config.port not in [465, 587]:
            warnings.append("Gmail SMTP should use port 465 (SSL) or 587 (TLS)")

        if config.port == 465 and not config.use_ssl:
            warnings.append("Gmail port 465 requires SSL")

        if config.port == 587 and not config.use_tls:
            warnings.append("Gmail port 587 requires TLS")

        if config.password and len(config.password) < 16:
            warnings.append(
                "Gmail requires app-specific passwords (16 characters) " "when 2FA is enabled"
            )

        return warnings

    @staticmethod
    def _validate_sendgrid_config(config: SMTPEmailConfig) -> List[str]:
        """Validate SendGrid-specific SMTP configuration."""
        warnings = []

        if config.host != "smtp.sendgrid.net":
            warnings.append(f"Unusual SendGrid host: {config.host} " "(expected smtp.sendgrid.net)")

        if config.username != "apikey":
            warnings.append("SendGrid SMTP username should be 'apikey'")

        if config.port not in [25, 587, 2525]:
            warnings.append("SendGrid SMTP typically uses ports 25, 587, or 2525")

        return warnings

    @staticmethod
    def _validate_mailgun_config(config: SMTPEmailConfig) -> List[str]:
        """Validate Mailgun-specific SMTP configuration."""
        warnings = []

        if not config.host.startswith("smtp.mailgun.org"):
            warnings.append(
                f"Unusual Mailgun host: {config.host} "
                "(expected smtp.mailgun.org or smtp.eu.mailgun.org)"
            )

        if config.port not in [25, 587, 465]:
            warnings.append("Mailgun SMTP typically uses ports 25, 587, or 465")

        return warnings


def validate_config_for_environment(config: EmailConfig, environment: str) -> List[str]:
    """
    Validate configuration is appropriate for the environment.

    Args:
        config: Email configuration
        environment: Environment name (development, staging, production)

    Returns:
        List of validation warnings
    """
    warnings = []
    validator = ConfigValidator()

    # Common validations
    warnings.extend(validator.validate_email_addresses(config))

    # Provider-specific validations
    if isinstance(config, SMTPEmailConfig):
        warnings.extend(validator.validate_smtp_config(config))
    elif isinstance(config, AWSSESConfig):
        warnings.extend(validator.validate_ses_config(config))

    # Environment-specific validations
    if environment == "production":
        warnings.extend(_validate_production_config(config))
    elif environment == "development":
        warnings.extend(_validate_development_config(config))

    return warnings


def _validate_production_config(config: EmailConfig) -> List[str]:
    """Validate configuration for production environment."""
    warnings = []

    # Should not use console provider in production
    if config.provider == "console":
        warnings.append("Console email provider should not be used in production")

    # Should have proper from address
    if config.from_email.endswith((".local", ".test", ".localhost")):
        warnings.append("Production should use a real domain for from_email")

    # Debug should be off
    if config.debug:
        warnings.append("Debug mode should be disabled in production")

    # Should have retry configuration
    if config.max_retries < 2:
        warnings.append("Production should have at least 2 retries for reliability")

    return warnings


def _validate_development_config(config: EmailConfig) -> List[str]:
    """Validate configuration for development environment."""
    warnings = []

    # Console provider is fine for development
    if config.provider != "console":
        if isinstance(config, SMTPEmailConfig):
            # Warn about using real SMTP in development
            if not config.host.startswith(("localhost", "127.0.0.1", "mailhog", "mailcatcher")):
                warnings.append(
                    "Consider using a local SMTP server (MailHog, MailCatcher) "
                    "for development instead of external services"
                )

    return warnings
