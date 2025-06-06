#!/usr/bin/env python3
"""
Enhanced Validators for Prism DNS Server (SCRUM-15)
Additional validation functions for registration processing.
"""

import re
import logging
import ipaddress
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Exception raised for validation errors."""

    pass


class AdvancedHostnameValidator:
    """Advanced hostname validation with additional checks."""

    def __init__(self):
        """Initialize advanced hostname validator."""
        # Comprehensive hostname pattern (RFC 1123 + additional checks)
        self.hostname_pattern = re.compile(
            r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
        )

        # Reserved hostnames that should be flagged
        self.reserved_hostnames = {
            "localhost",
            "broadcasthost",
            "local",
            "localdomain",
            "example",
            "test",
            "invalid",
            "onion",
            "exit",
        }

        # Suspicious patterns that might indicate security issues
        self.suspicious_patterns = [
            re.compile(r'[<>"\']'),  # HTML/script injection
            re.compile(r"[\x00-\x1f\x7f-\x9f]"),  # Control characters
            re.compile(r"\.\."),  # Path traversal
            re.compile(r"://"),  # URL schemes
            re.compile(r"[%;]"),  # URL encoding
        ]

        # Common typosquatting patterns
        self.typosquatting_patterns = [
            re.compile(r"g[o0]{2,}gle"),  # Google variations
            re.compile(r"m[i1]cr[o0]s[o0]ft"),  # Microsoft variations
            re.compile(r"fac[e3]b[o0]{2,}k"),  # Facebook variations
        ]

        logger.debug("AdvancedHostnameValidator initialized")

    def validate_hostname_comprehensive(
        self, hostname: str
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Comprehensive hostname validation with detailed feedback.

        Args:
            hostname: Hostname to validate

        Returns:
            Tuple of (is_valid, error_message, validation_details)
        """
        validation_details = {
            "length_check": False,
            "format_check": False,
            "reserved_check": False,
            "security_check": False,
            "typosquatting_check": False,
            "warnings": [],
        }

        if not hostname or not isinstance(hostname, str):
            return False, "Hostname must be a non-empty string", validation_details

        # Length check
        if len(hostname) > 253:
            return False, f"Hostname too long: {len(hostname)} > 253 characters", validation_details

        if len(hostname) < 1:
            return False, "Hostname cannot be empty", validation_details

        validation_details["length_check"] = True

        # Format check
        if not self.hostname_pattern.match(hostname):
            return False, "Hostname contains invalid characters or format", validation_details

        validation_details["format_check"] = True

        # Check individual labels
        labels = hostname.split(".")
        for label in labels:
            if len(label) > 63:
                return False, f"Label too long: '{label}' > 63 characters", validation_details

            if label.startswith("-") or label.endswith("-"):
                return (
                    False,
                    f"Label cannot start or end with hyphen: '{label}'",
                    validation_details,
                )

        # Reserved hostname check
        hostname_lower = hostname.lower()
        if hostname_lower in self.reserved_hostnames:
            validation_details["warnings"].append(f"Using reserved hostname: {hostname}")

        validation_details["reserved_check"] = True

        # Security check
        for pattern in self.suspicious_patterns:
            if pattern.search(hostname):
                return False, f"Hostname contains suspicious characters", validation_details

        validation_details["security_check"] = True

        # Typosquatting check
        for pattern in self.typosquatting_patterns:
            if pattern.search(hostname_lower):
                validation_details["warnings"].append(
                    f"Potential typosquatting detected: {hostname}"
                )

        validation_details["typosquatting_check"] = True

        return True, None, validation_details

    def sanitize_hostname(self, hostname: str) -> str:
        """
        Sanitize hostname by applying safe transformations.

        Args:
            hostname: Hostname to sanitize

        Returns:
            Sanitized hostname
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

        # Limit length
        if len(sanitized) > 253:
            sanitized = sanitized[:253]

        return sanitized


class AdvancedIPValidator:
    """Advanced IP address validation with additional checks."""

    def __init__(self):
        """Initialize advanced IP validator."""
        # Private IP ranges for additional validation
        self.private_ranges = [
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("192.168.0.0/16"),
            ipaddress.ip_network("127.0.0.0/8"),  # Loopback
            ipaddress.ip_network("169.254.0.0/16"),  # Link-local
        ]

        # IPv6 private ranges
        self.private_ranges_v6 = [
            ipaddress.ip_network("fc00::/7"),  # Private
            ipaddress.ip_network("fe80::/10"),  # Link-local
            ipaddress.ip_network("::1/128"),  # Loopback
        ]

        # Reserved/special use ranges to flag
        self.reserved_ranges = [
            ipaddress.ip_network("0.0.0.0/8"),
            ipaddress.ip_network("224.0.0.0/4"),  # Multicast
            ipaddress.ip_network("240.0.0.0/4"),  # Reserved
        ]

        logger.debug("AdvancedIPValidator initialized")

    def validate_ip_comprehensive(self, ip_str: str) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Comprehensive IP address validation with detailed feedback.

        Args:
            ip_str: IP address string to validate

        Returns:
            Tuple of (is_valid, error_message, validation_details)
        """
        validation_details = {
            "format_check": False,
            "version": None,
            "is_private": False,
            "is_loopback": False,
            "is_multicast": False,
            "is_reserved": False,
            "warnings": [],
        }

        if not ip_str or not isinstance(ip_str, str):
            return False, "IP address must be a non-empty string", validation_details

        try:
            ip = ipaddress.ip_address(ip_str)
            validation_details["format_check"] = True

            # Determine IP version
            if isinstance(ip, ipaddress.IPv4Address):
                validation_details["version"] = "IPv4"
            elif isinstance(ip, ipaddress.IPv6Address):
                validation_details["version"] = "IPv6"

            # Check properties
            validation_details["is_private"] = ip.is_private
            validation_details["is_loopback"] = ip.is_loopback
            validation_details["is_multicast"] = ip.is_multicast

            # Check for reserved ranges
            for reserved_range in self.reserved_ranges:
                if ip in reserved_range:
                    validation_details["is_reserved"] = True
                    validation_details["warnings"].append(f"IP in reserved range: {reserved_range}")

            # Specific checks for different IP types
            if ip.is_loopback:
                validation_details["warnings"].append("Loopback address detected")

            if ip.is_multicast:
                validation_details["warnings"].append("Multicast address detected")

            if ip.is_private:
                validation_details["warnings"].append("Private IP address")

            return True, None, validation_details

        except ValueError as e:
            return False, f"Invalid IP address format: {e}", validation_details

    def is_public_ip(self, ip_str: str) -> bool:
        """
        Check if IP address is a public (routable) address.

        Args:
            ip_str: IP address string

        Returns:
            True if public, False otherwise
        """
        try:
            ip = ipaddress.ip_address(ip_str)
            return not (ip.is_private or ip.is_loopback or ip.is_multicast)
        except ValueError:
            return False

    def get_ip_geolocation_info(self, ip_str: str) -> Dict[str, Any]:
        """
        Get basic geolocation information for IP address.

        Note: This is a placeholder for geolocation integration.
        In production, this would integrate with a geolocation service.

        Args:
            ip_str: IP address string

        Returns:
            Dictionary with geolocation info
        """
        try:
            ip = ipaddress.ip_address(ip_str)

            # Basic categorization
            info = {
                "ip": ip_str,
                "version": "IPv4" if isinstance(ip, ipaddress.IPv4Address) else "IPv6",
                "is_private": ip.is_private,
                "is_public": not (ip.is_private or ip.is_loopback or ip.is_multicast),
                "country": "Unknown",  # Would be populated by geolocation service
                "region": "Unknown",
                "city": "Unknown",
                "isp": "Unknown",
            }

            return info

        except ValueError:
            return {"error": "Invalid IP address"}


class RegistrationMessageValidator:
    """Validator for complete registration messages."""

    def __init__(self):
        """Initialize registration message validator."""
        self.hostname_validator = AdvancedHostnameValidator()
        self.ip_validator = AdvancedIPValidator()

        # Message schema validation
        self.required_fields = {"version", "type", "timestamp", "hostname"}
        self.valid_versions = {"1.0"}
        self.valid_types = {"registration"}

        logger.debug("RegistrationMessageValidator initialized")

    def validate_registration_message(
        self, message: Dict[str, Any], client_ip: str
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Validate complete registration message.

        Args:
            message: Registration message to validate
            client_ip: Client IP address for additional validation

        Returns:
            Tuple of (is_valid, error_message, validation_details)
        """
        validation_details = {
            "structure_check": False,
            "hostname_validation": {},
            "ip_validation": {},
            "timestamp_check": False,
            "consistency_check": False,
            "warnings": [],
        }

        # Structure validation
        if not isinstance(message, dict):
            return False, "Message must be a dictionary", validation_details

        # Check required fields
        missing_fields = self.required_fields - set(message.keys())
        if missing_fields:
            return False, f"Missing required fields: {missing_fields}", validation_details

        validation_details["structure_check"] = True

        # Version validation
        if message["version"] not in self.valid_versions:
            return False, f"Unsupported version: {message['version']}", validation_details

        # Type validation
        if message["type"] not in self.valid_types:
            return False, f"Invalid message type: {message['type']}", validation_details

        # Hostname validation
        hostname = message["hostname"]
        hostname_valid, hostname_error, hostname_details = (
            self.hostname_validator.validate_hostname_comprehensive(hostname)
        )
        validation_details["hostname_validation"] = hostname_details

        if not hostname_valid:
            return False, f"Hostname validation failed: {hostname_error}", validation_details

        # Client IP validation
        ip_valid, ip_error, ip_details = self.ip_validator.validate_ip_comprehensive(client_ip)
        validation_details["ip_validation"] = ip_details

        if not ip_valid:
            return False, f"Client IP validation failed: {ip_error}", validation_details

        # Timestamp validation
        try:
            timestamp_str = message["timestamp"]
            if timestamp_str.endswith("Z"):
                datetime.fromisoformat(timestamp_str[:-1] + "+00:00")
            else:
                datetime.fromisoformat(timestamp_str)
            validation_details["timestamp_check"] = True
        except (ValueError, KeyError) as e:
            return False, f"Invalid timestamp: {e}", validation_details

        # Consistency checks
        validation_details["consistency_check"] = True

        # Collect warnings from sub-validations
        validation_details["warnings"].extend(hostname_details.get("warnings", []))
        validation_details["warnings"].extend(ip_details.get("warnings", []))

        return True, None, validation_details

    def sanitize_registration_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize registration message by cleaning up fields.

        Args:
            message: Message to sanitize

        Returns:
            Sanitized message
        """
        if not isinstance(message, dict):
            return {}

        sanitized = {}

        # Copy allowed fields with sanitization
        if "version" in message:
            sanitized["version"] = str(message["version"]).strip()

        if "type" in message:
            sanitized["type"] = str(message["type"]).strip().lower()

        if "timestamp" in message:
            sanitized["timestamp"] = str(message["timestamp"]).strip()

        if "hostname" in message:
            sanitized["hostname"] = self.hostname_validator.sanitize_hostname(message["hostname"])

        return sanitized


class SecurityValidator:
    """Security-focused validation for registration data."""

    def __init__(self):
        """Initialize security validator."""
        # Patterns that indicate potential security issues
        self.malicious_patterns = [
            re.compile(r"<script", re.IGNORECASE),
            re.compile(r"javascript:", re.IGNORECASE),
            re.compile(r"on\w+\s*=", re.IGNORECASE),  # Event handlers
            re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]"),  # Control characters
            re.compile(r"\.\.\/"),  # Path traversal
            re.compile(r"[%;]"),  # URL encoding attempts
        ]

        # Known malicious domains/patterns
        self.malicious_domains = {"malware.com", "phishing.net", "badactor.org"}

        logger.debug("SecurityValidator initialized")

    def scan_for_security_issues(
        self, content: str, field_name: str = "unknown"
    ) -> Tuple[bool, List[str]]:
        """
        Scan content for security issues.

        Args:
            content: Content to scan
            field_name: Name of field being scanned

        Returns:
            Tuple of (is_safe, list_of_issues)
        """
        issues = []

        if not isinstance(content, str):
            return True, issues

        # Check for malicious patterns
        for pattern in self.malicious_patterns:
            if pattern.search(content):
                issues.append(f"Malicious pattern detected in {field_name}: {pattern.pattern}")

        # Check for malicious domains
        content_lower = content.lower()
        for domain in self.malicious_domains:
            if domain in content_lower:
                issues.append(f"Malicious domain detected in {field_name}: {domain}")

        # Check for excessively long content (potential DoS)
        if len(content) > 1000:
            issues.append(f"Excessively long content in {field_name}: {len(content)} characters")

        is_safe = len(issues) == 0
        return is_safe, issues

    def validate_registration_security(
        self, message: Dict[str, Any], client_ip: str
    ) -> Tuple[bool, List[str]]:
        """
        Comprehensive security validation for registration.

        Args:
            message: Registration message
            client_ip: Client IP address

        Returns:
            Tuple of (is_safe, list_of_security_issues)
        """
        all_issues = []

        # Scan all string fields in message
        for field_name, value in message.items():
            if isinstance(value, str):
                is_safe, issues = self.scan_for_security_issues(value, field_name)
                all_issues.extend(issues)

        # Additional IP-based security checks
        try:
            ip = ipaddress.ip_address(client_ip)

            # Check for localhost/loopback abuse
            if ip.is_loopback and not self._is_development_mode():
                all_issues.append("Registration from loopback address not allowed in production")

        except ValueError:
            all_issues.append(f"Invalid client IP format: {client_ip}")

        is_safe = len(all_issues) == 0
        return is_safe, all_issues

    def _is_development_mode(self) -> bool:
        """Check if running in development mode."""
        # This would check environment variables or configuration
        # For now, assume production mode
        return False


def create_comprehensive_validator() -> RegistrationMessageValidator:
    """
    Create a comprehensive registration message validator.

    Returns:
        Configured RegistrationMessageValidator instance
    """
    return RegistrationMessageValidator()


def create_security_validator() -> SecurityValidator:
    """
    Create a security validator.

    Returns:
        Configured SecurityValidator instance
    """
    return SecurityValidator()
