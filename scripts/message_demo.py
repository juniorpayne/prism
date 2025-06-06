#!/usr/bin/env python3
"""
Demo script for JSON Message Protocol (SCRUM-7)
Demonstrates message creation, validation, and serialization.
"""

import json
import sys
import os

# Add parent directory to path to import client modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from client.message_protocol import MessageProtocol, TCPSender, MessageValidationError
from client.system_info import SystemInfo


def main():
    """Demonstrate the message protocol functionality."""
    print("=== Prism Client Message Protocol Demo ===\n")

    # Initialize components
    system_info = SystemInfo()
    protocol = MessageProtocol()
    sender = TCPSender()

    try:
        # Step 1: Get hostname
        print("1. Detecting hostname...")
        hostname = system_info.get_hostname()
        print(f"   Detected hostname: {hostname}")

        # Step 2: Create message
        print("\n2. Creating registration message...")
        message = protocol.create_registration_message(hostname)
        print(f"   Message created: {json.dumps(message, indent=2)}")

        # Step 3: Validate message
        print("\n3. Validating message...")
        protocol.validate_message(message)
        print("   ✓ Message validation passed")

        # Step 4: Serialize message
        print("\n4. Serializing message...")
        serialized = protocol.serialize_message(message)
        print(f"   Serialized size: {len(serialized)} bytes")
        print(f"   Serialized data: {serialized.decode('utf-8')}")

        # Step 5: Frame message for TCP
        print("\n5. Framing message for TCP...")
        framed = sender.frame_message(serialized)
        print(f"   Framed size: {len(framed)} bytes (including 4-byte length prefix)")
        print(f"   Length prefix: {framed[:4].hex()}")

        # Step 6: Demonstrate unframing
        print("\n6. Demonstrating message unframing...")
        unframed = sender.unframe_message(framed)
        assert unframed == serialized
        print("   ✓ Unframing successful - message integrity verified")

        # Step 7: Show protocol versioning
        print("\n7. Protocol versioning...")
        print(f"   Current version: {protocol.get_current_version()}")
        print(f"   Supported versions: {sorted(protocol._supported_versions)}")
        print(f"   Supported message types: {sorted(protocol.get_supported_types())}")

        print("\n✅ All protocol operations completed successfully!")

    except MessageValidationError as e:
        print(f"\n❌ Message protocol error: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
