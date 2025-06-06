"""
Tests for Hostname Detection and System Information (SCRUM-6)
Following TDD approach as specified in the user story.
"""

import pytest
import platform
import socket
from unittest.mock import patch, MagicMock
from client.system_info import SystemInfo, HostnameValidationError


class TestSystemInfo:
    """Test suite for SystemInfo following SCRUM-6 requirements."""

    def test_hostname_detection_success(self):
        """Test successful hostname detection."""
        system_info = SystemInfo()
        hostname = system_info.get_hostname()

        assert isinstance(hostname, str)
        assert len(hostname) > 0
        # Should not be empty or just whitespace
        assert hostname.strip() != ""

    @patch("socket.gethostname")
    def test_hostname_detection_failure(self, mock_gethostname):
        """Test hostname detection when socket.gethostname fails."""
        mock_gethostname.side_effect = OSError("Hostname detection failed")

        system_info = SystemInfo()
        hostname = system_info.get_hostname()

        # Should return fallback hostname
        assert hostname.startswith("prism-client-")
        assert len(hostname) > len("prism-client-")

    def test_hostname_validation_valid(self):
        """Test hostname validation with valid hostnames."""
        system_info = SystemInfo()

        valid_hostnames = [
            "localhost",
            "my-computer",
            "server1",
            "test.example.com",
            "host-123",
            "a" * 63,  # Max single label length
        ]

        for hostname in valid_hostnames:
            # Should not raise any exception
            system_info.validate_hostname(hostname)

    def test_hostname_validation_invalid(self):
        """Test hostname validation with invalid hostnames."""
        system_info = SystemInfo()

        invalid_hostnames = [
            "",  # Empty
            " ",  # Whitespace only
            "a" * 64,  # Too long single label
            "host..name",  # Double dots
            ".hostname",  # Starts with dot
            "hostname.",  # Ends with dot
            "host name",  # Contains space
            "host@name",  # Contains invalid character
            "höst",  # Contains non-ASCII
        ]

        for hostname in invalid_hostnames:
            with pytest.raises(HostnameValidationError):
                system_info.validate_hostname(hostname)

    @patch("socket.gethostname")
    def test_fallback_hostname_generation(self, mock_gethostname):
        """Test fallback hostname generation."""
        mock_gethostname.side_effect = OSError("Hostname detection failed")

        system_info = SystemInfo()

        # Generate multiple fallback hostnames
        hostname1 = system_info.generate_fallback_hostname()
        hostname2 = system_info.generate_fallback_hostname()

        # Should both start with prefix
        assert hostname1.startswith("prism-client-")
        assert hostname2.startswith("prism-client-")

        # Should be different (due to timestamp/random component)
        assert hostname1 != hostname2

        # Should be valid hostnames
        system_info.validate_hostname(hostname1)
        system_info.validate_hostname(hostname2)

    def test_system_metadata_collection(self):
        """Test collection of optional system metadata."""
        system_info = SystemInfo()
        metadata = system_info.get_system_metadata()

        assert isinstance(metadata, dict)
        assert "os" in metadata
        assert "platform" in metadata
        assert "python_version" in metadata

        # Verify metadata values are strings
        assert isinstance(metadata["os"], str)
        assert isinstance(metadata["platform"], str)
        assert isinstance(metadata["python_version"], str)

        # Verify non-empty values
        assert len(metadata["os"]) > 0
        assert len(metadata["platform"]) > 0
        assert len(metadata["python_version"]) > 0

    def test_hostname_sanitization(self):
        """Test hostname sanitization functionality."""
        system_info = SystemInfo()

        test_cases = [
            ("  hostname  ", "hostname"),  # Trim whitespace
            ("HOSTNAME", "hostname"),  # Lowercase conversion
            ("Host-Name", "host-name"),  # Keep valid characters
            ("host_name", "host-name"),  # Convert underscores to hyphens
        ]

        for input_hostname, expected in test_cases:
            result = system_info.sanitize_hostname(input_hostname)
            assert result == expected

    @patch("platform.system")
    @patch("platform.platform")
    @patch("socket.gethostname")
    def test_cross_platform_compatibility(
        self, mock_gethostname, mock_platform_platform, mock_system
    ):
        """Test cross-platform compatibility."""
        # Test Windows
        mock_system.return_value = "Windows"
        mock_platform_platform.return_value = "Windows-10-10.0.19041-SP0"
        mock_gethostname.return_value = "WINDOWS-PC"

        system_info = SystemInfo()
        hostname = system_info.get_hostname()
        metadata = system_info.get_system_metadata()

        assert hostname == "windows-pc"  # Should be sanitized
        assert metadata["os"] == "Windows"

        # Test Linux
        mock_system.return_value = "Linux"
        mock_platform_platform.return_value = "Linux-5.4.0-42-generic-x86_64-with-glibc2.31"
        mock_gethostname.return_value = "linux-server"

        hostname = system_info.get_hostname()
        metadata = system_info.get_system_metadata()

        assert hostname == "linux-server"
        assert metadata["os"] == "Linux"

        # Test macOS
        mock_system.return_value = "Darwin"
        mock_platform_platform.return_value = "macOS-10.16-x86_64-i386-64bit"
        mock_gethostname.return_value = "MacBook-Pro"

        hostname = system_info.get_hostname()
        metadata = system_info.get_system_metadata()

        assert hostname == "macbook-pro"
        assert metadata["os"] == "Darwin"
