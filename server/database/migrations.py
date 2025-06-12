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
                # Add DNS tracking columns
                session.execute(
                    text(
                        """
                    ALTER TABLE hosts ADD COLUMN dns_zone VARCHAR(255)
                """
                    )
                )

                session.execute(
                    text(
                        """
                    ALTER TABLE hosts ADD COLUMN dns_record_id VARCHAR(255)
                """
                    )
                )

                session.execute(
                    text(
                        """
                    ALTER TABLE hosts ADD COLUMN dns_ttl INTEGER
                """
                    )
                )

                session.execute(
                    text(
                        """
                    ALTER TABLE hosts ADD COLUMN dns_sync_status VARCHAR(20) DEFAULT 'pending'
                """
                    )
                )

                session.execute(
                    text(
                        """
                    ALTER TABLE hosts ADD COLUMN dns_last_sync TIMESTAMP
                """
                    )
                )

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
