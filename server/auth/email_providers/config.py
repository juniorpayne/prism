#!/usr/bin/env python3
"""
Email provider configuration classes using Pydantic for validation.
"""

import os
from enum import Enum
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class EmailProviderType(str, Enum):
    """Supported email provider types."""

    CONSOLE = "console"
    SMTP = "smtp"
    AWS_SES = "aws_ses"


class ConsoleFormat(str, Enum):
    """Console output formats."""

    TEXT = "text"
    JSON = "json"
    PRETTY = "pretty"


class BaseEmailConfig(BaseModel):
    """Base configuration for all email providers."""

    provider: EmailProviderType
    from_email: EmailStr = Field(..., description="Default sender email address")
    from_name: str = Field(default="Prism DNS", description="Default sender name")
    reply_to: Optional[EmailStr] = Field(None, description="Reply-to email address")

    # Common settings
    enabled: bool = Field(default=True, description="Whether email sending is enabled")
    debug: bool = Field(default=False, description="Enable debug mode")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum send retries")
    retry_delay: int = Field(default=5, ge=1, le=60, description="Delay between retries in seconds")

    class Config:
        """Pydantic configuration."""

        extra = "forbid"  # Forbid extra attributes
        use_enum_values = True
        validate_assignment = True

    @field_validator("from_email")
    @classmethod
    def validate_from_email(cls, v: str) -> str:
        """Validate from email address."""
        if not v:
            raise ValueError("From email address is required")
        return v.lower()

    @field_validator("reply_to")
    @classmethod
    def validate_reply_to(cls, v: Optional[str]) -> Optional[str]:
        """Validate reply-to email address."""
        if v:
            return v.lower()
        return v


class ConsoleEmailConfig(BaseEmailConfig):
    """Configuration for console email provider."""

    provider: Literal[EmailProviderType.CONSOLE] = EmailProviderType.CONSOLE
    format: ConsoleFormat = Field(
        default=ConsoleFormat.PRETTY, description="Output format for console emails"
    )
    include_headers: bool = Field(default=True, description="Include email headers in output")
    include_attachments: bool = Field(
        default=False, description="Include attachment info in output"
    )
    use_colors: bool = Field(default=True, description="Use ANSI colors in output (if supported)")
    line_width: int = Field(default=80, ge=40, le=120, description="Maximum line width for output")


class SMTPEmailConfig(BaseEmailConfig):
    """Configuration for SMTP email provider."""

    provider: Literal[EmailProviderType.SMTP] = EmailProviderType.SMTP
    host: str = Field(..., description="SMTP server hostname")
    port: int = Field(default=587, ge=1, le=65535, description="SMTP server port")
    username: Optional[str] = Field(None, description="SMTP username")
    password: Optional[str] = Field(None, description="SMTP password")
    use_tls: bool = Field(default=True, description="Use TLS encryption")
    use_ssl: bool = Field(default=False, description="Use SSL encryption")
    timeout: int = Field(default=30, ge=5, le=300, description="Connection timeout in seconds")
    max_connections: int = Field(
        default=5, ge=1, le=20, description="Maximum concurrent connections"
    )

    # Advanced settings
    local_hostname: Optional[str] = Field(None, description="Local hostname for EHLO/HELO")
    validate_certs: bool = Field(default=True, description="Validate SSL certificates")

    @model_validator(mode="after")
    def validate_encryption(self) -> "SMTPEmailConfig":
        """Validate encryption settings."""
        if self.use_ssl and self.use_tls:
            raise ValueError("Cannot use both SSL and TLS encryption")

        # Common port validations
        if self.port == 465 and not self.use_ssl:
            raise ValueError("Port 465 typically requires SSL encryption")
        if self.port == 587 and not self.use_tls:
            raise ValueError("Port 587 typically requires TLS encryption")

        return self

    @model_validator(mode="after")
    def validate_auth(self) -> "SMTPEmailConfig":
        """Validate authentication settings."""
        if self.username and not self.password:
            raise ValueError("Password is required when username is provided")
        if self.password and not self.username:
            raise ValueError("Username is required when password is provided")
        return self


class AWSSESConfig(BaseEmailConfig):
    """Configuration for AWS SES email provider."""

    provider: Literal[EmailProviderType.AWS_SES] = EmailProviderType.AWS_SES
    region: str = Field(default="us-east-1", description="AWS region for SES")
    access_key_id: Optional[str] = Field(None, description="AWS access key ID")
    secret_access_key: Optional[str] = Field(None, description="AWS secret access key")
    session_token: Optional[str] = Field(
        None, description="AWS session token (for temporary credentials)"
    )
    configuration_set: Optional[str] = Field(None, description="SES configuration set name")
    use_iam_role: bool = Field(default=True, description="Use IAM role instead of credentials")

    # Advanced settings
    endpoint_url: Optional[str] = Field(None, description="Custom endpoint URL (for testing)")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    max_send_rate: Optional[float] = Field(None, ge=1.0, description="Maximum emails per second")

    @model_validator(mode="after")
    def validate_credentials(self) -> "AWSSESConfig":
        """Validate AWS credentials."""
        if not self.use_iam_role:
            if not self.access_key_id or not self.secret_access_key:
                raise ValueError(
                    "AWS credentials (access_key_id and secret_access_key) are required "
                    "when not using IAM role"
                )
        return self

    @field_validator("region")
    @classmethod
    def validate_region(cls, v: str) -> str:
        """Validate AWS region."""
        # Common AWS regions that support SES
        valid_regions = [
            "us-east-1",
            "us-east-2",
            "us-west-1",
            "us-west-2",
            "eu-west-1",
            "eu-west-2",
            "eu-west-3",
            "eu-central-1",
            "eu-north-1",
            "eu-south-1",
            "ap-south-1",
            "ap-northeast-1",
            "ap-northeast-2",
            "ap-northeast-3",
            "ap-southeast-1",
            "ap-southeast-2",
            "ca-central-1",
            "sa-east-1",
        ]

        if v not in valid_regions:
            raise ValueError(
                f"Invalid AWS region for SES: {v}. " f"Valid regions: {', '.join(valid_regions)}"
            )

        return v


# Union type for all email configurations
EmailConfig = ConsoleEmailConfig | SMTPEmailConfig | AWSSESConfig


def get_default_config(provider: EmailProviderType) -> Dict[str, Any]:
    """
    Get default configuration for a provider.

    Args:
        provider: Email provider type

    Returns:
        Default configuration dictionary
    """
    defaults = {
        "from_email": os.getenv("EMAIL_FROM_ADDRESS", "noreply@prism.thepaynes.ca"),
        "from_name": os.getenv("EMAIL_FROM_NAME", "Prism DNS"),
        "reply_to": os.getenv("EMAIL_REPLY_TO"),
        "enabled": os.getenv("EMAIL_ENABLED", "true").lower() == "true",
        "debug": os.getenv("EMAIL_DEBUG", "false").lower() == "true",
    }

    if provider == EmailProviderType.CONSOLE:
        defaults.update(
            {
                "format": os.getenv("EMAIL_CONSOLE_FORMAT", ConsoleFormat.PRETTY.value),
                "use_colors": os.getenv("EMAIL_CONSOLE_COLORS", "true").lower() == "true",
            }
        )
    elif provider == EmailProviderType.SMTP:
        defaults.update(
            {
                "host": os.getenv("SMTP_HOST"),
                "port": int(os.getenv("SMTP_PORT", "587")),
                "username": os.getenv("SMTP_USERNAME"),
                "password": os.getenv("SMTP_PASSWORD"),
                "use_tls": os.getenv("SMTP_USE_TLS", "true").lower() == "true",
                "use_ssl": os.getenv("SMTP_USE_SSL", "false").lower() == "true",
            }
        )
    elif provider == EmailProviderType.AWS_SES:
        defaults.update(
            {
                "region": os.getenv("AWS_REGION", "us-east-1"),
                "access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
                "secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
                "session_token": os.getenv("AWS_SESSION_TOKEN"),
                "configuration_set": os.getenv("SES_CONFIGURATION_SET"),
                "use_iam_role": os.getenv("SES_USE_IAM_ROLE", "true").lower() == "true",
            }
        )

    # Remove None values
    return {k: v for k, v in defaults.items() if v is not None}
