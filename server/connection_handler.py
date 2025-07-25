#!/usr/bin/env python3
"""
Connection Handler for Prism DNS Server (SCRUM-14)
Handles individual client connections and message processing.
"""

import asyncio
import logging
import time
from asyncio import StreamReader, StreamWriter
from typing import Any, Dict, List, Optional, Tuple

from .database.connection import DatabaseManager
from .database.operations import HostOperations
from .dns_manager import PowerDNSClient, create_dns_client
from .message_validator import MessageValidator, SecurityValidator
from .protocol import MessageProtocol, ProtocolError
from .registration_processor import RegistrationProcessor, create_registration_processor
from .server_stats import ServerStats

logger = logging.getLogger(__name__)


class ConnectionError(Exception):
    """Exception raised for connection-related errors."""

    pass


class ConnectionHandler:
    """
    Handles individual client connections.

    Manages the lifecycle of a single client connection including:
    - Message reading and parsing
    - Message validation and processing
    - Response generation and sending
    - Error handling and cleanup
    """

    def __init__(
        self,
        reader: StreamReader,
        writer: StreamWriter,
        config: Dict[str, Any],
        db_manager: Optional[DatabaseManager] = None,
        stats: Optional[ServerStats] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize connection handler.

        Args:
            reader: Asyncio stream reader for client connection
            writer: Asyncio stream writer for client connection
            config: Server configuration dictionary
            db_manager: Database manager for host operations
            stats: Server statistics tracker
            timeout: Connection timeout in seconds
        """
        self.reader = reader
        self.writer = writer
        self.config = config
        self.db_manager = db_manager
        self.stats = stats or ServerStats()
        self.timeout = timeout

        # Extract client IP address
        peername = writer.get_extra_info("peername")
        self.client_ip = peername[0] if peername else "unknown"
        self.client_port = peername[1] if peername else 0

        # Initialize protocol handlers
        self.protocol = MessageProtocol()
        self.validator = MessageValidator()
        self.security_validator = SecurityValidator()

        # Connection state
        self.connected = True
        self.start_time = time.time()
        self.messages_processed = 0

        # Initialize host operations if database available
        self.host_ops = None
        if self.db_manager:
            self.host_ops = HostOperations(self.db_manager)

        # Initialize registration processor with config
        self.registration_processor = None
        if config:
            self.registration_processor = create_registration_processor(config)

        # Initialize DNS client if enabled
        self.dns_client = None
        powerdns_config = config.get("powerdns", {})
        if powerdns_config.get("enabled", False):
            self.dns_client = create_dns_client(config)

        logger.info(f"Connection handler initialized for {self.client_ip}:{self.client_port}")

    async def handle_connection(self) -> None:
        """
        Main connection handling loop.

        Handles the complete lifecycle of a client connection including
        message reading, processing, and response sending.
        """
        try:
            # Record connection opening
            self.stats.connection_opened(self.client_ip)

            logger.info(f"Handling connection from {self.client_ip}:{self.client_port}")

            # Main message processing loop
            while self.connected:
                try:
                    # Read message with timeout
                    message_data = await asyncio.wait_for(
                        self.reader.read(4096), timeout=self.timeout
                    )

                    # Check for client disconnect
                    if not message_data:
                        logger.info(f"Client {self.client_ip} disconnected")
                        break

                    # Process received data
                    await self._process_received_data(message_data)

                except asyncio.TimeoutError:
                    logger.warning(f"Connection timeout for {self.client_ip}")
                    await self._send_error_response("Connection timeout")
                    break

                except ProtocolError as e:
                    logger.warning(f"Protocol error from {self.client_ip}: {e}")
                    self.stats.error_occurred("protocol_error", str(e))
                    await self._send_error_response(f"Protocol error: {e}")
                    # Continue to allow recovery from protocol errors

                except Exception as e:
                    logger.error(f"Unexpected error handling connection from {self.client_ip}: {e}")
                    self.stats.error_occurred("connection_error", str(e))
                    await self._send_error_response("Internal server error")
                    break

        except Exception as e:
            logger.error(f"Fatal error in connection handler for {self.client_ip}: {e}")
            self.stats.error_occurred("fatal_error", str(e))

        finally:
            await self._cleanup_connection()

    async def _process_received_data(self, data: bytes) -> None:
        """
        Process received data and extract messages.

        Args:
            data: Raw bytes received from client
        """
        try:
            # Decode messages from data
            messages = self.protocol.decode_messages(data)

            # Process each complete message
            for message in messages:
                start_time = time.time()
                await self._process_message(message)
                processing_time = time.time() - start_time

                # Record processing time
                self.stats.message_processed(processing_time)
                self.messages_processed += 1

        except ProtocolError as e:
            # Let the caller handle protocol errors
            raise
        except Exception as e:
            logger.error(f"Error processing data from {self.client_ip}: {e}")
            raise

    async def _process_message(self, message: Dict[str, Any]) -> None:
        """
        Process a single decoded message.

        Args:
            message: Decoded message dictionary
        """
        try:
            # Record message reception
            message_type = message.get("type", "unknown")
            self.stats.message_received(message_type)

            logger.debug(f"Processing {message_type} message from {self.client_ip}")

            # Security validation
            is_safe, security_error = self.security_validator.validate_message_security(message)
            if not is_safe:
                logger.warning(f"Security validation failed for {self.client_ip}: {security_error}")
                await self._send_error_response(f"Security validation failed: {security_error}")
                return

            # Message structure validation
            is_valid, validation_error = self.validator.validate_registration_message(message)
            if not is_valid:
                logger.warning(
                    f"Message validation failed for {self.client_ip}: {validation_error}"
                )
                await self._send_error_response(f"Invalid message: {validation_error}")
                return

            # Process by message type
            if message_type == "registration":
                await self._handle_registration(message)
            else:
                logger.warning(f"Unknown message type from {self.client_ip}: {message_type}")
                await self._send_error_response(f"Unknown message type: {message_type}")

        except Exception as e:
            logger.error(f"Error processing message from {self.client_ip}: {e}")
            await self._send_error_response("Message processing failed")

    async def _handle_registration(self, message: Dict[str, Any]) -> None:
        """
        Handle client registration message.

        Args:
            message: Registration message dictionary
        """
        try:
            hostname = message["hostname"]
            timestamp = message["timestamp"]

            logger.info(f"Processing registration for hostname '{hostname}' from {self.client_ip}")

            # Registration processor is required
            if not self.registration_processor:
                logger.error("Registration processor not available")
                await self._send_error_response("Server configuration error")
                return

            # Extract auth token (required)
            auth_token = message.get("auth_token")
            
            # Process registration with auth token
            result = await self.registration_processor.process_registration(
                hostname=hostname,
                client_ip=self.client_ip,
                message_timestamp=timestamp,
                auth_token=auth_token
            )

            if result.success:
                # Registration successful, now handle DNS if enabled
                if self.dns_client and result.result_type in ["new_registration", "ip_change"]:
                    await self._handle_dns_registration(hostname, self.client_ip, result)

                await self._send_success_response(result.message)
            else:
                await self._send_error_response(result.message)

        except Exception as e:
            logger.error(f"Error handling registration from {self.client_ip}: {e}")
            await self._send_error_response("Registration processing failed")

    async def _handle_dns_registration(
        self, hostname: str, ip_address: str, registration_result: Any
    ) -> None:
        """
        Handle DNS record creation/update for registered host.

        Args:
            hostname: Hostname to register in DNS
            ip_address: IP address for DNS record
            registration_result: Result from registration processor
        """
        try:
            # Determine if this is IPv4 or IPv6
            import ipaddress as ip_lib

            ip_obj = ip_lib.ip_address(ip_address)
            record_type = "A" if ip_obj.version == 4 else "AAAA"

            # Create or update DNS record
            if record_type == "A":
                dns_result = await self.dns_client.create_a_record(hostname, ip_address)
            else:
                dns_result = await self.dns_client.create_aaaa_record(hostname, ip_address)

            # Update host with DNS information
            if self.host_ops and dns_result.get("status") == "success":
                zone = dns_result.get("zone", self.dns_client.default_zone)
                self.host_ops.update_dns_info(
                    hostname=hostname,
                    dns_zone=zone,
                    dns_record_id=dns_result.get("fqdn"),
                    dns_sync_status="synced",
                )
                logger.info(f"DNS record created/updated for {hostname}: {dns_result}")
            elif self.host_ops:
                # DNS creation failed
                self.host_ops.update_dns_info(hostname=hostname, dns_sync_status="failed")
                logger.warning(f"Failed to create DNS record for {hostname}")

        except Exception as e:
            logger.error(f"Error handling DNS registration for {hostname}: {e}")
            # Update sync status to failed
            if self.host_ops:
                self.host_ops.update_dns_info(hostname=hostname, dns_sync_status="failed")


    async def _send_success_response(self, message: str) -> None:
        """
        Send success response to client.

        Args:
            message: Success message to send
        """
        await self._send_response("success", message)

    async def _send_error_response(self, message: str) -> None:
        """
        Send error response to client.

        Args:
            message: Error message to send
        """
        await self._send_response("error", message)

    async def _send_response(self, status: str, message: str) -> None:
        """
        Send response message to client.

        Args:
            status: Response status ('success' or 'error')
            message: Response message content
        """
        try:
            # Create response message
            response = self.protocol.create_registration_response(status, message)

            # Encode response
            encoded_response = self.protocol.encode_message(response)

            # Send response
            self.writer.write(encoded_response)
            await self.writer.drain()

            # Record message sent
            self.stats.message_sent("response")

            logger.debug(f"Sent {status} response to {self.client_ip}: {message}")

        except Exception as e:
            logger.error(f"Error sending response to {self.client_ip}: {e}")
            self.stats.error_occurred("response_error", str(e))

    async def _cleanup_connection(self) -> None:
        """Clean up connection resources."""
        try:
            self.connected = False

            # Close writer
            if self.writer and not self.writer.is_closing():
                self.writer.close()
                await self.writer.wait_closed()

            # Close DNS client if present
            if self.dns_client:
                await self.dns_client.close()

            # Record connection closing
            self.stats.connection_closed(self.client_ip)

            # Calculate connection duration
            duration = time.time() - self.start_time

            logger.info(
                f"Connection from {self.client_ip} closed after {duration:.2f}s, "
                f"processed {self.messages_processed} messages"
            )

        except Exception as e:
            logger.error(f"Error during connection cleanup for {self.client_ip}: {e}")

    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get information about this connection.

        Returns:
            Dictionary with connection information
        """
        return {
            "client_ip": self.client_ip,
            "client_port": self.client_port,
            "connected": self.connected,
            "start_time": self.start_time,
            "duration": time.time() - self.start_time,
            "messages_processed": self.messages_processed,
            "buffer_size": self.protocol.get_buffer_size(),
        }

    def is_connected(self) -> bool:
        """Check if connection is still active."""
        return self.connected and not self.writer.is_closing()

    async def close(self) -> None:
        """Gracefully close the connection."""
        logger.info(f"Closing connection to {self.client_ip}")
        self.connected = False
        await self._cleanup_connection()


class ConnectionManager:
    """Manages multiple client connections."""

    def __init__(self, max_connections: int = 1000):
        """
        Initialize connection manager.

        Args:
            max_connections: Maximum number of concurrent connections
        """
        self.max_connections = max_connections
        self.active_connections = {}
        self._connection_lock = asyncio.Lock()
        self.total_connections = 0

        logger.info(f"ConnectionManager initialized with max_connections={max_connections}")

    async def add_connection(self, connection_handler: ConnectionHandler) -> bool:
        """
        Add a new connection.

        Args:
            connection_handler: Connection handler to add

        Returns:
            True if connection was added, False if rejected
        """
        async with self._connection_lock:
            if len(self.active_connections) >= self.max_connections:
                logger.warning(
                    f"Connection limit reached, rejecting {connection_handler.client_ip}"
                )
                return False

            connection_id = f"{connection_handler.client_ip}:{connection_handler.client_port}"
            self.active_connections[connection_id] = connection_handler
            self.total_connections += 1

            logger.info(f"Added connection {connection_id}, active: {len(self.active_connections)}")
            return True

    async def remove_connection(self, connection_handler: ConnectionHandler) -> None:
        """
        Remove a connection.

        Args:
            connection_handler: Connection handler to remove
        """
        async with self._connection_lock:
            connection_id = f"{connection_handler.client_ip}:{connection_handler.client_port}"

            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
                logger.info(
                    f"Removed connection {connection_id}, active: {len(self.active_connections)}"
                )

    def get_active_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)

    def get_total_count(self) -> int:
        """Get total number of connections processed."""
        return self.total_connections

    async def close_all_connections(self) -> None:
        """Close all active connections."""
        async with self._connection_lock:
            logger.info(f"Closing {len(self.active_connections)} active connections")

            close_tasks = []
            for connection in self.active_connections.values():
                close_tasks.append(connection.close())

            if close_tasks:
                await asyncio.gather(*close_tasks, return_exceptions=True)

            self.active_connections.clear()

    def get_connection_list(self) -> List[Dict[str, Any]]:
        """Get list of active connection information."""
        return [conn.get_connection_info() for conn in self.active_connections.values()]
