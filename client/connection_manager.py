"""
Client Network Connection Management for Prism Host Client (SCRUM-5)
Handles TCP connections with retry logic, error handling, and configuration integration.
"""

import socket
import time
import logging
from typing import Optional, Dict, Any, Union
from client.config_manager import ConfigManager


class ConnectionError(Exception):
    """Custom exception for connection-related errors."""
    pass


class ConnectionManager:
    """
    Manages TCP connections to the server with retry logic and error handling.
    Integrates with ConfigManager for configuration and provides connection state management.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the ConnectionManager with configuration.
        
        Args:
            config: Configuration dictionary containing server settings
        """
        server_config = config['server']
        self._host = server_config['host']
        self._port = server_config['port']
        self._timeout = server_config['timeout']
        
        self._connection: Optional[socket.socket] = None
        self._connected = False
        self._logger = logging.getLogger(__name__)

    @classmethod
    def from_config_file(cls, config_file: str) -> 'ConnectionManager':
        """
        Create ConnectionManager from configuration file.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            Configured ConnectionManager instance
        """
        config_manager = ConfigManager()
        config = config_manager.load_config(config_file)
        return cls(config)

    def connect(self) -> socket.socket:
        """
        Establish TCP connection to the server.
        
        Returns:
            Connected socket object
            
        Raises:
            ConnectionError: If connection fails
        """
        try:
            # Create socket
            self._connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._connection.settimeout(self._timeout)
            
            # Attempt connection
            self._connection.connect((self._host, self._port))
            self._connected = True
            
            self._logger.info(f"Connected to server {self._host}:{self._port}")
            return self._connection
            
        except socket.timeout:
            self._cleanup_connection()
            raise ConnectionError(f"Connection timeout after {self._timeout} seconds")
            
        except socket.gaierror as e:
            self._cleanup_connection()
            raise ConnectionError(f"DNS resolution failed for {self._host}: {e}")
            
        except ConnectionRefusedError as e:
            self._cleanup_connection()
            raise ConnectionError(f"Connection refused by {self._host}:{self._port}: {e}")
            
        except OSError as e:
            self._cleanup_connection()
            raise ConnectionError(f"Network error connecting to {self._host}:{self._port}: {e}")
            
        except Exception as e:
            self._cleanup_connection()
            raise ConnectionError(f"Unexpected error connecting to {self._host}:{self._port}: {e}")

    def connect_with_retry(self, max_retries: int = 5) -> socket.socket:
        """
        Establish connection with exponential backoff retry logic.
        
        Args:
            max_retries: Maximum number of retry attempts
            
        Returns:
            Connected socket object
            
        Raises:
            ConnectionError: If all retry attempts fail
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                return self.connect()
                
            except ConnectionError as e:
                last_error = e
                
                if attempt < max_retries:
                    # Calculate exponential backoff delay (1s, 2s, 4s, 8s, max 60s)
                    delay = min(2 ** attempt, 60)
                    self._logger.warning(f"Connection attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    time.sleep(delay)
                else:
                    self._logger.error(f"All connection attempts failed after {max_retries + 1} tries")
                    break
        
        raise ConnectionError(f"Max retries exceeded ({max_retries}): {last_error}")

    def disconnect(self) -> None:
        """
        Disconnect from the server and cleanup resources.
        """
        if self._connection and self._connected:
            try:
                self._connection.close()
                self._logger.info(f"Disconnected from server {self._host}:{self._port}")
            except Exception as e:
                self._logger.warning(f"Error during disconnect: {e}")
            finally:
                self._connected = False
                self._connection = None

    def send_data(self, data: bytes) -> int:
        """
        Send data over the established connection.
        
        Args:
            data: Bytes to send
            
        Returns:
            Number of bytes sent
            
        Raises:
            ConnectionError: If sending fails or connection is broken
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to server")
        
        try:
            bytes_sent = self._connection.send(data)
            self._logger.debug(f"Sent {bytes_sent} bytes to server")
            return bytes_sent
            
        except socket.error as e:
            self._cleanup_connection()
            raise ConnectionError(f"Failed to send data: {e}")
        except Exception as e:
            self._cleanup_connection()
            raise ConnectionError(f"Unexpected error sending data: {e}")

    def receive_data(self, buffer_size: int = 4096) -> bytes:
        """
        Receive data from the established connection.
        
        Args:
            buffer_size: Maximum number of bytes to receive
            
        Returns:
            Received bytes
            
        Raises:
            ConnectionError: If receiving fails or connection is broken
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to server")
        
        try:
            data = self._connection.recv(buffer_size)
            if not data:
                # Empty data indicates connection closed by peer
                self._cleanup_connection()
                raise ConnectionError("Connection closed by server")
            
            self._logger.debug(f"Received {len(data)} bytes from server")
            return data
            
        except socket.timeout:
            raise ConnectionError("Receive timeout")
        except socket.error as e:
            self._cleanup_connection()
            raise ConnectionError(f"Failed to receive data: {e}")
        except Exception as e:
            self._cleanup_connection()
            raise ConnectionError(f"Unexpected error receiving data: {e}")

    def is_connected(self) -> bool:
        """
        Check if currently connected to the server.
        
        Returns:
            True if connected, False otherwise
        """
        return self._connected and self._connection is not None

    def get_connection(self) -> Optional[socket.socket]:
        """
        Get the current connection socket.
        
        Returns:
            Socket object if connected, None otherwise
        """
        return self._connection if self.is_connected() else None

    def get_server_info(self) -> Dict[str, Union[str, int]]:
        """
        Get server connection information.
        
        Returns:
            Dictionary with host, port, and timeout information
        """
        return {
            'host': self._host,
            'port': self._port,
            'timeout': self._timeout,
            'connected': self.is_connected()
        }

    def _cleanup_connection(self) -> None:
        """Clean up connection state and resources."""
        self._connected = False
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass  # Ignore errors during cleanup
            finally:
                self._connection = None

    def __enter__(self) -> 'ConnectionManager':
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit with automatic cleanup."""
        self.disconnect()

    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.disconnect()
        except Exception:
            pass  # Ignore errors during destruction