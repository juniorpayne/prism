#!/usr/bin/env python3
"""
Tests for Heartbeat Monitor (SCRUM-16)
Test-driven development for heartbeat monitoring and timeout detection.
"""

import unittest
import asyncio
import tempfile
import os
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch


class TestHeartbeatMonitor(unittest.TestCase):
    """Test heartbeat monitor functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name

        self.monitor_config = {
            "database": {"path": self.db_path, "connection_pool_size": 20},
            "heartbeat": {
                "check_interval": 30,
                "timeout_multiplier": 2,
                "grace_period": 30,
                "max_hosts_per_check": 1000,
                "cleanup_offline_after_days": 30,
            },
        }

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_heartbeat_monitor_class_exists(self):
        """Test that HeartbeatMonitor class exists."""
        try:
            from server.heartbeat_monitor import HeartbeatMonitor

            self.assertTrue(callable(HeartbeatMonitor))
        except ImportError:
            self.fail("HeartbeatMonitor should be importable from server.heartbeat_monitor")

    def test_heartbeat_monitor_initialization(self):
        """Test heartbeat monitor initialization."""
        from server.heartbeat_monitor import HeartbeatMonitor

        monitor = HeartbeatMonitor(self.monitor_config)

        self.assertIsNotNone(monitor)
        self.assertTrue(hasattr(monitor, "config"))
        self.assertTrue(hasattr(monitor, "db_manager"))

    def test_calculate_timeout_threshold(self):
        """Test timeout threshold calculation."""
        from server.heartbeat_monitor import HeartbeatMonitor

        monitor = HeartbeatMonitor(self.monitor_config)

        # Test default calculation: (heartbeat_interval * 2) + grace_period
        # Default client heartbeat is usually 60s
        threshold = monitor.calculate_timeout_threshold(heartbeat_interval=60, grace_period=30)

        # Should be 60 * 2 + 30 = 150 seconds
        expected_timeout = 60 * 2 + 30
        self.assertEqual(threshold, expected_timeout)

    def test_calculate_timeout_threshold_custom_multiplier(self):
        """Test timeout threshold with custom multiplier."""
        from server.heartbeat_monitor import HeartbeatMonitor

        # Custom config with different multiplier
        custom_config = self.monitor_config.copy()
        custom_config["heartbeat"]["timeout_multiplier"] = 3

        monitor = HeartbeatMonitor(custom_config)

        threshold = monitor.calculate_timeout_threshold(heartbeat_interval=60, grace_period=30)

        # Should be 60 * 3 + 30 = 210 seconds
        expected_timeout = 60 * 3 + 30
        self.assertEqual(threshold, expected_timeout)

    def test_check_host_timeouts_no_hosts(self):
        """Test timeout check with no hosts."""

        async def test_no_hosts():
            from server.heartbeat_monitor import HeartbeatMonitor

            monitor = HeartbeatMonitor(self.monitor_config)

            # Check timeouts with empty database
            timeout_results = await monitor.check_host_timeouts()

            self.assertEqual(timeout_results.hosts_checked, 0)
            self.assertEqual(timeout_results.hosts_timed_out, 0)
            self.assertEqual(len(timeout_results.timed_out_hosts), 0)

        asyncio.run(test_no_hosts())

    def test_check_host_timeouts_with_recent_hosts(self):
        """Test timeout check with recently active hosts."""

        async def test_recent_hosts():
            from server.heartbeat_monitor import HeartbeatMonitor
            from server.database.connection import DatabaseManager
            from server.database.operations import HostOperations

            monitor = HeartbeatMonitor(self.monitor_config)

            # Create recent host
            db_manager = DatabaseManager(self.monitor_config)
            db_manager.initialize_schema()
            host_ops = HostOperations(db_manager)
            host_ops.create_host("recent-host", "192.168.1.100")

            # Check timeouts - should find no timeouts
            timeout_results = await monitor.check_host_timeouts()

            self.assertEqual(timeout_results.hosts_checked, 1)
            self.assertEqual(timeout_results.hosts_timed_out, 0)

            db_manager.cleanup()

        asyncio.run(test_recent_hosts())

    def test_check_host_timeouts_with_old_hosts(self):
        """Test timeout check with old hosts that should timeout."""

        async def test_old_hosts():
            from server.heartbeat_monitor import HeartbeatMonitor
            from server.database.connection import DatabaseManager
            from server.database.operations import HostOperations
            from server.database.models import Host

            monitor = HeartbeatMonitor(self.monitor_config)

            # Create old host
            db_manager = DatabaseManager(self.monitor_config)
            db_manager.initialize_schema()
            host_ops = HostOperations(db_manager)
            host_ops.create_host("old-host", "192.168.1.100")

            # Manually set old last_seen time
            with host_ops.db_manager.get_session() as session:
                host = session.query(Host).filter(Host.hostname == "old-host").first()
                old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
                host.last_seen = old_time
                session.commit()

            # Check timeouts - should find timeout
            timeout_results = await monitor.check_host_timeouts()

            self.assertEqual(timeout_results.hosts_checked, 1)
            self.assertEqual(timeout_results.hosts_timed_out, 1)
            self.assertEqual(len(timeout_results.timed_out_hosts), 1)
            self.assertEqual(timeout_results.timed_out_hosts[0], "old-host")

            db_manager.cleanup()

        asyncio.run(test_old_hosts())

    def test_mark_hosts_offline(self):
        """Test marking hosts as offline."""

        async def test_mark_offline():
            from server.heartbeat_monitor import HeartbeatMonitor
            from server.database.connection import DatabaseManager
            from server.database.operations import HostOperations

            monitor = HeartbeatMonitor(self.monitor_config)

            # Create host
            db_manager = DatabaseManager(self.monitor_config)
            db_manager.initialize_schema()
            host_ops = HostOperations(db_manager)
            host_ops.create_host("test-host", "192.168.1.100")

            # Mark host offline
            hostnames = ["test-host"]
            result = await monitor.mark_hosts_offline(hostnames, "heartbeat_timeout")

            self.assertTrue(result.success)
            self.assertEqual(result.hosts_processed, 1)
            self.assertEqual(result.hosts_marked_offline, 1)

            # Verify host is offline
            host = host_ops.get_host_by_hostname("test-host")
            self.assertEqual(host.status, "offline")

            db_manager.cleanup()

        asyncio.run(test_mark_offline())

    def test_get_monitoring_statistics(self):
        """Test getting monitoring statistics."""

        async def test_statistics():
            from server.heartbeat_monitor import HeartbeatMonitor

            monitor = HeartbeatMonitor(self.monitor_config)

            # Get initial statistics
            stats = await monitor.get_monitoring_statistics()

            self.assertIn("total_checks_performed", stats)
            self.assertIn("total_hosts_timed_out", stats)
            self.assertIn("total_status_changes", stats)
            self.assertIn("last_check_time", stats)
            self.assertIn("average_check_duration", stats)

        asyncio.run(test_statistics())

    def test_get_hosts_by_last_seen(self):
        """Test getting hosts filtered by last seen time."""

        async def test_last_seen_filter():
            from server.heartbeat_monitor import HeartbeatMonitor
            from server.database.connection import DatabaseManager
            from server.database.operations import HostOperations
            from server.database.models import Host

            monitor = HeartbeatMonitor(self.monitor_config)

            # Create hosts with different last_seen times
            db_manager = DatabaseManager(self.monitor_config)
            db_manager.initialize_schema()
            host_ops = HostOperations(db_manager)

            host_ops.create_host("recent-host", "192.168.1.100")
            host_ops.create_host("old-host", "192.168.1.101")

            # Set old time for one host
            with host_ops.db_manager.get_session() as session:
                host = session.query(Host).filter(Host.hostname == "old-host").first()
                old_time = datetime.now(timezone.utc) - timedelta(hours=2)
                host.last_seen = old_time
                session.commit()

            # Get hosts last seen before 1 hour ago
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
            old_hosts = await monitor.get_hosts_by_last_seen(cutoff_time)

            self.assertEqual(len(old_hosts), 1)
            self.assertEqual(old_hosts[0].hostname, "old-host")

            db_manager.cleanup()

        asyncio.run(test_last_seen_filter())

    def test_heartbeat_monitor_performance(self):
        """Test heartbeat monitor performance with multiple hosts."""

        async def test_performance():
            from server.heartbeat_monitor import HeartbeatMonitor
            from server.database.connection import DatabaseManager
            from server.database.operations import HostOperations

            monitor = HeartbeatMonitor(self.monitor_config)

            # Create multiple hosts
            db_manager = DatabaseManager(self.monitor_config)
            db_manager.initialize_schema()
            host_ops = HostOperations(db_manager)

            # Create 100 hosts for performance test
            for i in range(100):
                host_ops.create_host(f"perf-host-{i}", f"192.168.1.{i % 200 + 10}")

            # Measure check performance
            start_time = time.time()
            timeout_results = await monitor.check_host_timeouts()
            check_duration = time.time() - start_time

            self.assertEqual(timeout_results.hosts_checked, 100)
            self.assertLess(check_duration, 5.0)  # Should complete in < 5 seconds

            db_manager.cleanup()

        asyncio.run(test_performance())


class TestTimeoutResult(unittest.TestCase):
    """Test timeout check result data structure."""

    def test_timeout_result_class_exists(self):
        """Test that TimeoutResult class exists."""
        try:
            from server.heartbeat_monitor import TimeoutResult

            self.assertTrue(callable(TimeoutResult))
        except ImportError:
            self.fail("TimeoutResult should be importable from server.heartbeat_monitor")

    def test_timeout_result_creation(self):
        """Test creating timeout result instances."""
        from server.heartbeat_monitor import TimeoutResult

        result = TimeoutResult(
            hosts_checked=100,
            hosts_timed_out=5,
            timed_out_hosts=["host1", "host2", "host3", "host4", "host5"],
            check_duration=2.5,
        )

        self.assertEqual(result.hosts_checked, 100)
        self.assertEqual(result.hosts_timed_out, 5)
        self.assertEqual(len(result.timed_out_hosts), 5)
        self.assertEqual(result.check_duration, 2.5)

    def test_timeout_result_to_dict(self):
        """Test converting timeout result to dictionary."""
        from server.heartbeat_monitor import TimeoutResult

        result = TimeoutResult(
            hosts_checked=50,
            hosts_timed_out=2,
            timed_out_hosts=["host1", "host2"],
            check_duration=1.2,
        )

        result_dict = result.to_dict()

        self.assertIsInstance(result_dict, dict)
        self.assertEqual(result_dict["hosts_checked"], 50)
        self.assertEqual(result_dict["hosts_timed_out"], 2)
        self.assertEqual(result_dict["timed_out_hosts"], ["host1", "host2"])


class TestStatusChangeResult(unittest.TestCase):
    """Test status change result data structure."""

    def test_status_change_result_class_exists(self):
        """Test that StatusChangeResult class exists."""
        try:
            from server.heartbeat_monitor import StatusChangeResult

            self.assertTrue(callable(StatusChangeResult))
        except ImportError:
            self.fail("StatusChangeResult should be importable from server.heartbeat_monitor")

    def test_status_change_result_creation(self):
        """Test creating status change result instances."""
        from server.heartbeat_monitor import StatusChangeResult

        result = StatusChangeResult(
            success=True,
            hosts_processed=10,
            hosts_marked_offline=8,
            failed_hosts=["host9", "host10"],
            operation_duration=0.5,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.hosts_processed, 10)
        self.assertEqual(result.hosts_marked_offline, 8)
        self.assertEqual(len(result.failed_hosts), 2)
        self.assertEqual(result.operation_duration, 0.5)


class TestHeartbeatConfig(unittest.TestCase):
    """Test heartbeat monitor configuration."""

    def test_heartbeat_config_class_exists(self):
        """Test that HeartbeatConfig class exists."""
        try:
            from server.heartbeat_monitor import HeartbeatConfig

            self.assertTrue(callable(HeartbeatConfig))
        except ImportError:
            self.fail("HeartbeatConfig should be importable from server.heartbeat_monitor")

    def test_heartbeat_config_initialization(self):
        """Test heartbeat config initialization."""
        from server.heartbeat_monitor import HeartbeatConfig

        config_dict = {
            "heartbeat": {
                "check_interval": 45,
                "timeout_multiplier": 3,
                "grace_period": 60,
                "max_hosts_per_check": 2000,
                "cleanup_offline_after_days": 60,
            }
        }

        config = HeartbeatConfig(config_dict)

        self.assertEqual(config.check_interval, 45)
        self.assertEqual(config.timeout_multiplier, 3)
        self.assertEqual(config.grace_period, 60)
        self.assertEqual(config.max_hosts_per_check, 2000)
        self.assertEqual(config.cleanup_offline_after_days, 60)

    def test_heartbeat_config_defaults(self):
        """Test heartbeat config default values."""
        from server.heartbeat_monitor import HeartbeatConfig

        config = HeartbeatConfig({})

        # Should have reasonable defaults
        self.assertIsInstance(config.check_interval, int)
        self.assertIsInstance(config.timeout_multiplier, int)
        self.assertIsInstance(config.grace_period, int)
        self.assertIsInstance(config.max_hosts_per_check, int)
        self.assertIsInstance(config.cleanup_offline_after_days, int)

    def test_heartbeat_config_validation(self):
        """Test heartbeat config validation."""
        from server.heartbeat_monitor import HeartbeatConfig, HeartbeatConfigError

        # Invalid configuration
        invalid_config = {"heartbeat": {"check_interval": -1}}  # Invalid negative value

        with self.assertRaises(HeartbeatConfigError):
            HeartbeatConfig(invalid_config)


if __name__ == "__main__":
    unittest.main()
