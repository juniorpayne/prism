#!/usr/bin/env python3
"""
Test host filtering by user (SCRUM-130)
Tests that users only see hosts they own.
"""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from fastapi.testclient import TestClient

from server.auth.models import User
from server.database.models import Host
from server.api.app import create_app
from server.auth.dependencies import get_current_verified_user
from server.api.dependencies import get_database_manager


# Test configuration
test_config = {
    "server": {"host": "0.0.0.0", "tcp_port": 53, "api_port": 8080},
    "database": {"path": ":memory:"},  # Use in-memory database
    "powerdns": {"enabled": False},
    "api": {"cors_origins": ["http://localhost:3000"]},
}


@pytest.fixture
def mock_user_a():
    """Create a mock authenticated user A."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.username = "usera"
    user.email = "usera@example.com"
    user.is_active = True
    return user


@pytest.fixture
def mock_user_b():
    """Create another mock user B."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.username = "userb"
    user.email = "userb@example.com"
    user.is_active = True
    return user


@pytest.fixture
def test_client_user_a(mock_user_a):
    """Test client authenticated as user A."""
    app = create_app(test_config)
    app.dependency_overrides[get_current_verified_user] = lambda: mock_user_a
    # Also mock database manager to avoid connection issues
    mock_db_manager = MagicMock()
    app.dependency_overrides[get_database_manager] = lambda: mock_db_manager
    return TestClient(app)


@pytest.fixture
def test_client_user_b(mock_user_b):
    """Test client authenticated as user B."""
    app = create_app(test_config)
    app.dependency_overrides[get_current_verified_user] = lambda: mock_user_b
    # Also mock database manager to avoid connection issues
    mock_db_manager = MagicMock()
    app.dependency_overrides[get_database_manager] = lambda: mock_db_manager
    return TestClient(app)


def test_users_see_only_their_hosts(test_client_user_a, mock_user_a, mock_user_b):
    """Test that users only see their own hosts."""
    # Create mock hosts
    host_a1 = MagicMock(spec=Host)
    host_a1.hostname = "host-a1"
    host_a1.current_ip = "192.168.1.1"
    host_a1.status = "online"
    host_a1.created_by = str(mock_user_a.id)
    host_a1.first_seen = "2025-01-01T00:00:00Z"
    host_a1.last_seen = "2025-01-01T00:00:00Z"
    
    host_a2 = MagicMock(spec=Host)
    host_a2.hostname = "host-a2"
    host_a2.current_ip = "192.168.1.2"
    host_a2.status = "online"
    host_a2.created_by = str(mock_user_a.id)
    host_a2.first_seen = "2025-01-01T00:00:00Z"
    host_a2.last_seen = "2025-01-01T00:00:00Z"
    
    host_b1 = MagicMock(spec=Host)
    host_b1.hostname = "host-b1"
    host_b1.current_ip = "192.168.1.3"
    host_b1.status = "online"
    host_b1.created_by = str(mock_user_b.id)
    host_b1.first_seen = "2025-01-01T00:00:00Z"
    host_b1.last_seen = "2025-01-01T00:00:00Z"
    
    # Mock host operations to return only user A's hosts
    with patch("server.api.routes.hosts.get_host_operations") as mock_get_ops:
        mock_ops = MagicMock()
        # For user A, return only their hosts
        mock_ops.get_all_hosts.return_value = [host_a1, host_a2]
        mock_get_ops.return_value = mock_ops
        
        # Make request
        response = test_client_user_a.get("/api/hosts")
        
        assert response.status_code == 200
        data = response.json()
        
        # Debug print to see what we get
        print(f"Response data: {data}")
        print(f"Mock calls: {mock_ops.get_all_hosts.call_args_list}")
        
        # User A should only see their 2 hosts
        assert data["total"] == 2
        assert len(data["hosts"]) == 2
        hostnames = [h["hostname"] for h in data["hosts"]]
        assert "host-a1" in hostnames
        assert "host-a2" in hostnames
        assert "host-b1" not in hostnames


def test_cannot_access_other_users_host(test_client_user_a, mock_user_a, mock_user_b):
    """Test that users cannot access other users' host details."""
    # Mock host operations
    with patch("server.api.routes.hosts.get_host_operations") as mock_get_ops:
        mock_ops = MagicMock()
        # When user A tries to get host-b1, return None (not found)
        mock_ops.get_host_by_hostname.return_value = None
        mock_get_ops.return_value = mock_ops
        
        # User A tries to access user B's host
        response = test_client_user_a.get("/api/hosts/host-b1")
        
        # Should return 404 (not 403 to avoid enumeration)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


def test_host_filtering_with_pagination(test_client_user_a, mock_user_a):
    """Test that pagination works with filtered hosts."""
    # Create 5 mock hosts for user A
    hosts = []
    for i in range(5):
        host = MagicMock(spec=Host)
        host.hostname = f"host-{i}"
        host.current_ip = f"192.168.1.{i+1}"
        host.status = "online"
        host.created_by = str(mock_user_a.id)
        host.first_seen = "2025-01-01T00:00:00Z"
        host.last_seen = "2025-01-01T00:00:00Z"
        hosts.append(host)
    
    with patch("server.api.routes.hosts.get_host_operations") as mock_get_ops:
        mock_ops = MagicMock()
        mock_ops.get_all_hosts.return_value = hosts
        mock_get_ops.return_value = mock_ops
        
        # Get page 1 with 2 items per page
        response = test_client_user_a.get("/api/hosts?page=1&per_page=2")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 5
        assert len(data["hosts"]) == 2
        assert data["page"] == 1
        assert data["pages"] == 3  # 5 items / 2 per page = 3 pages


def test_host_status_filter_with_user_filter(test_client_user_a, mock_user_a):
    """Test that status filtering respects user ownership."""
    # Create online and offline hosts
    host_online = MagicMock(spec=Host)
    host_online.hostname = "online-host"
    host_online.current_ip = "192.168.1.1"
    host_online.status = "online"
    host_online.created_by = str(mock_user_a.id)
    host_online.first_seen = "2025-01-01T00:00:00Z"
    host_online.last_seen = "2025-01-01T00:00:00Z"
    
    host_offline = MagicMock(spec=Host)
    host_offline.hostname = "offline-host"
    host_offline.current_ip = "192.168.1.2"
    host_offline.status = "offline"
    host_offline.created_by = str(mock_user_a.id)
    host_offline.first_seen = "2025-01-01T00:00:00Z"
    host_offline.last_seen = "2025-01-01T00:00:00Z"
    
    with patch("server.api.routes.hosts.get_host_operations") as mock_get_ops:
        mock_ops = MagicMock()
        # Mock filtering by status
        mock_ops.get_hosts_by_status.return_value = [host_online]
        mock_get_ops.return_value = mock_ops
        
        # Get only online hosts
        response = test_client_user_a.get("/api/hosts?status=online")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert data["hosts"][0]["hostname"] == "online-host"
        assert data["hosts"][0]["status"] == "online"


def test_host_stats_filtered_by_user(test_client_user_a, mock_user_a):
    """Test that host stats only include user's hosts."""
    with patch("server.api.routes.hosts.get_host_operations") as mock_get_ops:
        mock_ops = MagicMock()
        # Mock host count methods
        mock_ops.get_host_count.return_value = 5  # Total hosts for user
        mock_ops.get_host_count_by_status.side_effect = lambda status, user_id: {
            "online": 3,
            "offline": 2
        }.get(status, 0)
        mock_get_ops.return_value = mock_ops
        
        # Get stats
        response = test_client_user_a.get("/api/hosts/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_hosts"] == 5
        assert data["online_hosts"] == 3
        assert data["offline_hosts"] == 2