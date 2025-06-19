#!/usr/bin/env python3
"""
Unit tests for SMTP connection pooling.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import aiosmtplib
import pytest

from server.auth.email_providers.config import EmailProviderType, SMTPEmailConfig
from server.auth.email_providers.smtp_pool import PooledConnection, SMTPConnectionPool


class TestSMTPConnectionPool:
    """Test SMTP connection pool functionality."""

    @pytest.fixture
    def smtp_config(self):
        """Create test SMTP configuration."""
        return SMTPEmailConfig(
            provider=EmailProviderType.SMTP,
            from_email="test@example.com",
            from_name="Test App",
            host="smtp.example.com",
            port=587,
            username="test_user",
            password="test_pass",
            use_tls=True,
            use_ssl=False,
            timeout=30,
        )

    @pytest.fixture
    def mock_smtp(self):
        """Create mock SMTP connection."""
        mock = AsyncMock(spec=aiosmtplib.SMTP)
        mock.connect = AsyncMock()
        mock.starttls = AsyncMock()
        mock.login = AsyncMock()
        mock.quit = AsyncMock()
        mock.is_connected = True
        return mock

    @pytest.mark.asyncio
    async def test_create_pool(self, smtp_config):
        """Test creating connection pool."""
        pool = SMTPConnectionPool(smtp_config, max_size=3)

        assert pool.max_size == 3
        assert pool.connections == []
        assert pool.max_idle_time == 300

    @pytest.mark.asyncio
    async def test_acquire_connection_creates_new(self, smtp_config, mock_smtp):
        """Test acquiring connection when pool is empty."""
        pool = SMTPConnectionPool(smtp_config, max_size=3)

        with patch("aiosmtplib.SMTP", return_value=mock_smtp):
            connection = await pool._acquire_connection()

            assert isinstance(connection, PooledConnection)
            assert connection.smtp == mock_smtp
            assert connection.in_use is True
            assert len(pool.connections) == 1

            # Verify connection setup
            mock_smtp.connect.assert_called_once()
            mock_smtp.starttls.assert_called_once()
            mock_smtp.login.assert_called_once_with("test_user", "test_pass")

    @pytest.mark.asyncio
    async def test_acquire_connection_reuses_existing(self, smtp_config, mock_smtp):
        """Test reusing existing connection from pool."""
        pool = SMTPConnectionPool(smtp_config, max_size=3)

        # Create a connection and release it
        with patch("aiosmtplib.SMTP", return_value=mock_smtp):
            conn1 = await pool._acquire_connection()
            await pool._release_connection(conn1)

            # Reset mock to track new calls
            mock_smtp.reset_mock()

            # Acquire again - should reuse
            conn2 = await pool._acquire_connection()

            assert conn2 == conn1
            assert conn2.in_use is True
            # Should not create new connection
            mock_smtp.connect.assert_not_called()

    @pytest.mark.asyncio
    async def test_connection_pool_context_manager(self, smtp_config, mock_smtp):
        """Test using connection pool with context manager."""
        pool = SMTPConnectionPool(smtp_config, max_size=3)

        with patch("aiosmtplib.SMTP", return_value=mock_smtp):
            async with pool.get_connection() as smtp:
                assert smtp == mock_smtp
                # Connection should be in use
                assert pool.connections[0].in_use is True

            # After context, connection should be released
            assert pool.connections[0].in_use is False

    @pytest.mark.asyncio
    async def test_pool_size_limit(self, smtp_config):
        """Test pool respects max size limit."""
        pool = SMTPConnectionPool(smtp_config, max_size=2)

        mock_connections = []
        for i in range(3):
            mock = AsyncMock(spec=aiosmtplib.SMTP)
            mock.connect = AsyncMock()
            mock.starttls = AsyncMock()
            mock.login = AsyncMock()
            mock.is_connected = True
            mock_connections.append(mock)

        with patch("aiosmtplib.SMTP", side_effect=mock_connections):
            # Create 2 connections (max size)
            conn1 = await pool._acquire_connection()
            conn2 = await pool._acquire_connection()

            assert len(pool.connections) == 2

            # Try to acquire third when pool is full and all in use
            # This should wait or raise an exception
            with pytest.raises(Exception):  # Should implement waiting logic
                await asyncio.wait_for(pool._acquire_connection(), timeout=0.1)

    @pytest.mark.asyncio
    async def test_connection_health_check(self, smtp_config, mock_smtp):
        """Test connection health checking."""
        pool = SMTPConnectionPool(smtp_config, max_size=3)

        # Create connection
        conn = PooledConnection(
            smtp=mock_smtp,
            created_at=time.time(),
            last_used=time.time(),
            in_use=False,
        )

        # Healthy connection
        mock_smtp.is_connected = True
        assert pool._is_healthy(conn) is True

        # Unhealthy connection
        mock_smtp.is_connected = False
        assert pool._is_healthy(conn) is False

        # Old connection (idle too long)
        conn.last_used = time.time() - 400  # More than max_idle_time
        assert pool._is_healthy(conn) is False

    @pytest.mark.asyncio
    async def test_cleanup_idle_connections(self, smtp_config, mock_smtp):
        """Test cleanup of idle connections."""
        pool = SMTPConnectionPool(smtp_config, max_size=3)

        # Create old connection
        old_conn = PooledConnection(
            smtp=mock_smtp,
            created_at=time.time() - 400,
            last_used=time.time() - 400,
            in_use=False,
        )
        pool.connections.append(old_conn)

        # Create recent connection
        new_conn = PooledConnection(
            smtp=AsyncMock(spec=aiosmtplib.SMTP),
            created_at=time.time(),
            last_used=time.time(),
            in_use=False,
        )
        new_conn.smtp.is_connected = True
        pool.connections.append(new_conn)

        await pool._cleanup_idle_connections()

        # Old connection should be removed
        assert len(pool.connections) == 1
        assert pool.connections[0] == new_conn
        # Old connection should be closed
        mock_smtp.quit.assert_called_once()

    @pytest.mark.asyncio
    async def test_release_connection(self, smtp_config, mock_smtp):
        """Test releasing connection back to pool."""
        pool = SMTPConnectionPool(smtp_config, max_size=3)

        conn = PooledConnection(
            smtp=mock_smtp,
            created_at=time.time(),
            last_used=time.time() - 100,
            in_use=True,
        )
        pool.connections.append(conn)

        await pool._release_connection(conn)

        assert conn.in_use is False
        assert conn.last_used > time.time() - 1  # Recently used

    @pytest.mark.asyncio
    async def test_close_pool(self, smtp_config):
        """Test closing all connections in pool."""
        pool = SMTPConnectionPool(smtp_config, max_size=3)

        # Create multiple connections
        mocks = []
        for i in range(3):
            mock = AsyncMock(spec=aiosmtplib.SMTP)
            mock.quit = AsyncMock()
            conn = PooledConnection(
                smtp=mock,
                created_at=time.time(),
                last_used=time.time(),
                in_use=False,
            )
            pool.connections.append(conn)
            mocks.append(mock)

        await pool.close()

        # All connections should be closed
        assert len(pool.connections) == 0
        for mock in mocks:
            mock.quit.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, smtp_config):
        """Test handling connection errors."""
        pool = SMTPConnectionPool(smtp_config, max_size=3)

        # Mock SMTP that fails to connect
        mock_smtp = AsyncMock(spec=aiosmtplib.SMTP)
        mock_smtp.connect.side_effect = aiosmtplib.SMTPException("Connection failed")

        with patch("aiosmtplib.SMTP", return_value=mock_smtp):
            with pytest.raises(aiosmtplib.SMTPException):
                await pool._create_connection()

            # Pool should not contain failed connection
            assert len(pool.connections) == 0
