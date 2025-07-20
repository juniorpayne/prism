#!/usr/bin/env python3
"""
Test DNS authorization checks (SCRUM-131)
Tests that users can only modify zones they own.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi import HTTPException

from server.auth.models import User
from server.database.models import DNSZoneOwnership


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
async def test_cannot_update_other_users_zone(async_client, mock_user_a, mock_user_b):
    """Test that users cannot modify zones they don't own."""
    # Mock the dependencies
    with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_user_b):
        with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
            with patch("server.api.routes.dns.get_dns_zone_ops") as mock_zone_ops:
                # Mock that user B doesn't own the zone
                mock_ops = MagicMock()
                mock_ops.check_zone_ownership.return_value = False
                mock_zone_ops.return_value = mock_ops
                
                # User B tries to update a zone they don't own
                update_data = {"kind": "Master", "masters": ["1.2.3.4"]}
                response = await async_client.put(
                    "/api/dns/zones/usera.example.com",
                    json=update_data
                )
                
                # Should return 404 (not 403 to prevent enumeration)
                assert response.status_code == 404
                assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cannot_delete_other_users_zone(async_client, mock_user_a, mock_user_b):
    """Test that users cannot delete zones they don't own."""
    with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_user_b):
        with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
            with patch("server.api.routes.dns.get_dns_zone_ops") as mock_zone_ops:
                # Mock that user B doesn't own the zone
                mock_ops = MagicMock()
                mock_ops.check_zone_ownership.return_value = False
                mock_zone_ops.return_value = mock_ops
                
                # User B tries to delete a zone they don't own
                response = await async_client.delete("/api/dns/zones/usera.example.com")
                
                # Should return 404
                assert response.status_code == 404
                assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cannot_create_record_in_other_users_zone(async_client, mock_user_a, mock_user_b):
    """Test that users cannot add records to zones they don't own."""
    with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_user_b):
        with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
            with patch("server.api.routes.dns.get_dns_zone_ops") as mock_zone_ops:
                # Mock that user B doesn't own the zone
                mock_ops = MagicMock()
                mock_ops.check_zone_ownership.return_value = False
                mock_zone_ops.return_value = mock_ops
                
                # User B tries to add a record to a zone they don't own
                record_data = {
                    "name": "www.usera.example.com",
                    "type": "A",
                    "content": "192.168.1.1",
                    "ttl": 3600
                }
                response = await async_client.post(
                    "/api/dns/zones/usera.example.com/records",
                    json=record_data
                )
                
                # Should return 404
                assert response.status_code == 404
                assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_user_can_modify_own_zones(async_client, mock_user_a):
    """Test that users CAN modify their own zones."""
    with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_user_a):
        with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
            with patch("server.api.routes.dns.get_dns_zone_ops") as mock_zone_ops:
                # Mock that user A owns the zone
                mock_ops = MagicMock()
                mock_ops.check_zone_ownership.return_value = True
                mock_zone_ops.return_value = mock_ops
                
                # Mock PowerDNS client successful update
                mock_client = AsyncMock()
                mock_client.get_zone_details.return_value = {"name": "usera.example.com", "kind": "Native"}
                mock_client.update_zone.return_value = {"result": "success"}
                mock_dns_client.return_value.__aenter__.return_value = mock_client
                
                # User A updates their own zone
                update_data = {"metadata": {"description": ["My zone"]}}
                response = await async_client.put(
                    "/api/dns/zones/usera.example.com",
                    json=update_data
                )
                
                # Should succeed
                assert response.status_code == 200
                assert response.json()["result"] == "success"


@pytest.mark.asyncio
async def test_new_zone_gets_ownership_record(async_client, mock_user_a):
    """Test that creating a zone automatically creates ownership record."""
    with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_user_a):
        with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
            with patch("server.api.routes.dns.get_dns_zone_ops") as mock_zone_ops:
                # Mock successful zone creation
                mock_client = AsyncMock()
                mock_client.validate_zone_name.return_value = (True, None)
                mock_client.get_zone_details.return_value = None  # Zone doesn't exist yet
                mock_client.create_zone.return_value = {
                    "name": "newzone.example.com",
                    "kind": "Native",
                    "id": "newzone.example.com"
                }
                mock_dns_client.return_value.__aenter__.return_value = mock_client
                
                # Mock zone ownership operations
                mock_ops = MagicMock()
                mock_ops.create_zone_ownership.return_value = True
                mock_zone_ops.return_value = mock_ops
                
                # Create new zone
                zone_data = {"name": "newzone.example.com", "kind": "Native"}
                response = await async_client.post("/api/dns/zones", json=zone_data)
                
                assert response.status_code == 201
                
                # Verify ownership was created
                mock_ops.create_zone_ownership.assert_called_once_with(
                    "newzone.example.com",
                    str(mock_user_a.id)
                )


@pytest.mark.asyncio
async def test_cannot_update_record_in_other_users_zone(async_client, mock_user_a, mock_user_b):
    """Test that users cannot update records in zones they don't own."""
    with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_user_b):
        with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
            with patch("server.api.routes.dns.get_dns_zone_ops") as mock_zone_ops:
                # Mock that user B doesn't own the zone
                mock_ops = MagicMock()
                mock_ops.check_zone_ownership.return_value = False
                mock_zone_ops.return_value = mock_ops
                
                # User B tries to update a record
                record_data = {"content": ["192.168.1.2"], "ttl": 7200}
                response = await async_client.put(
                    "/api/dns/zones/usera.example.com/records/www.usera.example.com/A",
                    json=record_data
                )
                
                # Should return 404
                assert response.status_code == 404
                assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cannot_delete_record_in_other_users_zone(async_client, mock_user_a, mock_user_b):
    """Test that users cannot delete records in zones they don't own."""
    with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_user_b):
        with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
            with patch("server.api.routes.dns.get_dns_zone_ops") as mock_zone_ops:
                # Mock that user B doesn't own the zone
                mock_ops = MagicMock()
                mock_ops.check_zone_ownership.return_value = False
                mock_zone_ops.return_value = mock_ops
                
                # User B tries to delete a record
                response = await async_client.delete(
                    "/api/dns/zones/usera.example.com/records/www.usera.example.com/A"
                )
                
                # Should return 404
                assert response.status_code == 404
                assert "not found" in response.json()["detail"].lower()