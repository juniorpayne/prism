"""
Tests for Client Network Connection Management (SCRUM-5)
Following TDD approach as specified in the user story.
"""

import pytest
import socket
import time
from unittest.mock import Mock, patch, MagicMock, call
from client.connection_manager import ConnectionManager, ConnectionError
from client.config_manager import ConfigManager


class TestConnectionManager:
    """Test suite for ConnectionManager following SCRUM-5 requirements."""

    def test_successful_connection(self):
        """Test successful TCP connection establishment."""
        config = {
            'server': {
                'host': 'localhost',
                'port': 8080,
                'timeout': 10
            }
        }
        
        with patch('socket.socket') as mock_socket:
            mock_conn = Mock()
            mock_socket.return_value = mock_conn
            mock_conn.connect.return_value = None
            
            conn_manager = ConnectionManager(config)
            connection = conn_manager.connect()
            
            assert connection is not None
            assert conn_manager.is_connected() is True
            mock_conn.connect.assert_called_once_with(('localhost', 8080))
            mock_conn.settimeout.assert_called_with(10)

    def test_connection_timeout(self):
        """Test connection timeout handling."""
        config = {
            'server': {
                'host': 'unreachable.host',
                'port': 8080,
                'timeout': 5
            }
        }
        
        with patch('socket.socket') as mock_socket:
            mock_conn = Mock()
            mock_socket.return_value = mock_conn
            mock_conn.connect.side_effect = socket.timeout("Connection timed out")
            
            conn_manager = ConnectionManager(config)
            
            with pytest.raises(ConnectionError) as exc_info:
                conn_manager.connect()
            
            assert "Connection timeout" in str(exc_info.value)
            assert conn_manager.is_connected() is False

    def test_retry_logic_exponential_backoff(self):
        """Test retry logic with exponential backoff."""
        config = {
            'server': {
                'host': 'localhost', 
                'port': 8080,
                'timeout': 5
            }
        }
        
        with patch('socket.socket') as mock_socket, \
             patch('time.sleep') as mock_sleep:
            
            mock_conn = Mock()
            mock_socket.return_value = mock_conn
            
            # Fail first 3 attempts, succeed on 4th
            mock_conn.connect.side_effect = [
                socket.error("Connection refused"),
                socket.error("Connection refused"), 
                socket.error("Connection refused"),
                None  # Success
            ]
            
            conn_manager = ConnectionManager(config)
            connection = conn_manager.connect_with_retry()
            
            assert connection is not None
            assert conn_manager.is_connected() is True
            
            # Verify exponential backoff: 1s, 2s, 4s
            expected_calls = [call(1), call(2), call(4)]
            mock_sleep.assert_has_calls(expected_calls)
            assert mock_conn.connect.call_count == 4

    def test_max_retry_limit(self):
        """Test maximum retry limit is respected."""
        config = {
            'server': {
                'host': 'localhost',
                'port': 8080, 
                'timeout': 5
            }
        }
        
        with patch('socket.socket') as mock_socket, \
             patch('time.sleep') as mock_sleep:
            
            mock_conn = Mock()
            mock_socket.return_value = mock_conn
            mock_conn.connect.side_effect = socket.error("Connection refused")
            
            conn_manager = ConnectionManager(config)
            
            with pytest.raises(ConnectionError) as exc_info:
                conn_manager.connect_with_retry(max_retries=3)
            
            assert "Max retries exceeded" in str(exc_info.value)
            assert mock_conn.connect.call_count == 4  # Initial + 3 retries
            assert conn_manager.is_connected() is False

    def test_configuration_loading(self):
        """Test configuration loading from ConfigManager."""
        mock_config = {
            'server': {
                'host': 'test.example.com',
                'port': 9090,
                'timeout': 15
            }
        }
        
        with patch('client.connection_manager.ConfigManager') as mock_config_manager:
            mock_manager = Mock()
            mock_config_manager.return_value = mock_manager
            mock_manager.load_config.return_value = mock_config
            mock_manager.get_server_config.return_value = mock_config['server']
            
            conn_manager = ConnectionManager.from_config_file('test.yaml')
            
            assert conn_manager._host == 'test.example.com'
            assert conn_manager._port == 9090
            assert conn_manager._timeout == 15
            mock_manager.load_config.assert_called_once_with('test.yaml')

    def test_connection_error_handling(self):
        """Test various connection error scenarios."""
        config = {
            'server': {
                'host': 'localhost',
                'port': 8080,
                'timeout': 5
            }
        }
        
        error_scenarios = [
            (socket.gaierror("Name resolution failed"), "dns resolution failed"),
            (ConnectionRefusedError("Connection refused"), "connection refused"),
            (OSError("Network unreachable"), "network error"),
        ]
        
        for socket_error, expected_message in error_scenarios:
            with patch('socket.socket') as mock_socket:
                mock_conn = Mock()
                mock_socket.return_value = mock_conn
                mock_conn.connect.side_effect = socket_error
                
                conn_manager = ConnectionManager(config)
                
                with pytest.raises(ConnectionError) as exc_info:
                    conn_manager.connect()
                
                assert expected_message in str(exc_info.value).lower()

    def test_server_disconnection_detection(self):
        """Test detection and handling of server disconnections."""
        config = {
            'server': {
                'host': 'localhost',
                'port': 8080,
                'timeout': 5
            }
        }
        
        with patch('socket.socket') as mock_socket:
            mock_conn = Mock()
            mock_socket.return_value = mock_conn
            mock_conn.connect.return_value = None
            
            conn_manager = ConnectionManager(config)
            connection = conn_manager.connect()
            
            assert conn_manager.is_connected() is True
            
            # Simulate disconnection
            mock_conn.send.side_effect = socket.error("Connection broken")
            
            # Test data sending to detect disconnection
            with pytest.raises(ConnectionError):
                conn_manager.send_data(b"test data")
            
            assert conn_manager.is_connected() is False

    def test_connection_state_management(self):
        """Test connection state tracking and management."""
        config = {
            'server': {
                'host': 'localhost',
                'port': 8080,
                'timeout': 5
            }
        }
        
        conn_manager = ConnectionManager(config)
        
        # Initially not connected
        assert conn_manager.is_connected() is False
        assert conn_manager.get_connection() is None
        
        with patch('socket.socket') as mock_socket:
            mock_conn = Mock()
            mock_socket.return_value = mock_conn
            mock_conn.connect.return_value = None
            
            # Connect
            connection = conn_manager.connect()
            assert conn_manager.is_connected() is True
            assert conn_manager.get_connection() is mock_conn
            
            # Disconnect
            conn_manager.disconnect()
            assert conn_manager.is_connected() is False
            assert conn_manager.get_connection() is None
            mock_conn.close.assert_called_once()

    def test_send_data_functionality(self):
        """Test data sending over established connection."""
        config = {
            'server': {
                'host': 'localhost',
                'port': 8080,
                'timeout': 5
            }
        }
        
        with patch('socket.socket') as mock_socket:
            mock_conn = Mock()
            mock_socket.return_value = mock_conn
            mock_conn.connect.return_value = None
            mock_conn.send.return_value = 10  # Bytes sent
            
            conn_manager = ConnectionManager(config)
            conn_manager.connect()
            
            test_data = b"test message"
            bytes_sent = conn_manager.send_data(test_data)
            
            assert bytes_sent == 10
            mock_conn.send.assert_called_once_with(test_data)

    def test_connection_context_manager(self):
        """Test ConnectionManager as context manager for automatic cleanup."""
        config = {
            'server': {
                'host': 'localhost',
                'port': 8080,
                'timeout': 5
            }
        }
        
        with patch('socket.socket') as mock_socket:
            mock_conn = Mock()
            mock_socket.return_value = mock_conn
            mock_conn.connect.return_value = None
            
            with ConnectionManager(config) as conn_manager:
                connection = conn_manager.connect()
                assert conn_manager.is_connected() is True
            
            # Should automatically disconnect when exiting context
            mock_conn.close.assert_called_once()
            assert conn_manager.is_connected() is False