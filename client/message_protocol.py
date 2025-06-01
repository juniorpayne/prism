"""
JSON Message Protocol Implementation for Prism Host Client (SCRUM-7)
Handles message creation, validation, serialization, and TCP framing.
"""

import json
import struct
from datetime import datetime, timezone
from typing import Dict, Any, Union


class MessageValidationError(Exception):
    """Custom exception for message validation errors."""
    pass


class MessageProtocol:
    """
    Manages JSON message protocol for client-server communication.
    Handles message creation, validation, and serialization.
    """

    def __init__(self):
        """Initialize the MessageProtocol."""
        self._current_version = '1.0'
        self._supported_versions = {'1.0'}
        self._supported_types = {'registration'}

    def create_registration_message(self, hostname: str) -> Dict[str, Any]:
        """
        Create a registration message with hostname and timestamp.
        
        Args:
            hostname: Client hostname to register
            
        Returns:
            Dictionary containing the registration message
        """
        if not hostname or not isinstance(hostname, str):
            raise MessageValidationError("Hostname must be a non-empty string")
        
        # Create ISO 8601 timestamp with UTC timezone
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        message = {
            'version': self._current_version,
            'type': 'registration',
            'timestamp': timestamp,
            'hostname': hostname.strip()
        }
        
        return message

    def validate_message(self, message: Dict[str, Any]) -> None:
        """
        Validate message structure and content.
        
        Args:
            message: Message dictionary to validate
            
        Raises:
            MessageValidationError: If message is invalid
        """
        if not isinstance(message, dict):
            raise MessageValidationError("Message must be a dictionary")
        
        # Check required fields
        required_fields = ['version', 'type', 'timestamp', 'hostname']
        for field in required_fields:
            if field not in message:
                raise MessageValidationError(f"Missing required field: {field}")
        
        # Validate version
        version = message['version']
        if not isinstance(version, str):
            raise MessageValidationError("Version must be a string")
        if not self.is_supported_version(version):
            raise MessageValidationError(f"Unsupported version: {version}")
        
        # Validate message type
        msg_type = message['type']
        if not isinstance(msg_type, str):
            raise MessageValidationError("Message type must be a string")
        if msg_type not in self._supported_types:
            raise MessageValidationError(f"Unsupported message type: {msg_type}")
        
        # Validate timestamp format
        timestamp = message['timestamp']
        if not isinstance(timestamp, str):
            raise MessageValidationError("Timestamp must be a string")
        
        try:
            # Try to parse ISO 8601 timestamp
            if timestamp.endswith('Z'):
                datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                datetime.fromisoformat(timestamp)
        except ValueError as e:
            raise MessageValidationError(f"Invalid timestamp format: {e}")
        
        # Validate hostname
        hostname = message['hostname']
        if not isinstance(hostname, str):
            raise MessageValidationError("Hostname must be a string")
        if not hostname.strip():
            raise MessageValidationError("Hostname cannot be empty")

    def serialize_message(self, message: Dict[str, Any]) -> bytes:
        """
        Serialize message to JSON bytes.
        
        Args:
            message: Message dictionary to serialize
            
        Returns:
            JSON-encoded bytes
            
        Raises:
            MessageValidationError: If serialization fails
        """
        try:
            # Validate before serializing
            self.validate_message(message)
            
            # Serialize to JSON with consistent formatting
            json_str = json.dumps(message, separators=(',', ':'), ensure_ascii=True)
            return json_str.encode('utf-8')
            
        except (TypeError, ValueError) as e:
            raise MessageValidationError(f"JSON serialization failed: {e}")

    def get_current_version(self) -> str:
        """
        Get the current protocol version.
        
        Returns:
            Current version string
        """
        return self._current_version

    def is_supported_version(self, version: str) -> bool:
        """
        Check if a version is supported.
        
        Args:
            version: Version string to check
            
        Returns:
            True if version is supported, False otherwise
        """
        return version in self._supported_versions

    def get_supported_types(self) -> set:
        """
        Get supported message types.
        
        Returns:
            Set of supported message type strings
        """
        return self._supported_types.copy()


class TCPSender:
    """
    Handles TCP message sending with proper framing.
    Implements length-prefixed message framing for reliable delivery.
    """

    def send_message(self, connection, message_data: bytes) -> None:
        """
        Send a message over TCP connection with length framing.
        
        Args:
            connection: TCP socket connection
            message_data: Message bytes to send
            
        Raises:
            MessageValidationError: If sending fails
        """
        try:
            framed_data = self.frame_message(message_data)
            connection.send(framed_data)
            
        except Exception as e:
            raise MessageValidationError(f"Failed to send message: {e}")

    def frame_message(self, message_data: bytes) -> bytes:
        """
        Frame message with length prefix for TCP transmission.
        
        Args:
            message_data: Raw message bytes
            
        Returns:
            Framed message with 4-byte big-endian length prefix
        """
        if not isinstance(message_data, bytes):
            raise MessageValidationError("Message data must be bytes")
        
        # Create 4-byte big-endian length prefix
        length = len(message_data)
        length_prefix = struct.pack('>I', length)
        
        return length_prefix + message_data

    def unframe_message(self, framed_data: bytes) -> bytes:
        """
        Extract message from framed data.
        
        Args:
            framed_data: Framed message with length prefix
            
        Returns:
            Raw message bytes without framing
            
        Raises:
            MessageValidationError: If framing is invalid
        """
        if len(framed_data) < 4:
            raise MessageValidationError("Framed data too short for length prefix")
        
        # Extract length from first 4 bytes
        length_bytes = framed_data[:4]
        expected_length = struct.unpack('>I', length_bytes)[0]
        
        # Verify data length matches
        actual_length = len(framed_data) - 4
        if actual_length != expected_length:
            raise MessageValidationError(
                f"Message length mismatch: expected {expected_length}, got {actual_length}"
            )
        
        return framed_data[4:]