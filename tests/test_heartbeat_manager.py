"""
Tests for Heartbeat Registration Loop (SCRUM-8)
Following TDD approach as specified in the user story.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock, call
from client.heartbeat_manager import HeartbeatManager, HeartbeatError


class TestHeartbeatManager:
    """Test suite for HeartbeatManager following SCRUM-8 requirements."""

    def test_heartbeat_timer_creation(self):
        """Test heartbeat timer is created with correct interval."""
        config = {
            "heartbeat": {"interval": 30},
            "server": {"host": "localhost", "port": 8080, "timeout": 10},
        }

        with patch("threading.Timer") as mock_timer:
            heartbeat_manager = HeartbeatManager(config)

            # Timer should not be created until start() is called
            mock_timer.assert_not_called()

            heartbeat_manager.start()

            # Timer should be created with correct interval
            mock_timer.assert_called_with(30, heartbeat_manager._send_heartbeat)
            assert heartbeat_manager.is_running() is True

    def test_heartbeat_interval_configuration(self):
        """Test heartbeat interval can be configured from config file."""
        test_cases = [
            ({"heartbeat": {"interval": 45}}, 45),
            ({"heartbeat": {"interval": 120}}, 120),
            ({}, 60),  # Default value
        ]

        for config_heartbeat, expected_interval in test_cases:
            config = {
                **config_heartbeat,
                "server": {"host": "localhost", "port": 8080, "timeout": 10},
            }

            heartbeat_manager = HeartbeatManager(config)
            assert heartbeat_manager._interval == expected_interval

    def test_periodic_heartbeat_sending(self):
        """Test periodic heartbeat messages are sent at configured intervals."""
        config = {
            "heartbeat": {"interval": 1},  # 1 second for testing
            "server": {"host": "localhost", "port": 8080, "timeout": 10},
        }

        with (
            patch("client.heartbeat_manager.ConnectionManager") as mock_conn_manager,
            patch("client.heartbeat_manager.MessageProtocol") as mock_protocol,
            patch("client.heartbeat_manager.TCPSender") as mock_sender,
            patch("client.heartbeat_manager.SystemInfo") as mock_system_info,
            patch("threading.Timer") as mock_timer,
        ):

            # Setup mocks
            mock_conn_instance = Mock()
            mock_conn_manager.return_value = mock_conn_instance
            mock_conn_instance.connect_with_retry.return_value = Mock()
            mock_conn_instance.send_data.return_value = 50

            mock_protocol_instance = Mock()
            mock_protocol.return_value = mock_protocol_instance
            mock_protocol_instance.create_registration_message.return_value = {"test": "message"}
            mock_protocol_instance.serialize_message.return_value = b"serialized"

            mock_sender_instance = Mock()
            mock_sender.return_value = mock_sender_instance
            mock_sender_instance.frame_message.return_value = b"framed_message"

            mock_system_info_instance = Mock()
            mock_system_info.return_value = mock_system_info_instance
            mock_system_info_instance.get_hostname.return_value = "test-host"

            # Mock timer behavior
            mock_timer_instance = Mock()
            mock_timer.return_value = mock_timer_instance

            heartbeat_manager = HeartbeatManager(config)
            heartbeat_manager.start()

            # Simulate timer callback execution
            heartbeat_manager._send_heartbeat()

            # Verify heartbeat components were called
            mock_system_info_instance.get_hostname.assert_called_once()
            mock_protocol_instance.create_registration_message.assert_called_once_with("test-host")
            mock_protocol_instance.serialize_message.assert_called_once()
            mock_sender_instance.frame_message.assert_called_once()
            mock_conn_instance.connect_with_retry.assert_called_once()
            mock_conn_instance.send_data.assert_called_once_with(b"framed_message")

    def test_heartbeat_error_handling(self):
        """Test heartbeat continues running even after individual send failures."""
        config = {
            "heartbeat": {"interval": 1},
            "server": {"host": "localhost", "port": 8080, "timeout": 10},
        }

        with (
            patch("client.heartbeat_manager.ConnectionManager") as mock_conn_manager,
            patch("client.heartbeat_manager.MessageProtocol"),
            patch("client.heartbeat_manager.TCPSender"),
            patch("client.heartbeat_manager.SystemInfo"),
            patch("threading.Timer") as mock_timer,
        ):

            # Setup connection to fail
            mock_conn_instance = Mock()
            mock_conn_manager.return_value = mock_conn_instance
            mock_conn_instance.connect_with_retry.side_effect = Exception("Connection failed")

            mock_timer_instance = Mock()
            mock_timer.return_value = mock_timer_instance

            heartbeat_manager = HeartbeatManager(config)
            heartbeat_manager.start()

            # Send heartbeat should not raise exception
            heartbeat_manager._send_heartbeat()

            # Heartbeat manager should still be running
            assert heartbeat_manager.is_running() is True

            # Timer should be rescheduled despite the error
            mock_timer_instance.start.assert_called()

    def test_graceful_shutdown(self):
        """Test heartbeat manager can be gracefully stopped."""
        config = {
            "heartbeat": {"interval": 60},
            "server": {"host": "localhost", "port": 8080, "timeout": 10},
        }

        with patch("threading.Timer") as mock_timer:
            mock_timer_instance = Mock()
            mock_timer.return_value = mock_timer_instance

            heartbeat_manager = HeartbeatManager(config)
            heartbeat_manager.start()

            assert heartbeat_manager.is_running() is True

            heartbeat_manager.stop()

            assert heartbeat_manager.is_running() is False
            mock_timer_instance.cancel.assert_called_once()

    def test_heartbeat_logging(self):
        """Test heartbeat success and failure are properly logged."""
        config = {
            "heartbeat": {"interval": 1},
            "server": {"host": "localhost", "port": 8080, "timeout": 10},
        }

        with (
            patch("client.heartbeat_manager.ConnectionManager") as mock_conn_manager,
            patch("client.heartbeat_manager.MessageProtocol"),
            patch("client.heartbeat_manager.TCPSender"),
            patch("client.heartbeat_manager.SystemInfo"),
            patch("threading.Timer"),
            patch("client.heartbeat_manager.logging.getLogger") as mock_logger,
        ):

            mock_log = Mock()
            mock_logger.return_value = mock_log

            # Test successful heartbeat logging
            mock_conn_instance = Mock()
            mock_conn_manager.return_value = mock_conn_instance
            mock_conn_instance.connect_with_retry.return_value = Mock()
            mock_conn_instance.send_data.return_value = 50

            heartbeat_manager = HeartbeatManager(config)
            heartbeat_manager._send_heartbeat()

            mock_log.info.assert_called()

            # Test failed heartbeat logging
            mock_conn_instance.connect_with_retry.side_effect = Exception("Connection failed")

            heartbeat_manager._send_heartbeat()

            mock_log.error.assert_called()

    def test_heartbeat_loop_continues_after_error(self):
        """Test heartbeat loop reschedules itself after errors."""
        config = {
            "heartbeat": {"interval": 1},
            "server": {"host": "localhost", "port": 8080, "timeout": 10},
        }

        with (
            patch("client.heartbeat_manager.ConnectionManager") as mock_conn_manager,
            patch("client.heartbeat_manager.MessageProtocol"),
            patch("client.heartbeat_manager.TCPSender"),
            patch("client.heartbeat_manager.SystemInfo"),
            patch("threading.Timer") as mock_timer,
        ):

            # Setup to fail on first call, succeed on second
            mock_conn_instance = Mock()
            mock_conn_manager.return_value = mock_conn_instance
            mock_conn_instance.connect_with_retry.side_effect = [
                Exception("First failure"),
                Mock(),  # Success on second call
            ]
            mock_conn_instance.send_data.return_value = 50

            # Create enough mock timer instances
            mock_timer_instances = [Mock() for _ in range(5)]
            mock_timer.side_effect = mock_timer_instances

            heartbeat_manager = HeartbeatManager(config)
            heartbeat_manager.start()

            # First heartbeat fails, should reschedule
            heartbeat_manager._send_heartbeat()
            assert mock_timer.call_count == 2  # Initial + reschedule after error

            # Second heartbeat succeeds, should reschedule
            heartbeat_manager._send_heartbeat()
            assert mock_timer.call_count == 3  # Initial + 2 reschedules

    def test_heartbeat_thread_safety(self):
        """Test heartbeat manager is thread-safe for start/stop operations."""
        config = {
            "heartbeat": {"interval": 1},
            "server": {"host": "localhost", "port": 8080, "timeout": 10},
        }

        with patch("threading.Timer") as mock_timer:
            mock_timer_instance = Mock()
            mock_timer.return_value = mock_timer_instance

            heartbeat_manager = HeartbeatManager(config)

            # Test multiple start calls don't create multiple timers
            heartbeat_manager.start()
            heartbeat_manager.start()  # Should be ignored

            assert mock_timer.call_count == 1
            assert heartbeat_manager.is_running() is True

            # Test stop is idempotent
            heartbeat_manager.stop()
            heartbeat_manager.stop()  # Should not error

            assert heartbeat_manager.is_running() is False

    def test_heartbeat_context_manager(self):
        """Test HeartbeatManager as context manager for automatic cleanup."""
        config = {
            "heartbeat": {"interval": 60},
            "server": {"host": "localhost", "port": 8080, "timeout": 10},
        }

        with patch("threading.Timer") as mock_timer:
            mock_timer_instance = Mock()
            mock_timer.return_value = mock_timer_instance

            with HeartbeatManager(config) as heartbeat_manager:
                heartbeat_manager.start()
                assert heartbeat_manager.is_running() is True

            # Should automatically stop when exiting context
            mock_timer_instance.cancel.assert_called_once()

    def test_heartbeat_from_config_file(self):
        """Test HeartbeatManager creation from configuration file."""
        mock_config = {
            "heartbeat": {"interval": 45},
            "server": {"host": "config.test.com", "port": 9090, "timeout": 15},
            "logging": {"level": "DEBUG", "file": "test.log"},
        }

        with patch("client.heartbeat_manager.ConfigManager") as mock_config_manager:
            mock_manager = Mock()
            mock_config_manager.return_value = mock_manager
            mock_manager.load_config.return_value = mock_config

            heartbeat_manager = HeartbeatManager.from_config_file("test.yaml")

            assert heartbeat_manager._interval == 45
            mock_manager.load_config.assert_called_once_with("test.yaml")


if __name__ == "__main__":
    import subprocess

    result = subprocess.run(
        ["python", "-m", "pytest", __file__, "-v"], capture_output=True, text=True
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
