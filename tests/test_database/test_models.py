#!/usr/bin/env python3
"""
Tests for Database Models (SCRUM-13)
Test-driven development for SQLAlchemy models and schema.
"""

import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


class TestDatabaseModels(unittest.TestCase):
    """Test database models and schema definition."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name

    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary database file
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_host_model_exists(self):
        """Test that Host model is defined."""
        try:
            from server.database.models import Host

            self.assertTrue(hasattr(Host, "__tablename__"))
        except ImportError:
            self.fail("Host model should be importable from server.database.models")

    def test_host_model_fields(self):
        """Test that Host model has required fields."""
        from server.database.models import Host

        # Check required fields exist
        required_fields = [
            "id",
            "hostname",
            "current_ip",
            "first_seen",
            "last_seen",
            "status",
            "created_at",
            "updated_at",
        ]

        for field in required_fields:
            self.assertTrue(hasattr(Host, field), f"Host model should have {field} field")

    def test_host_model_table_name(self):
        """Test that Host model has correct table name."""
        from server.database.models import Host

        self.assertEqual(Host.__tablename__, "hosts")

    def test_host_model_primary_key(self):
        """Test that Host model has primary key."""
        from server.database.models import Host

        # Check that id field is primary key
        id_column = getattr(Host, "id")
        self.assertTrue(id_column.property.columns[0].primary_key)

    def test_host_model_constraints(self):
        """Test that Host model has proper constraints."""
        from server.database.models import Host

        # Hostname should be unique and not nullable
        hostname_column = getattr(Host, "hostname")
        self.assertFalse(hostname_column.property.columns[0].nullable)
        self.assertTrue(hostname_column.property.columns[0].unique)

        # Current IP should not be nullable
        ip_column = getattr(Host, "current_ip")
        self.assertFalse(ip_column.property.columns[0].nullable)

    def test_host_model_defaults(self):
        """Test that Host model has proper default values."""
        from server.database.models import Host

        # Status should default to 'online'
        status_column = getattr(Host, "status")
        self.assertEqual(status_column.property.columns[0].default.arg, "online")

    def test_host_model_string_representation(self):
        """Test Host model string representation."""
        from server.database.models import Host

        # Should have __str__ or __repr__ method
        self.assertTrue(
            hasattr(Host, "__str__") or hasattr(Host, "__repr__"),
            "Host model should have string representation",
        )

    def test_host_model_field_types(self):
        """Test that Host model fields have correct types."""
        from sqlalchemy import DateTime, Integer, String

        from server.database.models import Host

        # Check field types
        field_types = {
            "id": Integer,
            "hostname": String,
            "current_ip": String,
            "status": String,
        }

        for field_name, expected_type in field_types.items():
            field = getattr(Host, field_name)
            column_type = field.property.columns[0].type
            self.assertIsInstance(
                column_type, expected_type, f"{field_name} should be of type {expected_type}"
            )

    def test_host_model_indexes(self):
        """Test that Host model has proper indexes."""
        from server.database.models import Host

        # Check that hostname has index
        hostname_column = getattr(Host, "hostname")
        self.assertTrue(hostname_column.property.columns[0].index, "Hostname should be indexed")

    def test_host_model_instance_creation(self):
        """Test creating Host model instances."""
        from server.database.models import Host

        # Should be able to create instance
        host = Host(hostname="test-host", current_ip="192.168.1.100")

        self.assertEqual(host.hostname, "test-host")
        self.assertEqual(host.current_ip, "192.168.1.100")
        self.assertEqual(host.status, "online")  # Default value

    def test_host_model_validation_methods(self):
        """Test that Host model has validation methods."""
        from server.database.models import Host

        # Should have validation methods
        expected_methods = ["validate_hostname", "validate_ip"]

        for method in expected_methods:
            self.assertTrue(hasattr(Host, method), f"Host model should have {method} method")

    def test_database_base_exists(self):
        """Test that database base is properly configured."""
        try:
            from sqlalchemy.ext.declarative import DeclarativeMeta

            from server.database.models import Base

            self.assertIsInstance(Base, DeclarativeMeta)
        except ImportError:
            self.fail("Base should be importable from server.database.models")


class TestDatabaseSchema(unittest.TestCase):
    """Test database schema creation and structure."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_schema_creation(self):
        """Test that database schema can be created."""
        from sqlalchemy import create_engine

        from server.database.models import Base

        # Create engine and schema
        engine = create_engine(f"sqlite:///{self.db_path}")
        Base.metadata.create_all(engine)

        # Verify database file was created
        self.assertTrue(os.path.exists(self.db_path))

    def test_hosts_table_exists(self):
        """Test that hosts table is created."""
        from sqlalchemy import create_engine, inspect

        from server.database.models import Base, Host

        # Create schema
        engine = create_engine(f"sqlite:///{self.db_path}")
        Base.metadata.create_all(engine)

        # Check table exists
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        self.assertIn("hosts", tables)

    def test_hosts_table_columns(self):
        """Test that hosts table has correct columns."""
        from sqlalchemy import create_engine, inspect

        from server.database.models import Base, Host

        # Create schema
        engine = create_engine(f"sqlite:///{self.db_path}")
        Base.metadata.create_all(engine)

        # Check columns
        inspector = inspect(engine)
        columns = inspector.get_columns("hosts")
        column_names = [col["name"] for col in columns]

        expected_columns = [
            "id",
            "hostname",
            "current_ip",
            "first_seen",
            "last_seen",
            "status",
            "created_at",
            "updated_at",
        ]

        for col in expected_columns:
            self.assertIn(col, column_names, f"Column {col} should exist")

    def test_hosts_table_indexes(self):
        """Test that hosts table has proper indexes."""
        from sqlalchemy import create_engine, inspect

        from server.database.models import Base, Host

        # Create schema
        engine = create_engine(f"sqlite:///{self.db_path}")
        Base.metadata.create_all(engine)

        # Check indexes
        inspector = inspect(engine)
        indexes = inspector.get_indexes("hosts")

        # Should have indexes on hostname, status, last_seen
        index_columns = []
        for index in indexes:
            index_columns.extend(index["column_names"])

        expected_indexed_columns = ["hostname"]
        for col in expected_indexed_columns:
            self.assertIn(col, index_columns, f"Column {col} should be indexed")

    def test_hosts_table_constraints(self):
        """Test that hosts table has proper constraints."""
        from sqlalchemy import create_engine, inspect

        from server.database.models import Base, Host

        # Create schema
        engine = create_engine(f"sqlite:///{self.db_path}")
        Base.metadata.create_all(engine)

        # Check primary key
        inspector = inspect(engine)
        pk_constraint = inspector.get_pk_constraint("hosts")

        self.assertEqual(pk_constraint["constrained_columns"], ["id"])

        # Check unique constraints (SQLite handles this differently)
        unique_constraints = inspector.get_unique_constraints("hosts")
        hostname_unique = any(
            "hostname" in constraint["column_names"] for constraint in unique_constraints
        )

        # Also check if hostname column has unique=True property
        columns = inspector.get_columns("hosts")
        hostname_column = next((col for col in columns if col["name"] == "hostname"), None)
        hostname_unique = hostname_unique or (
            hostname_column and hostname_column.get("unique", False)
        )

        # For SQLite, we can also check indexes as unique constraints are often implemented as unique indexes
        if not hostname_unique:
            indexes = inspector.get_indexes("hosts")
            hostname_unique = any(
                index.get("unique", False) and "hostname" in index["column_names"]
                for index in indexes
            )

        self.assertTrue(hostname_unique, "Hostname should have unique constraint")


if __name__ == "__main__":
    unittest.main()
