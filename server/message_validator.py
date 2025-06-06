#!/usr/bin/env python3
"""
Message Validation for Prism DNS Server (SCRUM-14)
Validates message content and formats for security and correctness.
"""

import re
import logging
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
import ipaddress


logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Exception raised for validation errors."""

    pass


class MessageValidator:
    """
    Validates message content and formats.

    Provides validation for hostnames, timestamps, IP addresses,
    and message structure according to the protocol specification.
    """

    def __init__(self):
        """Initialize message validator with validation rules."""
        # Hostname validation regex (RFC 1123 compliant)
        self.hostname_pattern = re.compile(
            r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
        )

        # Maximum hostname length (RFC 1123)
        self.max_hostname_length = 253

        # Supported message versions
        self.supported_versions = {"1.0"}

        # Supported message types
        self.supported_message_types = {"registration"}

        logger.debug("MessageValidator initialized")

    def validate_hostname(self, hostname: str) -> Tuple[bool, Optional[str]]:
        """
        Validate hostname according to RFC 1123.

        Args:
            hostname: Hostname to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not hostname:
            return False, "Hostname cannot be empty"

        if not isinstance(hostname, str):
            return False, "Hostname must be a string"

        # Check length
        if len(hostname) > self.max_hostname_length:
            return False, f"Hostname too long: {len(hostname)} > {self.max_hostname_length}"

        # Check for valid characters and format
        if not self.hostname_pattern.match(hostname):
            return False, "Hostname contains invalid characters or format"

        # Additional checks
        if hostname.startswith("-") or hostname.endswith("-"):
            return False, "Hostname cannot start or end with hyphen"

        if hostname.startswith(".") or hostname.endswith("."):
            return False, "Hostname cannot start or end with dot"

        if ".." in hostname:
            return False, "Hostname cannot contain consecutive dots"

        # Check individual labels (between dots)
        labels = hostname.split(".")
        for label in labels:
            if len(label) > 63:
                return False, f"Hostname label too long: {len(label)} > 63"

            if not label:
                return False, "Hostname cannot have empty labels"

        logger.debug(f"Hostname validation passed: {hostname}")
        return True, None

    def validate_ip_address(self, ip_address: str) -> Tuple[bool, Optional[str]]:
        """
        Validate IP address (IPv4 or IPv6).

        Args:
            ip_address: IP address to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not ip_address:
            return False, "IP address cannot be empty"

        if not isinstance(ip_address, str):
            return False, "IP address must be a string"

        try:
            # This validates both IPv4 and IPv6
            ipaddress.ip_address(ip_address)
            logger.debug(f"IP address validation passed: {ip_address}")
            return True, None

        except ValueError as e:
            return False, f"Invalid IP address format: {e}"

    def validate_timestamp(self, timestamp: str) -> Tuple[bool, Optional[str]]:
        """
        Validate ISO 8601 timestamp with time component.

        Args:
            timestamp: Timestamp string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not timestamp:
            return False, "Timestamp cannot be empty"

        if not isinstance(timestamp, str):
            return False, "Timestamp must be a string"

        # Check for basic timestamp format (must include time)
        if "T" not in timestamp:
            return False, "Timestamp must include time component (ISO 8601 format)"

        try:
            # Support both 'Z' suffix and '+00:00' format
            if timestamp.endswith("Z"):
                datetime.fromisoformat(timestamp[:-1] + "+00:00")
            else:
                datetime.fromisoformat(timestamp)

            logger.debug(f"Timestamp validation passed: {timestamp}")
            return True, None

        except ValueError as e:
            return False, f"Invalid timestamp format: {e}"

    def validate_message_structure(self, message: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate basic message structure.

        Args:
            message: Message dictionary to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(message, dict):
            return False, "Message must be a dictionary"

        # Check required fields for registration message
        required_fields = ["version", "type", "timestamp", "hostname"]

        for field in required_fields:
            if field not in message:
                return False, f"Missing required field: {field}"

            # Check field types
            if not isinstance(message[field], str):
                return False, f"Field '{field}' must be a string"

        # Validate version
        if message["version"] not in self.supported_versions:
            return False, f"Unsupported version: {message['version']}"

        # Validate message type
        if message["type"] not in self.supported_message_types:
            return False, f"Unsupported message type: {message['type']}"

        # Validate individual fields
        is_valid, error = self.validate_hostname(message["hostname"])
        if not is_valid:
            return False, f"Invalid hostname: {error}"

        is_valid, error = self.validate_timestamp(message["timestamp"])
        if not is_valid:
            return False, f"Invalid timestamp: {error}"

        logger.debug(
            f"Message structure validation passed for {message['type']} from {message['hostname']}"
        )
        return True, None

    def sanitize_hostname(self, hostname: str) -> str:
        """
        Sanitize hostname by applying safe transformations.

        Args:
            hostname: Raw hostname to sanitize

        Returns:
            Sanitized hostname string
        """
        if not isinstance(hostname, str):
            return ""

        # Convert to lowercase
        sanitized = hostname.lower()

        # Strip whitespace
        sanitized = sanitized.strip()

        # Remove consecutive dots
        while ".." in sanitized:
            sanitized = sanitized.replace("..", ".")

        # Remove leading/trailing dots and hyphens
        sanitized = sanitized.strip(".-")

        logger.debug(f"Hostname sanitized: '{hostname}' -> '{sanitized}'")
        return sanitized

    def validate_registration_message(self, message: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Comprehensive validation for registration messages.

        Args:
            message: Registration message to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Basic structure validation
        is_valid, error = self.validate_message_structure(message)
        if not is_valid:
            return False, error

        # Registration-specific validation
        if message["type"] != "registration":
            return False, "Message type must be 'registration'"

        # Additional hostname validation for registration
        hostname = message["hostname"]

        # Check for reserved hostnames
        reserved_hostnames = {"localhost", "broadcasthost"}
        if hostname.lower() in reserved_hostnames:
            logger.warning(f"Registration attempt with reserved hostname: {hostname}")
            # Allow but log warning (may be legitimate for testing)

        # Check for suspicious patterns
        if any(char in hostname for char in ["<", ">", '"', "'", "&"]):
            return False, "Hostname contains potentially dangerous characters"

        # Length checks
        if len(hostname) < 1:
            return False, "Hostname too short"

        if len(hostname) > 253:
            return False, "Hostname too long"

        logger.info(f"Registration message validation passed for hostname: {hostname}")
        return True, None

    def get_validation_stats(self) -> Dict[str, Any]:
        """
        Get validation statistics and configuration.

        Returns:
            Dictionary with validation statistics
        """
        return {
            "max_hostname_length": self.max_hostname_length,
            "supported_versions": list(self.supported_versions),
            "supported_message_types": list(self.supported_message_types),
            "hostname_pattern": self.hostname_pattern.pattern,
        }


class SecurityValidator:
    """Additional security-focused validation."""

    def __init__(self):
        """Initialize security validator."""
        # Patterns that might indicate malicious content
        self.suspicious_patterns = [
            re.compile(r"<script", re.IGNORECASE),
            re.compile(r"javascript:", re.IGNORECASE),
            re.compile(r"on\w+\s*=", re.IGNORECASE),  # Event handlers
            re.compile(r"[\x00-\x1f\x7f-\x9f]"),  # Control characters
        ]

        # Rate limiting could be added here
        self.max_hostname_registrations_per_ip = 100

        logger.debug("SecurityValidator initialized")

    def scan_for_suspicious_content(self, content: str) -> Tuple[bool, Optional[str]]:
        """
        Scan content for suspicious patterns.

        Args:
            content: Content to scan

        Returns:
            Tuple of (is_safe, warning_message)
        """
        if not isinstance(content, str):
            return True, None

        for pattern in self.suspicious_patterns:
            if pattern.search(content):
                logger.warning(f"Suspicious pattern detected in content: {pattern.pattern}")
                return False, f"Content contains suspicious pattern: {pattern.pattern}"

        return True, None

    def validate_message_security(self, message: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Perform security validation on message.

        Args:
            message: Message to validate

        Returns:
            Tuple of (is_safe, warning_message)
        """
        # Check all string fields for suspicious content
        for key, value in message.items():
            if isinstance(value, str):
                is_safe, warning = self.scan_for_suspicious_content(value)
                if not is_safe:
                    return False, f"Security issue in field '{key}': {warning}"

        return True, None


def create_validator() -> MessageValidator:
    """
    Create a message validator instance.

    Returns:
        Configured MessageValidator instance
    """
    return MessageValidator()


def create_security_validator() -> SecurityValidator:
    """
    Create a security validator instance.

    Returns:
        Configured SecurityValidator instance
    """
    return SecurityValidator()
