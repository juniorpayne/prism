#!/usr/bin/env python3
"""
Email providers package for Prism DNS authentication system.
"""

from server.auth.email_providers.base import (
    EmailAttachment,
    EmailMessage,
    EmailPriority,
    EmailProvider,
    EmailResult,
)
from server.auth.email_providers.console import ConsoleEmailProvider
from server.auth.email_providers.exceptions import (
    EmailConfigurationError,
    EmailDeliveryError,
    EmailProviderError,
    EmailTemplateError,
)
from server.auth.email_providers.factory import EmailProviderFactory
from server.auth.email_providers.smtp import SMTPEmailProvider

__all__ = [
    # Base classes
    "EmailProvider",
    "EmailMessage",
    "EmailResult",
    "EmailAttachment",
    "EmailPriority",
    # Providers
    "ConsoleEmailProvider",
    "SMTPEmailProvider",
    # Factory
    "EmailProviderFactory",
    # Exceptions
    "EmailProviderError",
    "EmailConfigurationError",
    "EmailDeliveryError",
    "EmailTemplateError",
]
