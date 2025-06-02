#!/usr/bin/env python3
"""
Tests for IP Change Tracker (SCRUM-15)
Test-driven development for IP change detection and logging.
"""

import unittest
import asyncio
import tempfile
import os
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch


class TestIPTracker(unittest.TestCase):
    """Test IP change tracking functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        self.tracker_config = {
            'database': {
                'path': self.db_path,
                'connection_pool_size': 20
            },
            'ip_tracking': {
                'enable_change_logging': True,
                'max_history_entries': 1000,
                'cleanup_history_after_days': 90
            }
        }

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_ip_tracker_class_exists(self):
        """Test that IPTracker class exists."""
        try:
            from server.ip_tracker import IPTracker
            self.assertTrue(callable(IPTracker))
        except ImportError:
            self.fail("IPTracker should be importable from server.ip_tracker")

    def test_ip_tracker_initialization(self):
        """Test IP tracker initialization."""
        from server.ip_tracker import IPTracker
        
        tracker = IPTracker(self.tracker_config)
        
        self.assertIsNotNone(tracker)
        self.assertTrue(hasattr(tracker, 'config'))
        self.assertTrue(hasattr(tracker, 'db_manager'))

    def test_detect_ip_change_new_host(self):
        """Test detecting IP change for new host."""
        async def test_new_host():
            from server.ip_tracker import IPTracker
            
            tracker = IPTracker(self.tracker_config)
            
            # New host should not have IP change
            change = await tracker.detect_ip_change(
                hostname="new-host",
                new_ip="192.168.1.100"
            )
            
            self.assertIsNone(change)

        asyncio.run(test_new_host())

    def test_detect_ip_change_same_ip(self):
        """Test detecting IP change when IP is the same."""
        async def test_same_ip():
            from server.ip_tracker import IPTracker
            from server.database.connection import DatabaseManager
            from server.database.operations import HostOperations
            
            tracker = IPTracker(self.tracker_config)
            
            # Create host first
            db_manager = DatabaseManager(self.tracker_config)
            db_manager.initialize_schema()
            host_ops = HostOperations(db_manager)
            host_ops.create_host("same-ip-host", "192.168.1.100")
            
            # Check same IP - should not detect change
            change = await tracker.detect_ip_change(
                hostname="same-ip-host",
                new_ip="192.168.1.100"
            )
            
            self.assertIsNone(change)
            
            db_manager.cleanup()

        asyncio.run(test_same_ip())

    def test_detect_ip_change_different_ip(self):
        """Test detecting IP change when IP is different."""
        async def test_different_ip():
            from server.ip_tracker import IPTracker
            from server.database.connection import DatabaseManager
            from server.database.operations import HostOperations
            
            tracker = IPTracker(self.tracker_config)
            
            # Create host first
            db_manager = DatabaseManager(self.tracker_config)
            db_manager.initialize_schema()
            host_ops = HostOperations(db_manager)
            host_ops.create_host("change-ip-host", "192.168.1.100")
            
            # Check different IP - should detect change
            change = await tracker.detect_ip_change(
                hostname="change-ip-host",
                new_ip="192.168.1.200"
            )
            
            self.assertIsNotNone(change)
            self.assertEqual(change.hostname, "change-ip-host")
            self.assertEqual(change.previous_ip, "192.168.1.100")
            self.assertEqual(change.new_ip, "192.168.1.200")
            
            db_manager.cleanup()

        asyncio.run(test_different_ip())

    def test_log_ip_change(self):
        """Test logging IP change events."""
        async def test_log_change():
            from server.ip_tracker import IPTracker
            
            tracker = IPTracker(self.tracker_config)
            
            # Log IP change
            await tracker.log_ip_change(
                hostname="log-test-host",
                previous_ip="192.168.1.100",
                new_ip="192.168.1.200",
                change_reason="client_registration"
            )
            
            # Verify log entry was created
            history = await tracker.get_ip_change_history("log-test-host")
            
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0].hostname, "log-test-host")
            self.assertEqual(history[0].previous_ip, "192.168.1.100")
            self.assertEqual(history[0].new_ip, "192.168.1.200")
            self.assertEqual(history[0].change_reason, "client_registration")

        asyncio.run(test_log_change())

    def test_get_ip_change_history_empty(self):
        """Test getting IP change history for host with no changes."""
        async def test_empty_history():
            from server.ip_tracker import IPTracker
            
            tracker = IPTracker(self.tracker_config)
            
            history = await tracker.get_ip_change_history("nonexistent-host")
            
            self.assertEqual(len(history), 0)

        asyncio.run(test_empty_history())

    def test_get_ip_change_history_multiple(self):
        """Test getting IP change history with multiple entries."""
        async def test_multiple_history():
            from server.ip_tracker import IPTracker
            
            tracker = IPTracker(self.tracker_config)
            
            # Log multiple IP changes
            await tracker.log_ip_change(
                hostname="multi-change-host",
                previous_ip="192.168.1.100",
                new_ip="192.168.1.200",
                change_reason="registration"
            )
            
            await tracker.log_ip_change(
                hostname="multi-change-host",
                previous_ip="192.168.1.200",
                new_ip="192.168.1.300",
                change_reason="registration"
            )
            
            # Get history
            history = await tracker.get_ip_change_history("multi-change-host")
            
            self.assertEqual(len(history), 2)
            # Should be ordered by timestamp (most recent first)
            self.assertEqual(history[0].new_ip, "192.168.1.300")
            self.assertEqual(history[1].new_ip, "192.168.1.200")

        asyncio.run(test_multiple_history())

    def test_get_ip_change_history_with_limit(self):
        """Test getting IP change history with limit."""
        async def test_history_limit():
            from server.ip_tracker import IPTracker
            
            tracker = IPTracker(self.tracker_config)
            
            # Log multiple IP changes
            for i in range(5):
                await tracker.log_ip_change(
                    hostname="limit-test-host",
                    previous_ip=f"192.168.1.{100 + i}",
                    new_ip=f"192.168.1.{101 + i}",
                    change_reason="test"
                )
            
            # Get limited history
            history = await tracker.get_ip_change_history("limit-test-host", limit=3)
            
            self.assertEqual(len(history), 3)

        asyncio.run(test_history_limit())

    def test_get_recent_ip_changes(self):
        """Test getting recent IP changes across all hosts."""
        async def test_recent_changes():
            from server.ip_tracker import IPTracker
            
            tracker = IPTracker(self.tracker_config)
            
            # Log changes for different hosts
            await tracker.log_ip_change(
                hostname="host-1",
                previous_ip="192.168.1.100",
                new_ip="192.168.1.200",
                change_reason="registration"
            )
            
            await tracker.log_ip_change(
                hostname="host-2",
                previous_ip="192.168.1.101",
                new_ip="192.168.1.201",
                change_reason="registration"
            )
            
            # Get recent changes
            recent_changes = await tracker.get_recent_ip_changes(limit=10)
            
            self.assertGreaterEqual(len(recent_changes), 2)
            
            # Check that both hosts are represented
            hostnames = [change.hostname for change in recent_changes]
            self.assertIn("host-1", hostnames)
            self.assertIn("host-2", hostnames)

        asyncio.run(test_recent_changes())

    def test_get_ip_change_statistics(self):
        """Test getting IP change statistics."""
        async def test_statistics():
            from server.ip_tracker import IPTracker
            
            tracker = IPTracker(self.tracker_config)
            
            # Log some changes
            await tracker.log_ip_change(
                hostname="stats-host-1",
                previous_ip="192.168.1.100",
                new_ip="192.168.1.200",
                change_reason="registration"
            )
            
            await tracker.log_ip_change(
                hostname="stats-host-2",
                previous_ip="192.168.1.101",
                new_ip="192.168.1.201",
                change_reason="reconnection"
            )
            
            # Get statistics
            stats = await tracker.get_ip_change_statistics()
            
            self.assertGreaterEqual(stats['total_changes_logged'], 2)
            self.assertGreaterEqual(stats['unique_hosts'], 2)
            self.assertIn('changes_by_reason', stats)

        asyncio.run(test_statistics())

    def test_cleanup_old_ip_changes(self):
        """Test cleaning up old IP change records."""
        async def test_cleanup():
            from server.ip_tracker import IPTracker
            
            tracker = IPTracker(self.tracker_config)
            
            # This test would require manipulating timestamps
            # For now, just test that the method exists and runs
            cleaned_count = await tracker.cleanup_old_ip_changes(older_than_days=90)
            
            self.assertIsInstance(cleaned_count, int)
            self.assertGreaterEqual(cleaned_count, 0)

        asyncio.run(test_cleanup())

    def test_validate_ip_address(self):
        """Test IP address validation."""
        from server.ip_tracker import IPTracker
        
        tracker = IPTracker(self.tracker_config)
        
        # Valid IPv4 addresses
        self.assertTrue(tracker.validate_ip_address("192.168.1.1"))
        self.assertTrue(tracker.validate_ip_address("10.0.0.1"))
        self.assertTrue(tracker.validate_ip_address("255.255.255.255"))
        
        # Valid IPv6 addresses
        self.assertTrue(tracker.validate_ip_address("::1"))
        self.assertTrue(tracker.validate_ip_address("2001:db8::1"))
        
        # Invalid addresses
        self.assertFalse(tracker.validate_ip_address("192.168.1.256"))
        self.assertFalse(tracker.validate_ip_address("invalid.ip"))
        self.assertFalse(tracker.validate_ip_address(""))


class TestIPChangeEvent(unittest.TestCase):
    """Test IP change event data structure."""

    def test_ip_change_event_class_exists(self):
        """Test that IPChangeEvent class exists."""
        try:
            from server.ip_tracker import IPChangeEvent
            self.assertTrue(callable(IPChangeEvent))
        except ImportError:
            self.fail("IPChangeEvent should be importable from server.ip_tracker")

    def test_ip_change_event_creation(self):
        """Test creating IP change event instances."""
        from server.ip_tracker import IPChangeEvent
        
        now = datetime.now(timezone.utc)
        
        event = IPChangeEvent(
            hostname="test-host",
            previous_ip="192.168.1.100",
            new_ip="192.168.1.200",
            change_time=now,
            change_reason="registration"
        )
        
        self.assertEqual(event.hostname, "test-host")
        self.assertEqual(event.previous_ip, "192.168.1.100")
        self.assertEqual(event.new_ip, "192.168.1.200")
        self.assertEqual(event.change_time, now)
        self.assertEqual(event.change_reason, "registration")

    def test_ip_change_event_to_dict(self):
        """Test converting IP change event to dictionary."""
        from server.ip_tracker import IPChangeEvent
        
        now = datetime.now(timezone.utc)
        
        event = IPChangeEvent(
            hostname="test-host",
            previous_ip="192.168.1.100",
            new_ip="192.168.1.200",
            change_time=now,
            change_reason="registration"
        )
        
        event_dict = event.to_dict()
        
        self.assertIsInstance(event_dict, dict)
        self.assertEqual(event_dict['hostname'], "test-host")
        self.assertEqual(event_dict['previous_ip'], "192.168.1.100")
        self.assertEqual(event_dict['new_ip'], "192.168.1.200")
        self.assertEqual(event_dict['change_reason'], "registration")


class TestIPChangeDetection(unittest.TestCase):
    """Test IP change detection data structure."""

    def test_ip_change_detection_class_exists(self):
        """Test that IPChangeDetection class exists."""
        try:
            from server.ip_tracker import IPChangeDetection
            self.assertTrue(callable(IPChangeDetection))
        except ImportError:
            self.fail("IPChangeDetection should be importable from server.ip_tracker")

    def test_ip_change_detection_creation(self):
        """Test creating IP change detection instances."""
        from server.ip_tracker import IPChangeDetection
        
        now = datetime.now(timezone.utc)
        
        detection = IPChangeDetection(
            hostname="test-host",
            previous_ip="192.168.1.100",
            new_ip="192.168.1.200",
            detected_at=now
        )
        
        self.assertEqual(detection.hostname, "test-host")
        self.assertEqual(detection.previous_ip, "192.168.1.100")
        self.assertEqual(detection.new_ip, "192.168.1.200")
        self.assertEqual(detection.detected_at, now)

    def test_ip_change_detection_is_valid_change(self):
        """Test checking if IP change is valid."""
        from server.ip_tracker import IPChangeDetection
        
        now = datetime.now(timezone.utc)
        
        # Valid change
        detection = IPChangeDetection(
            hostname="test-host",
            previous_ip="192.168.1.100",
            new_ip="192.168.1.200",
            detected_at=now
        )
        
        self.assertTrue(detection.is_valid_change())
        
        # Invalid change (same IP)
        invalid_detection = IPChangeDetection(
            hostname="test-host",
            previous_ip="192.168.1.100",
            new_ip="192.168.1.100",
            detected_at=now
        )
        
        self.assertFalse(invalid_detection.is_valid_change())


if __name__ == "__main__":
    unittest.main()