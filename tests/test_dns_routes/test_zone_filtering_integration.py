#!/usr/bin/env python3
"""
Integration test for DNS zone filtering by user (SCRUM-129)
Tests the actual implementation with database.
"""

import pytest
from uuid import uuid4

from server.database.dns_operations import DNSZoneOwnershipOperations
from server.database.connection import DatabaseManager


@pytest.mark.asyncio
async def test_zone_filtering_integration(async_client, db_session):
    """Integration test for zone filtering."""
    # Create test users
    user1_id = str(uuid4())
    user2_id = str(uuid4())
    
    # Mock authentication to return user1
    from unittest.mock import patch, MagicMock
    mock_user1 = MagicMock()
    mock_user1.id = user1_id
    mock_user1.username = "testuser1"
    
    # Create zone ownership records
    config = {"database": {"path": "/app/data/prism.db"}}
    db_manager = DatabaseManager(config)
    dns_ops = DNSZoneOwnershipOperations(db_manager)
    
    # Create zones for different users
    dns_ops.create_zone_ownership("zone1.example.com.", user1_id)
    dns_ops.create_zone_ownership("zone2.example.com.", user1_id)
    dns_ops.create_zone_ownership("zone3.example.com.", user2_id)
    
    try:
        # Mock PowerDNS to return all zones
        with patch("server.api.routes.dns.get_current_verified_user", return_value=mock_user1):
            with patch("server.api.routes.dns.get_powerdns_client") as mock_dns_client:
                mock_client = MagicMock()
                mock_client.__aenter__ = lambda self: self
                mock_client.__aexit__ = lambda self, *args: None
                mock_dns_client.return_value = mock_client
                
                # Mock PowerDNS returning all zones
                mock_client.list_zones.return_value = [
                    {"name": "zone1.example.com.", "kind": "Native"},
                    {"name": "zone2.example.com.", "kind": "Native"},
                    {"name": "zone3.example.com.", "kind": "Native"},
                ]
                
                # Make request as user1
                response = await async_client.get("/api/dns/zones")
                
                assert response.status_code == 200
                data = response.json()
                
                # User1 should only see their 2 zones
                assert len(data["zones"]) == 2
                zone_names = [z["name"] for z in data["zones"]]
                assert "zone1.example.com." in zone_names
                assert "zone2.example.com." in zone_names
                assert "zone3.example.com." not in zone_names
    
    finally:
        # Clean up
        dns_ops.delete_zone_ownership("zone1.example.com.")
        dns_ops.delete_zone_ownership("zone2.example.com.")
        dns_ops.delete_zone_ownership("zone3.example.com.")