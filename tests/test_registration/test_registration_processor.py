#!/usr/bin/env python3
"""
Tests for Registration Processor (SCRUM-15)
Test-driven development for advanced registration processing logic.
"""

import unittest
import asyncio
import tempfile
import os
import time
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch


class TestRegistrationProcessor(unittest.TestCase):
    """Test registration processor functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        self.processor_config = {
            'database': {
                'path': self.db_path,
                'connection_pool_size': 20
            },
            'registration': {
                'enable_ip_tracking': True,
                'enable_event_logging': True,
                'max_registrations_per_minute': 1000,
                'duplicate_registration_window': 0  # Disable for testing
            }
        }

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_registration_processor_class_exists(self):
        """Test that RegistrationProcessor class exists."""
        try:
            from server.registration_processor import RegistrationProcessor
            self.assertTrue(callable(RegistrationProcessor))
        except ImportError:
            self.fail("RegistrationProcessor should be importable from server.registration_processor")

    def test_registration_processor_initialization(self):
        """Test registration processor initialization."""
        from server.registration_processor import RegistrationProcessor
        
        processor = RegistrationProcessor(self.processor_config)
        
        self.assertIsNotNone(processor)
        self.assertTrue(hasattr(processor, 'config'))
        self.assertTrue(hasattr(processor, 'db_manager'))

    def test_process_new_host_registration(self):
        """Test processing new host registration."""
        async def test_new_host():
            from server.registration_processor import RegistrationProcessor
            
            processor = RegistrationProcessor(self.processor_config)
            
            # Process new host registration
            result = await processor.process_registration(
                hostname="new-test-host",
                client_ip="192.168.1.100",
                message_timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            self.assertTrue(result.success)
            self.assertEqual(result.result_type, "new_registration")
            self.assertIn("new host registered", result.message.lower())
            self.assertEqual(result.hostname, "new-test-host")
            self.assertEqual(result.ip_address, "192.168.1.100")

        asyncio.run(test_new_host())

    def test_process_existing_host_same_ip(self):
        """Test processing existing host with same IP (heartbeat)."""
        async def test_heartbeat():
            from server.registration_processor import RegistrationProcessor
            
            processor = RegistrationProcessor(self.processor_config)
            
            # First registration
            await processor.process_registration(
                hostname="heartbeat-host",
                client_ip="192.168.1.200",
                message_timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            # Second registration with same IP (heartbeat)
            result = await processor.process_registration(
                hostname="heartbeat-host",
                client_ip="192.168.1.200",
                message_timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            self.assertTrue(result.success)
            self.assertEqual(result.result_type, "heartbeat_update")
            self.assertIn("heartbeat updated", result.message.lower())

        asyncio.run(test_heartbeat())

    def test_process_existing_host_ip_change(self):
        """Test processing existing host with IP change."""
        async def test_ip_change():
            from server.registration_processor import RegistrationProcessor
            
            processor = RegistrationProcessor(self.processor_config)
            
            # First registration
            await processor.process_registration(
                hostname="ip-change-host",
                client_ip="192.168.1.100",
                message_timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            # Second registration with different IP
            result = await processor.process_registration(
                hostname="ip-change-host",
                client_ip="192.168.1.200",
                message_timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            self.assertTrue(result.success)
            self.assertEqual(result.result_type, "ip_change")
            self.assertIn("ip changed", result.message.lower())
            self.assertEqual(result.previous_ip, "192.168.1.100")
            self.assertEqual(result.ip_address, "192.168.1.200")

        asyncio.run(test_ip_change())

    def test_process_offline_host_reconnection(self):
        """Test processing offline host coming back online."""
        async def test_reconnection():
            from server.registration_processor import RegistrationProcessor
            from server.database.connection import DatabaseManager
            from server.database.operations import HostOperations
            
            processor = RegistrationProcessor(self.processor_config)
            
            # Create host and mark offline
            db_manager = DatabaseManager(self.processor_config)
            db_manager.initialize_schema()
            host_ops = HostOperations(db_manager)
            
            host = host_ops.create_host("reconnect-host", "192.168.1.100")
            host_ops.mark_host_offline("reconnect-host")
            
            # Process reconnection
            result = await processor.process_registration(
                hostname="reconnect-host",
                client_ip="192.168.1.100",
                message_timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            self.assertTrue(result.success)
            self.assertEqual(result.result_type, "reconnection")
            self.assertIn("reconnected", result.message.lower())
            
            db_manager.cleanup()

        asyncio.run(test_reconnection())

    def test_process_invalid_hostname(self):
        """Test processing registration with invalid hostname."""
        async def test_invalid_hostname():
            from server.registration_processor import RegistrationProcessor
            
            processor = RegistrationProcessor(self.processor_config)
            
            # Process registration with invalid hostname
            result = await processor.process_registration(
                hostname="",  # Invalid empty hostname
                client_ip="192.168.1.100",
                message_timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            self.assertFalse(result.success)
            self.assertEqual(result.result_type, "validation_error")
            self.assertIn("invalid hostname", result.message.lower())

        asyncio.run(test_invalid_hostname())

    def test_process_invalid_ip_address(self):
        """Test processing registration with invalid IP address."""
        async def test_invalid_ip():
            from server.registration_processor import RegistrationProcessor
            
            processor = RegistrationProcessor(self.processor_config)
            
            # Process registration with invalid IP
            result = await processor.process_registration(
                hostname="test-host",
                client_ip="invalid.ip.address",
                message_timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            self.assertFalse(result.success)
            self.assertEqual(result.result_type, "validation_error")
            self.assertIn("invalid ip", result.message.lower())

        asyncio.run(test_invalid_ip())

    def test_registration_result_structure(self):
        """Test registration result structure and fields."""
        async def test_result_structure():
            from server.registration_processor import RegistrationProcessor
            
            processor = RegistrationProcessor(self.processor_config)
            
            result = await processor.process_registration(
                hostname="structure-test-host",
                client_ip="192.168.1.100",
                message_timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            # Check required fields
            self.assertTrue(hasattr(result, 'success'))
            self.assertTrue(hasattr(result, 'result_type'))
            self.assertTrue(hasattr(result, 'message'))
            self.assertTrue(hasattr(result, 'hostname'))
            self.assertTrue(hasattr(result, 'ip_address'))
            self.assertTrue(hasattr(result, 'timestamp'))
            
            # Check field types
            self.assertIsInstance(result.success, bool)
            self.assertIsInstance(result.result_type, str)
            self.assertIsInstance(result.message, str)
            self.assertIsInstance(result.hostname, str)
            self.assertIsInstance(result.ip_address, str)

        asyncio.run(test_result_structure())

    def test_duplicate_registration_detection(self):
        """Test detection of duplicate registrations within time window."""
        async def test_duplicate_detection():
            from server.registration_processor import RegistrationProcessor
            
            processor = RegistrationProcessor(self.processor_config)
            
            # First registration
            result1 = await processor.process_registration(
                hostname="duplicate-test-host",
                client_ip="192.168.1.100",
                message_timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            # Immediate duplicate registration
            result2 = await processor.process_registration(
                hostname="duplicate-test-host",
                client_ip="192.168.1.100",
                message_timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            self.assertTrue(result1.success)
            self.assertTrue(result2.success)
            self.assertEqual(result2.result_type, "duplicate_ignored")

        asyncio.run(test_duplicate_detection())

    def test_concurrent_registrations(self):
        """Test concurrent registration processing."""
        async def test_concurrent():
            from server.registration_processor import RegistrationProcessor
            
            processor = RegistrationProcessor(self.processor_config)
            
            async def register_host(host_id):
                return await processor.process_registration(
                    hostname=f"concurrent-host-{host_id}",
                    client_ip=f"192.168.1.{100 + host_id}",
                    message_timestamp=datetime.now(timezone.utc).isoformat()
                )
            
            # Process multiple registrations concurrently
            tasks = [register_host(i) for i in range(10)]
            results = await asyncio.gather(*tasks)
            
            # All should succeed
            for result in results:
                self.assertTrue(result.success)
                self.assertEqual(result.result_type, "new_registration")

        asyncio.run(test_concurrent())

    def test_registration_statistics(self):
        """Test registration statistics tracking."""
        async def test_statistics():
            from server.registration_processor import RegistrationProcessor
            
            processor = RegistrationProcessor(self.processor_config)
            
            # Process several registrations
            await processor.process_registration(
                hostname="stats-host-1",
                client_ip="192.168.1.100",
                message_timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            await processor.process_registration(
                hostname="stats-host-1",
                client_ip="192.168.1.200",  # IP change
                message_timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            await processor.process_registration(
                hostname="stats-host-2",
                client_ip="192.168.1.101",
                message_timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            # Get statistics
            stats = processor.get_registration_stats()
            
            self.assertGreaterEqual(stats['total_registrations'], 3)
            self.assertGreaterEqual(stats['new_registrations'], 2)
            self.assertGreaterEqual(stats['ip_changes'], 1)

        asyncio.run(test_statistics())


class TestRegistrationResult(unittest.TestCase):
    """Test registration result data structure."""

    def test_registration_result_class_exists(self):
        """Test that RegistrationResult class exists."""
        try:
            from server.registration_processor import RegistrationResult
            self.assertTrue(callable(RegistrationResult))
        except ImportError:
            self.fail("RegistrationResult should be importable from server.registration_processor")

    def test_registration_result_creation(self):
        """Test creating registration result instances."""
        from server.registration_processor import RegistrationResult
        
        result = RegistrationResult(
            success=True,
            result_type="new_registration",
            message="New host registered successfully",
            hostname="test-host",
            ip_address="192.168.1.100"
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.result_type, "new_registration")
        self.assertEqual(result.message, "New host registered successfully")
        self.assertEqual(result.hostname, "test-host")
        self.assertEqual(result.ip_address, "192.168.1.100")

    def test_registration_result_to_dict(self):
        """Test converting registration result to dictionary."""
        from server.registration_processor import RegistrationResult
        
        result = RegistrationResult(
            success=True,
            result_type="ip_change",
            message="IP address changed",
            hostname="test-host",
            ip_address="192.168.1.200",
            previous_ip="192.168.1.100"
        )
        
        result_dict = result.to_dict()
        
        self.assertIsInstance(result_dict, dict)
        self.assertEqual(result_dict['success'], True)
        self.assertEqual(result_dict['result_type'], "ip_change")
        self.assertEqual(result_dict['hostname'], "test-host")
        self.assertEqual(result_dict['ip_address'], "192.168.1.200")
        self.assertEqual(result_dict['previous_ip'], "192.168.1.100")

    def test_registration_result_json_serialization(self):
        """Test JSON serialization of registration result."""
        from server.registration_processor import RegistrationResult
        import json
        
        result = RegistrationResult(
            success=True,
            result_type="heartbeat_update",
            message="Heartbeat updated",
            hostname="test-host",
            ip_address="192.168.1.100"
        )
        
        json_str = result.to_json()
        parsed = json.loads(json_str)
        
        self.assertEqual(parsed['success'], True)
        self.assertEqual(parsed['result_type'], "heartbeat_update")
        self.assertEqual(parsed['hostname'], "test-host")


class TestRegistrationConfig(unittest.TestCase):
    """Test registration processor configuration."""

    def test_registration_config_class_exists(self):
        """Test that RegistrationConfig class exists."""
        try:
            from server.registration_processor import RegistrationConfig
            self.assertTrue(callable(RegistrationConfig))
        except ImportError:
            self.fail("RegistrationConfig should be importable from server.registration_processor")

    def test_registration_config_initialization(self):
        """Test registration config initialization."""
        from server.registration_processor import RegistrationConfig
        
        config_dict = {
            'registration': {
                'enable_ip_tracking': True,
                'enable_event_logging': True,
                'max_registrations_per_minute': 500,
                'duplicate_registration_window': 10
            }
        }
        
        config = RegistrationConfig(config_dict)
        
        self.assertTrue(config.enable_ip_tracking)
        self.assertTrue(config.enable_event_logging)
        self.assertEqual(config.max_registrations_per_minute, 500)
        self.assertEqual(config.duplicate_registration_window, 10)

    def test_registration_config_defaults(self):
        """Test registration config default values."""
        from server.registration_processor import RegistrationConfig
        
        config = RegistrationConfig({})
        
        # Should have reasonable defaults
        self.assertIsInstance(config.enable_ip_tracking, bool)
        self.assertIsInstance(config.enable_event_logging, bool)
        self.assertIsInstance(config.max_registrations_per_minute, int)
        self.assertIsInstance(config.duplicate_registration_window, int)

    def test_registration_config_validation(self):
        """Test registration config validation."""
        from server.registration_processor import RegistrationConfig, RegistrationConfigError
        
        # Invalid configuration
        invalid_config = {
            'registration': {
                'max_registrations_per_minute': -1  # Invalid negative value
            }
        }
        
        with self.assertRaises(RegistrationConfigError):
            RegistrationConfig(invalid_config)


if __name__ == "__main__":
    unittest.main()