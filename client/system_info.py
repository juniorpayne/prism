"""
System Information Detection for Prism Host Client (SCRUM-6)
Handles hostname detection, validation, and system metadata collection.
"""

import socket
import platform
import re
import time
import random
from typing import Dict, Any


class HostnameValidationError(Exception):
    """Custom exception for hostname validation errors."""

    pass


class SystemInfo:
    """
    Manages system information detection including hostname and metadata.
    Provides cross-platform hostname detection with fallback mechanisms.
    """

    def __init__(self):
        """Initialize the SystemInfo detector."""
        self._fallback_prefix = "prism-client-"

    def get_hostname(self) -> str:
        """
        Get the system hostname with sanitization and fallback.

        Returns:
            String containing the detected and sanitized hostname

        Note:
            If hostname detection fails, returns a generated fallback hostname.
        """
        try:
            # Try to get hostname from system
            raw_hostname = socket.gethostname()

            if not raw_hostname or raw_hostname.strip() == "":
                # Empty hostname, use fallback
                return self.generate_fallback_hostname()

            # Sanitize the hostname
            sanitized = self.sanitize_hostname(raw_hostname)

            # Validate the sanitized hostname
            self.validate_hostname(sanitized)

            return sanitized

        except (OSError, socket.error, HostnameValidationError):
            # Hostname detection failed or validation failed, use fallback
            return self.generate_fallback_hostname()

    def validate_hostname(self, hostname: str) -> None:
        """
        Validate hostname according to RFC standards.

        Args:
            hostname: Hostname string to validate

        Raises:
            HostnameValidationError: If hostname is invalid
        """
        if not hostname or not isinstance(hostname, str):
            raise HostnameValidationError("Hostname must be a non-empty string")

        # Remove leading/trailing whitespace for validation
        hostname = hostname.strip()

        if not hostname:
            raise HostnameValidationError("Hostname cannot be empty or whitespace only")

        # Check overall length (RFC 1035: max 255 characters)
        if len(hostname) > 255:
            raise HostnameValidationError("Hostname too long (max 255 characters)")

        # Check for invalid starting/ending characters
        if hostname.startswith(".") or hostname.endswith("."):
            raise HostnameValidationError("Hostname cannot start or end with a dot")

        # Split into labels and validate each
        labels = hostname.split(".")

        for label in labels:
            if not label:
                raise HostnameValidationError("Hostname cannot contain empty labels (double dots)")

            # Check label length (RFC 1035: max 63 characters per label)
            if len(label) > 63:
                raise HostnameValidationError(
                    f"Hostname label too long: '{label}' (max 63 characters)"
                )

            # Check for valid characters (letters, digits, hyphens)
            if not re.match(r"^[a-zA-Z0-9-]+$", label):
                raise HostnameValidationError(f"Invalid characters in hostname label: '{label}'")

            # Check that label doesn't start or end with hyphen
            if label.startswith("-") or label.endswith("-"):
                raise HostnameValidationError(
                    f"Hostname label cannot start or end with hyphen: '{label}'"
                )

    def sanitize_hostname(self, hostname: str) -> str:
        """
        Sanitize hostname to make it valid.

        Args:
            hostname: Raw hostname string

        Returns:
            Sanitized hostname string
        """
        if not hostname:
            return ""

        # Remove leading/trailing whitespace
        sanitized = hostname.strip()

        # Convert to lowercase
        sanitized = sanitized.lower()

        # Replace underscores with hyphens
        sanitized = sanitized.replace("_", "-")

        # Remove any non-ASCII characters
        sanitized = re.sub(r"[^\x00-\x7F]", "", sanitized)

        # Remove any characters that aren't letters, digits, dots, or hyphens
        sanitized = re.sub(r"[^a-z0-9.-]", "", sanitized)

        # Remove any double dots
        while ".." in sanitized:
            sanitized = sanitized.replace("..", ".")

        # Remove leading/trailing dots
        sanitized = sanitized.strip(".")

        return sanitized

    def generate_fallback_hostname(self) -> str:
        """
        Generate a fallback hostname when detection fails.

        Returns:
            Generated fallback hostname
        """
        # Use timestamp and random component for uniqueness
        timestamp = str(int(time.time()))[-6:]  # Last 6 digits of timestamp
        random_part = str(random.randint(100, 999))

        fallback = f"{self._fallback_prefix}{timestamp}-{random_part}"

        return fallback

    def get_system_metadata(self) -> Dict[str, Any]:
        """
        Collect optional system metadata.

        Returns:
            Dictionary containing system metadata
        """
        try:
            metadata = {
                "os": platform.system(),
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "architecture": platform.machine(),
                "processor": platform.processor() or "unknown",
            }

            # Ensure all values are strings and non-empty
            for key, value in metadata.items():
                if not isinstance(value, str):
                    metadata[key] = str(value)
                if not metadata[key]:
                    metadata[key] = "unknown"

            return metadata

        except Exception:
            # Return minimal metadata if collection fails
            return {
                "os": "unknown",
                "platform": "unknown",
                "python_version": "unknown",
                "architecture": "unknown",
                "processor": "unknown",
            }
