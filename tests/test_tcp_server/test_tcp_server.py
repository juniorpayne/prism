#!/usr/bin/env python3
"""
Tests for TCP Server Implementation (SCRUM-14)
Test-driven development for asyncio-based TCP server.
"""

import asyncio
import json
import os
import struct
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch


class TestTCPServer(unittest.TestCase):
    """Test main TCP server functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name

        self.server_config = {
            "server": {"tcp_port": 8080, "host": "localhost", "max_connections": 100},
            "database": {"path": self.db_path, "connection_pool_size": 20},
        }

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_tcp_server_class_exists(self):
        """Test that TCPServer class exists."""
        try:
            from server.tcp_server import TCPServer

            self.assertTrue(callable(TCPServer))
        except ImportError:
            self.fail("TCPServer should be importable from server.tcp_server")

    def test_tcp_server_initialization(self):
        """Test TCP server initialization with configuration."""
        from server.tcp_server import TCPServer

        server = TCPServer(self.server_config)

        self.assertIsNotNone(server)
        self.assertEqual(server.host, "localhost")
        self.assertEqual(server.port, 8080)
        self.assertEqual(server.max_connections, 100)

    def test_tcp_server_start_stop(self):
        """Test server start and stop lifecycle."""

        async def test_lifecycle():
            from server.tcp_server import TCPServer

            server = TCPServer(self.server_config)

            # Start server
            await server.start()
            self.assertTrue(server.is_running())

            # Stop server
            await server.stop()
            self.assertFalse(server.is_running())

        asyncio.run(test_lifecycle())

    def test_tcp_server_client_connection_acceptance(self):
        """Test that server accepts client connections."""

        async def test_connection():
            from server.tcp_server import TCPServer

            # Use a different port to avoid conflicts
            config = self.server_config.copy()
            config["server"]["tcp_port"] = 8081

            server = TCPServer(config)
            await server.start()

            try:
                # Connect as client
                reader, writer = await asyncio.open_connection("localhost", 8081)

                # Verify connection
                self.assertIsNotNone(reader)
                self.assertIsNotNone(writer)

                # Close connection
                writer.close()
                await writer.wait_closed()

            finally:
                await server.stop()

        asyncio.run(test_connection())

    def test_tcp_server_concurrent_connections(self):
        """Test server handling multiple concurrent connections."""

        async def test_concurrent():
            from server.tcp_server import TCPServer

            config = self.server_config.copy()
            config["server"]["tcp_port"] = 8082

            server = TCPServer(config)
            await server.start()

            try:
                # Create multiple concurrent connections
                connections = []
                for i in range(5):
                    reader, writer = await asyncio.open_connection("localhost", 8082)
                    connections.append((reader, writer))

                # Verify all connections established
                self.assertEqual(len(connections), 5)

                # Close all connections
                for reader, writer in connections:
                    writer.close()
                    await writer.wait_closed()

            finally:
                await server.stop()

        asyncio.run(test_concurrent())

    def test_tcp_server_max_connections_limit(self):
        """Test server enforces maximum connection limits."""

        async def test_max_connections():
            from server.tcp_server import TCPServer

            config = self.server_config.copy()
            config["server"]["tcp_port"] = 8083
            config["server"]["max_connections"] = 3  # Low limit for testing

            server = TCPServer(config)
            await server.start()

            try:
                # Create connections up to the limit
                connections = []
                for i in range(3):
                    reader, writer = await asyncio.open_connection("localhost", 8083)
                    connections.append((reader, writer))

                # Verify limit is respected
                active_count = server.get_active_connections()
                self.assertLessEqual(active_count, 3)

                # Clean up
                for reader, writer in connections:
                    writer.close()
                    await writer.wait_closed()

            finally:
                await server.stop()

        asyncio.run(test_max_connections())

    def test_tcp_server_message_processing(self):
        """Test server processes client messages correctly."""

        async def test_message_processing():
            from server.protocol import MessageProtocol
            from server.tcp_server import TCPServer

            config = self.server_config.copy()
            config["server"]["tcp_port"] = 8084

            server = TCPServer(config)
            await server.start()

            try:
                # Connect as client
                reader, writer = await asyncio.open_connection("localhost", 8084)

                # Send registration message
                protocol = MessageProtocol()
                message = {
                    "version": "1.0",
                    "type": "registration",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "hostname": "test-client",
                }

                encoded_message = protocol.encode_message(message)
                writer.write(encoded_message)
                await writer.drain()

                # Read response
                response_data = await reader.read(1024)
                responses = protocol.decode_messages(response_data)

                self.assertGreater(len(responses), 0)
                response = responses[0]
                self.assertEqual(response["type"], "response")
                self.assertIn(response["status"], ["success", "error"])

                # Close connection
                writer.close()
                await writer.wait_closed()

            finally:
                await server.stop()

        asyncio.run(test_message_processing())

    def test_tcp_server_client_ip_extraction(self):
        """Test server extracts client IP addresses correctly."""

        async def test_ip_extraction():
            from server.tcp_server import TCPServer

            config = self.server_config.copy()
            config["server"]["tcp_port"] = 8085

            server = TCPServer(config)
            await server.start()

            try:
                # Connect as client
                reader, writer = await asyncio.open_connection("localhost", 8085)

                # Allow server time to process connection
                await asyncio.sleep(0.1)

                # Check that server tracked the connection with IP
                connections = server.get_connection_info()
                self.assertGreater(len(connections), 0)

                # Verify IP was extracted (should be 127.0.0.1 for localhost)
                connection_ips = [conn["client_ip"] for conn in connections]
                self.assertIn("127.0.0.1", connection_ips)

                # Close connection
                writer.close()
                await writer.wait_closed()

            finally:
                await server.stop()

        asyncio.run(test_ip_extraction())

    def test_tcp_server_graceful_shutdown(self):
        """Test server handles graceful shutdown correctly."""

        async def test_graceful_shutdown():
            from server.tcp_server import TCPServer

            config = self.server_config.copy()
            config["server"]["tcp_port"] = 8086

            server = TCPServer(config)
            await server.start()

            # Create active connections
            connections = []
            for i in range(3):
                reader, writer = await asyncio.open_connection("localhost", 8086)
                connections.append((reader, writer))

            # Graceful shutdown should close all connections
            await server.stop(graceful=True)

            # Verify server is stopped
            self.assertFalse(server.is_running())

            # Connections should be closed
            for reader, writer in connections:
                try:
                    writer.close()
                    await writer.wait_closed()
                except:
                    pass  # Expected if already closed

        asyncio.run(test_graceful_shutdown())

    def test_tcp_server_error_handling(self):
        """Test server handles various error conditions."""

        async def test_error_handling():
            from server.tcp_server import TCPServer

            config = self.server_config.copy()
            config["server"]["tcp_port"] = 8087

            server = TCPServer(config)
            await server.start()

            try:
                # Connect and send malformed data
                reader, writer = await asyncio.open_connection("localhost", 8087)

                # Send malformed message (invalid length prefix)
                invalid_data = b"invalid_data_without_length_prefix"
                writer.write(invalid_data)
                await writer.drain()

                # Server should handle gracefully and not crash
                await asyncio.sleep(0.1)
                self.assertTrue(server.is_running())

                # Close connection
                writer.close()
                await writer.wait_closed()

            finally:
                await server.stop()

        asyncio.run(test_error_handling())

    def test_tcp_server_stats_tracking(self):
        """Test server tracks connection statistics."""

        async def test_stats_tracking():
            from server.tcp_server import TCPServer

            config = self.server_config.copy()
            config["server"]["tcp_port"] = 8088

            server = TCPServer(config)
            await server.start()

            try:
                initial_stats = server.get_stats()

                # Make some connections
                connections = []
                for i in range(3):
                    reader, writer = await asyncio.open_connection("localhost", 8088)
                    connections.append((reader, writer))

                await asyncio.sleep(0.1)  # Let stats update

                current_stats = server.get_stats()

                # Verify stats are being tracked
                self.assertGreaterEqual(
                    current_stats["total_connections"], initial_stats["total_connections"] + 3
                )

                # Clean up
                for reader, writer in connections:
                    writer.close()
                    await writer.wait_closed()

            finally:
                await server.stop()

        asyncio.run(test_stats_tracking())


class TestConnectionHandler(unittest.TestCase):
    """Test connection handler functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_connection_handler_class_exists(self):
        """Test that ConnectionHandler class exists."""
        try:
            from server.connection_handler import ConnectionHandler

            self.assertTrue(callable(ConnectionHandler))
        except ImportError:
            self.fail("ConnectionHandler should be importable from server.connection_handler")

    def test_connection_handler_initialization(self):
        """Test connection handler initialization."""
        from server.connection_handler import ConnectionHandler

        mock_reader = AsyncMock()
        mock_writer = Mock()
        mock_writer.get_extra_info.return_value = ("127.0.0.1", 12345)

        # Mock database manager to prevent logging errors
        mock_db_manager = Mock()
        mock_db_manager.health_check.return_value = True

        handler = ConnectionHandler(mock_reader, mock_writer, db_manager=mock_db_manager)

        self.assertIsNotNone(handler)
        self.assertEqual(handler.client_ip, "127.0.0.1")

    def test_connection_handler_message_processing(self):
        """Test connection handler processes messages."""

        async def test_processing():
            from server.connection_handler import ConnectionHandler
            from server.protocol import MessageProtocol

            # Mock reader/writer
            mock_reader = AsyncMock()
            mock_writer = Mock()
            mock_writer.get_extra_info.return_value = ("127.0.0.1", 12345)
            mock_writer.write = Mock()
            mock_writer.drain = AsyncMock()

            # Mock database manager and host operations
            mock_db_manager = Mock()
            mock_db_manager.health_check.return_value = True

            # Prepare test message
            protocol = MessageProtocol()
            message = {
                "version": "1.0",
                "type": "registration",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "hostname": "test-host",
            }
            encoded_message = protocol.encode_message(message)

            # Mock reader to return our test message, then simulate disconnect
            mock_reader.read.side_effect = [encoded_message, b""]  # First message, then disconnect

            handler = ConnectionHandler(mock_reader, mock_writer, db_manager=mock_db_manager)

            # Mock host operations with all required methods
            mock_host_ops = Mock()
            mock_host_ops.get_host_by_hostname.return_value = None  # New host
            
            # Mock successful host creation
            mock_new_host = Mock()
            mock_new_host.hostname = "test-host"
            mock_new_host.current_ip = "127.0.0.1"
            mock_host_ops.create_host.return_value = mock_new_host
            mock_host_ops.update_host_ip.return_value = True
            mock_host_ops.update_host_last_seen.return_value = True
            
            handler.host_ops = mock_host_ops

            # Process message
            await handler.handle_connection()

            # Verify writer was called (response sent)
            mock_writer.write.assert_called()

        asyncio.run(test_processing())

    def test_connection_handler_client_disconnect(self):
        """Test connection handler handles client disconnections."""

        async def test_disconnect():
            from server.connection_handler import ConnectionHandler

            # Mock reader/writer
            mock_reader = AsyncMock()
            mock_writer = Mock()
            mock_writer.get_extra_info.return_value = ("127.0.0.1", 12345)
            mock_writer.write = Mock()
            mock_writer.drain = AsyncMock()
            mock_writer.close = Mock()
            mock_writer.wait_closed = AsyncMock()
            mock_writer.is_closing.return_value = False  # Not closing initially

            # Mock reader to simulate client disconnect (empty read)
            mock_reader.read.return_value = b""

            # Mock database manager to prevent logging errors
            mock_db_manager = Mock()
            mock_db_manager.health_check.return_value = True

            handler = ConnectionHandler(mock_reader, mock_writer, db_manager=mock_db_manager)

            # Handle connection (should detect disconnect)
            await handler.handle_connection()

            # Verify cleanup was performed
            mock_writer.close.assert_called()

        asyncio.run(test_disconnect())

    def test_connection_handler_timeout(self):
        """Test connection handler handles timeouts."""

        async def test_timeout():
            from server.connection_handler import ConnectionHandler

            # Mock reader/writer
            mock_reader = AsyncMock()
            mock_writer = Mock()
            mock_writer.get_extra_info.return_value = ("127.0.0.1", 12345)
            mock_writer.write = Mock()
            mock_writer.drain = AsyncMock()
            mock_writer.close = Mock()
            mock_writer.wait_closed = AsyncMock()
            mock_writer.is_closing.return_value = False  # Not closing initially

            # Mock reader to simulate timeout
            mock_reader.read.side_effect = asyncio.TimeoutError()

            # Mock database manager to prevent logging errors
            mock_db_manager = Mock()
            mock_db_manager.health_check.return_value = True

            handler = ConnectionHandler(mock_reader, mock_writer, db_manager=mock_db_manager, timeout=1.0)

            # Handle connection (should handle timeout gracefully)
            await handler.handle_connection()

            # Verify cleanup was performed
            mock_writer.close.assert_called()

        asyncio.run(test_timeout())


class TestServerStats(unittest.TestCase):
    """Test server statistics functionality."""

    def test_server_stats_class_exists(self):
        """Test that ServerStats class exists."""
        try:
            from server.server_stats import ServerStats

            self.assertTrue(callable(ServerStats))
        except ImportError:
            self.fail("ServerStats should be importable from server.server_stats")

    def test_server_stats_initialization(self):
        """Test server stats initialization."""
        from server.server_stats import ServerStats

        stats = ServerStats()

        self.assertIsNotNone(stats)
        self.assertEqual(stats.get_total_connections(), 0)
        self.assertEqual(stats.get_active_connections(), 0)

    def test_server_stats_connection_tracking(self):
        """Test connection tracking in server stats."""
        from server.server_stats import ServerStats

        stats = ServerStats()

        # Track connections
        stats.connection_opened("127.0.0.1")
        stats.connection_opened("192.168.1.100")

        self.assertEqual(stats.get_total_connections(), 2)
        self.assertEqual(stats.get_active_connections(), 2)

        # Close one connection
        stats.connection_closed("127.0.0.1")

        self.assertEqual(stats.get_total_connections(), 2)
        self.assertEqual(stats.get_active_connections(), 1)

    def test_server_stats_message_tracking(self):
        """Test message processing tracking."""
        from server.server_stats import ServerStats

        stats = ServerStats()

        # Track messages
        stats.message_received("registration")
        stats.message_received("registration")
        stats.message_sent("response")

        self.assertEqual(stats.get_messages_received(), 2)
        self.assertEqual(stats.get_messages_sent(), 1)

    def test_server_stats_error_tracking(self):
        """Test error tracking in server stats."""
        from server.server_stats import ServerStats

        stats = ServerStats()

        # Track errors
        stats.error_occurred("protocol_error")
        stats.error_occurred("connection_timeout")
        stats.error_occurred("protocol_error")

        self.assertEqual(stats.get_total_errors(), 3)
        error_counts = stats.get_error_counts()
        self.assertEqual(error_counts["protocol_error"], 2)
        self.assertEqual(error_counts["connection_timeout"], 1)

    def test_server_stats_performance_metrics(self):
        """Test performance metrics tracking."""
        import time

        from server.server_stats import ServerStats

        stats = ServerStats()

        # Track message processing time
        start_time = time.time()
        time.sleep(0.01)  # Simulate processing
        stats.message_processed(time.time() - start_time)

        metrics = stats.get_performance_metrics()
        self.assertGreater(metrics["avg_processing_time"], 0)
        self.assertGreater(metrics["total_processing_time"], 0)

    def test_server_stats_reset(self):
        """Test resetting server stats."""
        from server.server_stats import ServerStats

        stats = ServerStats()

        # Add some data
        stats.connection_opened("127.0.0.1")
        stats.message_received("registration")
        stats.error_occurred("test_error")

        # Reset stats
        stats.reset()

        self.assertEqual(stats.get_total_connections(), 0)
        self.assertEqual(stats.get_messages_received(), 0)
        self.assertEqual(stats.get_total_errors(), 0)

    def test_server_stats_json_export(self):
        """Test exporting stats as JSON."""
        import json

        from server.server_stats import ServerStats

        stats = ServerStats()

        # Add some data
        stats.connection_opened("127.0.0.1")
        stats.message_received("registration")

        # Export as JSON
        json_stats = stats.to_json()
        parsed_stats = json.loads(json_stats)

        self.assertIn("total_connections", parsed_stats)
        self.assertIn("active_connections", parsed_stats)
        self.assertIn("messages_received", parsed_stats)


if __name__ == "__main__":
    unittest.main()
