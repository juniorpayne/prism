#!/usr/bin/env python3
"""
SMTP connection pooling for improved performance and resource management.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import List, Optional

import aiosmtplib

from .config import SMTPEmailConfig

logger = logging.getLogger(__name__)


@dataclass
class PooledConnection:
    """Represents a pooled SMTP connection."""

    smtp: aiosmtplib.SMTP
    created_at: float
    last_used: float
    in_use: bool = False


class SMTPConnectionPool:
    """
    Manages a pool of SMTP connections for reuse.

    Features:
    - Connection reuse for better performance
    - Automatic cleanup of idle connections
    - Health checks for connection validity
    - Thread-safe connection management
    """

    def __init__(self, config: SMTPEmailConfig, max_size: int = 5):
        """
        Initialize SMTP connection pool.

        Args:
            config: SMTP configuration
            max_size: Maximum number of connections in pool
        """
        self.config = config
        self.max_size = max_size
        self.connections: List[PooledConnection] = []
        self.lock = asyncio.Lock()
        self.max_idle_time = 300  # 5 minutes
        self._closed = False

    @asynccontextmanager
    async def get_connection(self):
        """
        Get a connection from the pool.

        Yields:
            aiosmtplib.SMTP: SMTP connection

        Raises:
            Exception: If unable to acquire connection
        """
        connection = None
        try:
            connection = await self._acquire_connection()
            yield connection.smtp
        finally:
            if connection:
                await self._release_connection(connection)

    async def _acquire_connection(self) -> PooledConnection:
        """
        Acquire a connection from pool or create new.

        Returns:
            PooledConnection: Available connection

        Raises:
            Exception: If unable to acquire connection
        """
        async with self.lock:
            if self._closed:
                raise Exception("Connection pool is closed")

            # Try to find an available healthy connection
            for conn in self.connections:
                if not conn.in_use and self._is_healthy(conn):
                    conn.in_use = True
                    conn.last_used = time.time()
                    logger.debug("Reusing existing SMTP connection")
                    return conn

            # Remove unhealthy connections
            self.connections = [
                conn for conn in self.connections if conn.in_use or self._is_healthy(conn)
            ]

            # Create new connection if pool not full
            if len(self.connections) < self.max_size:
                logger.debug("Creating new SMTP connection")
                new_conn = await self._create_connection()
                self.connections.append(new_conn)
                return new_conn

            # Wait for available connection
            return await self._wait_for_connection()

    async def _create_connection(self) -> PooledConnection:
        """
        Create new SMTP connection.

        Returns:
            PooledConnection: New connection

        Raises:
            aiosmtplib.SMTPException: If connection fails
        """
        smtp = aiosmtplib.SMTP(
            hostname=self.config.host,
            port=self.config.port,
            timeout=self.config.timeout,
        )

        await smtp.connect()

        if self.config.use_tls:
            await smtp.starttls()

        if self.config.username and self.config.password:
            await smtp.login(self.config.username, self.config.password)

        return PooledConnection(
            smtp=smtp,
            created_at=time.time(),
            last_used=time.time(),
            in_use=True,
        )

    async def _wait_for_connection(self) -> PooledConnection:
        """
        Wait for an available connection.

        Returns:
            PooledConnection: Available connection

        Raises:
            Exception: If timeout waiting for connection
        """
        # Simple implementation - in production, use more sophisticated waiting
        max_wait = 30  # seconds
        start_time = time.time()

        while time.time() - start_time < max_wait:
            # Release lock and wait briefly
            await asyncio.sleep(0.1)

            async with self.lock:
                for conn in self.connections:
                    if not conn.in_use and self._is_healthy(conn):
                        conn.in_use = True
                        conn.last_used = time.time()
                        return conn

        raise Exception("Timeout waiting for available connection")

    def _is_healthy(self, connection: PooledConnection) -> bool:
        """
        Check if connection is healthy.

        Args:
            connection: Connection to check

        Returns:
            bool: True if healthy, False otherwise
        """
        # Check if connection is too old
        if time.time() - connection.last_used > self.max_idle_time:
            logger.debug("Connection idle too long")
            return False

        # Check if SMTP connection is still alive
        try:
            return connection.smtp.is_connected
        except Exception:
            return False

    async def _release_connection(self, connection: PooledConnection) -> None:
        """
        Release connection back to pool.

        Args:
            connection: Connection to release
        """
        async with self.lock:
            connection.in_use = False
            connection.last_used = time.time()
            logger.debug("Released SMTP connection back to pool")

    async def _cleanup_idle_connections(self) -> None:
        """Clean up idle connections that are too old."""
        async with self.lock:
            current_time = time.time()
            connections_to_close = []
            connections_to_keep = []

            # Separate connections to keep and close
            for conn in self.connections:
                if conn.in_use or (current_time - conn.last_used <= self.max_idle_time):
                    connections_to_keep.append(conn)
                else:
                    connections_to_close.append(conn)

            # Update connections list
            self.connections = connections_to_keep

            # Close removed connections
            for conn in connections_to_close:
                try:
                    await conn.smtp.quit()
                except Exception as e:
                    logger.warning(f"Error closing idle connection: {e}")

    async def close(self) -> None:
        """Close all connections in the pool."""
        async with self.lock:
            self._closed = True

            # Close all connections
            for conn in self.connections:
                try:
                    await conn.smtp.quit()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")

            self.connections.clear()
            logger.info("SMTP connection pool closed")

    def __repr__(self) -> str:
        """String representation."""
        active = sum(1 for c in self.connections if c.in_use)
        total = len(self.connections)
        return f"<SMTPConnectionPool size={total} active={active} max={self.max_size}>"
