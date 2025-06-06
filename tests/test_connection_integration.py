"""
Integration test for Client Network Connection Management (SCRUM-5)
Tests integration with ConfigManager and MessageProtocol components.
"""

import tempfile
import os
from unittest.mock import patch, Mock
from client.connection_manager import ConnectionManager, ConnectionError
from client.config_manager import ConfigManager
from client.message_protocol import MessageProtocol, TCPSender
from client.system_info import SystemInfo


def test_connection_with_config_integration():
    """Test ConnectionManager integration with ConfigManager."""
    # Create a temporary config file
    config_content = """
server:
  host: integration.test.com
  port: 9999
  timeout: 5
heartbeat:
  interval: 30
logging:
  level: DEBUG
  file: integration.log
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(config_content)
        config_file = f.name

    try:
        with patch("socket.socket") as mock_socket:
            mock_conn = Mock()
            mock_socket.return_value = mock_conn
            mock_conn.connect.return_value = None

            # Create ConnectionManager from config file
            conn_manager = ConnectionManager.from_config_file(config_file)

            # Verify configuration was loaded correctly
            server_info = conn_manager.get_server_info()
            assert server_info["host"] == "integration.test.com"
            assert server_info["port"] == 9999
            assert server_info["timeout"] == 5

            # Test connection
            connection = conn_manager.connect()
            assert conn_manager.is_connected() is True
            mock_conn.connect.assert_called_once_with(("integration.test.com", 9999))

    finally:
        os.unlink(config_file)


def test_connection_with_message_protocol_integration():
    """Test ConnectionManager integration with MessageProtocol and TCPSender."""
    config = {"server": {"host": "localhost", "port": 8080, "timeout": 10}}

    with patch("socket.socket") as mock_socket:
        mock_conn = Mock()
        mock_socket.return_value = mock_conn
        mock_conn.connect.return_value = None
        mock_conn.send.return_value = 42  # Bytes sent

        # Initialize components
        conn_manager = ConnectionManager(config)
        protocol = MessageProtocol()
        sender = TCPSender()
        system_info = SystemInfo()

        # Connect to server
        connection = conn_manager.connect()
        assert conn_manager.is_connected() is True

        # Create and send a message
        hostname = system_info.get_hostname()
        message = protocol.create_registration_message(hostname)
        serialized = protocol.serialize_message(message)
        framed = sender.frame_message(serialized)

        # Send through ConnectionManager
        bytes_sent = conn_manager.send_data(framed)
        assert bytes_sent == 42

        # Verify the complete integration flow
        mock_conn.send.assert_called_once_with(framed)

        # Verify message structure
        import json

        parsed_message = json.loads(serialized.decode("utf-8"))
        assert parsed_message["hostname"] == hostname
        assert parsed_message["version"] == "1.0"
        assert parsed_message["type"] == "registration"


def test_connection_retry_integration():
    """Test ConnectionManager retry logic with realistic scenarios."""
    config = {"server": {"host": "unreliable.server.com", "port": 8080, "timeout": 2}}

    with patch("socket.socket") as mock_socket, patch("time.sleep") as mock_sleep:

        mock_conn = Mock()
        mock_socket.return_value = mock_conn

        # Simulate intermittent connection failures
        import socket

        mock_conn.connect.side_effect = [
            socket.error("Connection refused"),
            socket.timeout("Connection timed out"),
            None,  # Success on third attempt
        ]

        conn_manager = ConnectionManager(config)
        connection = conn_manager.connect_with_retry(max_retries=3)

        # Should succeed after retries
        assert conn_manager.is_connected() is True
        assert mock_conn.connect.call_count == 3

        # Verify exponential backoff was used
        assert mock_sleep.call_count == 2  # Two retries
        mock_sleep.assert_any_call(1)  # First retry delay
        mock_sleep.assert_any_call(2)  # Second retry delay


def test_complete_client_workflow():
    """Test a complete client workflow: config -> connect -> send message."""
    # Setup configuration
    config = {
        "server": {"host": "workflow.test.com", "port": 8080, "timeout": 10},
        "heartbeat": {"interval": 60},
        "logging": {"level": "INFO", "file": "client.log"},
    }

    with patch("socket.socket") as mock_socket:
        mock_conn = Mock()
        mock_socket.return_value = mock_conn
        mock_conn.connect.return_value = None
        mock_conn.send.return_value = 100

        # Step 1: Initialize all components
        conn_manager = ConnectionManager(config)
        protocol = MessageProtocol()
        sender = TCPSender()
        system_info = SystemInfo()

        # Step 2: Connect to server
        with conn_manager as cm:
            connection = cm.connect()
            assert cm.is_connected() is True

            # Step 3: Prepare and send registration message
            hostname = system_info.get_hostname()
            message = protocol.create_registration_message(hostname)
            serialized = protocol.serialize_message(message)
            framed = sender.frame_message(serialized)

            # Step 4: Send message
            bytes_sent = cm.send_data(framed)
            assert bytes_sent == 100

            # Verify the complete workflow
            mock_conn.connect.assert_called_once_with(("workflow.test.com", 8080))
            mock_conn.send.assert_called_once_with(framed)

        # Context manager should have disconnected
        mock_conn.close.assert_called_once()


if __name__ == "__main__":
    test_connection_with_config_integration()
    test_connection_with_message_protocol_integration()
    test_connection_retry_integration()
    test_complete_client_workflow()
    print("All integration tests passed!")
