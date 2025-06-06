"""
Integration tests for Heartbeat Registration Loop (SCRUM-8)
Tests integration with all client components.
"""

import tempfile
import os
import time
from unittest.mock import patch, Mock
from client.heartbeat_manager import HeartbeatManager
from client.config_manager import ConfigManager
from client.connection_manager import ConnectionManager
from client.message_protocol import MessageProtocol, TCPSender
from client.system_info import SystemInfo


def test_heartbeat_with_config_integration():
    """Test HeartbeatManager integration with ConfigManager."""
    # Create a temporary config file
    config_content = """
heartbeat:
  interval: 30
server:
  host: heartbeat.test.com
  port: 8888
  timeout: 5
logging:
  level: DEBUG
  file: heartbeat.log
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(config_content)
        config_file = f.name

    try:
        with patch("threading.Timer") as mock_timer:
            mock_timer_instance = Mock()
            mock_timer.return_value = mock_timer_instance

            # Create HeartbeatManager from config file
            heartbeat_manager = HeartbeatManager.from_config_file(config_file)

            # Verify configuration was loaded correctly
            assert heartbeat_manager._interval == 30

            # Test start/stop functionality
            heartbeat_manager.start()
            assert heartbeat_manager.is_running() is True

            heartbeat_manager.stop()
            assert heartbeat_manager.is_running() is False

    finally:
        os.unlink(config_file)


def test_heartbeat_with_all_components_integration():
    """Test HeartbeatManager integration with all client components."""
    config = {
        "heartbeat": {"interval": 1},
        "server": {"host": "integration.test.com", "port": 8080, "timeout": 10},
        "logging": {"level": "INFO", "file": "integration.log"},
    }

    with patch("socket.socket") as mock_socket, patch("threading.Timer") as mock_timer:

        # Setup socket mock
        mock_conn = Mock()
        mock_socket.return_value = mock_conn
        mock_conn.connect.return_value = None
        mock_conn.send.return_value = 75

        # Setup timer mock
        mock_timer_instance = Mock()
        mock_timer.return_value = mock_timer_instance

        # Initialize HeartbeatManager
        heartbeat_manager = HeartbeatManager(config)

        # Start heartbeat and send one heartbeat
        heartbeat_manager.start()
        heartbeat_manager._send_heartbeat()

        # Verify full integration workflow
        mock_conn.connect.assert_called_once_with(("integration.test.com", 8080))
        mock_conn.send.assert_called_once()
        mock_conn.close.assert_called_once()

        # Verify timer was scheduled
        mock_timer.assert_called()
        mock_timer_instance.start.assert_called()

        heartbeat_manager.stop()


def test_heartbeat_retry_integration():
    """Test HeartbeatManager integration with connection retry logic."""
    config = {
        "heartbeat": {"interval": 1},
        "server": {"host": "retry.test.com", "port": 8080, "timeout": 5},
    }

    with (
        patch("socket.socket") as mock_socket,
        patch("threading.Timer") as mock_timer,
        patch("time.sleep") as mock_sleep,
    ):

        mock_conn = Mock()
        mock_socket.return_value = mock_conn

        # Simulate connection failures then success
        import socket

        mock_conn.connect.side_effect = [
            socket.error("Connection refused"),
            socket.timeout("Connection timed out"),
            None,  # Success on third attempt
        ]
        mock_conn.send.return_value = 50

        mock_timer_instance = Mock()
        mock_timer.return_value = mock_timer_instance

        heartbeat_manager = HeartbeatManager(config)
        heartbeat_manager.start()

        # Send heartbeat with retry logic
        heartbeat_manager._send_heartbeat()

        # Should succeed after retries
        assert mock_conn.connect.call_count == 3
        mock_conn.send.assert_called_once()

        # Verify exponential backoff was used
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)  # First retry delay
        mock_sleep.assert_any_call(2)  # Second retry delay


def test_heartbeat_message_protocol_integration():
    """Test HeartbeatManager integration with message protocol components."""
    config = {
        "heartbeat": {"interval": 1},
        "server": {"host": "protocol.test.com", "port": 8080, "timeout": 10},
    }

    with patch("socket.socket") as mock_socket, patch("threading.Timer"):

        mock_conn = Mock()
        mock_socket.return_value = mock_conn
        mock_conn.connect.return_value = None
        mock_conn.send.return_value = 100

        heartbeat_manager = HeartbeatManager(config)

        # Manually access components to verify integration
        protocol = heartbeat_manager._protocol
        sender = heartbeat_manager._sender
        system_info = heartbeat_manager._system_info

        # Create a test message using the same flow as heartbeat
        hostname = system_info.get_hostname()
        message = protocol.create_registration_message(hostname)
        serialized = protocol.serialize_message(message)
        framed = sender.frame_message(serialized)

        # Send heartbeat and verify message structure
        heartbeat_manager._send_heartbeat()

        # Verify message was sent
        mock_conn.send.assert_called_once()
        sent_data = mock_conn.send.call_args[0][0]

        # Verify it's a properly framed message
        assert len(sent_data) > 4  # At least length prefix + content
        assert isinstance(sent_data, bytes)


def test_heartbeat_error_recovery_integration():
    """Test HeartbeatManager error recovery with all components."""
    config = {
        "heartbeat": {"interval": 1},
        "server": {"host": "error.test.com", "port": 8080, "timeout": 10},
    }

    with patch("socket.socket") as mock_socket, patch("threading.Timer") as mock_timer:

        mock_conn = Mock()
        mock_socket.return_value = mock_conn

        # Setup various error scenarios
        error_scenarios = [
            Exception("DNS resolution failed"),
            Exception("Connection timeout"),
            Exception("Send failed"),
            None,  # Success after errors
        ]
        mock_conn.connect.side_effect = error_scenarios
        mock_conn.send.return_value = 42

        # Setup timer mocks
        mock_timer_instances = [Mock() for _ in range(10)]
        mock_timer.side_effect = mock_timer_instances

        heartbeat_manager = HeartbeatManager(config)
        heartbeat_manager.start()

        # Send multiple heartbeats with errors
        for i in range(4):
            heartbeat_manager._send_heartbeat()

        # Should continue running despite errors
        assert heartbeat_manager.is_running() is True

        # Should reschedule after each attempt
        assert mock_timer.call_count >= 4  # Initial + reschedules


def test_complete_heartbeat_workflow():
    """Test complete heartbeat workflow from start to finish."""
    # Setup configuration
    config = {
        "heartbeat": {"interval": 2},
        "server": {"host": "workflow.test.com", "port": 8080, "timeout": 10},
        "logging": {"level": "INFO", "file": "workflow.log"},
    }

    with patch("socket.socket") as mock_socket, patch("threading.Timer") as mock_timer:

        mock_conn = Mock()
        mock_socket.return_value = mock_conn
        mock_conn.connect.return_value = None
        mock_conn.send.return_value = 150

        mock_timer_instance = Mock()
        mock_timer.return_value = mock_timer_instance

        # Step 1: Initialize HeartbeatManager
        heartbeat_manager = HeartbeatManager(config)
        assert heartbeat_manager.is_running() is False

        # Step 2: Start heartbeat loop
        heartbeat_manager.start()
        assert heartbeat_manager.is_running() is True

        # Step 3: Verify timer was scheduled
        mock_timer.assert_called_with(2, heartbeat_manager._send_heartbeat)
        mock_timer_instance.start.assert_called_once()

        # Step 4: Send a heartbeat message
        heartbeat_manager._send_heartbeat()

        # Step 5: Verify complete workflow
        mock_conn.connect.assert_called_once_with(("workflow.test.com", 8080))
        mock_conn.send.assert_called_once()
        mock_conn.close.assert_called_once()

        # Step 6: Verify next heartbeat was scheduled
        assert mock_timer.call_count == 2  # Initial + reschedule

        # Step 7: Stop heartbeat
        heartbeat_manager.stop()
        assert heartbeat_manager.is_running() is False
        mock_timer_instance.cancel.assert_called_once()


def test_heartbeat_context_manager_integration():
    """Test HeartbeatManager context manager with full integration."""
    config = {
        "heartbeat": {"interval": 1},
        "server": {"host": "context.test.com", "port": 8080, "timeout": 10},
    }

    with patch("threading.Timer") as mock_timer:
        mock_timer_instance = Mock()
        mock_timer.return_value = mock_timer_instance

        # Use HeartbeatManager as context manager
        with HeartbeatManager(config) as heartbeat_manager:
            heartbeat_manager.start()
            assert heartbeat_manager.is_running() is True

            # Get status
            status = heartbeat_manager.get_status()
            assert status["running"] is True
            assert status["interval"] == 1

        # Should automatically stop when exiting context
        mock_timer_instance.cancel.assert_called_once()


if __name__ == "__main__":
    test_heartbeat_with_config_integration()
    test_heartbeat_with_all_components_integration()
    test_heartbeat_retry_integration()
    test_heartbeat_message_protocol_integration()
    test_heartbeat_error_recovery_integration()
    test_complete_heartbeat_workflow()
    test_heartbeat_context_manager_integration()
    print("All integration tests passed!")
