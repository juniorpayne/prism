#!/usr/bin/env python3
"""
Database Migration System for Prism DNS Server (SCRUM-13)
Handles database schema versioning and upgrades.
"""

import logging
from typing import Any, Callable, Dict, List

from sqlalchemy import MetaData, Table, text
from sqlalchemy.exc import SQLAlchemyError

from .connection import DatabaseManager
from .models import SCHEMA_VERSION

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Exception raised for migration errors."""

    pass


class DatabaseMigrations:
    """
    Database migration management system.

    Handles schema versioning, upgrades, and maintains database compatibility
    across different versions of the application.
    """

    def __init__(self, database_manager: DatabaseManager):
        """
        Initialize migration manager.

        Args:
            database_manager: Database manager instance
        """
        self.db_manager = database_manager
        self._migrations: Dict[int, Callable] = {}
        self._register_migrations()

    def _register_migrations(self) -> None:
        """Register all available migrations."""
        # Migration from version 0 (initial) to version 1
        self._migrations[1] = self._migrate_to_v1
        # Migration from version 1 to version 2 (PowerDNS integration)
        self._migrations[2] = self._migrate_to_v2
        # Migration from version 2 to version 3 (Multi-tenancy fields)
        self._migrations[3] = self._migrate_to_v3
        # Migration from version 3 to version 4 (User isolation - enforce created_by)
        self._migrations[4] = self._migrate_to_v4
        # Migration from version 4 to version 5 (User-scoped hostnames)
        self._migrations[5] = self._migrate_to_v5
        # Migration from version 5 to version 6 (DNS zone ownership tracking)
        self._migrations[6] = self._migrate_to_v6
        # Migration from version 6 to version 7 (Add is_admin field to users)
        self._migrations[7] = self._migrate_to_v7

    def get_current_schema_version(self) -> int:
        """
        Get current database schema version.

        Returns:
            Current schema version or 0 if not initialized
        """
        try:
            with self.db_manager.get_session() as session:
                # Check if schema_version table exists
                try:
                    result = session.execute(
                        text("SELECT version FROM schema_version ORDER BY id DESC LIMIT 1")
                    )
                    row = result.fetchone()
                    return row[0] if row else 0
                except SQLAlchemyError:
                    # Table doesn't exist, database is uninitialized
                    return 0

        except SQLAlchemyError as e:
            logger.error(f"Error getting schema version: {e}")
            return 0

    def create_schema_version_table(self) -> None:
        """Create schema version tracking table."""
        try:
            with self.db_manager.get_session() as session:
                session.execute(
                    text(
                        """
                    CREATE TABLE IF NOT EXISTS schema_version (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        version INTEGER NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        description TEXT
                    )
                """
                    )
                )

                logger.info("Schema version table created")

        except SQLAlchemyError as e:
            logger.error(f"Error creating schema version table: {e}")
            raise MigrationError(f"Failed to create schema version table: {e}")

    def record_migration(self, version: int, description: str) -> None:
        """
        Record a migration in the schema version table.

        Args:
            version: Schema version number
            description: Migration description
        """
        try:
            with self.db_manager.get_session() as session:
                session.execute(
                    text(
                        "INSERT INTO schema_version (version, description) VALUES (:version, :description)"
                    ),
                    {"version": version, "description": description},
                )

                logger.info(f"Recorded migration to version {version}: {description}")

        except SQLAlchemyError as e:
            logger.error(f"Error recording migration: {e}")
            raise MigrationError(f"Failed to record migration: {e}")

    def migrate_to_latest(self) -> None:
        """
        Migrate database to the latest schema version.

        Raises:
            MigrationError: If migration fails
        """
        current_version = self.get_current_schema_version()
        target_version = SCHEMA_VERSION

        if current_version == target_version:
            logger.info(f"Database already at latest version {target_version}")
            return

        if current_version > target_version:
            raise MigrationError(
                f"Database version {current_version} is newer than application version {target_version}"
            )

        logger.info(f"Migrating database from version {current_version} to {target_version}")

        # Ensure schema version table exists
        if current_version == 0:
            self.create_schema_version_table()

        # Apply migrations sequentially
        for version in range(current_version + 1, target_version + 1):
            if version not in self._migrations:
                raise MigrationError(f"Migration to version {version} not found")

            logger.info(f"Applying migration to version {version}")

            try:
                self._migrations[version]()
                self.record_migration(version, f"Migration to version {version}")

            except Exception as e:
                logger.error(f"Migration to version {version} failed: {e}")
                raise MigrationError(f"Migration to version {version} failed: {e}")

        logger.info(f"Database migration completed to version {target_version}")

    def _migrate_to_v1(self) -> None:
        """
        Migration to version 1: Create initial schema.

        This migration creates the hosts table and initial indexes.
        """
        logger.info("Applying migration to version 1: Initial schema")

        try:
            # Initialize the schema using our models
            self.db_manager.initialize_schema()

            # Additional setup if needed
            with self.db_manager.get_session() as session:
                # Create additional indexes for performance
                session.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_hosts_last_seen_status 
                    ON hosts(last_seen, status)
                """
                    )
                )

                session.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_hosts_created_at 
                    ON hosts(created_at)
                """
                    )
                )

            logger.info("Initial schema migration completed")

        except SQLAlchemyError as e:
            logger.error(f"Initial schema migration failed: {e}")
            raise

    def _migrate_to_v2(self) -> None:
        """
        Migration to version 2: Add PowerDNS integration fields.

        This migration adds DNS tracking fields to the hosts table.
        """
        logger.info("Applying migration to version 2: PowerDNS integration")

        try:
            with self.db_manager.get_session() as session:
                # Check if columns already exist
                result = session.execute(text("PRAGMA table_info(hosts)"))
                existing_columns = {row[1] for row in result.fetchall()}

                # Add DNS tracking columns only if they don't exist
                if "dns_zone" not in existing_columns:
                    session.execute(text("ALTER TABLE hosts ADD COLUMN dns_zone VARCHAR(255)"))

                if "dns_record_id" not in existing_columns:
                    session.execute(text("ALTER TABLE hosts ADD COLUMN dns_record_id VARCHAR(255)"))

                if "dns_ttl" not in existing_columns:
                    session.execute(text("ALTER TABLE hosts ADD COLUMN dns_ttl INTEGER"))

                if "dns_sync_status" not in existing_columns:
                    session.execute(
                        text(
                            "ALTER TABLE hosts ADD COLUMN dns_sync_status VARCHAR(20) DEFAULT 'pending'"
                        )
                    )

                if "dns_last_sync" not in existing_columns:
                    session.execute(text("ALTER TABLE hosts ADD COLUMN dns_last_sync TIMESTAMP"))

                # Create index for DNS sync status
                session.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_hosts_dns_sync_status 
                    ON hosts(dns_sync_status)
                """
                    )
                )

            logger.info("PowerDNS integration migration completed")

        except SQLAlchemyError as e:
            logger.error(f"PowerDNS integration migration failed: {e}")
            raise

    def _migrate_to_v3(self) -> None:
        """
        Migration to version 3: Add multi-tenancy fields.

        This migration adds org_id, zone_id, and created_by fields for multi-tenancy support.
        """
        logger.info("Applying migration to version 3: Multi-tenancy fields")

        try:
            with self.db_manager.get_session() as session:
                # Check if columns already exist
                result = session.execute(text("PRAGMA table_info(hosts)"))
                existing_columns = {row[1] for row in result.fetchall()}

                # Add multi-tenancy columns only if they don't exist
                if "org_id" not in existing_columns:
                    session.execute(text("ALTER TABLE hosts ADD COLUMN org_id VARCHAR(36)"))

                if "zone_id" not in existing_columns:
                    session.execute(text("ALTER TABLE hosts ADD COLUMN zone_id VARCHAR(36)"))

                if "created_by" not in existing_columns:
                    session.execute(text("ALTER TABLE hosts ADD COLUMN created_by VARCHAR(36)"))

                # Create indexes for multi-tenancy fields
                session.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_hosts_org_id 
                    ON hosts(org_id)
                """
                    )
                )

                session.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_hosts_zone_id 
                    ON hosts(zone_id)
                """
                    )
                )

            logger.info("Multi-tenancy migration completed")

        except SQLAlchemyError as e:
            logger.error(f"Multi-tenancy migration failed: {e}")
            raise

    def _migrate_to_v4(self) -> None:
        """
        Migration to version 4: Enforce user isolation with created_by field.
        
        This migration:
        1. Updates any NULL created_by values to system user
        2. Makes created_by field NOT NULL
        3. Adds index on created_by for performance
        """
        logger.info("Applying migration to version 4: User isolation enforcement")
        
        system_user_id = "00000000-0000-0000-0000-000000000000"
        
        try:
            with self.db_manager.get_session() as session:
                # First, update any NULL created_by values to system user
                logger.info("Updating NULL created_by values to system user")
                update_result = session.execute(
                    text(
                        "UPDATE hosts SET created_by = :system_user_id WHERE created_by IS NULL"
                    ),
                    {"system_user_id": system_user_id}
                )
                updated_count = update_result.rowcount
                logger.info(f"Updated {updated_count} hosts with system user")
                
                # SQLite doesn't support ALTER COLUMN to add NOT NULL constraint directly
                # We need to recreate the table with the constraint
                
                # Check if we've already done this migration (idempotency)
                result = session.execute(text("PRAGMA table_info(hosts)"))
                columns = result.fetchall()
                created_by_col = next((col for col in columns if col[1] == 'created_by'), None)
                
                if created_by_col and created_by_col[3] == 0:  # notnull is 0 (nullable)
                    logger.info("Recreating hosts table with NOT NULL constraint on created_by")
                    
                    # Create temporary table with new schema
                    session.execute(text("""
                        CREATE TABLE hosts_new (
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
                            created_by VARCHAR(36) NOT NULL,
                            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    
                    # Copy data from old table with explicit column mapping
                    session.execute(text("""
                        INSERT INTO hosts_new (
                            id, hostname, current_ip, first_seen, last_seen, status,
                            dns_zone, dns_record_id, dns_ttl, dns_sync_status, dns_last_sync,
                            org_id, zone_id, created_by, created_at, updated_at
                        )
                        SELECT 
                            id, hostname, current_ip, first_seen, last_seen, status,
                            dns_zone, dns_record_id, dns_ttl, dns_sync_status, dns_last_sync,
                            org_id, zone_id, created_by, created_at, updated_at
                        FROM hosts
                    """))
                    
                    # Drop old table and rename new table
                    session.execute(text("DROP TABLE hosts"))
                    session.execute(text("ALTER TABLE hosts_new RENAME TO hosts"))
                    
                    # Recreate indexes
                    session.execute(text("CREATE UNIQUE INDEX idx_hostname ON hosts(hostname)"))
                    session.execute(text("CREATE INDEX idx_hostname_status ON hosts(hostname, status)"))
                    session.execute(text("CREATE INDEX idx_last_seen_status ON hosts(last_seen, status)"))
                    session.execute(text("CREATE INDEX idx_hosts_org_id ON hosts(org_id)"))
                    session.execute(text("CREATE INDEX idx_hosts_zone_id ON hosts(zone_id)"))
                else:
                    logger.info("created_by field already has NOT NULL constraint")
                
                # Create index on created_by if it doesn't exist
                session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_hosts_created_by 
                    ON hosts(created_by)
                """))
                
                logger.info("User isolation enforcement migration completed")
                
        except SQLAlchemyError as e:
            logger.error(f"User isolation enforcement migration failed: {e}")
            raise MigrationError(f"Migration to version 4 failed: {e}")
    
    def _migrate_to_v5(self) -> None:
        """
        Migration to version 5: Enable user-scoped hostnames.
        
        This migration:
        1. Removes unique constraint on hostname
        2. Adds composite unique constraint on (hostname, created_by)
        3. Allows different users to have hosts with the same hostname
        """
        logger.info("Applying migration to version 5: User-scoped hostnames")
        
        try:
            with self.db_manager.get_session() as session:
                # SQLite doesn't support dropping constraints, so we need to recreate the table
                logger.info("Recreating hosts table with user-scoped hostname constraint")
                
                # Create new table with updated constraints
                session.execute(text("""
                    CREATE TABLE hosts_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        hostname VARCHAR(255) NOT NULL,
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
                        created_by VARCHAR(36) NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(hostname, created_by)
                    )
                """))
                
                # Copy data from old table with explicit column mapping
                session.execute(text("""
                    INSERT INTO hosts_new (
                        id, hostname, current_ip, first_seen, last_seen, status,
                        dns_zone, dns_record_id, dns_ttl, dns_sync_status, dns_last_sync,
                        org_id, zone_id, created_by, created_at, updated_at
                    )
                    SELECT 
                        id, hostname, current_ip, first_seen, last_seen, status,
                        dns_zone, dns_record_id, dns_ttl, dns_sync_status, dns_last_sync,
                        org_id, zone_id, created_by, created_at, updated_at
                    FROM hosts
                """))
                
                # Drop old table and rename new table
                session.execute(text("DROP TABLE hosts"))
                session.execute(text("ALTER TABLE hosts_new RENAME TO hosts"))
                
                # Recreate indexes
                session.execute(text("CREATE INDEX idx_hostname ON hosts(hostname)"))
                session.execute(text("CREATE INDEX idx_hostname_status ON hosts(hostname, status)"))
                session.execute(text("CREATE INDEX idx_last_seen_status ON hosts(last_seen, status)"))
                session.execute(text("CREATE INDEX idx_hosts_created_by ON hosts(created_by)"))
                session.execute(text("CREATE INDEX idx_hosts_org_id ON hosts(org_id)"))
                session.execute(text("CREATE INDEX idx_hosts_zone_id ON hosts(zone_id)"))
                
                logger.info("User-scoped hostnames migration completed")
                
        except SQLAlchemyError as e:
            logger.error(f"User-scoped hostnames migration failed: {e}")
            raise MigrationError(f"Migration to version 5 failed: {e}")
    
    def _migrate_to_v6(self) -> None:
        """
        Migration to version 6: Add DNS zone ownership tracking.
        
        Creates dns_zones table to track which users own which DNS zones.
        This enables filtering zones by user without modifying PowerDNS.
        """
        logger.info("Running migration to version 6: DNS zone ownership tracking")
        
        try:
            with self.db_manager.get_session() as session:
                # Create dns_zone_ownership table
                session.execute(text("""
                    CREATE TABLE IF NOT EXISTS dns_zone_ownership (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        zone_name VARCHAR(255) NOT NULL UNIQUE,
                        created_by VARCHAR(36) NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create indexes
                session.execute(text("CREATE INDEX IF NOT EXISTS idx_dns_zone_ownership_zone_name ON dns_zone_ownership(zone_name)"))
                session.execute(text("CREATE INDEX IF NOT EXISTS idx_dns_zone_ownership_created_by ON dns_zone_ownership(created_by)"))
                
                # Add trigger for updated_at
                session.execute(text("""
                    CREATE TRIGGER IF NOT EXISTS update_dns_zone_ownership_updated_at
                    AFTER UPDATE ON dns_zone_ownership
                    BEGIN
                        UPDATE dns_zone_ownership SET updated_at = CURRENT_TIMESTAMP
                        WHERE id = NEW.id;
                    END
                """))
                
                logger.info("DNS zone ownership tracking migration completed")
                
        except SQLAlchemyError as e:
            logger.error(f"DNS zone ownership tracking migration failed: {e}")
            raise MigrationError(f"Migration to version 6 failed: {e}")

    def _migrate_to_v7(self) -> None:
        """
        Migration to version 7: Add is_admin field to users table.
        
        Adds is_admin boolean field to support admin override functionality.
        This enables admins to optionally view all users' data for support.
        """
        logger.info("Running migration to version 7: Add is_admin field to users")
        
        try:
            with self.db_manager.get_session() as session:
                # Check if users table exists
                result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'"))
                if not result.fetchone():
                    logger.info("Users table does not exist, skipping is_admin migration")
                    return
                
                # Check if is_admin column already exists
                result = session.execute(text("PRAGMA table_info(users)"))
                existing_columns = {row[1] for row in result.fetchall()}
                
                if "is_admin" not in existing_columns:
                    # Add is_admin column with default false
                    session.execute(text("""
                        ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0
                    """))
                    logger.info("Added is_admin column to users table")
                else:
                    logger.info("is_admin column already exists in users table")
                
                logger.info("Admin field migration completed")
                
        except SQLAlchemyError as e:
            logger.error(f"Admin field migration failed: {e}")
            raise MigrationError(f"Migration to version 7 failed: {e}")

    def get_migration_history(self) -> List[Dict[str, Any]]:
        """
        Get migration history.

        Returns:
            List of migration records
        """
        try:
            with self.db_manager.get_session() as session:
                result = session.execute(
                    text(
                        """
                    SELECT version, applied_at, description 
                    FROM schema_version 
                    ORDER BY version
                """
                    )
                )

                return [
                    {"version": row[0], "applied_at": row[1], "description": row[2]}
                    for row in result.fetchall()
                ]

        except SQLAlchemyError as e:
            logger.error(f"Error getting migration history: {e}")
            return []

    def validate_schema(self) -> bool:
        """
        Validate current database schema.

        Returns:
            True if schema is valid, False otherwise
        """
        try:
            # Check that all expected tables exist
            metadata = MetaData()
            metadata.reflect(bind=self.db_manager.engine)

            expected_tables = ["hosts", "schema_version"]
            existing_tables = list(metadata.tables.keys())

            for table in expected_tables:
                if table not in existing_tables:
                    logger.error(f"Missing expected table: {table}")
                    return False

            # Check hosts table structure
            hosts_table = metadata.tables.get("hosts")
            if hosts_table is None:
                logger.error("hosts table not found")
                return False

            expected_columns = [
                "id",
                "hostname",
                "current_ip",
                "first_seen",
                "last_seen",
                "status",
                "dns_zone",
                "dns_record_id",
                "dns_ttl",
                "dns_sync_status",
                "dns_last_sync",
                "org_id",
                "zone_id",
                "created_by",
                "created_at",
                "updated_at",
            ]

            existing_columns = [col.name for col in hosts_table.columns]

            for column in expected_columns:
                if column not in existing_columns:
                    logger.error(f"Missing expected column in hosts table: {column}")
                    return False

            logger.info("Schema validation passed")
            return True

        except SQLAlchemyError as e:
            logger.error(f"Schema validation failed: {e}")
            return False

    def reset_database(self) -> None:
        """
        Reset database by dropping all tables and recreating schema.

        WARNING: This will delete all data!
        """
        logger.warning("Resetting database - all data will be lost!")

        try:
            # Drop all tables
            metadata = MetaData()
            metadata.reflect(bind=self.db_manager.engine)
            metadata.drop_all(bind=self.db_manager.engine)

            # Recreate schema
            self.migrate_to_latest()

            logger.info("Database reset completed")

        except SQLAlchemyError as e:
            logger.error(f"Database reset failed: {e}")
            raise MigrationError(f"Database reset failed: {e}")


def init_database(database_manager: DatabaseManager) -> None:
    """
    Initialize database with proper migrations.

    Args:
        database_manager: Database manager instance
    """
    migrations = DatabaseMigrations(database_manager)
    migrations.migrate_to_latest()

    # Validate schema after migration
    if not migrations.validate_schema():
        raise MigrationError("Schema validation failed after migration")
