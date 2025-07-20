#!/usr/bin/env python3
"""
Test DNS zone filtering by user (SCRUM-129)
Tests that users only see DNS zones they own.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from uuid import uuid4

from server.auth.models import User


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.username = "testuser"
    user.email = "test@example.com"
    user.is_active = True
    return user


@pytest.fixture
def mock_other_user():
    """Create another mock user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.username = "otheruser"
    user.email = "other@example.com"
    user.is_active = True
    return user


@pytest.mark.asyncio
async def test_user_sees_only_their_zones(async_client, mock_user, mock_other_user):
    """Test that users only see their own zones."""
    # Mock the dependencies
    with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_user):
        with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
            # Mock PowerDNS client
            mock_client = AsyncMock()
            mock_dns_client.return_value.__aenter__.return_value = mock_client
            
            # Mock zones from PowerDNS - all zones
            all_zones = [
                {"name": "user-a.example.com.", "kind": "Native"},
                {"name": "user-b.example.com.", "kind": "Native"},
                {"name": "shared.example.com.", "kind": "Native"},
            ]
            mock_client.list_zones.return_value = all_zones
            
            # Mock zone ownership data
            with patch("server.api.routes.dns.get_dns_zone_ops") as mock_get_ops:
                # Mock the operations object
                mock_ops = MagicMock()
                mock_ops.get_user_zones.return_value = ["user-a.example.com."]
                mock_get_ops.return_value = mock_ops
                
                # Make request
                response = await async_client.get(
                    "/api/dns/zones",
                    headers={"Authorization": "Bearer fake-token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # User should only see their zone
                assert len(data["zones"]) == 1
                assert data["zones"][0]["name"] == "user-a.example.com."
                assert data["pagination"]["total"] == 1


@pytest.mark.asyncio
async def test_zone_filtering_with_pagination(async_client, mock_user):
    """Test that pagination works with filtered zones."""
    with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_user):
        with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
            # Mock PowerDNS client
            mock_client = AsyncMock()
            mock_dns_client.return_value.__aenter__.return_value = mock_client
            
            # Mock 15 zones total
            all_zones = [{"name": f"zone{i}.example.com.", "kind": "Native"} for i in range(15)]
            mock_client.list_zones.return_value = all_zones
            
            # Mock that user owns 10 zones
            with patch("server.api.routes.dns.get_user_zones") as mock_get_user_zones:
                user_zones = [f"zone{i}.example.com." for i in range(10)]
                mock_get_user_zones.return_value = user_zones
                
                # Get page 1 with limit 5
                response = await async_client.get(
                    "/api/dns/zones?page=1&limit=5",
                    headers={"Authorization": "Bearer fake-token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # Should see 5 zones on first page
                assert len(data["zones"]) == 5
                assert data["pagination"]["total"] == 10  # Only user's zones counted
                assert data["pagination"]["pages"] == 2
                
                # Get page 2
                response = await async_client.get(
                    "/api/dns/zones?page=2&limit=5",
                    headers={"Authorization": "Bearer fake-token"}
                )
                
                data = response.json()
                assert len(data["zones"]) == 5  # Remaining 5 zones


@pytest.mark.asyncio
async def test_search_filters_by_user(async_client, mock_user):
    """Test that search only searches within user's zones."""
    with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_user):
        with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
            # Mock PowerDNS client
            mock_client = AsyncMock()
            mock_dns_client.return_value.__aenter__.return_value = mock_client
            
            # Mock zones
            all_zones = [
                {"name": "test-user.example.com.", "kind": "Native"},
                {"name": "test-other.example.com.", "kind": "Native"},
                {"name": "prod-user.example.com.", "kind": "Native"},
            ]
            mock_client.list_zones.return_value = all_zones
            
            # User owns two zones
            with patch("server.api.routes.dns.get_user_zones") as mock_get_user_zones:
                mock_get_user_zones.return_value = [
                    "test-user.example.com.", 
                    "prod-user.example.com."
                ]
                
                # Search for "test"
                response = await async_client.get(
                    "/api/dns/zones?search=test",
                    headers={"Authorization": "Bearer fake-token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # Should only find user's zone with "test"
                assert len(data["zones"]) == 1
                assert data["zones"][0]["name"] == "test-user.example.com."


@pytest.mark.asyncio
async def test_empty_zones_for_new_user(async_client, mock_user):
    """Test that new user with no zones sees empty list."""
    with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_user):
        with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
            # Mock PowerDNS client
            mock_client = AsyncMock()
            mock_dns_client.return_value.__aenter__.return_value = mock_client
            
            # Mock zones exist
            all_zones = [
                {"name": "zone1.example.com.", "kind": "Native"},
                {"name": "zone2.example.com.", "kind": "Native"},
            ]
            mock_client.list_zones.return_value = all_zones
            
            # But user owns none
            with patch("server.api.routes.dns.get_user_zones") as mock_get_user_zones:
                mock_get_user_zones.return_value = []
                
                response = await async_client.get(
                    "/api/dns/zones",
                    headers={"Authorization": "Bearer fake-token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # Should see empty list
                assert len(data["zones"]) == 0
                assert data["pagination"]["total"] == 0


@pytest.mark.asyncio
async def test_zone_filtering_performance(async_client, mock_user):
    """Test that filtering performs well with many zones."""
    with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_user):
        with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
            # Mock PowerDNS client
            mock_client = AsyncMock()
            mock_dns_client.return_value.__aenter__.return_value = mock_client
            
            # Mock 1000 zones
            all_zones = [{"name": f"zone{i}.example.com.", "kind": "Native"} for i in range(1000)]
            mock_client.list_zones.return_value = all_zones
            
            # User owns 50 zones
            with patch("server.api.routes.dns.get_user_zones") as mock_get_user_zones:
                user_zones = [f"zone{i}.example.com." for i in range(50)]
                mock_get_user_zones.return_value = user_zones
                
                import time
                start = time.time()
                
                response = await async_client.get(
                    "/api/dns/zones",
                    headers={"Authorization": "Bearer fake-token"}
                )
                
                duration = time.time() - start
                
                assert response.status_code == 200
                data = response.json()
                assert data["pagination"]["total"] == 50
                
                # Should complete quickly (< 50ms added for filtering)
                assert duration < 0.1  # 100ms total including mock overhead