"""
Integration test for System Information Detection (SCRUM-6)
Tests the complete hostname detection and system info workflow.
"""

from client.system_info import SystemInfo, HostnameValidationError


def test_complete_system_info_workflow():
    """Test the complete system information detection workflow."""
    system_info = SystemInfo()

    # Test hostname detection
    hostname = system_info.get_hostname()
    assert isinstance(hostname, str)
    assert len(hostname) > 0

    # Hostname should be valid (no exception raised)
    system_info.validate_hostname(hostname)

    # Test system metadata collection
    metadata = system_info.get_system_metadata()
    assert isinstance(metadata, dict)

    required_fields = ["os", "platform", "python_version", "architecture", "processor"]
    for field in required_fields:
        assert field in metadata
        assert isinstance(metadata[field], str)
        assert len(metadata[field]) > 0

    # Test sanitization with real hostname
    raw_hostname = system_info.get_hostname()
    sanitized = system_info.sanitize_hostname(raw_hostname.upper())
    assert sanitized == raw_hostname  # Should be the same when converted back

    print(f"Detected hostname: {hostname}")
    print(f"System metadata: {metadata}")


def test_fallback_hostname_functionality():
    """Test that fallback hostname generation works and produces valid hostnames."""
    system_info = SystemInfo()

    # Generate multiple fallback hostnames
    hostnames = [system_info.generate_fallback_hostname() for _ in range(5)]

    # All should be different
    assert len(set(hostnames)) == 5

    # All should be valid
    for hostname in hostnames:
        system_info.validate_hostname(hostname)
        assert hostname.startswith("prism-client-")

    print(f"Generated fallback hostnames: {hostnames}")


if __name__ == "__main__":
    test_complete_system_info_workflow()
    test_fallback_hostname_functionality()
