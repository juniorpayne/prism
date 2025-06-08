#!/usr/bin/env python3
"""
Integration Tests for TCP Server (SCRUM-14)
Test-driven development for complete TCP server integration.
"""

import asyncio
import json
import os
import struct
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone


class TestTCPServerIntegration(unittest.TestCase):
    """Test complete TCP server integration with database."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name

        self.server_config = {
            "server": {"tcp_port": 9001, "host": "127.0.0.1", "max_connections": 100},
            "database": {"path": self.db_path, "connection_pool_size": 20},
        }

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_complete_registration_flow(self):
        """Test complete client registration flow with database integration."""

        async def test_flow():
            from server.database.connection import DatabaseManager
            from server.database.operations import HostOperations
            from server.protocol import MessageProtocol
            from server.tcp_server import TCPServer

            # Initialize database
            db_manager = DatabaseManager(self.server_config)
            db_manager.initialize_schema()
            host_ops = HostOperations(db_manager)

            # Start server
            server = TCPServer(self.server_config)
            await server.start()

            try:
                # Connect as client
                reader, writer = await asyncio.open_connection("127.0.0.1", 9001)

                # Send registration message
                protocol = MessageProtocol()
                message = {
                    "version": "1.0",
                    "type": "registration",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "hostname": "integration-test-host",
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
                self.assertEqual(response["status"], "success")

                # Verify host was registered in database
                host = host_ops.get_host_by_hostname("integration-test-host")
                self.assertIsNotNone(host)
                self.assertEqual(host.hostname, "integration-test-host")
                self.assertEqual(host.current_ip, "127.0.0.1")
                self.assertEqual(host.status, "online")

                # Close connection
                writer.close()
                await writer.wait_closed()

            finally:
                await server.stop()
                db_manager.cleanup()

        asyncio.run(test_flow())

    def test_multiple_client_registrations(self):
        """Test multiple clients registering simultaneously."""

        async def test_multiple_clients():
            from server.database.connection import DatabaseManager
            from server.database.operations import HostOperations
            from server.protocol import MessageProtocol
            from server.tcp_server import TCPServer

            # Initialize database
            db_manager = DatabaseManager(self.server_config)
            db_manager.initialize_schema()
            host_ops = HostOperations(db_manager)

            # Start server
            config = self.server_config.copy()
            config["server"]["tcp_port"] = 9002
            server = TCPServer(config)
            await server.start()

            try:

                async def register_client(client_id):
                    """Register a single client."""
                    reader, writer = await asyncio.open_connection("127.0.0.1", 9002)

                    protocol = MessageProtocol()
                    message = {
                        "version": "1.0",
                        "type": "registration",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "hostname": f"client-{client_id}",
                    }

                    encoded_message = protocol.encode_message(message)
                    writer.write(encoded_message)
                    await writer.drain()

                    # Read response
                    response_data = await reader.read(1024)
                    responses = protocol.decode_messages(response_data)

                    writer.close()
                    await writer.wait_closed()

                    return responses[0] if responses else None

                # Register multiple clients concurrently
                tasks = [register_client(i) for i in range(5)]
                responses = await asyncio.gather(*tasks)

                # Verify all registrations succeeded
                for response in responses:
                    self.assertIsNotNone(response)
                    self.assertEqual(response["type"], "response")
                    self.assertEqual(response["status"], "success")

                # Verify all hosts in database
                all_hosts = host_ops.get_all_hosts()
                hostnames = [host.hostname for host in all_hosts]

                for i in range(5):
                    self.assertIn(f"client-{i}", hostnames)

            finally:
                await server.stop()
                db_manager.cleanup()

        asyncio.run(test_multiple_clients())

    def test_client_reconnection_ip_update(self):
        """Test client reconnection updates IP address."""

        async def test_reconnection():
            from server.database.connection import DatabaseManager
            from server.database.operations import HostOperations
            from server.protocol import MessageProtocol
            from server.tcp_server import TCPServer

            # Initialize database
            db_manager = DatabaseManager(self.server_config)
            db_manager.initialize_schema()
            host_ops = HostOperations(db_manager)

            # Pre-register a host with different IP
            host_ops.create_host("reconnect-test-host", "192.168.1.100")

            # Start server
            config = self.server_config.copy()
            config["server"]["tcp_port"] = 9003
            server = TCPServer(config)
            await server.start()

            try:
                # Connect as existing client (will have 127.0.0.1 IP)
                reader, writer = await asyncio.open_connection("127.0.0.1", 9003)

                protocol = MessageProtocol()
                message = {
                    "version": "1.0",
                    "type": "registration",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "hostname": "reconnect-test-host",
                }

                encoded_message = protocol.encode_message(message)
                writer.write(encoded_message)
                await writer.drain()

                # Read response
                response_data = await reader.read(1024)
                responses = protocol.decode_messages(response_data)

                self.assertGreater(len(responses), 0)
                response = responses[0]
                self.assertEqual(response["status"], "success")

                # Verify IP was updated in database
                host = host_ops.get_host_by_hostname("reconnect-test-host")
                self.assertEqual(host.current_ip, "127.0.0.1")  # Updated to new IP

                writer.close()
                await writer.wait_closed()

            finally:
                await server.stop()
                db_manager.cleanup()

        asyncio.run(test_reconnection())

    def test_invalid_message_handling(self):
        """Test server handles invalid messages gracefully."""

        async def test_invalid_messages():
            from server.protocol import MessageProtocol
            from server.tcp_server import TCPServer

            config = self.server_config.copy()
            config["server"]["tcp_port"] = 9004
            server = TCPServer(config)
            await server.start()

            try:
                # Test cases for invalid messages
                test_cases = [
                    b"invalid_data_no_length_prefix",
                    struct.pack("!I", 100) + b"short_data",  # Length mismatch
                    struct.pack("!I", 15) + b'{"invalid": json}',  # Invalid JSON
                    struct.pack("!I", 25) + b'{"version": "unsupported"}',  # Invalid version
                ]

                for invalid_data in test_cases:
                    with self.subTest(data=invalid_data[:20]):
                        reader, writer = await asyncio.open_connection("127.0.0.1", 9004)

                        # Send invalid data
                        writer.write(invalid_data)
                        await writer.drain()

                        # Try to read response (may get error response or connection close)
                        try:
                            response_data = await asyncio.wait_for(reader.read(1024), timeout=1.0)

                            if response_data:
                                protocol = MessageProtocol()
                                responses = protocol.decode_messages(response_data)
                                if responses:
                                    response = responses[0]
                                    # Should get error response
                                    self.assertEqual(response.get("status"), "error")
                        except asyncio.TimeoutError:
                            # Connection might be closed by server
                            pass

                        writer.close()
                        await writer.wait_closed()

                        # Server should still be running
                        self.assertTrue(server.is_running())

            finally:
                await server.stop()

        asyncio.run(test_invalid_messages())

    def test_server_performance_under_load(self):
        """Test server performance with many concurrent connections."""

        async def test_performance():
            from server.database.connection import DatabaseManager
            from server.protocol import MessageProtocol
            from server.tcp_server import TCPServer

            # Initialize database
            db_manager = DatabaseManager(self.server_config)
            db_manager.initialize_schema()

            config = self.server_config.copy()
            config["server"]["tcp_port"] = 9005
            config["server"]["max_connections"] = 50
            server = TCPServer(config)
            await server.start()

            try:

                async def rapid_client(client_id):
                    """Rapid client connection and registration."""
                    start_time = time.time()

                    reader, writer = await asyncio.open_connection("127.0.0.1", 9005)

                    protocol = MessageProtocol()
                    message = {
                        "version": "1.0",
                        "type": "registration",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "hostname": f"perf-client-{client_id}",
                    }

                    encoded_message = protocol.encode_message(message)
                    writer.write(encoded_message)
                    await writer.drain()

                    response_data = await reader.read(1024)
                    writer.close()
                    await writer.wait_closed()

                    return time.time() - start_time

                # Create many concurrent clients
                start_time = time.time()
                tasks = [rapid_client(i) for i in range(20)]
                processing_times = await asyncio.gather(*tasks)
                total_time = time.time() - start_time

                # Performance assertions
                avg_processing_time = sum(processing_times) / len(processing_times)
                self.assertLess(avg_processing_time, 0.1)  # <100ms per message
                self.assertLess(total_time, 5.0)  # <5s total for 20 clients

                # Verify server stats
                stats = server.get_stats()
                self.assertGreaterEqual(stats["connections"]["total_connections"], 20)

            finally:
                await server.stop()
                db_manager.cleanup()

        asyncio.run(test_performance())

    def test_server_graceful_shutdown_with_active_connections(self):
        """Test server graceful shutdown with active connections."""

        async def test_graceful_shutdown():
            from server.database.connection import DatabaseManager
            from server.tcp_server import TCPServer

            # Initialize database
            db_manager = DatabaseManager(self.server_config)
            db_manager.initialize_schema()

            config = self.server_config.copy()
            config["server"]["tcp_port"] = 9006
            server = TCPServer(config)
            await server.start()

            # Create active connections
            connections = []
            for i in range(3):
                reader, writer = await asyncio.open_connection("127.0.0.1", 9006)
                connections.append((reader, writer))

            # Allow connections to be established
            await asyncio.sleep(0.1)

            # Verify connections are active
            self.assertGreater(server.get_active_connections(), 0)

            # Graceful shutdown
            shutdown_start = time.time()
            await server.stop(graceful=True)
            shutdown_time = time.time() - shutdown_start

            # Verify shutdown completed reasonably quickly (CI environments can be slow)
            self.assertLess(shutdown_time, 35.0)

            # Verify server is stopped
            self.assertFalse(server.is_running())

            # Clean up connections
            for reader, writer in connections:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass  # May already be closed

            db_manager.cleanup()

        asyncio.run(test_graceful_shutdown())

    def test_database_integration_error_handling(self):
        """Test server handles database errors gracefully."""

        async def test_db_error_handling():
            import logging
            from server.protocol import MessageProtocol
            from server.tcp_server import TCPServer

            # Temporarily suppress excessive error logging for this test
            connection_logger = logging.getLogger("server.connection_handler")
            tcp_logger = logging.getLogger("server.tcp_server")
            original_level = connection_logger.level
            tcp_original_level = tcp_logger.level
            connection_logger.setLevel(logging.CRITICAL)
            tcp_logger.setLevel(logging.CRITICAL)

            # Use invalid database path to simulate database errors
            bad_config = self.server_config.copy()
            bad_config["server"]["tcp_port"] = 9007
            bad_config["database"]["path"] = "/invalid/path/database.db"

            # Server should start even with database issues (graceful degradation)
            server = TCPServer(bad_config)

            try:
                await server.start()

                # Connect as client
                reader, writer = await asyncio.open_connection("127.0.0.1", 9007)

                # Send registration message
                protocol = MessageProtocol()
                message = {
                    "version": "1.0",
                    "type": "registration",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "hostname": "db-error-test-host",
                }

                encoded_message = protocol.encode_message(message)
                writer.write(encoded_message)
                await writer.drain()

                # Should get error response due to database issues
                response_data = await reader.read(1024)
                responses = protocol.decode_messages(response_data)

                if responses:
                    response = responses[0]
                    self.assertEqual(response["type"], "response")
                    self.assertEqual(response["status"], "error")
                    self.assertIn("database", response["message"].lower())

                writer.close()
                await writer.wait_closed()

            finally:
                await server.stop()
                # Restore original logging levels
                connection_logger.setLevel(original_level)
                tcp_logger.setLevel(tcp_original_level)

        asyncio.run(test_db_error_handling())


class TestTCPServerStressTest(unittest.TestCase):
    """Stress tests for TCP server under high load."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name

        self.server_config = {
            "server": {"tcp_port": 9100, "host": "127.0.0.1", "max_connections": 200},
            "database": {"path": self.db_path, "connection_pool_size": 50},
        }

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_high_volume_concurrent_registrations(self):
        """Test server handles high volume of concurrent registrations."""

        async def test_high_volume():
            from server.database.connection import DatabaseManager
            from server.database.operations import HostOperations
            from server.protocol import MessageProtocol
            from server.tcp_server import TCPServer

            # Initialize database
            db_manager = DatabaseManager(self.server_config)
            db_manager.initialize_schema()
            host_ops = HostOperations(db_manager)

            server = TCPServer(self.server_config)
            await server.start()

            try:

                async def burst_client(client_id):
                    """High-speed client registration."""
                    reader, writer = await asyncio.open_connection("127.0.0.1", 9100)

                    protocol = MessageProtocol()
                    message = {
                        "version": "1.0",
                        "type": "registration",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "hostname": f"burst-client-{client_id}",
                    }

                    encoded_message = protocol.encode_message(message)
                    writer.write(encoded_message)
                    await writer.drain()

                    response_data = await reader.read(1024)
                    writer.close()
                    await writer.wait_closed()

                    return client_id

                # Launch high volume of concurrent clients
                start_time = time.time()
                tasks = [burst_client(i) for i in range(100)]
                completed_clients = await asyncio.gather(*tasks, return_exceptions=True)
                total_time = time.time() - start_time

                # Count successful registrations
                successful = sum(1 for result in completed_clients if isinstance(result, int))

                # Performance requirements
                self.assertGreater(successful, 90)  # >90% success rate
                self.assertLess(total_time, 10.0)  # <10s for 100 clients

                # Verify database consistency
                all_hosts = host_ops.get_all_hosts()
                self.assertGreater(len(all_hosts), 90)

            finally:
                await server.stop()
                db_manager.cleanup()

        asyncio.run(test_high_volume())

    def test_memory_usage_under_load(self):
        """Test server memory usage remains stable under load."""

        async def test_memory_usage():
            import os

            import psutil

            from server.database.connection import DatabaseManager
            from server.tcp_server import TCPServer

            # Initialize database
            db_manager = DatabaseManager(self.server_config)
            db_manager.initialize_schema()

            config = self.server_config.copy()
            config["server"]["tcp_port"] = 9101
            server = TCPServer(config)
            await server.start()

            try:
                # Get initial memory usage
                process = psutil.Process(os.getpid())
                initial_memory = process.memory_info().rss / 1024 / 1024  # MB

                # Create sustained load
                for round in range(5):

                    async def memory_test_client(client_id):
                        reader, writer = await asyncio.open_connection("127.0.0.1", 9101)
                        await asyncio.sleep(0.1)  # Hold connection briefly
                        writer.close()
                        await writer.wait_closed()

                    # Create batch of connections
                    tasks = [memory_test_client(i) for i in range(20)]
                    await asyncio.gather(*tasks)

                    # Check memory after each round
                    current_memory = process.memory_info().rss / 1024 / 1024
                    memory_growth = current_memory - initial_memory

                    # Memory growth should be reasonable (< 50MB)
                    self.assertLess(memory_growth, 50)

            finally:
                await server.stop()
                db_manager.cleanup()

        asyncio.run(test_memory_usage())


if __name__ == "__main__":
    unittest.main()
