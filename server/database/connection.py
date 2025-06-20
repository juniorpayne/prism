#!/usr/bin/env python3
"""
Database Connection Management for Prism DNS Server (SCRUM-13)
Handles SQLite connections, pooling, and session management.
"""

import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator, Optional

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base

logger = logging.getLogger(__name__)


class DatabaseConfigError(Exception):
    """Exception raised for database configuration errors."""

    pass


class DatabaseConfig:
    """Database configuration handler with validation and defaults."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize database configuration.

        Args:
            config: Configuration dictionary

        Raises:
            DatabaseConfigError: If configuration is invalid
        """
        try:
            db_config = config["database"]
        except KeyError:
            raise DatabaseConfigError("Missing 'database' section in configuration")

        # Required fields
        if "path" not in db_config:
            raise DatabaseConfigError("Missing required field: database.path")

        self.path = db_config["path"]

        # Optional fields with defaults
        self.connection_pool_size = db_config.get("connection_pool_size", 20)
        self.pool_recycle = db_config.get("pool_recycle", 3600)  # 1 hour
        self.pool_timeout = db_config.get("pool_timeout", 30)
        self.echo = db_config.get("echo", False)  # SQL logging

        # Validate configuration
        self._validate()

    def _validate(self) -> None:
        """Validate configuration values."""
        if self.connection_pool_size < 1:
            raise DatabaseConfigError("connection_pool_size must be positive")

        if self.pool_timeout < 1:
            raise DatabaseConfigError("pool_timeout must be positive")

        # Ensure directory exists for database file (if possible)
        try:
            db_path = Path(self.path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            # If we can't create the directory, we'll let SQLAlchemy handle it
            # This allows for testing with invalid paths
            logger.warning(f"Could not ensure database directory exists: {e}")


class DatabaseManager:
    """
    Manages database connections, sessions, and schema operations.

    Provides connection pooling, session management, and database operations
    for the Prism DNS Server.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize database manager.

        Args:
            config: Database configuration dictionary
        """
        self.config = DatabaseConfig(config)
        self.engine: Optional[Engine] = None
        self.session_factory: Optional[sessionmaker] = None
        self._scoped_session: Optional[scoped_session] = None

        self._initialize_engine()
        self._initialize_sessions()

    def _initialize_engine(self) -> None:
        """Initialize SQLAlchemy engine with proper configuration."""
        # Create SQLite database URL
        db_url = f"sqlite:///{self.config.path}"

        # Engine configuration for SQLite
        engine_kwargs = {
            "poolclass": StaticPool,
            "pool_pre_ping": True,
            "pool_recycle": self.config.pool_recycle,
            "echo": self.config.echo,
            "connect_args": {
                "check_same_thread": False,  # Allow multi-threading
                "timeout": self.config.pool_timeout,
            },
        }

        try:
            self.engine = create_engine(db_url, **engine_kwargs)

            # Configure SQLite settings
            self._configure_sqlite()

            logger.info(f"Database engine initialized: {self.config.path}")

        except Exception as e:
            logger.error(f"Failed to initialize database engine: {e}")
            raise

    def _configure_sqlite(self) -> None:
        """Configure SQLite-specific settings."""

        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set SQLite pragmas for better performance and reliability."""
            cursor = dbapi_connection.cursor()

            # Enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys=ON")

            # Set WAL mode for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL")

            # Set synchronous mode for better performance
            cursor.execute("PRAGMA synchronous=NORMAL")

            # Set cache size (negative value = KB)
            cursor.execute("PRAGMA cache_size=-64000")  # 64MB

            # Set busy timeout
            cursor.execute("PRAGMA busy_timeout=30000")  # 30 seconds

            cursor.close()

    def _initialize_sessions(self) -> None:
        """Initialize session factory and scoped sessions."""
        if not self.engine:
            raise RuntimeError("Engine must be initialized before sessions")

        # Create session factory
        self.session_factory = sessionmaker(
            bind=self.engine, autocommit=False, autoflush=True, expire_on_commit=False
        )

        # Create scoped session for thread-local sessions
        self._scoped_session = scoped_session(self.session_factory)

        logger.info("Database sessions initialized")

    def initialize_schema(self) -> None:
        """
        Create database schema if it doesn't exist.

        Raises:
            SQLAlchemyError: If schema creation fails
        """
        try:
            # Create all tables
            Base.metadata.create_all(self.engine)
            logger.info("Database schema initialized")

        except SQLAlchemyError as e:
            logger.error(f"Failed to initialize database schema: {e}")
            raise

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session with automatic cleanup.

        Yields:
            SQLAlchemy session

        Example:
            with db_manager.get_session() as session:
                host = session.query(Host).first()
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_scoped_session(self) -> scoped_session:
        """
        Get thread-local scoped session.

        Returns:
            Scoped session instance
        """
        return self._scoped_session

    def health_check(self) -> bool:
        """
        Perform database health check.

        Returns:
            True if database is healthy, False otherwise
        """
        try:
            from sqlalchemy import text

            with self.get_session() as session:
                # Simple query to test connection
                session.execute(text("SELECT 1"))
            return True

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get database connection information.

        Returns:
            Dictionary with connection details
        """
        return {
            "database_path": self.config.path,
            "engine_url": str(self.engine.url),
            "pool_size": self.config.connection_pool_size,
            "pool_checked_in": self.engine.pool.checkedin(),
            "pool_checked_out": self.engine.pool.checkedout(),
            "pool_size_current": self.engine.pool.size(),
        }

    def cleanup(self) -> None:
        """Clean up database resources."""
        try:
            if self._scoped_session:
                self._scoped_session.remove()

            if self.engine:
                self.engine.dispose()

            logger.info("Database resources cleaned up")

        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()


class AsyncDatabaseManager:
    """
    Async database manager for async operations.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize async database manager."""
        self.config = DatabaseConfig(config)
        self.engine = None
        self.async_session_maker = None
        self._initialize_async_engine()

    def _initialize_async_engine(self):
        """Initialize async SQLAlchemy engine."""
        try:
            # Create database URL (convert from sync to async)
            if self.config.path == ":memory:":
                url = "sqlite+aiosqlite:///:memory:"
            else:
                url = f"sqlite+aiosqlite:///{self.config.path}"

            # Create async engine
            self.engine = create_async_engine(
                url, echo=False, pool_pre_ping=True, connect_args={"check_same_thread": False}
            )

            # Create async session factory
            self.async_session_maker = async_sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )

            logger.info(f"Async database engine initialized: {url}")

        except Exception as e:
            logger.error(f"Failed to initialize async database engine: {e}")
            raise DatabaseConfigError(f"Failed to initialize async database: {e}")

    async def create_tables(self):
        """Create database tables asynchronously."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session."""
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def cleanup(self):
        """Clean up async database resources."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Async database resources cleaned up")


# Global async database manager instance
_async_db_manager: Optional[AsyncDatabaseManager] = None


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get async database session.

    Usage in FastAPI:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_async_db)):
            ...
    """
    if _async_db_manager is None:
        raise RuntimeError("Async database not initialized. Call init_async_db() first.")

    async for session in _async_db_manager.get_session():
        yield session


def init_async_db(config: Dict[str, Any]):
    """Initialize async database manager."""
    global _async_db_manager
    _async_db_manager = AsyncDatabaseManager(config)
    return _async_db_manager
