#!/usr/bin/env python3
"""
Message Protocol Handling for Prism DNS Server (SCRUM-14)
Handles length-prefixed JSON message framing and parsing.
"""

import json
import logging
import struct
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ProtocolError(Exception):
    """Exception raised for protocol-related errors."""

    pass


class MessageProtocol:
    """
    Length-prefixed JSON message protocol handler.

    Message format:
    [4 bytes: message length (big-endian uint32)][JSON message data]
    """

    def __init__(self, max_message_size: int = 65536, max_buffer_size: int = 1048576):
        """
        Initialize message protocol handler.

        Args:
            max_message_size: Maximum size for individual messages (64KB default)
            max_buffer_size: Maximum size for internal buffer (1MB default)
        """
        self.max_message_size = max_message_size
        self.max_buffer_size = max_buffer_size
        self._buffer = bytearray()

        logger.debug(
            f"MessageProtocol initialized with max_message_size={max_message_size}, "
            f"max_buffer_size={max_buffer_size}"
        )

    def encode_message(self, message: Dict[str, Any]) -> bytes:
        """
        Encode a message with length prefix.

        Args:
            message: Dictionary to encode as JSON

        Returns:
            Encoded message with length prefix

        Raises:
            ProtocolError: If message is too large or encoding fails
        """
        try:
            # Convert message to JSON
            json_data = json.dumps(message, ensure_ascii=True, separators=(",", ":"))
            json_bytes = json_data.encode("utf-8")

            # Check message size
            if len(json_bytes) > self.max_message_size:
                raise ProtocolError(
                    f"Message too large: {len(json_bytes)} > {self.max_message_size}"
                )

            # Create length prefix (4 bytes, big-endian)
            length_prefix = struct.pack("!I", len(json_bytes))

            # Combine prefix and data
            encoded_message = length_prefix + json_bytes

            logger.debug(f"Encoded message of {len(json_bytes)} bytes")
            return encoded_message

        except json.JSONEncoder as e:
            raise ProtocolError(f"JSON encoding failed: {e}")
        except Exception as e:
            raise ProtocolError(f"Message encoding failed: {e}")

    def decode_messages(self, data: bytes) -> List[Dict[str, Any]]:
        """
        Decode one or more messages from byte data.

        Args:
            data: Raw byte data to decode

        Returns:
            List of decoded message dictionaries

        Raises:
            ProtocolError: If decoding fails or limits exceeded
        """
        # Add new data to buffer
        self._buffer.extend(data)

        # Check buffer size limit
        if len(self._buffer) > self.max_buffer_size:
            raise ProtocolError(f"Buffer overflow: {len(self._buffer)} > {self.max_buffer_size}")

        messages = []

        while len(self._buffer) >= 4:  # Need at least 4 bytes for length prefix
            # Read length prefix
            length = struct.unpack("!I", self._buffer[:4])[0]

            # Check message size limit
            if length > self.max_message_size:
                raise ProtocolError(f"Message too large: {length} > {self.max_message_size}")

            # Check if we have complete message
            total_length = 4 + length
            if len(self._buffer) < total_length:
                break  # Wait for more data

            # Extract message data
            message_data = self._buffer[4:total_length]

            try:
                # Decode JSON
                json_str = message_data.decode("utf-8")
                message = json.loads(json_str)
                messages.append(message)

                logger.debug(
                    f"Decoded message: {message.get('type', 'unknown')} from {message.get('hostname', 'unknown')}"
                )

            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                raise ProtocolError(f"Message decoding failed: {e}")

            # Remove processed message from buffer
            self._buffer = self._buffer[total_length:]

        return messages

    def reset_buffer(self) -> None:
        """Reset internal buffer (useful for connection cleanup)."""
        self._buffer.clear()
        logger.debug("Protocol buffer reset")

    def get_buffer_size(self) -> int:
        """Get current buffer size in bytes."""
        return len(self._buffer)

    def create_registration_response(self, status: str, message: str) -> Dict[str, Any]:
        """
        Create a registration response message.

        Args:
            status: Response status ('success' or 'error')
            message: Response message text

        Returns:
            Response message dictionary
        """
        response = {
            "version": "1.0",
            "type": "response",
            "status": status,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.debug(f"Created response: {status} - {message}")
        return response

    def validate_registration_message(self, message: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate a registration message.

        Args:
            message: Message dictionary to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = ["version", "type", "timestamp", "hostname"]

        # Check required fields
        for field in required_fields:
            if field not in message:
                return False, f"Missing required field: {field}"

        # Check version
        if message["version"] != "1.0":
            return False, f"Unsupported version: {message['version']}"

        # Check message type
        if message["type"] != "registration":
            return False, f"Invalid message type: {message['type']}"

        # Check hostname
        hostname = message["hostname"]
        if not hostname or not isinstance(hostname, str):
            return False, "Invalid hostname: must be non-empty string"

        # Check timestamp format (basic validation)
        timestamp = message["timestamp"]
        if not timestamp or not isinstance(timestamp, str):
            return False, "Invalid timestamp: must be ISO format string"

        try:
            # Try to parse timestamp
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return False, "Invalid timestamp format: must be ISO 8601"

        return True, None

    def get_protocol_stats(self) -> Dict[str, Any]:
        """
        Get protocol statistics.

        Returns:
            Dictionary with protocol statistics
        """
        return {
            "buffer_size": len(self._buffer),
            "max_message_size": self.max_message_size,
            "max_buffer_size": self.max_buffer_size,
            "buffer_utilization": len(self._buffer) / self.max_buffer_size,
        }


class ProtocolConfig:
    """Configuration for message protocol."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize protocol configuration.

        Args:
            config: Configuration dictionary
        """
        protocol_config = config.get("protocol", {})

        self.max_message_size = protocol_config.get("max_message_size", 65536)  # 64KB
        self.max_buffer_size = protocol_config.get("max_buffer_size", 1048576)  # 1MB
        self.encoding = protocol_config.get("encoding", "utf-8")
        self.json_ensure_ascii = protocol_config.get("json_ensure_ascii", True)

        # Validation
        if self.max_message_size <= 0:
            raise ValueError("max_message_size must be positive")

        if self.max_buffer_size <= 0:
            raise ValueError("max_buffer_size must be positive")

        if self.max_buffer_size < self.max_message_size:
            raise ValueError("max_buffer_size must be >= max_message_size")

        logger.info(
            f"Protocol configured: max_message_size={self.max_message_size}, "
            f"max_buffer_size={self.max_buffer_size}"
        )


def create_protocol(config: Dict[str, Any]) -> MessageProtocol:
    """
    Create a message protocol instance from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Configured MessageProtocol instance
    """
    protocol_config = ProtocolConfig(config)

    return MessageProtocol(
        max_message_size=protocol_config.max_message_size,
        max_buffer_size=protocol_config.max_buffer_size,
    )
