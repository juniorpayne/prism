#!/usr/bin/env python3
"""
Email configuration loader that supports multiple sources.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml
from dotenv import load_dotenv
from pydantic import ValidationError

from server.auth.email_providers.config import (
    AWSSESConfig,
    ConsoleEmailConfig,
    EmailConfig,
    EmailProviderType,
    SMTPEmailConfig,
    get_default_config,
)

logger = logging.getLogger(__name__)


class EmailConfigLoader:
    """
    Loads email configuration from various sources.

    Priority order:
    1. Environment variables
    2. Configuration files (.env, .yaml, .json)
    3. Default values
    """

    def __init__(self, env: Optional[str] = None):
        """
        Initialize configuration loader.

        Args:
            env: Environment name (development, staging, production)
        """
        self.env = env or os.getenv("PRISM_ENV", "development")
        self._loaded_config: Optional[EmailConfig] = None

        # Load environment files
        self._load_env_files()

    def _load_env_files(self) -> None:
        """Load environment files based on current environment."""
        # Load base .env file
        base_env = Path(".env")
        if base_env.exists():
            load_dotenv(base_env)
            logger.debug(f"Loaded base .env file")

        # Load environment-specific .env file
        env_file = Path(f".env.{self.env}")
        if env_file.exists():
            load_dotenv(env_file, override=True)
            logger.debug(f"Loaded environment file: {env_file}")

        # Load local overrides (not committed to git)
        local_env = Path(f".env.{self.env}.local")
        if local_env.exists():
            load_dotenv(local_env, override=True)
            logger.debug(f"Loaded local overrides: {local_env}")

    def load_config(self, config_path: Optional[str] = None) -> EmailConfig:
        """
        Load email configuration.

        Args:
            config_path: Optional path to configuration file

        Returns:
            Loaded email configuration

        Raises:
            ValidationError: If configuration is invalid
        """
        if self._loaded_config and not config_path:
            return self._loaded_config

        # Load raw configuration data
        if config_path:
            # Load from file - provider will be in the file
            raw_config = self._load_config_from_file(config_path)
            provider_str = raw_config.get("provider", "console")
            try:
                provider = EmailProviderType(provider_str.lower())
            except ValueError:
                logger.warning(f"Unknown provider '{provider_str}', defaulting to console")
                provider = EmailProviderType.CONSOLE
        else:
            # Get provider from environment
            provider = self._get_provider()
            raw_config = self._load_config_from_env(provider)

        # Add provider to config data
        raw_config["provider"] = provider.value

        # Create configuration instance
        try:
            if provider == EmailProviderType.CONSOLE:
                config = ConsoleEmailConfig(**raw_config)
            elif provider == EmailProviderType.SMTP:
                config = SMTPEmailConfig(**raw_config)
            elif provider == EmailProviderType.AWS_SES:
                config = AWSSESConfig(**raw_config)
            else:
                raise ValueError(f"Unknown email provider: {provider}")

            self._loaded_config = config

            return config

        except ValidationError as e:
            logger.error(f"Invalid email configuration: {e}")
            raise

    def _get_provider(self) -> EmailProviderType:
        """Determine email provider from environment or defaults."""
        provider_str = os.getenv("EMAIL_PROVIDER", "console").lower()

        # Map environment values to enum
        provider_map = {
            "console": EmailProviderType.CONSOLE,
            "smtp": EmailProviderType.SMTP,
            "aws_ses": EmailProviderType.AWS_SES,
            "ses": EmailProviderType.AWS_SES,  # Alias
        }

        provider = provider_map.get(provider_str)
        if not provider:
            logger.warning(f"Unknown email provider '{provider_str}', defaulting to console")
            provider = EmailProviderType.CONSOLE

        return provider

    def _load_config_from_file(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from file.

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration data dictionary
        """
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"Configuration file not found: {config_path}")
            return {}

        try:
            with open(path, "r") as f:
                if path.suffix in [".yaml", ".yml"]:
                    data = yaml.safe_load(f)
                elif path.suffix == ".json":
                    data = json.load(f)
                else:
                    logger.error(f"Unsupported config file format: {path.suffix}")
                    return {}

            # Extract email configuration section if nested
            if "email" in data and isinstance(data["email"], dict):
                return data["email"]

            return data

        except Exception as e:
            logger.error(f"Failed to load config file {config_path}: {e}")
            return {}

    def _load_config_from_env(self, provider: EmailProviderType) -> Dict[str, Any]:
        """
        Load configuration from environment variables.

        Args:
            provider: Email provider type

        Returns:
            Configuration data dictionary
        """
        # Get defaults with environment overrides
        return get_default_config(provider)

    def _load_config_file(self, config_path: str) -> Optional[Dict[str, Any]]:
        """
        Load configuration from file.

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration data or None if file doesn't exist
        """
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"Configuration file not found: {config_path}")
            return None

        # Delegate to _load_config_from_file
        return self._load_config_from_file(config_path) or None

    def validate_config(self, config: Optional[EmailConfig] = None) -> bool:
        """
        Validate email configuration.

        Args:
            config: Configuration to validate (uses loaded config if None)

        Returns:
            True if valid, False otherwise
        """
        if not config:
            config = self._loaded_config

        if not config:
            logger.error("No configuration to validate")
            return False

        try:
            # Pydantic already validates on creation, but we can do additional checks
            if isinstance(config, SMTPEmailConfig):
                return self._validate_smtp_config(config)
            elif isinstance(config, AWSSESConfig):
                return self._validate_ses_config(config)
            elif isinstance(config, ConsoleEmailConfig):
                return True  # Console config is always valid if it passes Pydantic

            return True

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False

    def _validate_smtp_config(self, config: SMTPEmailConfig) -> bool:
        """Validate SMTP-specific configuration."""
        # Additional SMTP validations beyond Pydantic
        if config.host.startswith("smtp.gmail.com"):
            if not config.username or not config.password:
                logger.warning("Gmail SMTP requires authentication")
                return False
            if config.port not in [465, 587]:
                logger.warning("Gmail SMTP typically uses port 465 (SSL) or 587 (TLS)")

        return True

    def _validate_ses_config(self, config: AWSSESConfig) -> bool:
        """Validate AWS SES-specific configuration."""
        # Additional SES validations
        if not config.use_iam_role and config.endpoint_url:
            logger.warning("Using custom endpoint with explicit credentials may cause issues")

        return True

    def get_config_info(self) -> Dict[str, Any]:
        """
        Get information about the current configuration.

        Returns:
            Configuration information dictionary
        """
        if not self._loaded_config:
            return {
                "loaded": False,
                "environment": self.env,
            }

        config = self._loaded_config
        info = {
            "loaded": True,
            "environment": self.env,
            "provider": config.provider,
            "from_email": config.from_email,
            "from_name": config.from_name,
            "enabled": config.enabled,
            "debug": config.debug,
        }

        # Add provider-specific info
        if isinstance(config, SMTPEmailConfig):
            info.update(
                {
                    "host": config.host,
                    "port": config.port,
                    "encryption": "SSL" if config.use_ssl else "TLS" if config.use_tls else "None",
                    "authenticated": bool(config.username),
                }
            )
        elif isinstance(config, AWSSESConfig):
            info.update(
                {
                    "region": config.region,
                    "use_iam_role": config.use_iam_role,
                    "configuration_set": config.configuration_set,
                }
            )
        elif isinstance(config, ConsoleEmailConfig):
            info.update(
                {
                    "format": config.format,
                    "use_colors": config.use_colors,
                    "line_width": config.line_width,
                }
            )

        return info


# Singleton instance
_config_loader: Optional[EmailConfigLoader] = None


def get_config_loader(env: Optional[str] = None) -> EmailConfigLoader:
    """
    Get or create configuration loader instance.

    Args:
        env: Environment name (uses existing if None)

    Returns:
        Configuration loader instance
    """
    global _config_loader

    if _config_loader is None or (env and env != _config_loader.env):
        _config_loader = EmailConfigLoader(env)

    return _config_loader
