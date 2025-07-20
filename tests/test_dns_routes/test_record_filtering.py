#!/usr/bin/env python3
"""
Test DNS record filtering by user (SCRUM-132)
Tests that users only see records from zones they own.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from server.auth.models import User


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


@pytest.mark.asyncio
async def test_cannot_list_records_in_other_users_zone(async_client, mock_user_a, mock_user_b):
    """Test that users cannot see records in zones they don't own."""
    # Mock the dependencies
    with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_user_b):
        with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
            with patch("server.api.routes.dns.get_dns_zone_ops") as mock_zone_ops:
                # Mock that user B doesn't own the zone
                mock_ops = MagicMock()
                mock_ops.check_zone_ownership.return_value = False
                mock_zone_ops.return_value = mock_ops
                
                # User B tries to list records in User A's zone
                response = await async_client.get("/api/dns/zones/usera.com/records")
                
                # Should return 404 (zone not found)
                assert response.status_code == 404
                assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_search_only_returns_users_records(async_client, mock_user_a, mock_user_b):
    """Test that record search only returns records from user's zones."""
    with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_user_a):
        with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
            with patch("server.api.routes.dns.get_dns_zone_ops") as mock_zone_ops:
                # Mock PowerDNS client
                mock_client = AsyncMock()
                mock_dns_client.return_value.__aenter__.return_value = mock_client
                
                # Mock all zones from PowerDNS
                all_zones = [
                    {"name": "usera.com.", "kind": "Native"},
                    {"name": "userb.com.", "kind": "Native"},
                ]
                mock_client.list_zones.return_value = all_zones
                
                # Mock zone ownership - user A owns only usera.com
                mock_ops = MagicMock()
                mock_ops.get_user_zones.return_value = ["usera.com."]
                mock_zone_ops.return_value = mock_ops
                
                # Mock records in zones
                def mock_get_records(zone_name):
                    if zone_name == "usera.com.":
                        return [
                            {"name": "www.usera.com.", "type": "A", "content": "192.168.1.1"},
                            {"name": "mail.usera.com.", "type": "A", "content": "192.168.1.2"},
                        ]
                    elif zone_name == "userb.com.":
                        return [
                            {"name": "www.userb.com.", "type": "A", "content": "192.168.2.1"},
                        ]
                    return []
                
                mock_client.get_records.side_effect = mock_get_records
                
                # User A searches for "www"
                response = await async_client.get("/api/dns/records/search?q=www")
                
                assert response.status_code == 200
                data = response.json()
                records = data["records"]
                
                # Should only see www.usera.com, not www.userb.com
                assert len(records) == 1
                assert records[0]["name"] == "www.usera.com."
                assert data["zones_searched"] == 1


@pytest.mark.asyncio
async def test_export_only_includes_users_records(async_client, mock_user_a, mock_user_b):
    """Test that export only includes records from user's zones."""
    with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_user_a):
        with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
            with patch("server.api.routes.dns.get_dns_zone_ops") as mock_zone_ops:
                # Mock PowerDNS client
                mock_client = AsyncMock()
                mock_dns_client.return_value.__aenter__.return_value = mock_client
                
                # Mock all zones
                all_zones = [
                    {"name": "zone1.com.", "kind": "Native"},
                    {"name": "zone2.com.", "kind": "Native"},
                    {"name": "other.com.", "kind": "Native"},
                ]
                mock_client.list_zones.return_value = all_zones
                
                # Mock zone ownership - user A owns zone1 and zone2
                mock_ops = MagicMock()
                mock_ops.get_user_zones.return_value = ["zone1.com.", "zone2.com."]
                mock_zone_ops.return_value = mock_ops
                
                # Mock records in zones
                def mock_get_records(zone_name):
                    if zone_name == "zone1.com.":
                        return [{"name": "www.zone1.com.", "type": "A", "content": "1.1.1.1"}]
                    elif zone_name == "zone2.com.":
                        return [{"name": "www.zone2.com.", "type": "A", "content": "2.2.2.2"}]
                    elif zone_name == "other.com.":
                        return [{"name": "www.other.com.", "type": "A", "content": "3.3.3.3"}]
                    return []
                
                mock_client.get_records.side_effect = mock_get_records
                
                # Export records
                response = await async_client.get("/api/dns/records/export?format=json")
                
                assert response.status_code == 200
                export_data = response.json()
                
                # Should only have 2 zones, not 3
                assert len(export_data["zones"]) == 2
                zone_names = {z["name"] for z in export_data["zones"]}
                assert zone_names == {"zone1.com.", "zone2.com."}
                assert export_data["user"] == "usera"


@pytest.mark.asyncio
async def test_user_can_list_records_in_own_zone(async_client, mock_user_a):
    """Test that users CAN list records in their own zones."""
    with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_user_a):
        with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
            with patch("server.api.routes.dns.get_dns_zone_ops") as mock_zone_ops:
                # Mock that user A owns the zone
                mock_ops = MagicMock()
                mock_ops.check_zone_ownership.return_value = True
                mock_zone_ops.return_value = mock_ops
                
                # Mock PowerDNS client
                mock_client = AsyncMock()
                mock_client.get_records.return_value = [
                    {"name": "www.usera.com.", "type": "A", "content": "192.168.1.1"},
                    {"name": "mail.usera.com.", "type": "A", "content": "192.168.1.2"},
                ]
                mock_dns_client.return_value.__aenter__.return_value = mock_client
                
                # User A lists records in their zone
                response = await async_client.get("/api/dns/zones/usera.com/records")
                
                assert response.status_code == 200
                data = response.json()
                assert len(data["records"]) == 2
                assert data["count"] == 2


@pytest.mark.asyncio
async def test_record_type_filtering_works(async_client, mock_user_a):
    """Test that record type filtering works with user filtering."""
    with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_user_a):
        with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
            with patch("server.api.routes.dns.get_dns_zone_ops") as mock_zone_ops:
                # Mock that user A owns the zone
                mock_ops = MagicMock()
                mock_ops.check_zone_ownership.return_value = True
                mock_zone_ops.return_value = mock_ops
                
                # Mock PowerDNS client
                mock_client = AsyncMock()
                mock_client.get_records.return_value = [
                    {"name": "www.usera.com.", "type": "A", "content": "192.168.1.1"},
                    {"name": "mail.usera.com.", "type": "MX", "content": "10 mail.usera.com."},
                    {"name": "txt.usera.com.", "type": "TXT", "content": "v=spf1 ~all"},
                ]
                mock_dns_client.return_value.__aenter__.return_value = mock_client
                
                # Filter by record type A
                response = await async_client.get("/api/dns/zones/usera.com/records?record_type=A")
                
                assert response.status_code == 200
                data = response.json()
                assert len(data["records"]) == 1
                assert data["records"][0]["type"] == "A"


@pytest.mark.asyncio
async def test_search_within_content_works(async_client, mock_user_a):
    """Test that searching within record content works correctly."""
    with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_user_a):
        with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
            with patch("server.api.routes.dns.get_dns_zone_ops") as mock_zone_ops:
                # Mock PowerDNS client
                mock_client = AsyncMock()
                mock_dns_client.return_value.__aenter__.return_value = mock_client
                
                # Mock zones
                all_zones = [{"name": "usera.com.", "kind": "Native"}]
                mock_client.list_zones.return_value = all_zones
                
                # Mock zone ownership
                mock_ops = MagicMock()
                mock_ops.get_user_zones.return_value = ["usera.com."]
                mock_zone_ops.return_value = mock_ops
                
                # Mock records with different IPs
                mock_client.get_records.return_value = [
                    {"name": "web1.usera.com.", "type": "A", "content": "192.168.1.1"},
                    {"name": "web2.usera.com.", "type": "A", "content": "192.168.1.2"},
                    {"name": "db.usera.com.", "type": "A", "content": "10.0.0.1"},
                ]
                
                # Search for "192.168"
                response = await async_client.get("/api/dns/records/search?q=192.168")
                
                assert response.status_code == 200
                data = response.json()
                records = data["records"]
                
                # Should find 2 records with 192.168 in content
                assert len(records) == 2
                assert all("192.168" in r["content"] for r in records)