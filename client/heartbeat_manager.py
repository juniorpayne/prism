"""
Heartbeat Registration Loop for Prism Host Client (SCRUM-8)
Handles periodic heartbeat messages to the server with configurable intervals.
"""

import json
import logging
import threading
import time
from typing import Any, Dict, Optional

from client.config_manager import ConfigManager
from client.connection_manager import ConnectionError, ConnectionManager
from client.message_protocol import MessageProtocol, TCPSender
from client.system_info import SystemInfo


class HeartbeatError(Exception):
    """Custom exception for heartbeat-related errors."""

    pass


class HeartbeatManager:
    """
    Manages periodic heartbeat messages to the server.
    Integrates with all client components for registration loop functionality.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the HeartbeatManager with configuration.

        Args:
            config: Configuration dictionary containing heartbeat and server settings
        """
        # Load heartbeat configuration with default
        heartbeat_config = config.get("heartbeat", {})
        self._interval = heartbeat_config.get("interval", 60)  # Default 60 seconds

        # Initialize components
        self._config = config
        self._connection_manager = ConnectionManager(config)
        self._protocol = MessageProtocol()
        self._sender = TCPSender()
        self._system_info = SystemInfo()
        
        # Extract auth token (required)
        self.auth_token = config["server"]["auth_token"]
        
        # State management
        self._timer: Optional[threading.Timer] = None
        self._running = False
        self._lock = threading.Lock()
        self._logger = logging.getLogger(__name__)
        
        # Log auth configuration (without exposing token)
        self._logger.info("Client configured with API token authentication")

    @classmethod
    def from_config_file(cls, config_file: str) -> "HeartbeatManager":
        """
        Create HeartbeatManager from configuration file.

        Args:
            config_file: Path to configuration file

        Returns:
            Configured HeartbeatManager instance
        """
        config_manager = ConfigManager()
        config = config_manager.load_config(config_file)
        return cls(config)

    def start(self) -> None:
        """
        Start the heartbeat loop with periodic message sending.
        Thread-safe and idempotent - multiple calls are ignored.
        """
        with self._lock:
            if self._running:
                self._logger.debug("Heartbeat manager already running")
                return

            self._running = True
            self._schedule_next_heartbeat()
            self._logger.info(f"Heartbeat manager started with {self._interval}s interval")

    def stop(self) -> None:
        """
        Stop the heartbeat loop and cancel any pending timers.
        Thread-safe and idempotent - multiple calls are safe.
        """
        with self._lock:
            if not self._running:
                return

            self._running = False

            if self._timer:
                self._timer.cancel()
                self._timer = None

            self._logger.info("Heartbeat manager stopped")

    def is_running(self) -> bool:
        """
        Check if the heartbeat manager is currently running.

        Returns:
            True if running, False otherwise
        """
        with self._lock:
            return self._running

    def _schedule_next_heartbeat(self) -> None:
        """Schedule the next heartbeat message."""
        if self._running:
            self._timer = threading.Timer(self._interval, self._send_heartbeat)
            self._timer.start()

    def _get_local_ip(self) -> str:
        """Get local IP address for the client."""
        try:
            import socket
            # Create a socket and connect to a public DNS server
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "unknown"

    def _create_registration_message(self) -> Dict[str, Any]:
        """
        Create registration message with optional auth token.
        
        Returns:
            Dictionary containing the registration message
        """
        from datetime import datetime, timezone
        
        # Get system information
        hostname = self._system_info.get_hostname()
        client_ip = self._get_local_ip()
        
        message = {
            "version": "1.0",
            "type": "registration",
            "hostname": hostname,
            "client_ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "auth_token": self.auth_token
        }
            
        return message
    
    def _create_heartbeat_message(self) -> Dict[str, Any]:
        """
        Create heartbeat message with auth token.
        
        Returns:
            Dictionary containing the heartbeat message
        """
        from datetime import datetime, timezone
        
        # Get system information
        hostname = self._system_info.get_hostname()
        client_ip = self._get_local_ip()
        
        message = {
            "version": "1.0",
            "type": "registration",
            "hostname": hostname,
            "client_ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "auth_token": self.auth_token
        }
            
        return message

    def _send_heartbeat(self) -> None:
        """
        Send a heartbeat registration message to the server.
        Handles errors gracefully and reschedules the next heartbeat.
        """
        try:
            # Create heartbeat message with auth token support
            message = self._create_heartbeat_message()

            # Serialize and frame the message
            serialized = json.dumps(message).encode("utf-8")
            framed = self._sender.frame_message(serialized)

            # Connect and send
            connection = self._connection_manager.connect_with_retry(max_retries=3)
            bytes_sent = self._connection_manager.send_data(framed)

            # Disconnect after sending
            self._connection_manager.disconnect()

            self._logger.info(f"Heartbeat sent successfully: {bytes_sent} bytes to server")

        except Exception as e:
            self._logger.error(f"Heartbeat failed: {e}")
            # Continue running despite errors - this is a key requirement

        finally:
            # Always reschedule the next heartbeat if still running
            with self._lock:
                if self._running:
                    self._schedule_next_heartbeat()

    def get_status(self) -> Dict[str, Any]:
        """
        Get heartbeat manager status information.

        Returns:
            Dictionary with status information
        """
        with self._lock:
            return {
                "running": self._running,
                "interval": self._interval,
                "next_heartbeat": f"in {self._interval}s" if self._running else "stopped",
            }

    def __enter__(self) -> "HeartbeatManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit with automatic cleanup."""
        self.stop()

    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.stop()
        except Exception:
            pass  # Ignore errors during destruction
