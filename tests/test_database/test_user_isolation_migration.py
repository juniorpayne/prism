#!/usr/bin/env python3
"""
Tests for user isolation database migration (SCRUM-127).
Tests that created_by field is properly configured for user isolation.
"""

import pytest
import sqlite3
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from server.database.models import Base, Host
from server.database.migrations import DatabaseMigrations
from server.database.connection import DatabaseManager


class TestUserIsolationMigration:
    """Test suite for user isolation database migration."""

    @pytest.fixture
    def test_db(self, tmp_path):
        """Create a test database simulating pre-migration state."""
        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        
        # Create engine
        engine = create_engine(db_url)
        
        # Create hosts table with created_by as nullable (pre-migration state)
        with engine.connect() as conn:
            # Create table manually to simulate old schema
            conn.execute(text("""
                CREATE TABLE hosts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hostname VARCHAR(255) NOT NULL UNIQUE,
                    current_ip VARCHAR(45) NOT NULL,
                    first_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(20) NOT NULL DEFAULT 'online',
                    dns_zone VARCHAR(255),
                    dns_record_id VARCHAR(255),
                    dns_ttl INTEGER,
                    dns_sync_status VARCHAR(20) DEFAULT 'pending',
                    dns_last_sync TIMESTAMP,
                    org_id VARCHAR(36),
                    zone_id VARCHAR(36),
                    created_by VARCHAR(36),  -- Nullable in pre-migration state
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create indexes
            conn.execute(text("CREATE UNIQUE INDEX idx_hostname ON hosts(hostname)"))
            conn.execute(text("CREATE INDEX idx_hostname_status ON hosts(hostname, status)"))
            conn.execute(text("CREATE INDEX idx_last_seen_status ON hosts(last_seen, status)"))
            conn.execute(text("CREATE INDEX idx_hosts_org_id ON hosts(org_id)"))
            conn.execute(text("CREATE INDEX idx_hosts_zone_id ON hosts(zone_id)"))
            
            # Create schema_version table and mark as version 3 (pre-v4 migration)
            conn.execute(text("""
                CREATE TABLE schema_version (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version INTEGER NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            """))
            conn.execute(text("""
                INSERT INTO schema_version (version, description) 
                VALUES (3, 'Pre-migration state for testing')
            """))
            conn.commit()
        
        # Create database manager with proper config
        config = {
            "database": {
                "path": str(db_path),
                "connection_pool_size": 5
            }
        }
        db_manager = DatabaseManager(config)
        db_manager.engine = engine
        
        return db_manager, engine, str(db_path)

    def test_created_by_field_exists(self, test_db):
        """Test that created_by field exists in hosts table."""
        _, engine, _ = test_db
        
        # Get table info
        inspector = inspect(engine)
        columns = inspector.get_columns('hosts')
        column_names = [col['name'] for col in columns]
        
        assert 'created_by' in column_names, "created_by field should exist in hosts table"
        
        # Check column properties
        created_by_col = next(col for col in columns if col['name'] == 'created_by')
        assert created_by_col['type'].__class__.__name__ == 'VARCHAR'
        
    def test_created_by_cannot_be_null_after_migration(self, test_db):
        """Test that created_by field cannot be NULL after migration v4."""
        db_manager, engine, _ = test_db
        
        # First, verify we can insert NULL before migration
        with engine.connect() as conn:
            conn.execute(text(
                "INSERT INTO hosts (hostname, current_ip, status, created_by, first_seen, last_seen, created_at, updated_at) "
                "VALUES ('test-host', '192.168.1.1', 'online', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ))
            conn.commit()
        
        # Run migration to v4
        migrations = DatabaseMigrations(db_manager)
        migrations._migrate_to_v4()
        
        # Try to insert host without created_by - should fail
        Session = sessionmaker(bind=engine)
        session = Session()
        
        with pytest.raises(IntegrityError) as exc_info:
            session.execute(text(
                "INSERT INTO hosts (hostname, current_ip, status, created_by, first_seen, last_seen, created_at, updated_at) "
                "VALUES ('test-host2', '192.168.1.2', 'online', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ))
            session.commit()
        
        assert "NOT NULL constraint failed" in str(exc_info.value)
        session.rollback()
        session.close()
        
    def test_created_by_index_exists_after_migration(self, test_db):
        """Test that index exists on created_by field after migration."""
        db_manager, engine, db_path = test_db
        
        # Run migration
        migrations = DatabaseMigrations(db_manager)
        migrations._migrate_to_v4()
        
        # Check indexes using raw SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='hosts'")
        indexes = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        assert 'idx_hosts_created_by' in indexes, "Index on created_by should exist"
        
    def test_migration_updates_null_values(self, test_db):
        """Test that migration updates existing NULL created_by values."""
        db_manager, engine, _ = test_db
        
        # Insert hosts with NULL created_by
        with engine.connect() as conn:
            conn.execute(text(
                "INSERT INTO hosts (hostname, current_ip, status, created_by, first_seen, last_seen, created_at, updated_at) "
                "VALUES ('null-host1', '192.168.1.1', 'online', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ))
            conn.execute(text(
                "INSERT INTO hosts (hostname, current_ip, status, created_by, first_seen, last_seen, created_at, updated_at) "
                "VALUES ('null-host2', '192.168.1.2', 'online', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ))
            conn.execute(text(
                "INSERT INTO hosts (hostname, current_ip, status, created_by, first_seen, last_seen, created_at, updated_at) "
                "VALUES ('valid-host', '192.168.1.3', 'online', 'user-123', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ))
            conn.commit()
        
        # Run migration
        migrations = DatabaseMigrations(db_manager)
        migrations._migrate_to_v4()
        
        # Check that NULL values were updated
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT hostname, created_by FROM hosts ORDER BY hostname"
            ))
            hosts = result.fetchall()
        
        # All hosts should have created_by set
        for hostname, created_by in hosts:
            assert created_by is not None, f"Host {hostname} should have created_by set"
            
        # NULL hosts should be assigned to system user
        system_user_id = "00000000-0000-0000-0000-000000000000"
        null_hosts = [h for h in hosts if h[0].startswith('null-host')]
        for hostname, created_by in null_hosts:
            assert created_by == system_user_id, f"Host {hostname} should be assigned to system user"
            
        # Valid host should keep its original value
        valid_host = next(h for h in hosts if h[0] == 'valid-host')
        assert valid_host[1] == 'user-123', "Existing created_by values should be preserved"
        
    def test_migration_is_idempotent(self, test_db):
        """Test that migration can be run multiple times safely."""
        db_manager, engine, _ = test_db
        
        # Insert test data
        with engine.connect() as conn:
            conn.execute(text(
                "INSERT INTO hosts (hostname, current_ip, status, created_by, first_seen, last_seen, created_at, updated_at) "
                "VALUES ('test-host', '192.168.1.1', 'online', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ))
            conn.commit()
        
        migrations = DatabaseMigrations(db_manager)
        
        # Run migration twice
        migrations._migrate_to_v4()
        migrations._migrate_to_v4()  # Should not fail
        
        # Verify data is still correct
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM hosts"))
            count = result.scalar()
            assert count == 1, "Should still have only one host"
            
    def test_host_model_validates_created_by(self, test_db):
        """Test that Host model validates created_by is not None."""
        _, engine, _ = test_db
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Try to create host without created_by
        with pytest.raises(ValueError) as exc_info:
            host = Host(
                hostname="test-host",
                current_ip="192.168.1.1"
                # created_by intentionally omitted
            )
            session.add(host)
            session.commit()
            
        assert "created_by is required" in str(exc_info.value)
        session.rollback()
        session.close()