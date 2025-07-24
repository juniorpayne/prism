"""Test cases for host filtering by user functionality."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4, UUID
from unittest.mock import MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from server.api.routes.hosts import get_hosts, get_host, get_host_stats
from server.auth.models import User
from server.database.models import Host
from fastapi import HTTPException


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "admin@example.com"
    user.username = "admin"
    user.is_admin = True
    return user


@pytest.fixture
def mock_regular_user():
    """Create a mock regular user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "user@example.com"
    user.username = "regularuser"
    user.is_admin = False
    return user


@pytest.fixture
def mock_other_user():
    """Create another regular user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "other@example.com"
    user.username = "otheruser"
    user.is_admin = False
    return user


@pytest.fixture
def mock_hosts(mock_regular_user, mock_other_user):
    """Create mock hosts for testing."""
    now = datetime.now(timezone.utc)
    
    # Regular user's hosts
    user_host1 = MagicMock(spec=Host)
    user_host1.id = 1
    user_host1.hostname = "host1.example.com"
    user_host1.current_ip = "192.168.1.10"
    user_host1.status = "online"
    user_host1.last_seen = now
    user_host1.first_seen = now
    user_host1.created_by = str(mock_regular_user.id)
    
    user_host2 = MagicMock(spec=Host)
    user_host2.id = 2
    user_host2.hostname = "host2.example.com"
    user_host2.current_ip = "192.168.1.11"
    user_host2.status = "offline"
    user_host2.last_seen = now
    user_host2.first_seen = now
    user_host2.created_by = str(mock_regular_user.id)
    
    # Other user's host
    other_host = MagicMock(spec=Host)
    other_host.id = 3
    other_host.hostname = "other.example.com"
    other_host.current_ip = "192.168.1.20"
    other_host.status = "online"
    other_host.last_seen = now
    other_host.first_seen = now
    other_host.created_by = str(mock_other_user.id)
    
    return [user_host1, user_host2, other_host]


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock(spec=AsyncSession)
    return db


@pytest.fixture 
def mock_host_ops(mock_hosts):
    """Create mock host operations."""
    host_ops = MagicMock()
    
    # Default to returning all hosts
    host_ops.get_all_hosts.return_value = mock_hosts
    host_ops.get_hosts_by_status.return_value = mock_hosts
    
    return host_ops


class TestHostListFiltering:
    """Test host list filtering by user."""
    
    @pytest.mark.asyncio
    async def test_regular_user_sees_only_own_hosts(self, mock_regular_user, mock_hosts, mock_host_ops):
        """Test that regular users only see their own hosts."""
        # Filter mock hosts to only user's hosts
        user_hosts = [h for h in mock_hosts if h.created_by == str(mock_regular_user.id)]
        mock_host_ops.get_all_hosts.return_value = user_hosts
        
        # Call the endpoint
        result = await get_hosts(
            all=False,
            page=1,
            per_page=50,
            status=None,
            search=None,
            current_user=mock_regular_user,
            host_ops=mock_host_ops
        )
        
        # Verify results
        assert len(result.hosts) == 2
        assert all(h.hostname in ["host1.example.com", "host2.example.com"] for h in result.hosts)
        
        # Verify host_ops was called with user ID
        mock_host_ops.get_all_hosts.assert_called_with(user_id=str(mock_regular_user.id))
        
    @pytest.mark.asyncio
    async def test_admin_sees_all_hosts_with_flag(self, mock_admin_user, mock_hosts, mock_db):
        """Test that admin can see all hosts when all=true."""
        # Admin with all=true should see all hosts
        result = await get_hosts(
            all=True,
            status=None,
            current_user=mock_admin_user,
            db=mock_db
        )
        
        # Should see all 3 hosts
        assert len(result) == 3
        assert any(h.hostname == "other.example.com" for h in result)
        
        # Should include owner information
        assert all(hasattr(h, 'owner') for h in result)
        
    @pytest.mark.asyncio
    async def test_admin_sees_only_own_without_flag(self, mock_admin_user, mock_hosts, mock_db):
        """Test that admin sees only their hosts without all=true."""
        # Filter to admin's hosts (none in this case)
        mock_db._order_by_mock.all.return_value = []
        
        result = await get_hosts(
            all=False,
            status=None,
            current_user=mock_admin_user,
            db=mock_db
        )
        
        # Admin has no hosts
        assert len(result) == 0
        
    @pytest.mark.asyncio
    async def test_status_filter(self, mock_regular_user, mock_hosts, mock_db):
        """Test filtering by status."""
        # Filter to online hosts only
        online_hosts = [h for h in mock_hosts 
                       if h.created_by == str(mock_regular_user.id) and h.status == "online"]
        mock_db._order_by_mock.all.return_value = online_hosts
        
        result = await get_hosts(
            all=False,
            status="online",
            current_user=mock_regular_user,
            db=mock_db
        )
        
        assert len(result) == 1
        assert result[0].status == "online"


class TestHostDetailAccess:
    """Test host detail access control."""
    
    @pytest.mark.asyncio
    async def test_user_can_access_own_host(self, mock_regular_user, mock_hosts, mock_db):
        """Test user can access their own host."""
        host = mock_hosts[0]  # User's host
        
        # Mock query result
        query_result = MagicMock()
        query_result.filter.return_value.first.return_value = host
        mock_db.query.return_value = query_result
        
        result = await get_host(
            host_id=1,
            current_user=mock_regular_user,
            db=mock_db
        )
        
        assert result.id == 1
        assert result.hostname == "host1.example.com"
        
    @pytest.mark.asyncio
    async def test_user_cannot_access_others_host(self, mock_regular_user, mock_hosts, mock_db):
        """Test user cannot access another user's host."""
        other_host = mock_hosts[2]  # Other user's host
        
        # Mock query result
        query_result = MagicMock()
        query_result.filter.return_value.first.return_value = other_host
        mock_db.query.return_value = query_result
        
        with pytest.raises(HTTPException) as exc_info:
            await get_host(
                host_id=3,
                current_user=mock_regular_user,
                db=mock_db
            )
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Host not found"
        
    @pytest.mark.asyncio
    async def test_admin_can_access_any_host(self, mock_admin_user, mock_hosts, mock_db):
        """Test admin can access any host."""
        other_host = mock_hosts[2]
        
        # Mock query result
        query_result = MagicMock()
        query_result.filter.return_value.first.return_value = other_host
        mock_db.query.return_value = query_result
        
        # Mock get_username_by_id
        with pytest.mock.patch('server.api.routes.hosts.get_username_by_id', return_value='otheruser'):
            result = await get_host(
                host_id=3,
                current_user=mock_admin_user,
                db=mock_db
            )
        
        assert result.id == 3
        assert result.owner_username == 'otheruser'


class TestHostStatistics:
    """Test host statistics with user filtering."""
    
    @pytest.mark.asyncio
    async def test_user_stats_only_own_hosts(self, mock_regular_user, mock_hosts, mock_db):
        """Test user statistics only include their hosts."""
        # Filter to user's hosts
        user_hosts = [h for h in mock_hosts if h.created_by == str(mock_regular_user.id)]
        
        query_result = MagicMock()
        query_result.filter.return_value.all.return_value = user_hosts
        mock_db.query.return_value = query_result
        
        result = await get_host_stats(
            current_user=mock_regular_user,
            db=mock_db
        )
        
        assert result["total_hosts"] == 2
        assert result["online_hosts"] == 1
        assert result["offline_hosts"] == 1
        assert "system_stats" not in result  # Not admin
        
    @pytest.mark.asyncio
    async def test_admin_gets_system_stats(self, mock_admin_user, mock_hosts, mock_db):
        """Test admin gets system-wide statistics."""
        # Admin has no hosts
        query_result = MagicMock()
        query_result.filter.return_value.all.return_value = []
        query_result.count.return_value = 3  # Total system hosts
        query_result.distinct.return_value.count.return_value = 2  # Users with hosts
        mock_db.query.return_value = query_result
        
        result = await get_host_stats(
            current_user=mock_admin_user,
            db=mock_db
        )
        
        assert result["total_hosts"] == 0  # Admin's hosts
        assert "system_stats" in result
        assert result["system_stats"]["total_hosts"] == 3
        assert result["system_stats"]["users_with_hosts"] == 2