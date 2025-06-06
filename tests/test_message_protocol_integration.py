"""
Integration test for JSON Message Protocol Implementation (SCRUM-7)
Tests the complete message protocol workflow including integration with SystemInfo.
"""

import json
from client.message_protocol import MessageProtocol, TCPSender
from client.system_info import SystemInfo


def test_complete_protocol_integration():
    """Test complete protocol integration with real hostname detection."""
    # Get real hostname from SystemInfo
    system_info = SystemInfo()
    hostname = system_info.get_hostname()

    # Create message protocol
    protocol = MessageProtocol()

    # Create registration message
    message = protocol.create_registration_message(hostname)

    # Validate message
    protocol.validate_message(message)

    # Serialize message
    serialized = protocol.serialize_message(message)

    # Test TCP framing
    sender = TCPSender()
    framed = sender.frame_message(serialized)

    # Unframe and verify
    unframed = sender.unframe_message(framed)
    assert unframed == serialized

    # Parse back to verify integrity
    parsed = json.loads(unframed.decode("utf-8"))
    assert parsed["hostname"] == hostname
    assert parsed["version"] == "1.0"
    assert parsed["type"] == "registration"
    assert "timestamp" in parsed

    print(f"Integration test successful!")
    print(f"Hostname: {hostname}")
    print(f"Message: {json.dumps(parsed, indent=2)}")
    print(f"Serialized size: {len(serialized)} bytes")
    print(f"Framed size: {len(framed)} bytes")


def test_message_size_and_performance():
    """Test message size characteristics and basic performance."""
    protocol = MessageProtocol()

    # Test with various hostname lengths
    test_hostnames = [
        "a",
        "short-host",
        "medium-length-hostname-test",
        "very-long-hostname-for-testing-message-size-characteristics.example.com",
    ]

    for hostname in test_hostnames:
        message = protocol.create_registration_message(hostname)
        serialized = protocol.serialize_message(message)

        sender = TCPSender()
        framed = sender.frame_message(serialized)

        print(f"Hostname: {hostname}")
        print(f"  Message size: {len(serialized)} bytes")
        print(f"  Framed size: {len(framed)} bytes")
        print(f"  Overhead: {len(framed) - len(serialized)} bytes")
        print()


if __name__ == "__main__":
    test_complete_protocol_integration()
    print("\n" + "=" * 50 + "\n")
    test_message_size_and_performance()
