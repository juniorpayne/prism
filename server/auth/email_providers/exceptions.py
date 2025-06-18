#!/usr/bin/env python3
"""
Email provider exceptions.
"""

from typing import Any, Dict, Optional


class EmailProviderError(Exception):
    """Base exception for email provider errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize email provider error.

        Args:
            message: Error message
            error_code: Provider-specific error code
            details: Additional error details
        """
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class EmailConfigurationError(EmailProviderError):
    """Raised when email provider configuration is invalid."""

    def __init__(self, message: str, missing_fields: Optional[list] = None):
        """
        Initialize configuration error.

        Args:
            message: Error message
            missing_fields: List of missing configuration fields
        """
        details = {"missing_fields": missing_fields} if missing_fields else {}
        super().__init__(message, error_code="CONFIG_ERROR", details=details)


class EmailDeliveryError(EmailProviderError):
    """Raised when email delivery fails."""

    def __init__(
        self,
        message: str,
        recipient: Optional[str] = None,
        retry_after: Optional[int] = None,
        permanent: bool = False,
    ):
        """
        Initialize delivery error.

        Args:
            message: Error message
            recipient: Failed recipient email
            retry_after: Seconds to wait before retry
            permanent: Whether this is a permanent failure
        """
        details = {
            "recipient": recipient,
            "retry_after": retry_after,
            "permanent": permanent,
        }
        error_code = "PERMANENT_FAILURE" if permanent else "TEMPORARY_FAILURE"
        super().__init__(message, error_code=error_code, details=details)


class EmailTemplateError(EmailProviderError):
    """Raised when email template rendering fails."""

    def __init__(
        self,
        message: str,
        template_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize template error.

        Args:
            message: Error message
            template_name: Name of the failed template
            context: Template context that caused the error
        """
        details = {"template_name": template_name, "context": context}
        super().__init__(message, error_code="TEMPLATE_ERROR", details=details)


class EmailRateLimitError(EmailProviderError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: int,
        limit: Optional[int] = None,
        window: Optional[str] = None,
    ):
        """
        Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retry
            limit: Rate limit threshold
            window: Rate limit window (e.g., "1h", "24h")
        """
        details = {
            "retry_after": retry_after,
            "limit": limit,
            "window": window,
        }
        super().__init__(message, error_code="RATE_LIMIT_EXCEEDED", details=details)


class EmailAuthenticationError(EmailProviderError):
    """Raised when provider authentication fails."""

    def __init__(self, message: str, provider: Optional[str] = None):
        """
        Initialize authentication error.

        Args:
            message: Error message
            provider: Provider name that failed authentication
        """
        details = {"provider": provider}
        super().__init__(message, error_code="AUTH_FAILED", details=details)
