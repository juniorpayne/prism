#!/usr/bin/env python3
"""
Tests for Message Protocol Handling (SCRUM-14)
Test-driven development for length-prefixed JSON message protocol.
"""

import asyncio
import json
import struct
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch


class TestMessageProtocol(unittest.TestCase):
    """Test message protocol framing and parsing."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_registration_message = {
            "version": "1.0",
            "type": "registration",
            "timestamp": "2025-06-01T15:30:00Z",
            "hostname": "test-host-001",
        }

        self.sample_response_message = {
            "version": "1.0",
            "type": "response",
            "status": "success",
            "message": "Registration successful",
            "timestamp": "2025-06-01T15:30:01Z",
        }

    def test_message_protocol_class_exists(self):
        """Test that MessageProtocol class exists."""
        try:
            from server.protocol import MessageProtocol

            self.assertTrue(callable(MessageProtocol))
        except ImportError:
            self.fail("MessageProtocol should be importable from server.protocol")

    def test_encode_message(self):
        """Test encoding JSON message with length prefix."""
        from server.protocol import MessageProtocol

        protocol = MessageProtocol()
        encoded = protocol.encode_message(self.sample_registration_message)

        # Should have 4-byte length prefix + JSON data
        self.assertGreater(len(encoded), 4)

        # First 4 bytes should be message length
        message_length = struct.unpack("!I", encoded[:4])[0]
        json_data = encoded[4:]

        self.assertEqual(len(json_data), message_length)

        # JSON data should be parseable
        parsed = json.loads(json_data.decode("utf-8"))
        self.assertEqual(parsed, self.sample_registration_message)

    def test_decode_message_complete(self):
        """Test decoding complete length-prefixed message."""
        from server.protocol import MessageProtocol

        protocol = MessageProtocol()

        # Encode a message first
        encoded = protocol.encode_message(self.sample_registration_message)

        # Decode it back
        messages = protocol.decode_messages(encoded)

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0], self.sample_registration_message)

    def test_decode_message_partial(self):
        """Test decoding partial messages and buffering."""
        from server.protocol import MessageProtocol

        protocol = MessageProtocol()

        # Encode a message
        encoded = protocol.encode_message(self.sample_registration_message)

        # Send partial message (first half)
        partial1 = encoded[: len(encoded) // 2]
        messages1 = protocol.decode_messages(partial1)
        self.assertEqual(len(messages1), 0)  # No complete messages yet

        # Send remaining message
        partial2 = encoded[len(encoded) // 2 :]
        messages2 = protocol.decode_messages(partial2)
        self.assertEqual(len(messages2), 1)
        self.assertEqual(messages2[0], self.sample_registration_message)

    def test_decode_multiple_messages(self):
        """Test decoding multiple messages in single buffer."""
        from server.protocol import MessageProtocol

        protocol = MessageProtocol()

        # Encode multiple messages
        msg1_encoded = protocol.encode_message(self.sample_registration_message)
        msg2_encoded = protocol.encode_message(self.sample_response_message)

        # Combine messages
        combined = msg1_encoded + msg2_encoded

        # Decode both
        messages = protocol.decode_messages(combined)

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0], self.sample_registration_message)
        self.assertEqual(messages[1], self.sample_response_message)

    def test_decode_invalid_json(self):
        """Test handling of invalid JSON in message."""
        from server.protocol import MessageProtocol, ProtocolError

        protocol = MessageProtocol()

        # Create message with invalid JSON
        invalid_json = b"{ invalid json }"
        length_prefix = struct.pack("!I", len(invalid_json))
        encoded = length_prefix + invalid_json

        with self.assertRaises(ProtocolError):
            protocol.decode_messages(encoded)

    def test_decode_oversized_message(self):
        """Test handling of oversized messages."""
        from server.protocol import MessageProtocol, ProtocolError

        protocol = MessageProtocol(max_message_size=1024)  # 1KB limit

        # Create oversized message
        large_data = "x" * 2048  # 2KB
        oversized_length = struct.pack("!I", len(large_data))

        with self.assertRaises(ProtocolError):
            protocol.decode_messages(oversized_length)

    def test_create_registration_response_success(self):
        """Test creating successful registration response."""
        from server.protocol import MessageProtocol

        protocol = MessageProtocol()
        response = protocol.create_registration_response(
            status="success", message="Registration successful"
        )

        self.assertEqual(response["version"], "1.0")
        self.assertEqual(response["type"], "response")
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["message"], "Registration successful")
        self.assertIn("timestamp", response)

    def test_create_registration_response_error(self):
        """Test creating error registration response."""
        from server.protocol import MessageProtocol

        protocol = MessageProtocol()
        response = protocol.create_registration_response(
            status="error", message="Invalid hostname format"
        )

        self.assertEqual(response["status"], "error")
        self.assertEqual(response["message"], "Invalid hostname format")

    def test_validate_registration_message_valid(self):
        """Test validation of valid registration message."""
        from server.protocol import MessageProtocol

        protocol = MessageProtocol()
        is_valid, error = protocol.validate_registration_message(self.sample_registration_message)

        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_registration_message_missing_fields(self):
        """Test validation of message with missing required fields."""
        from server.protocol import MessageProtocol

        protocol = MessageProtocol()

        # Missing hostname
        invalid_message = {
            "version": "1.0",
            "type": "registration",
            "timestamp": "2025-06-01T15:30:00Z",
        }

        is_valid, error = protocol.validate_registration_message(invalid_message)

        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        self.assertIn("hostname", error.lower())

    def test_validate_registration_message_invalid_version(self):
        """Test validation of message with unsupported version."""
        from server.protocol import MessageProtocol

        protocol = MessageProtocol()

        # Unsupported version
        invalid_message = {
            "version": "2.0",  # Unsupported
            "type": "registration",
            "timestamp": "2025-06-01T15:30:00Z",
            "hostname": "test-host",
        }

        is_valid, error = protocol.validate_registration_message(invalid_message)

        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        self.assertIn("version", error.lower())

    def test_validate_registration_message_invalid_type(self):
        """Test validation of message with wrong type."""
        from server.protocol import MessageProtocol

        protocol = MessageProtocol()

        # Wrong message type
        invalid_message = {
            "version": "1.0",
            "type": "heartbeat",  # Should be registration
            "timestamp": "2025-06-01T15:30:00Z",
            "hostname": "test-host",
        }

        is_valid, error = protocol.validate_registration_message(invalid_message)

        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        self.assertIn("type", error.lower())

    def test_protocol_buffer_management(self):
        """Test internal buffer management for partial messages."""
        from server.protocol import MessageProtocol

        protocol = MessageProtocol()

        # Send length prefix only
        length_only = struct.pack("!I", 100)
        messages1 = protocol.decode_messages(length_only)
        self.assertEqual(len(messages1), 0)

        # Check buffer has length prefix
        self.assertGreater(len(protocol._buffer), 0)

        # Clear buffer
        protocol.reset_buffer()
        self.assertEqual(len(protocol._buffer), 0)

    def test_protocol_max_buffer_size(self):
        """Test enforcement of maximum buffer size."""
        from server.protocol import MessageProtocol, ProtocolError

        protocol = MessageProtocol(max_buffer_size=512)

        # Try to exceed buffer size
        large_data = b"x" * 1024  # 1KB

        with self.assertRaises(ProtocolError):
            protocol.decode_messages(large_data)

    def test_protocol_concurrent_safety(self):
        """Test protocol thread safety with concurrent access."""
        import threading
        import time

        from server.protocol import MessageProtocol

        protocol = MessageProtocol()
        results = []
        errors = []

        def encode_decode_worker(worker_id):
            try:
                for i in range(10):
                    message = {
                        "version": "1.0",
                        "type": "registration",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "hostname": f"worker-{worker_id}-host-{i}",
                    }

                    encoded = protocol.encode_message(message)
                    # Small delay to test concurrency
                    time.sleep(0.001)

                    # Create new protocol instance for decoding to avoid shared buffer
                    decode_protocol = MessageProtocol()
                    decoded = decode_protocol.decode_messages(encoded)

                    if decoded and decoded[0]["hostname"] == message["hostname"]:
                        results.append(f"worker-{worker_id}-success")
            except Exception as e:
                errors.append(f"worker-{worker_id}: {e}")

        # Start multiple worker threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=encode_decode_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 50)  # 5 workers * 10 messages each


class TestMessageValidator(unittest.TestCase):
    """Test message validation functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.valid_message = {
            "version": "1.0",
            "type": "registration",
            "timestamp": "2025-06-01T15:30:00Z",
            "hostname": "valid-hostname",
        }

    def test_message_validator_class_exists(self):
        """Test that MessageValidator class exists."""
        try:
            from server.message_validator import MessageValidator

            self.assertTrue(callable(MessageValidator))
        except ImportError:
            self.fail("MessageValidator should be importable from server.message_validator")

    def test_validate_hostname_valid(self):
        """Test validation of valid hostnames."""
        from server.message_validator import MessageValidator

        validator = MessageValidator()

        valid_hostnames = [
            "test-host",
            "web-server-01",
            "api.example.com",
            "localhost",
            "host123",
            "my-awesome-server",
        ]

        for hostname in valid_hostnames:
            with self.subTest(hostname=hostname):
                is_valid, error = validator.validate_hostname(hostname)
                self.assertTrue(is_valid, f"Hostname '{hostname}' should be valid")
                self.assertIsNone(error)

    def test_validate_hostname_invalid(self):
        """Test validation of invalid hostnames."""
        from server.message_validator import MessageValidator

        validator = MessageValidator()

        invalid_hostnames = [
            "",  # Empty
            "a" * 256,  # Too long
            "-invalid",  # Starts with hyphen
            "invalid-",  # Ends with hyphen
            "inv@lid",  # Invalid character
            "inv alid",  # Space
            "inv..alid",  # Double dots
            ".invalid",  # Starts with dot
            "invalid.",  # Ends with dot
        ]

        for hostname in invalid_hostnames:
            with self.subTest(hostname=hostname):
                is_valid, error = validator.validate_hostname(hostname)
                self.assertFalse(is_valid, f"Hostname '{hostname}' should be invalid")
                self.assertIsNotNone(error)

    def test_validate_message_structure(self):
        """Test validation of message structure."""
        from server.message_validator import MessageValidator

        validator = MessageValidator()

        # Valid message
        is_valid, error = validator.validate_message_structure(self.valid_message)
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_timestamp_format(self):
        """Test timestamp format validation."""
        from server.message_validator import MessageValidator

        validator = MessageValidator()

        valid_timestamps = ["2025-06-01T15:30:00Z", "2025-12-31T23:59:59Z", "2025-01-01T00:00:00Z"]

        for timestamp in valid_timestamps:
            with self.subTest(timestamp=timestamp):
                is_valid, error = validator.validate_timestamp(timestamp)
                self.assertTrue(is_valid, f"Timestamp '{timestamp}' should be valid")
                self.assertIsNone(error)

    def test_validate_timestamp_invalid(self):
        """Test validation of invalid timestamps."""
        from server.message_validator import MessageValidator

        validator = MessageValidator()

        invalid_timestamps = [
            "2025-06-01",  # Missing time
            "15:30:00",  # Missing date
            "2025-06-01 15:30:00",  # Wrong format
            "invalid",  # Not a timestamp
            "",  # Empty
        ]

        for timestamp in invalid_timestamps:
            with self.subTest(timestamp=timestamp):
                is_valid, error = validator.validate_timestamp(timestamp)
                self.assertFalse(is_valid, f"Timestamp '{timestamp}' should be invalid")
                self.assertIsNotNone(error)

    def test_sanitize_hostname(self):
        """Test hostname sanitization."""
        from server.message_validator import MessageValidator

        validator = MessageValidator()

        test_cases = [
            ("Test-Host", "test-host"),  # Lowercase
            ("  host  ", "host"),  # Strip whitespace
            ("host..name", "host.name"),  # Remove double dots
        ]

        for input_hostname, expected in test_cases:
            with self.subTest(input=input_hostname):
                sanitized = validator.sanitize_hostname(input_hostname)
                self.assertEqual(sanitized, expected)


if __name__ == "__main__":
    unittest.main()
