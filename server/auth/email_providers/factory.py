#!/usr/bin/env python3
"""
Email provider factory for creating email providers based on configuration.
"""

import logging
from typing import Any, Dict, Optional, Type, Union

from server.auth.email_providers.base import EmailProvider
from server.auth.email_providers.config import (
    AWSSESConfig,
    ConsoleEmailConfig,
    EmailConfig,
    EmailProviderType,
    SMTPEmailConfig,
)
from server.auth.email_providers.console import ConsoleEmailProvider
from server.auth.email_providers.exceptions import EmailConfigurationError
from server.auth.email_providers.smtp import SMTPEmailProvider, create_smtp_provider

logger = logging.getLogger(__name__)


class EmailProviderFactory:
    """
    Factory for creating email providers based on configuration.

    This factory supports dynamic provider registration and creation.
    """

    # Registry of available providers
    _providers: Dict[EmailProviderType, Type[EmailProvider]] = {
        EmailProviderType.CONSOLE: ConsoleEmailProvider,
        EmailProviderType.SMTP: SMTPEmailProvider,
        # Future providers will be added here:
        # EmailProviderType.AWS_SES: SESEmailProvider,
    }

    @classmethod
    def register_provider(
        cls, provider_type: EmailProviderType, provider_class: Type[EmailProvider]
    ) -> None:
        """
        Register a new email provider.

        Args:
            provider_type: Provider type enum
            provider_class: Provider class that extends EmailProvider
        """
        if not issubclass(provider_class, EmailProvider):
            raise ValueError(f"{provider_class} must extend EmailProvider")

        cls._providers[provider_type] = provider_class
        logger.info(f"Registered email provider: {provider_type.value}")

    @classmethod
    def create_provider(
        cls, provider_name: str, config: Optional[Dict[str, Any]] = None
    ) -> EmailProvider:
        """
        Create an email provider instance from string name and config dict.

        This method is kept for backward compatibility.

        Args:
            provider_name: Name of the provider to create
            config: Provider-specific configuration

        Returns:
            EmailProvider instance

        Raises:
            EmailConfigurationError: If provider is not found or configuration is invalid
        """
        # Convert string to enum
        try:
            provider_type = EmailProviderType(provider_name.lower())
        except ValueError:
            available = ", ".join(p.value for p in EmailProviderType)
            raise EmailConfigurationError(
                f"Unknown email provider: {provider_name}. Available providers: {available}"
            )

        # Create appropriate config object
        config = config or {}
        config["provider"] = provider_type

        try:
            if provider_type == EmailProviderType.CONSOLE:
                email_config = ConsoleEmailConfig(**config)
            elif provider_type == EmailProviderType.SMTP:
                email_config = SMTPEmailConfig(**config)
            elif provider_type == EmailProviderType.AWS_SES:
                email_config = AWSSESConfig(**config)
            else:
                raise ValueError(f"No config class for {provider_type}")
        except Exception as e:
            raise EmailConfigurationError(f"Invalid configuration: {e}")

        return cls.create_from_email_config(email_config)

    @classmethod
    def create_from_email_config(cls, config: EmailConfig) -> EmailProvider:
        """
        Create an email provider from a typed configuration object.

        Args:
            config: Typed email configuration

        Returns:
            EmailProvider instance

        Raises:
            EmailConfigurationError: If provider is not found
        """
        # Get provider type - could be string or enum due to use_enum_values=True
        provider_value = config.provider
        if isinstance(provider_value, str):
            # Convert string to enum
            try:
                provider_type = EmailProviderType(provider_value)
            except ValueError:
                available = ", ".join(p.value for p in cls._providers.keys())
                raise EmailConfigurationError(
                    f"Unknown email provider: {provider_value}. Available providers: {available}"
                )
        else:
            provider_type = provider_value

        if provider_type not in cls._providers:
            available = ", ".join(p.value for p in cls._providers.keys())
            raise EmailConfigurationError(
                f"Unknown email provider: {provider_type.value}. Available providers: {available}"
            )

        provider_class = cls._providers[provider_type]

        try:
            # Create provider with appropriate config type
            if provider_type == EmailProviderType.SMTP:
                # Use factory function that returns basic or enhanced SMTP provider
                provider = create_smtp_provider(config)
            else:
                # Other providers expect dict for now
                config_dict = config.model_dump(exclude={"provider"})
                provider = provider_class(config_dict)
            logger.info(f"Created {provider_type.value} email provider")
            return provider
        except Exception as e:
            logger.error(f"Failed to create {provider_type.value} provider: {e}")
            raise EmailConfigurationError(f"Failed to create {provider_type.value} provider: {e}")

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
        return [p.value for p in cls._providers.keys()]

    @classmethod
    def is_provider_available(cls, provider_name: str) -> bool:
        """Check if a provider is available."""
        try:
            provider_type = EmailProviderType(provider_name.lower())
            return provider_type in cls._providers
        except ValueError:
            return False
