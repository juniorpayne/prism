#!/usr/bin/env python3
"""
Tests for Host Manager (SCRUM-15)
Test-driven development for host record management.
"""

import unittest
import asyncio
import tempfile
import os
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch


class TestHostManager(unittest.TestCase):
    """Test host manager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name

        self.manager_config = {
            "database": {"path": self.db_path, "connection_pool_size": 20},
            "host_management": {
                "status_check_interval": 30,
                "offline_threshold_multiplier": 2,
                "cleanup_offline_after_days": 30,
            },
        }

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_host_manager_class_exists(self):
        """Test that HostManager class exists."""
        try:
            from server.host_manager import HostManager

            self.assertTrue(callable(HostManager))
        except ImportError:
            self.fail("HostManager should be importable from server.host_manager")

    def test_host_manager_initialization(self):
        """Test host manager initialization."""
        from server.host_manager import HostManager

        manager = HostManager(self.manager_config)

        self.assertIsNotNone(manager)
        self.assertTrue(hasattr(manager, "config"))
        self.assertTrue(hasattr(manager, "db_manager"))

    def test_register_new_host(self):
        """Test registering a new host."""

        async def test_new_host():
            from server.host_manager import HostManager

            manager = HostManager(self.manager_config)

            result = await manager.register_host(hostname="new-host", ip_address="192.168.1.100")

            self.assertTrue(result.success)
            self.assertEqual(result.action, "created")
            self.assertEqual(result.hostname, "new-host")
            self.assertEqual(result.ip_address, "192.168.1.100")

        asyncio.run(test_new_host())

    def test_update_existing_host_same_ip(self):
        """Test updating existing host with same IP."""

        async def test_same_ip():
            from server.host_manager import HostManager

            manager = HostManager(self.manager_config)

            # Register host
            await manager.register_host(hostname="existing-host", ip_address="192.168.1.100")

            # Update with same IP
            result = await manager.register_host(
                hostname="existing-host", ip_address="192.168.1.100"
            )

            self.assertTrue(result.success)
            self.assertEqual(result.action, "updated_timestamp")
            self.assertIsNone(result.previous_ip)

        asyncio.run(test_same_ip())

    def test_update_existing_host_different_ip(self):
        """Test updating existing host with different IP."""

        async def test_different_ip():
            from server.host_manager import HostManager

            manager = HostManager(self.manager_config)

            # Register host
            await manager.register_host(hostname="ip-change-host", ip_address="192.168.1.100")

            # Update with different IP
            result = await manager.register_host(
                hostname="ip-change-host", ip_address="192.168.1.200"
            )

            self.assertTrue(result.success)
            self.assertEqual(result.action, "updated_ip")
            self.assertEqual(result.previous_ip, "192.168.1.100")
            self.assertEqual(result.ip_address, "192.168.1.200")

        asyncio.run(test_different_ip())

    def test_reactivate_offline_host(self):
        """Test reactivating an offline host."""

        async def test_reactivation():
            from server.host_manager import HostManager
            from server.database.connection import DatabaseManager
            from server.database.operations import HostOperations

            manager = HostManager(self.manager_config)

            # Create host and mark offline
            db_manager = DatabaseManager(self.manager_config)
            db_manager.initialize_schema()
            host_ops = HostOperations(db_manager)

            host = host_ops.create_host("offline-host", "192.168.1.100")
            host_ops.mark_host_offline("offline-host")

            # Reactivate host
            result = await manager.register_host(
                hostname="offline-host", ip_address="192.168.1.100"
            )

            self.assertTrue(result.success)
            self.assertEqual(result.action, "reactivated")
            self.assertEqual(result.previous_status, "offline")

            db_manager.cleanup()

        asyncio.run(test_reactivation())

    def test_get_host_info(self):
        """Test getting host information."""

        async def test_host_info():
            from server.host_manager import HostManager

            manager = HostManager(self.manager_config)

            # Register host
            await manager.register_host(hostname="info-host", ip_address="192.168.1.100")

            # Get host info
            host_info = await manager.get_host_info("info-host")

            self.assertIsNotNone(host_info)
            self.assertEqual(host_info.hostname, "info-host")
            self.assertEqual(host_info.current_ip, "192.168.1.100")
            self.assertEqual(host_info.status, "online")

        asyncio.run(test_host_info())

    def test_get_nonexistent_host_info(self):
        """Test getting info for non-existent host."""

        async def test_nonexistent():
            from server.host_manager import HostManager

            manager = HostManager(self.manager_config)

            host_info = await manager.get_host_info("nonexistent-host")

            self.assertIsNone(host_info)

        asyncio.run(test_nonexistent())

    def test_list_hosts_by_status(self):
        """Test listing hosts by status."""

        async def test_list_by_status():
            from server.host_manager import HostManager
            from server.database.connection import DatabaseManager
            from server.database.operations import HostOperations

            manager = HostManager(self.manager_config)

            # Register hosts
            await manager.register_host("online-host-1", "192.168.1.100")
            await manager.register_host("online-host-2", "192.168.1.101")

            # Mark one offline
            db_manager = DatabaseManager(self.manager_config)
            db_manager.initialize_schema()
            host_ops = HostOperations(db_manager)
            host_ops.mark_host_offline("online-host-2")

            # List online hosts
            online_hosts = await manager.list_hosts_by_status("online")
            offline_hosts = await manager.list_hosts_by_status("offline")

            self.assertEqual(len(online_hosts), 1)
            self.assertEqual(len(offline_hosts), 1)
            self.assertEqual(online_hosts[0].hostname, "online-host-1")
            self.assertEqual(offline_hosts[0].hostname, "online-host-2")

            db_manager.cleanup()

        asyncio.run(test_list_by_status())

    def test_list_all_hosts(self):
        """Test listing all hosts."""

        async def test_list_all():
            from server.host_manager import HostManager

            manager = HostManager(self.manager_config)

            # Register multiple hosts
            hostnames = ["host-1", "host-2", "host-3"]
            for hostname in hostnames:
                await manager.register_host(hostname, f"192.168.1.{100 + len(hostname)}")

            # List all hosts
            all_hosts = await manager.list_all_hosts()

            self.assertEqual(len(all_hosts), 3)
            host_names = [host.hostname for host in all_hosts]
            for hostname in hostnames:
                self.assertIn(hostname, host_names)

        asyncio.run(test_list_all())

    def test_get_host_count(self):
        """Test getting host count."""

        async def test_host_count():
            from server.host_manager import HostManager

            manager = HostManager(self.manager_config)

            # Initially no hosts
            count = await manager.get_host_count()
            self.assertEqual(count, 0)

            # Add hosts
            await manager.register_host("count-host-1", "192.168.1.100")
            await manager.register_host("count-host-2", "192.168.1.101")

            count = await manager.get_host_count()
            self.assertEqual(count, 2)

        asyncio.run(test_host_count())

    def test_get_host_count_by_status(self):
        """Test getting host count by status."""

        async def test_count_by_status():
            from server.host_manager import HostManager
            from server.database.connection import DatabaseManager
            from server.database.operations import HostOperations

            manager = HostManager(self.manager_config)

            # Register hosts
            await manager.register_host("status-host-1", "192.168.1.100")
            await manager.register_host("status-host-2", "192.168.1.101")
            await manager.register_host("status-host-3", "192.168.1.102")

            # Mark one offline
            db_manager = DatabaseManager(self.manager_config)
            db_manager.initialize_schema()
            host_ops = HostOperations(db_manager)
            host_ops.mark_host_offline("status-host-2")

            online_count = await manager.get_host_count_by_status("online")
            offline_count = await manager.get_host_count_by_status("offline")

            self.assertEqual(online_count, 2)
            self.assertEqual(offline_count, 1)

            db_manager.cleanup()

        asyncio.run(test_count_by_status())

    def test_host_exists(self):
        """Test checking if host exists."""

        async def test_exists():
            from server.host_manager import HostManager

            manager = HostManager(self.manager_config)

            # Non-existent host
            exists = await manager.host_exists("nonexistent")
            self.assertFalse(exists)

            # Register host
            await manager.register_host("exists-host", "192.168.1.100")

            # Existing host
            exists = await manager.host_exists("exists-host")
            self.assertTrue(exists)

        asyncio.run(test_exists())

    def test_delete_host(self):
        """Test deleting a host."""

        async def test_delete():
            from server.host_manager import HostManager

            manager = HostManager(self.manager_config)

            # Register host
            await manager.register_host("delete-host", "192.168.1.100")

            # Verify exists
            exists = await manager.host_exists("delete-host")
            self.assertTrue(exists)

            # Delete host
            success = await manager.delete_host("delete-host")
            self.assertTrue(success)

            # Verify deleted
            exists = await manager.host_exists("delete-host")
            self.assertFalse(exists)

        asyncio.run(test_delete())

    def test_cleanup_old_hosts(self):
        """Test cleaning up old offline hosts."""

        async def test_cleanup():
            from server.host_manager import HostManager
            from server.database.connection import DatabaseManager
            from server.database.operations import HostOperations
            from server.database.models import Host

            manager = HostManager(self.manager_config)

            # Create old offline host
            db_manager = DatabaseManager(self.manager_config)
            db_manager.initialize_schema()
            host_ops = HostOperations(db_manager)

            host = host_ops.create_host("old-host", "192.168.1.100")
            host_ops.mark_host_offline("old-host")

            # Manually set old last_seen date
            with host_ops.db_manager.get_session() as session:
                host_to_update = session.query(Host).filter(Host.hostname == "old-host").first()
                old_date = datetime.now(timezone.utc) - timedelta(days=35)
                host_to_update.last_seen = old_date
                session.commit()

            # Cleanup
            cleaned_count = await manager.cleanup_old_hosts(older_than_days=30)

            self.assertEqual(cleaned_count, 1)

            # Verify host was removed
            exists = await manager.host_exists("old-host")
            self.assertFalse(exists)

            db_manager.cleanup()

        asyncio.run(test_cleanup())


class TestHostRegistrationResult(unittest.TestCase):
    """Test host registration result data structure."""

    def test_host_registration_result_class_exists(self):
        """Test that HostRegistrationResult class exists."""
        try:
            from server.host_manager import HostRegistrationResult

            self.assertTrue(callable(HostRegistrationResult))
        except ImportError:
            self.fail("HostRegistrationResult should be importable from server.host_manager")

    def test_host_registration_result_creation(self):
        """Test creating host registration result instances."""
        from server.host_manager import HostRegistrationResult

        result = HostRegistrationResult(
            success=True, action="created", hostname="test-host", ip_address="192.168.1.100"
        )

        self.assertTrue(result.success)
        self.assertEqual(result.action, "created")
        self.assertEqual(result.hostname, "test-host")
        self.assertEqual(result.ip_address, "192.168.1.100")

    def test_host_registration_result_with_previous_ip(self):
        """Test creating result with previous IP information."""
        from server.host_manager import HostRegistrationResult

        result = HostRegistrationResult(
            success=True,
            action="updated_ip",
            hostname="test-host",
            ip_address="192.168.1.200",
            previous_ip="192.168.1.100",
        )

        self.assertEqual(result.previous_ip, "192.168.1.100")
        self.assertEqual(result.ip_address, "192.168.1.200")

    def test_host_registration_result_with_status_change(self):
        """Test creating result with status change information."""
        from server.host_manager import HostRegistrationResult

        result = HostRegistrationResult(
            success=True,
            action="reactivated",
            hostname="test-host",
            ip_address="192.168.1.100",
            previous_status="offline",
        )

        self.assertEqual(result.action, "reactivated")
        self.assertEqual(result.previous_status, "offline")


class TestHostInfo(unittest.TestCase):
    """Test host information data structure."""

    def test_host_info_class_exists(self):
        """Test that HostInfo class exists."""
        try:
            from server.host_manager import HostInfo

            self.assertTrue(callable(HostInfo))
        except ImportError:
            self.fail("HostInfo should be importable from server.host_manager")

    def test_host_info_creation(self):
        """Test creating host info instances."""
        from server.host_manager import HostInfo

        now = datetime.now(timezone.utc)

        host_info = HostInfo(
            hostname="test-host",
            current_ip="192.168.1.100",
            status="online",
            first_seen=now,
            last_seen=now,
        )

        self.assertEqual(host_info.hostname, "test-host")
        self.assertEqual(host_info.current_ip, "192.168.1.100")
        self.assertEqual(host_info.status, "online")
        self.assertEqual(host_info.first_seen, now)
        self.assertEqual(host_info.last_seen, now)

    def test_host_info_to_dict(self):
        """Test converting host info to dictionary."""
        from server.host_manager import HostInfo

        now = datetime.now(timezone.utc)

        host_info = HostInfo(
            hostname="test-host",
            current_ip="192.168.1.100",
            status="online",
            first_seen=now,
            last_seen=now,
        )

        info_dict = host_info.to_dict()

        self.assertIsInstance(info_dict, dict)
        self.assertEqual(info_dict["hostname"], "test-host")
        self.assertEqual(info_dict["current_ip"], "192.168.1.100")
        self.assertEqual(info_dict["status"], "online")


if __name__ == "__main__":
    unittest.main()
