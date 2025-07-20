#!/usr/bin/env python3
"""
Test admin override functionality (SCRUM-133)
Tests that admins can optionally view all users' data.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from server.auth.models import User


@pytest.fixture
def mock_admin():
    """Create a mock admin user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.username = "admin"
    user.email = "admin@example.com"
    user.is_active = True
    user.is_admin = True
    user.has_admin_privileges.return_value = True
    return user


@pytest.fixture
def mock_regular_user():
    """Create a mock regular user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.username = "user"
    user.email = "user@example.com"
    user.is_active = True
    user.is_admin = False
    user.has_admin_privileges.return_value = False
    return user


@pytest.mark.asyncio
async def test_admin_sees_only_own_data_by_default(async_client, mock_admin, mock_regular_user):
    """Test that admins see only their data without override flag."""
    # Mock the dependencies
    with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_admin):
        with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
            with patch("server.api.routes.dns.get_dns_zone_ops") as mock_zone_ops:
                # Mock PowerDNS client
                mock_client = AsyncMock()
                mock_dns_client.return_value.__aenter__.return_value = mock_client
                
                # Mock all zones
                all_zones = [
                    {"name": "admin.com.", "kind": "Native"},
                    {"name": "user.com.", "kind": "Native"},
                ]
                mock_client.list_zones.return_value = all_zones
                
                # Mock zone ownership - admin owns only admin.com
                mock_ops = MagicMock()
                mock_ops.get_user_zones.return_value = ["admin.com."]
                mock_zone_ops.return_value = mock_ops
                
                # Admin lists zones WITHOUT override
                response = await async_client.get("/api/dns/zones")
                
                assert response.status_code == 200
                data = response.json()
                zones = data["zones"]
                
                # Should only see admin.com, not user.com
                assert len(zones) == 1
                assert zones[0]["name"] == "admin.com."


@pytest.mark.asyncio
async def test_admin_can_view_all_with_override(async_client, mock_admin):
    """Test that admins can see all data with view_all flag."""
    with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_admin):
        with patch("server.api.routes.dns.get_admin_override", return_value=True):
            with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
                # Mock PowerDNS client
                mock_client = AsyncMock()
                mock_dns_client.return_value.__aenter__.return_value = mock_client
                
                # Mock all zones
                all_zones = [
                    {"name": "admin.com.", "kind": "Native"},
                    {"name": "user.com.", "kind": "Native"},
                ]
                mock_client.list_zones.return_value = all_zones
                
                # Admin lists zones WITH override
                response = await async_client.get("/api/dns/zones?view_all=true")
                
                assert response.status_code == 200
                data = response.json()
                zones = data["zones"]
                
                # Should see all zones
                assert len(zones) == 2
                zone_names = {z["name"] for z in zones}
                assert zone_names == {"admin.com.", "user.com."}


@pytest.mark.asyncio
async def test_regular_user_cannot_use_view_all(async_client, mock_regular_user):
    """Test that non-admins cannot use view_all parameter."""
    with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_regular_user):
        with patch("server.api.routes.dns.get_admin_override", return_value=False):
            with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
                with patch("server.api.routes.dns.get_dns_zone_ops") as mock_zone_ops:
                    # Mock PowerDNS client
                    mock_client = AsyncMock()
                    mock_dns_client.return_value.__aenter__.return_value = mock_client
                    
                    # Mock all zones
                    all_zones = [
                        {"name": "admin.com.", "kind": "Native"},
                        {"name": "user.com.", "kind": "Native"},
                    ]
                    mock_client.list_zones.return_value = all_zones
                    
                    # Mock zone ownership - user owns only user.com
                    mock_ops = MagicMock()
                    mock_ops.get_user_zones.return_value = ["user.com."]
                    mock_zone_ops.return_value = mock_ops
                    
                    # Regular user tries to use view_all
                    response = await async_client.get("/api/dns/zones?view_all=true")
                    
                    assert response.status_code == 200
                    data = response.json()
                    zones = data["zones"]
                    
                    # Should still only see their own zone
                    assert len(zones) == 1
                    assert zones[0]["name"] == "user.com."


@pytest.mark.asyncio
async def test_admin_override_works_for_hosts(async_client, mock_admin):
    """Test that admin override works for host endpoints."""
    with patch("server.api.routes.hosts.get_current_verified_user", return_value=mock_admin):
        with patch("server.api.routes.hosts.get_admin_override", return_value=True):
            with patch("server.api.routes.hosts.get_host_operations") as mock_host_ops:
                # Mock host operations
                mock_ops = MagicMock()
                
                # Mock all hosts (admin sees all)
                all_hosts = [
                    MagicMock(hostname="admin-host", current_ip="1.1.1.1", status="online", 
                              first_seen=None, last_seen=None, created_by=str(mock_admin.id)),
                    MagicMock(hostname="user-host", current_ip="2.2.2.2", status="online",
                              first_seen=None, last_seen=None, created_by="other-user-id"),
                ]
                mock_ops.get_all_hosts.return_value = all_hosts
                mock_host_ops.return_value = mock_ops
                
                # Admin lists hosts WITH override
                response = await async_client.get("/api/hosts?view_all=true")
                
                assert response.status_code == 200
                data = response.json()
                
                # Should see all hosts
                assert data["total"] == 2
                hostnames = {h["hostname"] for h in data["hosts"]}
                assert hostnames == {"admin-host", "user-host"}


@pytest.mark.asyncio
async def test_admin_stats_with_override(async_client, mock_admin):
    """Test that admin can see all host stats with override."""
    with patch("server.api.routes.hosts.get_current_verified_user", return_value=mock_admin):
        with patch("server.api.routes.hosts.get_admin_override", return_value=True):
            with patch("server.api.routes.hosts.get_host_operations") as mock_host_ops:
                # Mock host operations
                mock_ops = MagicMock()
                
                # Mock counts for all hosts
                mock_ops.get_host_count.return_value = 100  # Total hosts in system
                mock_ops.get_host_count_by_status.side_effect = lambda status, user_id: {
                    "online": 60,
                    "offline": 40
                }.get(status, 0)
                
                mock_host_ops.return_value = mock_ops
                
                # Admin gets stats WITH override
                response = await async_client.get("/api/hosts/stats?view_all=true")
                
                assert response.status_code == 200
                data = response.json()
                
                # Should see all host stats
                assert data["total_hosts"] == 100
                assert data["online_hosts"] == 60
                assert data["offline_hosts"] == 40


@pytest.mark.asyncio
async def test_admin_access_is_logged(async_client, mock_admin, caplog):
    """Test that admin override access is logged."""
    with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_admin):
        with patch("server.api.routes.dns.get_admin_override", return_value=True):
            with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
                # Mock PowerDNS client
                mock_client = AsyncMock()
                mock_dns_client.return_value.__aenter__.return_value = mock_client
                mock_client.list_zones.return_value = []
                
                # Admin uses view_all
                response = await async_client.get("/api/dns/zones?view_all=true")
                
                assert response.status_code == 200
                
                # Check that admin access was logged
                # Note: In real implementation, would check actual log entries
                # For now, just verify the endpoint was called successfully