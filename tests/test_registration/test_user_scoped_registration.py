#!/usr/bin/env python3
"""
Tests for user-scoped host registration (SCRUM-128).
Tests that host registrations are automatically assigned to the authenticated user.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from server.database.models import Base, Host
from server.database.connection import DatabaseManager
from server.registration_processor import RegistrationProcessor, RegistrationResult
from server.auth.models import User

# Mark all async tests
pytestmark = pytest.mark.asyncio


class TestUserScopedRegistration:
    """Test suite for user-scoped host registration."""

    @pytest.fixture
    def test_db(self, tmp_path):
        """Create a test database."""
        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        
        # Create engine and tables
        engine = create_engine(db_url)
        Base.metadata.create_all(engine)
        
        # Create database manager
        config = {
            "database": {
                "path": str(db_path),
                "connection_pool_size": 5
            }
        }
        db_manager = DatabaseManager(config)
        db_manager.engine = engine
        
        return db_manager, engine
    
    @pytest.fixture
    def test_user(self):
        """Create a test user."""
        user = Mock(spec=User)
        user.id = "test-user-123"
        user.username = "testuser"
        user.email = "testuser@example.com"
        user.is_active = True
        user.email_verified = True
        return user
    
    @pytest.fixture
    def registration_processor(self, test_db):
        """Create a registration processor with test database."""
        db_manager, _ = test_db
        config = {
            "database": {
                "path": db_manager.config.path,
                "connection_pool_size": 5
            },
            "registration": {
                "enable_ip_tracking": True,
                "enable_event_logging": True
            }
        }
        processor = RegistrationProcessor(config)
        processor.db_manager = db_manager
        return processor

    async def test_host_registration_assigns_user(self, registration_processor, test_user, test_db):
        """Test that registering a host assigns current user."""
        db_manager, engine = test_db
        
        # Register host with user context
        result = await registration_processor.process_registration(
            hostname="myhost.example.com",
            client_ip="192.168.1.100",
            message_timestamp=datetime.now(timezone.utc).isoformat(),
            user_id=test_user.id  # Pass user context
        )
        
        # Verify registration succeeded
        assert result.success is True
        assert result.result_type == "new_registration"
        
        # Verify host has created_by set to user
        with db_manager.get_session() as session:
            host = session.query(Host).filter(Host.hostname == "myhost.example.com").first()
            assert host is not None
            assert host.created_by == test_user.id
    
    async def test_registration_without_user_fails(self, registration_processor, test_db):
        """Test that registration without user context fails."""
        # Try to register without user_id
        with pytest.raises(ValueError) as exc_info:
            await registration_processor.process_registration(
                hostname="myhost.example.com",
                client_ip="192.168.1.100",
                message_timestamp=datetime.now(timezone.utc).isoformat()
                # user_id intentionally omitted
            )
        
        assert "user_id is required" in str(exc_info.value)
    
    async def test_different_users_have_separate_hosts(self, registration_processor, test_db):
        """Test that different users can have same hostname."""
        db_manager, engine = test_db
        
        # User A registers "webserver"
        user_a_id = "user-a-123"
        result_a = await registration_processor.process_registration(
            hostname="webserver",
            client_ip="192.168.1.100",
            message_timestamp=datetime.now(timezone.utc).isoformat(),
            user_id=user_a_id
        )
        assert result_a.success is True
        
        # User B registers "webserver" with different IP
        user_b_id = "user-b-456"
        result_b = await registration_processor.process_registration(
            hostname="webserver",
            client_ip="192.168.1.101",
            message_timestamp=datetime.now(timezone.utc).isoformat(),
            user_id=user_b_id
        )
        assert result_b.success is True
        
        # Verify both hosts exist with different owners
        with db_manager.get_session() as session:
            hosts = session.query(Host).filter(Host.hostname == "webserver").all()
            assert len(hosts) == 2
            
            # Check that they have different owners
            created_by_values = {host.created_by for host in hosts}
            assert created_by_values == {user_a_id, user_b_id}
            
            # Check that they have different IPs
            ips = {host.current_ip for host in hosts}
            assert ips == {"192.168.1.100", "192.168.1.101"}
    
    async def test_host_update_preserves_user(self, registration_processor, test_user, test_db):
        """Test that updating a host preserves the original user assignment."""
        db_manager, engine = test_db
        
        # Initial registration
        result1 = await registration_processor.process_registration(
            hostname="updatehost.example.com",
            client_ip="192.168.1.100",
            message_timestamp=datetime.now(timezone.utc).isoformat(),
            user_id=test_user.id
        )
        assert result1.success is True
        
        # Update registration (heartbeat/IP change)
        result2 = await registration_processor.process_registration(
            hostname="updatehost.example.com",
            client_ip="192.168.1.200",  # Different IP
            message_timestamp=datetime.now(timezone.utc).isoformat(),
            user_id=test_user.id
        )
        assert result2.success is True
        assert result2.result_type == "ip_change"
        
        # Verify user assignment unchanged
        with db_manager.get_session() as session:
            host = session.query(Host).filter(Host.hostname == "updatehost.example.com").first()
            assert host.created_by == test_user.id
            assert host.current_ip == "192.168.1.200"
    
    async def test_invalid_user_id_format(self, registration_processor):
        """Test that invalid user ID format is rejected."""
        # Try registration with invalid characters
        with pytest.raises(ValueError) as exc_info:
            await registration_processor.process_registration(
                hostname="test.example.com",
                client_ip="192.168.1.100",
                message_timestamp=datetime.now(timezone.utc).isoformat(),
                user_id="invalid@user!id"  # Contains invalid characters
            )
        
        assert "Invalid user_id format" in str(exc_info.value)
    
    # TODO: Implement TCP authentication and then enable this test
    # async def test_registration_with_auth_token(self, registration_processor, test_user, test_db):
    #     """Test that registration can extract user from auth token."""
    #     # This test will be implemented when TCP authentication is added