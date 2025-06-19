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


# Deprecated: Use EmailConfigLoader.load_config() instead
# This function is kept for backward compatibility only
def get_email_provider_from_env() -> Dict[str, str]:
    """
    Get email provider configuration from environment variables.

    DEPRECATED: Use EmailConfigLoader from server.auth.email_providers.config_loader instead.
    This function is kept for backward compatibility only.

    Returns:
        Dictionary with provider configuration
    """
    import warnings

    warnings.warn(
        "get_email_provider_from_env() is deprecated. "
        "Use EmailConfigLoader.load_config() instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    from server.auth.email_providers.config_loader import get_config_loader

    # Use the new config loader
    loader = get_config_loader()
    config = loader.load_config()

    # Convert to legacy dict format
    legacy_config = {
        "provider": config.provider.value,
        "from_email": config.from_email,
        "from_name": config.from_name or "Prism DNS",
    }

    # Add provider-specific fields
    if hasattr(config, "host"):
        legacy_config["host"] = config.host
    if hasattr(config, "port"):
        legacy_config["port"] = str(config.port)
    if hasattr(config, "username"):
        legacy_config["username"] = config.username or ""
    if hasattr(config, "password"):
        legacy_config["password"] = config.password or ""
    if hasattr(config, "use_tls"):
        legacy_config["use_tls"] = config.use_tls
    if hasattr(config, "use_ssl"):
        legacy_config["use_ssl"] = config.use_ssl
    if hasattr(config, "format"):
        legacy_config["format"] = config.format.value
    if hasattr(config, "use_colors"):
        legacy_config["use_colors"] = config.use_colors
    if hasattr(config, "highlight_links"):
        legacy_config["highlight_links"] = config.highlight_links

    return legacy_config


# Deprecated: Use get_default_config() from config module instead
def create_default_email_config() -> Dict[str, str]:
    """
    Create default email configuration for development.

    DEPRECATED: Use get_default_config() from server.auth.email_providers.config instead.
    This function is kept for backward compatibility only.

    Returns:
        Dictionary with default configuration
    """
    import warnings

    warnings.warn(
        "create_default_email_config() is deprecated. "
        "Use get_default_config() from server.auth.email_providers.config instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    from server.auth.email_providers.config import EmailProviderType, get_default_config

    # Get default config for console provider
    return get_default_config(EmailProviderType.CONSOLE)
