#!/usr/bin/env python3
"""
Utility functions for email providers.
"""

import os
import re
from typing import Dict, List, Optional


def validate_email_address(email: str) -> bool:
    """
    Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    return bool(pattern.match(email))


def validate_email_list(emails: List[str]) -> List[str]:
    """
    Validate a list of email addresses.

    Args:
        emails: List of email addresses

    Returns:
        List of invalid email addresses
    """
    invalid = []
    for email in emails:
        if not validate_email_address(email):
            invalid.append(email)
    return invalid


def sanitize_email_content(content: str) -> str:
    """
    Sanitize email content to prevent injection attacks.

    Args:
        content: Email content to sanitize

    Returns:
        Sanitized content
    """
    # Remove potential header injection attempts
    content = re.sub(r"[\r\n]+", " ", content)
    return content.strip()


def extract_domain_from_email(email: str) -> Optional[str]:
    """
    Extract domain from email address.

    Args:
        email: Email address

    Returns:
        Domain part of email or None if invalid
    """
    match = re.match(r"^[^@]+@([^@]+)$", email)
    return match.group(1) if match else None


def is_disposable_email(email: str) -> bool:
    """
    Check if email is from a known disposable email provider.

    This is a simple check and should be enhanced with a proper
    disposable email domain list in production.

    Args:
        email: Email address to check

    Returns:
        True if potentially disposable, False otherwise
    """
    # Common disposable email domains (this list should be expanded)
    disposable_domains = {
        "mailinator.com",
        "guerrillamail.com",
        "10minutemail.com",
        "throwaway.email",
        "yopmail.com",
        "tempmail.com",
        "getairmail.com",
        "dispostable.com",
        "getnada.com",
        "trashmail.com",
    }

    domain = extract_domain_from_email(email.lower())
    return domain in disposable_domains if domain else False


def get_email_provider_from_env() -> Dict[str, str]:
    """
    Get email provider configuration from environment variables.

    Returns:
        Dictionary with provider configuration
    """
    provider = os.getenv("EMAIL_PROVIDER", "console").lower()

    config = {
        "provider": provider,
    }

    if provider == "smtp":
        config.update(
            {
                "host": os.getenv("EMAIL_SMTP_HOST", ""),
                "port": os.getenv("EMAIL_SMTP_PORT", "587"),
                "username": os.getenv("EMAIL_SMTP_USERNAME", ""),
                "password": os.getenv("EMAIL_SMTP_PASSWORD", ""),
                "use_tls": os.getenv("EMAIL_SMTP_USE_TLS", "true").lower() == "true",
                "use_ssl": os.getenv("EMAIL_SMTP_USE_SSL", "false").lower() == "true",
                "from_email": os.getenv("EMAIL_FROM_ADDRESS", ""),
                "from_name": os.getenv("EMAIL_FROM_NAME", ""),
            }
        )
    elif provider == "console":
        config.update(
            {
                "format": os.getenv("EMAIL_CONSOLE_FORMAT", "pretty"),
                "use_colors": os.getenv("EMAIL_CONSOLE_USE_COLORS", "false").lower() == "true",
                "highlight_links": os.getenv("EMAIL_CONSOLE_HIGHLIGHT_LINKS", "true").lower()
                == "true",
            }
        )
    # Add more providers as needed

    return config


def create_default_email_config() -> Dict[str, str]:
    """
    Create default email configuration for development.

    Returns:
        Dictionary with default configuration
    """
    return {
        "provider": "console",
        "format": "pretty",
        "use_colors": False,
        "highlight_links": True,
        "from_email": "noreply@prism.local",
        "from_name": "Prism DNS (Dev)",
    }
