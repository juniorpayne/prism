#!/usr/bin/env python3
"""
Email provider factory for creating email providers based on configuration.
"""

import logging
from typing import Any, Dict, Optional, Type

from server.auth.email_providers.base import EmailProvider
from server.auth.email_providers.console import ConsoleEmailProvider
from server.auth.email_providers.exceptions import EmailConfigurationError
from server.auth.email_providers.smtp import SMTPEmailProvider

logger = logging.getLogger(__name__)


class EmailProviderFactory:
    """
    Factory for creating email providers based on configuration.

    This factory supports dynamic provider registration and creation.
    """

    # Registry of available providers
    _providers: Dict[str, Type[EmailProvider]] = {
        "console": ConsoleEmailProvider,
        "smtp": SMTPEmailProvider,
        # Future providers will be added here:
        # "ses": SESEmailProvider,
        # "sendgrid": SendGridEmailProvider,
    }

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[EmailProvider]) -> None:
        """
        Register a new email provider.

        Args:
            name: Provider name (e.g., "smtp", "ses")
            provider_class: Provider class that extends EmailProvider
        """
        if not issubclass(provider_class, EmailProvider):
            raise ValueError(f"{provider_class} must extend EmailProvider")

        cls._providers[name.lower()] = provider_class
        logger.info(f"Registered email provider: {name}")

    @classmethod
    def create_provider(
        cls, provider_name: str, config: Optional[Dict[str, Any]] = None
    ) -> EmailProvider:
        """
        Create an email provider instance.

        Args:
            provider_name: Name of the provider to create
            config: Provider-specific configuration

        Returns:
            EmailProvider instance

        Raises:
            EmailConfigurationError: If provider is not found or configuration is invalid
        """
        provider_name = provider_name.lower()

        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise EmailConfigurationError(
                f"Unknown email provider: {provider_name}. Available providers: {available}"
            )

        provider_class = cls._providers[provider_name]
        config = config or {}

        try:
            provider = provider_class(config)
            logger.info(f"Created {provider_name} email provider")
            return provider
        except Exception as e:
            logger.error(f"Failed to create {provider_name} provider: {e}")
            raise EmailConfigurationError(f"Failed to create {provider_name} provider: {e}")

    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> EmailProvider:
        """
        Create an email provider from a configuration dictionary.

        The configuration should have a 'provider' key specifying the provider type,
        and all other keys will be passed as provider-specific configuration.

        Args:
            config: Configuration dictionary with 'provider' key

        Returns:
            EmailProvider instance

        Example:
            config = {
                "provider": "smtp",
                "host": "smtp.gmail.com",
                "port": 587,
                "username": "user@gmail.com",
                "password": "app-password"
            }
            provider = EmailProviderFactory.create_from_config(config)
        """
        if "provider" not in config:
            raise EmailConfigurationError("Configuration must include 'provider' key")

        provider_name = config.pop("provider")
        return cls.create_provider(provider_name, config)

    @classmethod
    def get_available_providers(cls) -> list:
        """Get list of available provider names."""
        return list(cls._providers.keys())

    @classmethod
    def is_provider_available(cls, provider_name: str) -> bool:
        """Check if a provider is available."""
        return provider_name.lower() in cls._providers
