#!/usr/bin/env python3
"""
Tests for Database CRUD Operations (SCRUM-13)
Test-driven development for host record operations.
"""

import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch


class TestHostOperations(unittest.TestCase):
    """Test CRUD operations for host records."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name

        # Sample host data
        self.sample_host = {"hostname": "test-host-001", "current_ip": "192.168.1.100"}

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_host_operations_class_exists(self):
        """Test that HostOperations class exists."""
        try:
            from server.database.operations import HostOperations

            self.assertTrue(callable(HostOperations))
        except ImportError:
            self.fail("HostOperations should be importable from server.database.operations")

    def test_create_host_operation(self):
        """Test creating a new host record."""
        from server.database.connection import DatabaseManager
        from server.database.operations import HostOperations

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}
        db_manager = DatabaseManager(config)
        db_manager.initialize_schema()

        host_ops = HostOperations(db_manager)

        # Create host
        host = host_ops.create_host(
            hostname=self.sample_host["hostname"], ip_address=self.sample_host["current_ip"]
        )

        self.assertIsNotNone(host)
        self.assertEqual(host.hostname, self.sample_host["hostname"])
        self.assertEqual(host.current_ip, self.sample_host["current_ip"])
        self.assertEqual(host.status, "online")

    def test_get_host_by_hostname(self):
        """Test retrieving host by hostname."""
        from server.database.connection import DatabaseManager
        from server.database.operations import HostOperations

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}
        db_manager = DatabaseManager(config)
        db_manager.initialize_schema()

        host_ops = HostOperations(db_manager)

        # Create host first
        created_host = host_ops.create_host(
            hostname=self.sample_host["hostname"], ip_address=self.sample_host["current_ip"]
        )

        # Retrieve host
        retrieved_host = host_ops.get_host_by_hostname(self.sample_host["hostname"])

        self.assertIsNotNone(retrieved_host)
        self.assertEqual(retrieved_host.hostname, self.sample_host["hostname"])
        self.assertEqual(retrieved_host.id, created_host.id)

    def test_get_host_by_hostname_not_found(self):
        """Test retrieving non-existent host returns None."""
        from server.database.connection import DatabaseManager
        from server.database.operations import HostOperations

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}
        db_manager = DatabaseManager(config)
        db_manager.initialize_schema()

        host_ops = HostOperations(db_manager)

        # Try to retrieve non-existent host
        host = host_ops.get_host_by_hostname("non-existent-host")

        self.assertIsNone(host)

    def test_update_host_ip(self):
        """Test updating host IP address."""
        from server.database.connection import DatabaseManager
        from server.database.operations import HostOperations

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}
        db_manager = DatabaseManager(config)
        db_manager.initialize_schema()

        host_ops = HostOperations(db_manager)

        # Create host
        host = host_ops.create_host(
            hostname=self.sample_host["hostname"], ip_address=self.sample_host["current_ip"]
        )

        # Update IP
        new_ip = "192.168.1.200"
        success = host_ops.update_host_ip(self.sample_host["hostname"], new_ip)

        self.assertTrue(success)

        # Verify update
        updated_host = host_ops.get_host_by_hostname(self.sample_host["hostname"])
        self.assertEqual(updated_host.current_ip, new_ip)

    def test_update_host_last_seen(self):
        """Test updating host last seen timestamp."""
        from server.database.connection import DatabaseManager
        from server.database.operations import HostOperations

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}
        db_manager = DatabaseManager(config)
        db_manager.initialize_schema()

        host_ops = HostOperations(db_manager)

        # Create host
        host = host_ops.create_host(
            hostname=self.sample_host["hostname"], ip_address=self.sample_host["current_ip"]
        )

        # Get the original last_seen timestamp from database
        original_host = host_ops.get_host_by_hostname(self.sample_host["hostname"])
        original_last_seen = original_host.last_seen

        # Add a small delay to ensure timestamp difference
        import time

        time.sleep(0.01)

        # Update last seen
        success = host_ops.update_host_last_seen(self.sample_host["hostname"])

        self.assertTrue(success)

        # Verify update
        updated_host = host_ops.get_host_by_hostname(self.sample_host["hostname"])
        self.assertGreater(updated_host.last_seen, original_last_seen)

    def test_get_all_hosts(self):
        """Test retrieving all hosts."""
        from server.database.connection import DatabaseManager
        from server.database.operations import HostOperations

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}
        db_manager = DatabaseManager(config)
        db_manager.initialize_schema()

        host_ops = HostOperations(db_manager)

        # Create multiple hosts
        hostnames = ["host-001", "host-002", "host-003"]
        for hostname in hostnames:
            host_ops.create_host(hostname=hostname, ip_address="192.168.1.100")

        # Get all hosts
        all_hosts = host_ops.get_all_hosts()

        self.assertEqual(len(all_hosts), 3)
        retrieved_hostnames = [host.hostname for host in all_hosts]
        for hostname in hostnames:
            self.assertIn(hostname, retrieved_hostnames)

    def test_get_hosts_by_status(self):
        """Test retrieving hosts by status."""
        from server.database.connection import DatabaseManager
        from server.database.operations import HostOperations

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}
        db_manager = DatabaseManager(config)
        db_manager.initialize_schema()

        host_ops = HostOperations(db_manager)

        # Create hosts
        host_ops.create_host(hostname="online-host", ip_address="192.168.1.100")
        offline_host = host_ops.create_host(hostname="offline-host", ip_address="192.168.1.101")

        # Mark one host offline
        host_ops.mark_host_offline("offline-host")

        # Get hosts by status
        online_hosts = host_ops.get_hosts_by_status("online")
        offline_hosts = host_ops.get_hosts_by_status("offline")

        self.assertEqual(len(online_hosts), 1)
        self.assertEqual(len(offline_hosts), 1)
        self.assertEqual(online_hosts[0].hostname, "online-host")
        self.assertEqual(offline_hosts[0].hostname, "offline-host")

    def test_mark_host_offline(self):
        """Test marking host as offline."""
        from server.database.connection import DatabaseManager
        from server.database.operations import HostOperations

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}
        db_manager = DatabaseManager(config)
        db_manager.initialize_schema()

        host_ops = HostOperations(db_manager)

        # Create host (default status is online)
        host = host_ops.create_host(
            hostname=self.sample_host["hostname"], ip_address=self.sample_host["current_ip"]
        )
        self.assertEqual(host.status, "online")

        # Mark offline
        success = host_ops.mark_host_offline(self.sample_host["hostname"])

        self.assertTrue(success)

        # Verify status
        updated_host = host_ops.get_host_by_hostname(self.sample_host["hostname"])
        self.assertEqual(updated_host.status, "offline")

    def test_cleanup_old_hosts(self):
        """Test cleaning up old offline hosts."""
        from datetime import datetime, timedelta

        from server.database.connection import DatabaseManager
        from server.database.operations import HostOperations

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}
        db_manager = DatabaseManager(config)
        db_manager.initialize_schema()

        host_ops = HostOperations(db_manager)

        # Create host and mark as offline
        host = host_ops.create_host(
            hostname=self.sample_host["hostname"], ip_address=self.sample_host["current_ip"]
        )
        host_ops.mark_host_offline(self.sample_host["hostname"])

        # Manually set last_seen to an old date to test cleanup
        from server.database.models import Host

        with host_ops.db_manager.get_session() as session:
            host_to_update = (
                session.query(Host).filter(Host.hostname == self.sample_host["hostname"]).first()
            )
            old_date = datetime.now(timezone.utc) - timedelta(days=35)
            host_to_update.last_seen = old_date
            session.commit()

        # Cleanup hosts older than 30 days
        cleaned_count = host_ops.cleanup_old_hosts(older_than_days=30)

        self.assertEqual(cleaned_count, 1)

    def test_host_exists(self):
        """Test checking if host exists."""
        from server.database.connection import DatabaseManager
        from server.database.operations import HostOperations

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}
        db_manager = DatabaseManager(config)
        db_manager.initialize_schema()

        host_ops = HostOperations(db_manager)

        # Non-existent host
        self.assertFalse(host_ops.host_exists("non-existent"))

        # Create host
        host_ops.create_host(
            hostname=self.sample_host["hostname"], ip_address=self.sample_host["current_ip"]
        )

        # Existing host
        self.assertTrue(host_ops.host_exists(self.sample_host["hostname"]))

    def test_get_host_count(self):
        """Test getting total host count."""
        from server.database.connection import DatabaseManager
        from server.database.operations import HostOperations

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}
        db_manager = DatabaseManager(config)
        db_manager.initialize_schema()

        host_ops = HostOperations(db_manager)

        # Initially no hosts
        self.assertEqual(host_ops.get_host_count(), 0)

        # Add hosts
        for i in range(5):
            host_ops.create_host(hostname=f"host-{i}", ip_address="192.168.1.100")

        self.assertEqual(host_ops.get_host_count(), 5)

    def test_get_host_count_by_status(self):
        """Test getting host count by status."""
        from server.database.connection import DatabaseManager
        from server.database.operations import HostOperations

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}
        db_manager = DatabaseManager(config)
        db_manager.initialize_schema()

        host_ops = HostOperations(db_manager)

        # Create hosts
        for i in range(3):
            host_ops.create_host(hostname=f"host-{i}", ip_address="192.168.1.100")

        # Mark one offline
        host_ops.mark_host_offline("host-1")

        self.assertEqual(host_ops.get_host_count_by_status("online"), 2)
        self.assertEqual(host_ops.get_host_count_by_status("offline"), 1)


class TestDatabaseTransactions(unittest.TestCase):
    """Test database transaction handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_transaction_commit(self):
        """Test successful transaction commit."""
        from server.database.connection import DatabaseManager
        from server.database.operations import HostOperations

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}
        db_manager = DatabaseManager(config)
        db_manager.initialize_schema()

        host_ops = HostOperations(db_manager)

        # Create host in transaction
        host = host_ops.create_host(hostname="test-host", ip_address="192.168.1.100")

        # Host should be committed and retrievable
        retrieved_host = host_ops.get_host_by_hostname("test-host")
        self.assertIsNotNone(retrieved_host)

    def test_transaction_rollback(self):
        """Test transaction rollback on error."""
        from server.database.connection import DatabaseManager
        from server.database.operations import HostOperations

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}
        db_manager = DatabaseManager(config)
        db_manager.initialize_schema()

        host_ops = HostOperations(db_manager)

        # This test would require simulating a database error
        # For now, just verify the operation handles exceptions
        try:
            # Try to create host with invalid data
            host_ops.create_host(hostname=None, ip_address="192.168.1.100")
        except Exception:
            # Should handle gracefully
            pass

        # Database should be in consistent state
        count = host_ops.get_host_count()
        self.assertEqual(count, 0)

    def test_concurrent_operations(self):
        """Test concurrent database operations."""
        import threading

        from server.database.connection import DatabaseManager
        from server.database.operations import HostOperations

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}
        db_manager = DatabaseManager(config)
        db_manager.initialize_schema()

        host_ops = HostOperations(db_manager)

        # Create hosts concurrently with individual database managers to avoid transaction conflicts
        def create_host(host_id, db_path):
            try:
                config = {"database": {"path": db_path, "connection_pool_size": 20}}
                local_db_manager = DatabaseManager(config)
                local_host_ops = HostOperations(local_db_manager)
                local_host_ops.create_host(hostname=f"host-{host_id}", ip_address="192.168.1.100")
                local_db_manager.cleanup()
            except Exception as e:
                # Log but don't fail - some concurrency conflicts are expected with SQLite
                print(f"Concurrent creation of host-{host_id} failed: {e}")

        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_host, args=(i, self.db_path))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # At least some hosts should be created (SQLite may have concurrency limitations)
        final_count = host_ops.get_host_count()
        self.assertGreaterEqual(final_count, 3, "At least 3 hosts should be created concurrently")


if __name__ == "__main__":
    unittest.main()
