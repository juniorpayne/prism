#!/usr/bin/env python3
"""
Test fixtures for authentication tests.
"""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from server.api.app import create_app

# Import all auth models to ensure they're registered with Base
from server.auth.models import (
    APIKey,
    DNSZone,
    EmailVerificationToken,
    Organization,
    PasswordResetToken,
    RefreshToken,
    User,
    UserOrganization,
)
from server.database.connection import get_async_db
from server.database.models import Base

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def app():
    """Create FastAPI app for tests."""
    import tempfile

    # Create a temporary file for the test database
    # This ensures all connections use the same database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    test_config = {
        "server": {"host": "127.0.0.1", "tcp_port": 8080, "api_port": 8081, "max_connections": 100},
        "database": {"path": db_path, "connection_pool_size": 5},
        "api": {
            "enable_cors": True,
            "cors_origins": ["http://localhost:3000"],
            "request_timeout": 30,
        },
        "heartbeat": {
            "check_interval": 30,
            "timeout_multiplier": 2,
            "grace_period": 30,
            "cleanup_after_days": 30,
        },
        "logging": {"level": "INFO", "file": "test.log", "max_size": 10485760, "backup_count": 3},
        "powerdns": {"enabled": False},
    }

    # Create tables in the temp database
    from sqlalchemy import create_engine

    sync_engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    app = create_app(test_config)

    yield app

    # Cleanup
    import os

    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest_asyncio.fixture(scope="function")
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for tests."""
    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def db_session(app):
    """Get database session from app for testing."""
    from server.database.connection import _async_db_manager

    if _async_db_manager is None:
        # If not initialized, get from app config
        from server.database.connection import init_async_db

        config = app.extra.get("config", {})
        init_async_db(config)

    async for session in _async_db_manager.get_session():
        yield session
        await session.rollback()  # Rollback any changes made in tests
