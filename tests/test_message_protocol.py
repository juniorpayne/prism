"""
Tests for JSON Message Protocol Implementation (SCRUM-7)
Following TDD approach as specified in the user story.
"""

import pytest
import json
import struct
from datetime import datetime
from unittest.mock import MagicMock, patch
from client.message_protocol import MessageProtocol, MessageValidationError, TCPSender


class TestMessageProtocol:
    """Test suite for MessageProtocol following SCRUM-7 requirements."""

    def test_create_registration_message(self):
        """Test creation of valid JSON registration message."""
        protocol = MessageProtocol()
        hostname = "test-host"

        message = protocol.create_registration_message(hostname)

        assert isinstance(message, dict)
        assert message["version"] == "1.0"
        assert message["type"] == "registration"
        assert message["hostname"] == hostname
        assert "timestamp" in message

        # Verify timestamp format (ISO 8601)
        timestamp = message["timestamp"]
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_message_validation_success(self):
        """Test successful message validation."""
        protocol = MessageProtocol()

        valid_message = {
            "version": "1.0",
            "type": "registration",
            "timestamp": "2025-01-06T12:00:00Z",
            "hostname": "valid-host",
        }

        # Should not raise any exception
        protocol.validate_message(valid_message)

    def test_message_validation_failure(self):
        """Test message validation with invalid messages."""
        protocol = MessageProtocol()

        invalid_messages = [
            {},  # Empty message
            {"version": "1.0"},  # Missing required fields
            {
                "version": "2.0",
                "type": "registration",
                "timestamp": "2025-01-06T12:00:00Z",
                "hostname": "test",
            },  # Invalid version
            {
                "version": "1.0",
                "type": "invalid",
                "timestamp": "2025-01-06T12:00:00Z",
                "hostname": "test",
            },  # Invalid type
            {
                "version": "1.0",
                "type": "registration",
                "timestamp": "invalid-timestamp",
                "hostname": "test",
            },  # Invalid timestamp
            {
                "version": "1.0",
                "type": "registration",
                "timestamp": "2025-01-06T12:00:00Z",
                "hostname": "",
            },  # Empty hostname
            {
                "version": "1.0",
                "type": "registration",
                "timestamp": "2025-01-06T12:00:00Z",
                "hostname": None,
            },  # None hostname
        ]

        for invalid_message in invalid_messages:
            with pytest.raises(MessageValidationError):
                protocol.validate_message(invalid_message)

    def test_json_serialization(self):
        """Test JSON serialization of messages."""
        protocol = MessageProtocol()

        message = {
            "version": "1.0",
            "type": "registration",
            "timestamp": "2025-01-06T12:00:00Z",
            "hostname": "test-host",
        }

        json_data = protocol.serialize_message(message)

        assert isinstance(json_data, bytes)

        # Should be valid JSON
        parsed = json.loads(json_data.decode("utf-8"))
        assert parsed == message

    def test_json_serialization_error(self):
        """Test JSON serialization error handling."""
        protocol = MessageProtocol()

        # Create message with non-serializable object
        invalid_message = {
            "version": "1.0",
            "type": "registration",
            "timestamp": "2025-01-06T12:00:00Z",
            "hostname": "test-host",
            "invalid": object(),  # Non-serializable object
        }

        with pytest.raises(MessageValidationError):
            protocol.serialize_message(invalid_message)

    def test_tcp_message_sending(self):
        """Test TCP message sending functionality."""
        mock_connection = MagicMock()
        sender = TCPSender()

        message_data = b'{"version": "1.0", "type": "registration"}'

        sender.send_message(mock_connection, message_data)

        # Verify connection.send was called
        mock_connection.send.assert_called()

        # Get the data that was sent
        sent_data = mock_connection.send.call_args[0][0]

        # Should start with length prefix (4 bytes, big-endian)
        expected_length = len(message_data)
        expected_prefix = struct.pack(">I", expected_length)

        assert sent_data.startswith(expected_prefix)
        assert sent_data[4:] == message_data

    def test_message_framing(self):
        """Test message framing with length prefix."""
        sender = TCPSender()

        test_message = b'{"test": "message"}'
        framed_data = sender.frame_message(test_message)

        # Should be 4 bytes length + message
        expected_length = len(test_message)
        assert len(framed_data) == 4 + expected_length

        # First 4 bytes should be length in big-endian format
        length_bytes = framed_data[:4]
        unpacked_length = struct.unpack(">I", length_bytes)[0]
        assert unpacked_length == expected_length

        # Rest should be the message
        assert framed_data[4:] == test_message

    def test_message_versioning(self):
        """Test message versioning system."""
        protocol = MessageProtocol()

        # Test current version
        assert protocol.get_current_version() == "1.0"

        # Test version validation
        assert protocol.is_supported_version("1.0") is True
        assert protocol.is_supported_version("2.0") is False
        assert protocol.is_supported_version("0.9") is False

        # Test version compatibility
        message_v1 = {
            "version": "1.0",
            "type": "registration",
            "timestamp": "2025-01-06T12:00:00Z",
            "hostname": "test",
        }

        protocol.validate_message(message_v1)  # Should not raise

    def test_complete_message_workflow(self):
        """Test the complete message creation, validation, and serialization workflow."""
        protocol = MessageProtocol()
        hostname = "integration-test-host"

        # Create message
        message = protocol.create_registration_message(hostname)

        # Validate message
        protocol.validate_message(message)

        # Serialize message
        serialized = protocol.serialize_message(message)

        # Verify serialized data
        assert isinstance(serialized, bytes)
        assert len(serialized) > 0

        # Should be deserializable
        deserialized = json.loads(serialized.decode("utf-8"))
        assert deserialized["hostname"] == hostname
        assert deserialized["version"] == "1.0"
        assert deserialized["type"] == "registration"
