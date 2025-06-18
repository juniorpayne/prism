#!/usr/bin/env python3
"""
Base classes and interfaces for email providers.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EmailPriority(Enum):
    """Email priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass
class EmailAttachment:
    """Email attachment data."""

    filename: str
    content: bytes
    content_type: str = "application/octet-stream"
    content_id: Optional[str] = None
    is_inline: bool = False


@dataclass
class EmailMessage:
    """
    Email message data structure.

    This class represents a complete email message with all necessary fields
    for sending through any email provider.
    """

    to: List[str]
    subject: str
    html_body: str
    text_body: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    reply_to: Optional[str] = None
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    headers: Optional[Dict[str, str]] = None
    attachments: Optional[List[EmailAttachment]] = None
    priority: EmailPriority = EmailPriority.NORMAL
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate email message after initialization."""
        if not self.to:
            raise ValueError("At least one recipient is required")

        if not self.subject:
            raise ValueError("Subject is required")

        if not self.html_body and not self.text_body:
            raise ValueError("Either html_body or text_body is required")

        # Ensure lists are initialized
        self.to = [email.lower().strip() for email in self.to]
        if self.cc:
            self.cc = [email.lower().strip() for email in self.cc]
        if self.bcc:
            self.bcc = [email.lower().strip() for email in self.bcc]


@dataclass
class EmailResult:
    """
    Result of an email send operation.

    Contains success status and additional information about the send operation.
    """

    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    provider: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None
    retry_after: Optional[int] = None  # Seconds to wait before retry

    def __str__(self) -> str:
        """String representation of result."""
        if self.success:
            return (
                f"EmailResult(success=True, message_id={self.message_id}, provider={self.provider})"
            )
        else:
            return f"EmailResult(success=False, error={self.error}, provider={self.provider})"


class EmailProvider(ABC):
    """
    Abstract base class for all email providers.

    This class defines the interface that all email providers must implement.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize email provider.

        Args:
            config: Provider-specific configuration
        """
        self.config = config or {}
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def send_email(self, message: EmailMessage) -> EmailResult:
        """
        Send an email message.

        Args:
            message: Email message to send

        Returns:
            EmailResult with send operation status
        """
        pass

    @abstractmethod
    async def verify_configuration(self) -> bool:
        """
        Verify provider configuration is valid.

        Returns:
            True if configuration is valid, False otherwise
        """
        pass

    async def send_bulk(self, messages: List[EmailMessage]) -> List[EmailResult]:
        """
        Send multiple emails in bulk.

        Default implementation sends sequentially. Providers can override
        for more efficient bulk sending.

        Args:
            messages: List of email messages to send

        Returns:
            List of EmailResult objects
        """
        results = []
        for message in messages:
            try:
                result = await self.send_email(message)
                results.append(result)
            except Exception as e:
                self._logger.error(f"Error sending bulk email: {e}")
                results.append(
                    EmailResult(
                        success=False,
                        error=str(e),
                        provider=self.__class__.__name__,
                    )
                )
        return results

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return self.__class__.__name__.replace("EmailProvider", "")

    def __repr__(self) -> str:
        """String representation of provider."""
        return f"{self.__class__.__name__}(config_keys={list(self.config.keys())})"


class EmailProviderConfig:
    """Base configuration class for email providers."""

    def __init__(self, **kwargs):
        """Initialize configuration with keyword arguments."""
        for key, value in kwargs.items():
            setattr(self, key, value)

    def validate(self) -> None:
        """
        Validate configuration.

        Should be overridden by subclasses to implement specific validation.
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {key: value for key, value in self.__dict__.items() if not key.startswith("_")}
