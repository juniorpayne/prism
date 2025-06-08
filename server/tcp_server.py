#!/usr/bin/env python3
"""
TCP Server for Prism DNS Server (SCRUM-14)
Asyncio-based TCP server for handling client registrations.
"""

import asyncio
import logging
import signal
import time
from asyncio import Server
from typing import Any, Callable, Dict, List, Optional

from .connection_handler import ConnectionHandler, ConnectionManager
from .database.connection import DatabaseManager
from .database.migrations import init_database
from .server_stats import ServerStats, StatsCollector

logger = logging.getLogger(__name__)


class ServerError(Exception):
    """Exception raised for server-related errors."""

    pass


class TCPServerConfig:
    """Configuration for TCP server."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize server configuration.

        Args:
            config: Configuration dictionary
        """
        server_config = config.get("server", {})

        self.host = server_config.get("host", "localhost")
        self.tcp_port = server_config.get("tcp_port", 8080)
        self.max_connections = server_config.get("max_connections", 1000)
        self.connection_timeout = server_config.get("connection_timeout", 30.0)
        self.graceful_shutdown_timeout = server_config.get("graceful_shutdown_timeout", 10.0)

        # Database configuration
        self.database_config = config.get("database", {})

        # Validation
        if self.tcp_port <= 0 or self.tcp_port > 65535:
            raise ValueError(f"Invalid TCP port: {self.tcp_port}")

        if self.max_connections <= 0:
            raise ValueError(f"Invalid max_connections: {self.max_connections}")

        if self.connection_timeout <= 0:
            raise ValueError(f"Invalid connection_timeout: {self.connection_timeout}")

        logger.info(
            f"TCP server configured: {self.host}:{self.tcp_port}, "
            f"max_connections={self.max_connections}"
        )


class TCPServer:
    """
    Asyncio-based TCP server for handling client connections.

    Provides concurrent handling of multiple client connections with
    message processing, database integration, and comprehensive monitoring.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize TCP server.

        Args:
            config: Server configuration dictionary
        """
        self.config = TCPServerConfig(config)

        # Server state
        self._server: Optional[Server] = None
        self._running = False
        self._start_time: Optional[float] = None

        # Connection management
        self.connection_manager = ConnectionManager(self.config.max_connections)

        # Statistics and monitoring
        self.stats_collector = StatsCollector()
        self.stats = self.stats_collector.server_stats

        # Database integration
        self.db_manager: Optional[DatabaseManager] = None
        self._initialize_database()

        # Shutdown handling
        self._shutdown_event = asyncio.Event()
        self._setup_signal_handlers()

        logger.info(f"TCPServer initialized for {self.config.host}:{self.config.tcp_port}")

    @property
    def host(self) -> str:
        """Get server host."""
        return self.config.host

    @property
    def port(self) -> int:
        """Get server port."""
        return self.config.tcp_port

    @property
    def max_connections(self) -> int:
        """Get maximum connections."""
        return self.config.max_connections

    def _initialize_database(self) -> None:
        """Initialize database connection and schema."""
        try:
            # Check if database configuration has required parameters
            if self.config.database_config and "path" in self.config.database_config:
                self.db_manager = DatabaseManager({"database": self.config.database_config})

                # Initialize database schema with migrations
                init_database(self.db_manager)

                logger.info("Database initialized successfully")
            else:
                logger.warning(
                    "No database configuration provided or missing required 'path' parameter"
                )

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            logger.error(f"Database config was: {self.config.database_config}")
            # Continue without database (graceful degradation)
            self.db_manager = None

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown")
            asyncio.create_task(self.stop(graceful=True))

        # Only setup signal handlers if we're in the main thread
        try:
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
            logger.debug("Signal handlers configured")
        except ValueError:
            # Not in main thread, skip signal handling
            logger.debug("Skipping signal handlers (not in main thread)")

    async def start(self) -> None:
        """
        Start the TCP server.

        Raises:
            ServerError: If server fails to start
        """
        if self._running:
            raise ServerError("Server is already running")

        try:
            logger.info(f"Starting TCP server on {self.config.host}:{self.config.tcp_port}")

            # Create asyncio server
            self._server = await asyncio.start_server(
                self._handle_client_connection,
                self.config.host,
                self.config.tcp_port,
                limit=16384,  # Per-connection buffer limit
                reuse_address=True,
                reuse_port=True,
            )

            # Update server state
            self._running = True
            self._start_time = time.time()

            # Add custom metrics
            self.stats_collector.add_custom_metric("server_start_time", self._start_time)
            self.stats_collector.add_custom_metric("server_version", "1.0")

            logger.info(
                f"TCP server started successfully on {self.config.host}:{self.config.tcp_port}"
            )

        except OSError as e:
            raise ServerError(f"Failed to start server: {e}")
        except Exception as e:
            logger.error(f"Unexpected error starting server: {e}")
            raise ServerError(f"Server startup failed: {e}")

    async def stop(self, graceful: bool = True) -> None:
        """
        Stop the TCP server.

        Args:
            graceful: Whether to perform graceful shutdown
        """
        if not self._running:
            logger.warning("Server is not running")
            return

        logger.info(f"Stopping TCP server (graceful={graceful})")

        try:
            # Set shutdown event
            self._shutdown_event.set()

            # Close server socket (stop accepting new connections)
            if self._server:
                self._server.close()
                await self._server.wait_closed()

            if graceful:
                # Graceful shutdown: wait for existing connections
                await self._graceful_shutdown()
            else:
                # Force close all connections
                await self.connection_manager.close_all_connections()

            # Update server state
            self._running = False

            # Cleanup database
            if self.db_manager:
                self.db_manager.cleanup()

            # Calculate uptime
            uptime = time.time() - self._start_time if self._start_time else 0
            logger.info(f"TCP server stopped after {uptime:.2f} seconds")

        except Exception as e:
            logger.error(f"Error during server shutdown: {e}")
            raise

    async def _graceful_shutdown(self) -> None:
        """Perform graceful shutdown of server."""
        try:
            # Wait for connections to finish or timeout
            shutdown_start = time.time()

            while (
                self.connection_manager.get_active_count() > 0
                and time.time() - shutdown_start < self.config.graceful_shutdown_timeout
            ):

                logger.info(
                    f"Waiting for {self.connection_manager.get_active_count()} connections to close"
                )
                await asyncio.sleep(1.0)

            # Force close any remaining connections
            if self.connection_manager.get_active_count() > 0:
                logger.warning(
                    f"Force closing {self.connection_manager.get_active_count()} remaining connections"
                )
                await self.connection_manager.close_all_connections()

        except Exception as e:
            logger.error(f"Error during graceful shutdown: {e}")

    async def _handle_client_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """
        Handle new client connection.

        Args:
            reader: Stream reader for client connection
            writer: Stream writer for client connection
        """
        connection_handler = None

        try:
            # Create connection handler
            connection_handler = ConnectionHandler(
                reader,
                writer,
                db_manager=self.db_manager,
                stats=self.stats,
                timeout=self.config.connection_timeout,
            )

            # Check connection limits
            if not await self.connection_manager.add_connection(connection_handler):
                logger.warning(
                    f"Connection limit reached, rejecting {connection_handler.client_ip}"
                )
                await connection_handler._send_error_response("Server at capacity")
                await connection_handler.close()
                return

            # Handle the connection
            await connection_handler.handle_connection()

        except Exception as e:
            logger.error(f"Error handling client connection: {e}")
            self.stats.error_occurred("connection_handling_error", str(e))

        finally:
            # Clean up connection
            if connection_handler:
                await self.connection_manager.remove_connection(connection_handler)
                if connection_handler.is_connected():
                    await connection_handler.close()

    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running

    def get_active_connections(self) -> int:
        """Get number of active connections."""
        return self.connection_manager.get_active_count()

    def get_total_connections(self) -> int:
        """Get total number of connections processed."""
        return self.connection_manager.get_total_count()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive server statistics.

        Returns:
            Dictionary with server statistics
        """
        stats = self.stats_collector.get_all_stats()

        # Add server-specific stats
        stats["server"] = {
            "running": self._running,
            "start_time": self._start_time,
            "uptime": time.time() - self._start_time if self._start_time else 0,
            "host": self.config.host,
            "port": self.config.tcp_port,
            "max_connections": self.config.max_connections,
            "active_connections": self.get_active_connections(),
            "total_connections": self.get_total_connections(),
        }

        return stats

    def get_connection_info(self) -> List[Dict[str, Any]]:
        """
        Get information about active connections.

        Returns:
            List of connection information dictionaries
        """
        return self.connection_manager.get_connection_list()

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get server health status.

        Returns:
            Dictionary with health status information
        """
        base_health = self.stats.get_health_status()

        # Add server-specific health checks
        issues = base_health.get("issues", [])

        # Check if database is available
        if not self.db_manager or not self.db_manager.health_check():
            issues.append("Database unavailable")
            base_health["status"] = "degraded"

        # Check connection capacity
        connection_utilization = self.get_active_connections() / self.config.max_connections
        if connection_utilization > 0.9:  # >90% capacity
            issues.append(f"High connection utilization: {connection_utilization:.1%}")
            base_health["status"] = "warning"

        base_health["issues"] = issues
        base_health["connection_utilization"] = connection_utilization
        base_health["database_available"] = (
            self.db_manager is not None and self.db_manager.health_check()
        )

        return base_health

    async def run_forever(self) -> None:
        """
        Run server forever until shutdown signal.

        This is a convenience method for running the server as the main application.
        """
        if not self._running:
            await self.start()

        try:
            # Wait for shutdown signal
            await self._shutdown_event.wait()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            if self._running:
                await self.stop(graceful=True)

    def get_server_address(self) -> tuple:
        """
        Get server address.

        Returns:
            Tuple of (host, port)
        """
        if self._server and self._server.sockets:
            sock = self._server.sockets[0]
            return sock.getsockname()
        else:
            return (self.config.host, self.config.tcp_port)


async def create_server(config: Dict[str, Any]) -> TCPServer:
    """
    Create and configure a TCP server.

    Args:
        config: Server configuration dictionary

    Returns:
        Configured TCPServer instance
    """
    server = TCPServer(config)
    return server


async def run_server(config: Dict[str, Any]) -> None:
    """
    Create and run a TCP server.

    Args:
        config: Server configuration dictionary
    """
    server = await create_server(config)
    await server.run_forever()


if __name__ == "__main__":
    # Basic server configuration for standalone execution
    basic_config = {
        "server": {"host": "localhost", "tcp_port": 8080, "max_connections": 100},
        "database": {"path": "./prism_server.db", "connection_pool_size": 20},
    }

    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Run server
    asyncio.run(run_server(basic_config))
