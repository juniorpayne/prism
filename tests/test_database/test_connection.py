#!/usr/bin/env python3
"""
Tests for Database Connection Management (SCRUM-13)
Test-driven development for database connection pooling and management.
"""

import asyncio
import os
import tempfile
import unittest
from unittest.mock import Mock, patch


class TestDatabaseConnection(unittest.TestCase):
    """Test database connection management."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_database_manager_exists(self):
        """Test that DatabaseManager class exists."""
        try:
            from server.database.connection import DatabaseManager

            self.assertTrue(callable(DatabaseManager))
        except ImportError:
            self.fail("DatabaseManager should be importable from server.database.connection")

    def test_database_manager_initialization(self):
        """Test DatabaseManager initialization."""
        from server.database.connection import DatabaseManager

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}

        db_manager = DatabaseManager(config)
        self.assertIsNotNone(db_manager)

    def test_database_manager_create_engine(self):
        """Test that DatabaseManager creates SQLAlchemy engine."""
        from server.database.connection import DatabaseManager

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}

        db_manager = DatabaseManager(config)
        self.assertTrue(hasattr(db_manager, "engine"))
        self.assertIsNotNone(db_manager.engine)

    def test_database_manager_get_session(self):
        """Test that DatabaseManager provides session factory."""
        from server.database.connection import DatabaseManager

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}

        db_manager = DatabaseManager(config)

        # Should have session factory
        self.assertTrue(hasattr(db_manager, "get_session"))
        self.assertTrue(callable(db_manager.get_session))

    def test_database_manager_context_manager(self):
        """Test that DatabaseManager works as context manager."""
        from server.database.connection import DatabaseManager

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}

        db_manager = DatabaseManager(config)

        # Should support context manager protocol
        self.assertTrue(hasattr(db_manager, "__enter__"))
        self.assertTrue(hasattr(db_manager, "__exit__"))

    def test_database_manager_session_context(self):
        """Test session context manager."""
        from server.database.connection import DatabaseManager

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}

        db_manager = DatabaseManager(config)

        # Should provide session context manager
        with db_manager.get_session() as session:
            self.assertIsNotNone(session)
            # Session should have query method
            self.assertTrue(hasattr(session, "query"))

    def test_database_manager_initialize_schema(self):
        """Test schema initialization."""
        from server.database.connection import DatabaseManager

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}

        db_manager = DatabaseManager(config)

        # Should have initialize_schema method
        self.assertTrue(hasattr(db_manager, "initialize_schema"))

        # Should be able to call without error
        db_manager.initialize_schema()

    def test_database_manager_connection_pooling(self):
        """Test connection pooling configuration."""
        from server.database.connection import DatabaseManager

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}

        db_manager = DatabaseManager(config)

        # Engine should be configured with pooling
        engine = db_manager.engine
        self.assertIsNotNone(engine.pool)

    def test_database_manager_concurrent_connections(self):
        """Test handling of concurrent connections."""
        from server.database.connection import DatabaseManager

        config = {"database": {"path": self.db_path, "connection_pool_size": 5}}

        db_manager = DatabaseManager(config)
        db_manager.initialize_schema()

        # Should be able to get multiple sessions
        sessions = []
        for _ in range(3):
            session = db_manager.get_session()
            sessions.append(session)

        # All sessions should be valid
        for session in sessions:
            self.assertIsNotNone(session)

    def test_database_manager_cleanup(self):
        """Test proper cleanup of database resources."""
        from server.database.connection import DatabaseManager

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}

        db_manager = DatabaseManager(config)

        # Should have cleanup method
        self.assertTrue(hasattr(db_manager, "cleanup"))

        # Should be able to call cleanup
        db_manager.cleanup()

    def test_database_manager_health_check(self):
        """Test database health check."""
        from server.database.connection import DatabaseManager

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}

        db_manager = DatabaseManager(config)
        db_manager.initialize_schema()

        # Should have health check method
        self.assertTrue(hasattr(db_manager, "health_check"))

        # Health check should return True for healthy database
        is_healthy = db_manager.health_check()
        self.assertTrue(is_healthy)

    def test_database_manager_error_handling(self):
        """Test error handling for invalid database paths."""
        from server.database.connection import DatabaseManager

        # Invalid database path
        config = {"database": {"path": "/invalid/path/database.db", "connection_pool_size": 20}}

        # Should handle invalid path gracefully
        try:
            db_manager = DatabaseManager(config)
            # May fail on connection attempt, not on initialization
        except Exception as e:
            # Should be a specific database exception
            self.assertIn("database", str(e).lower())


class TestDatabaseConnectionAsync(unittest.TestCase):
    """Test async database connection functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_async_database_manager_exists(self):
        """Test that AsyncDatabaseManager exists for async operations."""
        try:
            from server.database.connection import AsyncDatabaseManager

            self.assertTrue(callable(AsyncDatabaseManager))
        except ImportError:
            # Async manager is optional for initial implementation
            self.skipTest("AsyncDatabaseManager not yet implemented")

    def test_async_session_factory(self):
        """Test async session factory."""
        try:
            from server.database.connection import AsyncDatabaseManager
        except ImportError:
            self.skipTest("AsyncDatabaseManager not yet implemented")

        config = {"database": {"path": self.db_path, "connection_pool_size": 20}}

        try:
            async_db_manager = AsyncDatabaseManager(config)
            # Should have async session factory
            self.assertTrue(hasattr(async_db_manager, "get_async_session"))
        except NotImplementedError:
            self.skipTest("AsyncDatabaseManager not yet implemented")


class TestDatabaseConfiguration(unittest.TestCase):
    """Test database configuration handling."""

    def test_database_config_validation(self):
        """Test database configuration validation."""
        from server.database.connection import DatabaseConfig

        # Valid configuration
        valid_config = {"database": {"path": "./test.db", "connection_pool_size": 20}}

        db_config = DatabaseConfig(valid_config)
        self.assertIsNotNone(db_config)

    def test_database_config_defaults(self):
        """Test database configuration defaults."""
        from server.database.connection import DatabaseConfig

        # Minimal configuration
        minimal_config = {"database": {"path": "./test.db"}}

        db_config = DatabaseConfig(minimal_config)

        # Should have default values
        self.assertEqual(db_config.connection_pool_size, 20)

    def test_database_config_validation_errors(self):
        """Test database configuration validation errors."""
        from server.database.connection import DatabaseConfig, DatabaseConfigError

        # Invalid configuration - missing path
        invalid_config = {"database": {"connection_pool_size": 20}}

        with self.assertRaises(DatabaseConfigError):
            DatabaseConfig(invalid_config)


if __name__ == "__main__":
    unittest.main()
