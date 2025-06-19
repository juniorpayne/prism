#!/usr/bin/env python3
"""
Unit tests for email configuration management.
"""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock, patch

import pytest
import yaml
from pydantic import ValidationError

from server.auth.email_providers.config import (
    AWSSESConfig,
    ConsoleEmailConfig,
    ConsoleFormat,
    EmailProviderType,
    SMTPEmailConfig,
    get_default_config,
)
from server.auth.email_providers.config_loader import EmailConfigLoader, get_config_loader
from server.auth.email_providers.validators import (
    ConfigValidator,
    validate_config_for_environment,
)


class TestEmailConfigs:
    """Test email configuration classes."""

    def test_console_config_defaults(self):
        """Test console config with defaults."""
        config = ConsoleEmailConfig(
            provider=EmailProviderType.CONSOLE,
            from_email="test@example.com",
        )

        assert config.provider == EmailProviderType.CONSOLE
        assert config.from_email == "test@example.com"
        assert config.from_name == "Prism DNS"
        assert config.format == ConsoleFormat.PRETTY
        assert config.use_colors is True
        assert config.line_width == 80

    def test_console_config_custom(self):
        """Test console config with custom values."""
        config = ConsoleEmailConfig(
            provider=EmailProviderType.CONSOLE,
            from_email="custom@example.com",
            from_name="Custom App",
            format=ConsoleFormat.JSON,
            use_colors=False,
            line_width=100,
        )

        assert config.from_name == "Custom App"
        assert config.format == ConsoleFormat.JSON
        assert config.use_colors is False
        assert config.line_width == 100

    def test_smtp_config_validation(self):
        """Test SMTP config validation."""
        # Valid config
        config = SMTPEmailConfig(
            provider=EmailProviderType.SMTP,
            from_email="test@example.com",
            host="smtp.example.com",
            port=587,
            username="user",
            password="pass",
            use_tls=True,
        )

        assert config.host == "smtp.example.com"
        assert config.port == 587
        assert config.use_tls is True
        assert config.use_ssl is False

    def test_smtp_config_invalid_encryption(self):
        """Test SMTP config with invalid encryption settings."""
        with pytest.raises(ValidationError) as exc_info:
            SMTPEmailConfig(
                provider=EmailProviderType.SMTP,
                from_email="test@example.com",
                host="smtp.example.com",
                use_tls=True,
                use_ssl=True,  # Can't use both
            )

        assert "Cannot use both SSL and TLS" in str(exc_info.value)

    def test_smtp_config_port_validation(self):
        """Test SMTP port validation."""
        # Port 465 should require SSL
        with pytest.raises(ValidationError) as exc_info:
            SMTPEmailConfig(
                provider=EmailProviderType.SMTP,
                from_email="test@example.com",
                host="smtp.example.com",
                port=465,
                use_ssl=False,
            )

        assert "Port 465 typically requires SSL" in str(exc_info.value)

    def test_smtp_config_auth_validation(self):
        """Test SMTP authentication validation."""
        # Username without password
        with pytest.raises(ValidationError) as exc_info:
            SMTPEmailConfig(
                provider=EmailProviderType.SMTP,
                from_email="test@example.com",
                host="smtp.example.com",
                username="user",
                # Missing password
            )

        assert "Password is required" in str(exc_info.value)

    def test_ses_config_defaults(self):
        """Test SES config with defaults."""
        config = AWSSESConfig(
            provider=EmailProviderType.AWS_SES,
            from_email="test@example.com",
        )

        assert config.region == "us-east-1"
        assert config.use_iam_role is True
        assert config.verify_ssl is True

    def test_ses_config_with_credentials(self):
        """Test SES config with explicit credentials."""
        config = AWSSESConfig(
            provider=EmailProviderType.AWS_SES,
            from_email="test@example.com",
            use_iam_role=False,
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )

        assert config.use_iam_role is False
        assert config.access_key_id == "AKIAIOSFODNN7EXAMPLE"

    def test_ses_config_invalid_credentials(self):
        """Test SES config with invalid credentials."""
        with pytest.raises(ValidationError) as exc_info:
            AWSSESConfig(
                provider=EmailProviderType.AWS_SES,
                from_email="test@example.com",
                use_iam_role=False,
                # Missing credentials
            )

        assert "AWS credentials" in str(exc_info.value)

    def test_ses_region_validation(self):
        """Test SES region validation."""
        # Valid region
        config = AWSSESConfig(
            provider=EmailProviderType.AWS_SES,
            from_email="test@example.com",
            region="us-west-2",
        )
        assert config.region == "us-west-2"

        # Invalid region
        with pytest.raises(ValidationError) as exc_info:
            AWSSESConfig(
                provider=EmailProviderType.AWS_SES,
                from_email="test@example.com",
                region="invalid-region",
            )

        assert "Invalid AWS region" in str(exc_info.value)

    def test_email_validation(self):
        """Test email address validation."""
        # Invalid email
        with pytest.raises(ValidationError) as exc_info:
            ConsoleEmailConfig(
                provider=EmailProviderType.CONSOLE,
                from_email="not-an-email",
            )

        assert "value is not a valid email address" in str(exc_info.value)

        # Email normalization (lowercase)
        config = ConsoleEmailConfig(
            provider=EmailProviderType.CONSOLE,
            from_email="Test@EXAMPLE.COM",
        )
        assert config.from_email == "test@example.com"

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError) as exc_info:
            ConsoleEmailConfig(
                provider=EmailProviderType.CONSOLE,
                from_email="test@example.com",
                unknown_field="value",  # Extra field
            )

        assert "Extra inputs are not permitted" in str(exc_info.value)


class TestConfigLoader:
    """Test email configuration loader."""

    def test_loader_initialization(self):
        """Test config loader initialization."""
        loader = EmailConfigLoader("development")
        assert loader.env == "development"
        assert loader._loaded_config is None

    @patch.dict(os.environ, {"PRISM_ENV": "staging"})
    def test_loader_env_detection(self):
        """Test environment detection."""
        loader = EmailConfigLoader()
        assert loader.env == "staging"

    @patch.dict(
        os.environ,
        {
            "EMAIL_PROVIDER": "console",
            "EMAIL_FROM_ADDRESS": "test@example.com",
            "EMAIL_FROM_NAME": "Test App",
        },
    )
    def test_load_console_config_from_env(self):
        """Test loading console config from environment."""
        loader = EmailConfigLoader()
        config = loader.load_config()

        assert isinstance(config, ConsoleEmailConfig)
        assert config.from_email == "test@example.com"
        assert config.from_name == "Test App"

    @patch.dict(
        os.environ,
        {
            "EMAIL_PROVIDER": "smtp",
            "EMAIL_FROM_ADDRESS": "smtp@example.com",
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_PORT": "587",
            "SMTP_USERNAME": "user@gmail.com",
            "SMTP_PASSWORD": "app-password",
        },
    )
    def test_load_smtp_config_from_env(self):
        """Test loading SMTP config from environment."""
        loader = EmailConfigLoader()
        config = loader.load_config()

        assert isinstance(config, SMTPEmailConfig)
        assert config.from_email == "smtp@example.com"
        assert config.host == "smtp.gmail.com"
        assert config.port == 587
        assert config.username == "user@gmail.com"

    @patch.dict(
        os.environ,
        {
            "EMAIL_PROVIDER": "aws_ses",
            "EMAIL_FROM_ADDRESS": "ses@example.com",
            "AWS_REGION": "us-west-2",
            "SES_USE_IAM_ROLE": "true",
        },
    )
    def test_load_ses_config_from_env(self):
        """Test loading SES config from environment."""
        loader = EmailConfigLoader()
        config = loader.load_config()

        assert isinstance(config, AWSSESConfig)
        assert config.from_email == "ses@example.com"
        assert config.region == "us-west-2"
        assert config.use_iam_role is True

    def test_load_config_from_yaml(self):
        """Test loading config from YAML file."""
        yaml_config = {
            "email": {
                "provider": "smtp",
                "from_email": "yaml@example.com",
                "host": "smtp.example.com",
                "port": 587,
            }
        }

        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(yaml_config, f)
            temp_path = f.name

        try:
            loader = EmailConfigLoader()
            config = loader.load_config(temp_path)

            assert isinstance(config, SMTPEmailConfig)
            assert config.from_email == "yaml@example.com"
            assert config.host == "smtp.example.com"
        finally:
            Path(temp_path).unlink()

    def test_load_config_from_json(self):
        """Test loading config from JSON file."""
        json_config = {
            "provider": "console",
            "from_email": "json@example.com",
            "format": "json",
        }

        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(json_config, f)
            temp_path = f.name

        try:
            loader = EmailConfigLoader()
            config = loader.load_config(temp_path)

            assert isinstance(config, ConsoleEmailConfig)
            assert config.from_email == "json@example.com"
            assert config.format == ConsoleFormat.JSON
        finally:
            Path(temp_path).unlink()

    @patch.dict(os.environ, {"EMAIL_PROVIDER": "unknown"})
    def test_unknown_provider_defaults_to_console(self):
        """Test unknown provider defaults to console."""
        loader = EmailConfigLoader()
        config = loader.load_config()

        assert isinstance(config, ConsoleEmailConfig)

    def test_config_caching(self):
        """Test configuration caching."""
        loader = EmailConfigLoader()

        with patch.dict(os.environ, {"EMAIL_PROVIDER": "console"}):
            config1 = loader.load_config()
            config2 = loader.load_config()

        assert config1 is config2  # Same instance

    def test_get_config_info(self):
        """Test getting configuration info."""
        loader = EmailConfigLoader()

        # Before loading
        info = loader.get_config_info()
        assert info["loaded"] is False
        assert info["environment"] == "development"

        # After loading
        with patch.dict(
            os.environ,
            {
                "EMAIL_PROVIDER": "smtp",
                "SMTP_HOST": "smtp.example.com",
                "SMTP_PORT": "587",
                "SMTP_USE_TLS": "true",
            },
        ):
            loader.load_config()
            info = loader.get_config_info()

        assert info["loaded"] is True
        assert info["provider"] == EmailProviderType.SMTP
        assert info["host"] == "smtp.example.com"
        assert info["encryption"] == "TLS"

    def test_singleton_pattern(self):
        """Test config loader singleton pattern."""
        loader1 = get_config_loader()
        loader2 = get_config_loader()
        assert loader1 is loader2

        # Different environment creates new instance
        loader3 = get_config_loader("production")
        assert loader3 is not loader1
        assert loader3.env == "production"


class TestConfigValidation:
    """Test configuration validation."""

    def test_validate_smtp_gmail(self):
        """Test Gmail SMTP validation."""
        config = SMTPEmailConfig(
            provider=EmailProviderType.SMTP,
            from_email="test@example.com",
            host="smtp.gmail.com",
            port=587,
            username="user@gmail.com",
            password="short",  # Too short for app password
            use_tls=True,
        )

        warnings = ConfigValidator.validate_smtp_config(config)
        assert any("app-specific passwords" in w for w in warnings)

    def test_validate_smtp_sendgrid(self):
        """Test SendGrid SMTP validation."""
        config = SMTPEmailConfig(
            provider=EmailProviderType.SMTP,
            from_email="test@example.com",
            host="smtp.sendgrid.net",
            port=587,
            username="wronguser",  # Should be 'apikey'
            password="SG.xxxxx",
        )

        warnings = ConfigValidator.validate_smtp_config(config)
        assert any("should be 'apikey'" in w for w in warnings)

    def test_validate_email_addresses(self):
        """Test email address validation."""
        # Test domain
        config = ConsoleEmailConfig(
            provider=EmailProviderType.CONSOLE,
            from_email="test@example.com",
        )

        warnings = ConfigValidator.validate_email_addresses(config)
        assert any("test domain" in w for w in warnings)

        # No-reply without reply-to
        config = ConsoleEmailConfig(
            provider=EmailProviderType.CONSOLE,
            from_email="noreply@realcompany.com",
        )

        warnings = ConfigValidator.validate_email_addresses(config)
        assert any("reply_to" in w for w in warnings)

    def test_validate_production_config(self):
        """Test production environment validation."""
        # Console in production
        config = ConsoleEmailConfig(
            provider=EmailProviderType.CONSOLE,
            from_email="test@example.com",
        )

        warnings = validate_config_for_environment(config, "production")
        assert any("should not be used in production" in w for w in warnings)

        # Debug enabled in production
        config = SMTPEmailConfig(
            provider=EmailProviderType.SMTP,
            from_email="prod@realcompany.com",
            host="smtp.example.com",
            debug=True,
        )

        warnings = validate_config_for_environment(config, "production")
        assert any("Debug mode should be disabled" in w for w in warnings)

    def test_validate_development_config(self):
        """Test development environment validation."""
        # External SMTP in development
        config = SMTPEmailConfig(
            provider=EmailProviderType.SMTP,
            from_email="dev@example.com",
            host="smtp.gmail.com",
        )

        warnings = validate_config_for_environment(config, "development")
        assert any("local SMTP server" in w for w in warnings)

        # Console is fine for development
        config = ConsoleEmailConfig(
            provider=EmailProviderType.CONSOLE,
            from_email="dev@prism-dev.com",
        )

        warnings = validate_config_for_environment(config, "development")
        # Should have minimal warnings for development
        assert len(warnings) == 0 or all("MX records" in w for w in warnings)

    @patch("socket.socket")
    def test_host_reachability(self, mock_socket):
        """Test host reachability check."""
        # Reachable host
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_socket.return_value = mock_sock

        assert ConfigValidator._is_host_reachable("smtp.example.com", 587) is True

        # Unreachable host
        mock_sock.connect_ex.return_value = 1
        assert ConfigValidator._is_host_reachable("smtp.example.com", 587) is False

    def test_get_default_config(self):
        """Test getting default configuration."""
        with patch.dict(
            os.environ,
            {
                "EMAIL_FROM_ADDRESS": "env@example.com",
                "EMAIL_FROM_NAME": "Env App",
            },
        ):
            defaults = get_default_config(EmailProviderType.CONSOLE)

        assert defaults["from_email"] == "env@example.com"
        assert defaults["from_name"] == "Env App"
        assert "reply_to" not in defaults  # None values removed
