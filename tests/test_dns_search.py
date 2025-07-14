#!/usr/bin/env python3
"""
Test DNS Search and Filter API (SCRUM-119)
Tests for DNS search and filtering capabilities.
"""

from unittest.mock import MagicMock, patch
from asyncio import Future

import pytest
from fastapi.testclient import TestClient

from server.api.app import create_app
from server.auth.dependencies import get_current_verified_user
from server.dns_manager import PowerDNSClient, PowerDNSError


def async_return(result):
    """Helper to create an async return value."""
    future = Future()
    future.set_result(result)
    return future


@pytest.fixture
def test_config():
    """Test configuration."""
    return {
        "server": {"tcp_port": 8080, "api_port": 8081, "host": "localhost", "environment": "test"},
        "database": {"path": ":memory:", "connection_pool_size": 1},
        "powerdns": {
            "enabled": True,
            "api_url": "http://localhost:8053/api/v1",
            "api_key": "test-key",
            "default_zone": "test.local.",
            "default_ttl": 300,
        },
        "api": {"enable_cors": True},
    }


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    mock = MagicMock()
    mock.id = 1
    mock.username = "testuser"
    mock.email = "test@example.com"
    mock.is_active = True
    mock.email_verified = True
    return mock


@pytest.fixture
def client(test_config, mock_user):
    """Test client fixture with authentication override."""
    app = create_app(test_config)
    app.dependency_overrides[get_current_verified_user] = lambda: mock_user
    return TestClient(app)


def test_search_zones(client):
    """Test zone search functionality."""
    mock_zones = [
        {"name": "example.com.", "kind": "Native", "serial": 2024122001},
        {"name": "test.example.com.", "kind": "Native", "serial": 2024122002},
        {"name": "dev.example.com.", "kind": "Native", "serial": 2024122003},
    ]
    
    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.search_zones.return_value = async_return(mock_zones[:2])
        mock_get_client.return_value.__aenter__.return_value = mock_client
        mock_get_client.return_value.__aexit__.return_value = async_return(None)
        
        response = client.get("/api/dns/zones/search?q=example")
    
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "example"
    assert data["total"] == 2
    assert len(data["zones"]) == 2
    
    # Verify search was called with correct parameters
    mock_client.search_zones.assert_called_once_with(
        query="example",
        zone_type=None,
        hierarchy_level=None,
        limit=100
    )


def test_search_zones_with_filters(client):
    """Test zone search with type and hierarchy filters."""
    mock_zones = [
        {"name": "example.com.", "kind": "Master", "serial": 2024122001},
    ]
    
    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.search_zones.return_value = async_return(mock_zones)
        mock_get_client.return_value.__aenter__.return_value = mock_client
        mock_get_client.return_value.__aexit__.return_value = async_return(None)
        
        response = client.get(
            "/api/dns/zones/search?q=example&zone_type=Master&hierarchy_level=0"
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["filters"]["zone_type"] == "Master"
    assert data["filters"]["hierarchy_level"] == 0
    
    mock_client.search_zones.assert_called_once_with(
        query="example",
        zone_type="Master",
        hierarchy_level=0,
        limit=100
    )


def test_search_zones_wildcard(client):
    """Test zone search with wildcard pattern."""
    mock_zones = [
        {"name": "test.example.com.", "kind": "Native", "serial": 2024122001},
        {"name": "dev.example.com.", "kind": "Native", "serial": 2024122002},
    ]
    
    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.search_zones.return_value = async_return(mock_zones)
        mock_get_client.return_value.__aenter__.return_value = mock_client
        mock_get_client.return_value.__aexit__.return_value = async_return(None)
        
        response = client.get("/api/dns/zones/search?q=*.example.com.")
    
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "*.example.com."
    assert data["total"] == 2


def test_search_records(client):
    """Test record search functionality."""
    mock_records = [
        {
            "name": "www.example.com.",
            "type": "A",
            "ttl": 3600,
            "records": [{"content": "192.168.1.1"}],
            "zone": "example.com."
        },
        {
            "name": "mail.example.com.",
            "type": "A",
            "ttl": 3600,
            "records": [{"content": "192.168.1.2"}],
            "zone": "example.com."
        }
    ]
    
    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.search_records.return_value = async_return(mock_records)
        mock_get_client.return_value.__aenter__.return_value = mock_client
        mock_get_client.return_value.__aexit__.return_value = async_return(None)
        
        response = client.get("/api/dns/records/search?q=mail")
    
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "mail"
    assert data["total"] == 2
    assert all("zone" in record for record in data["records"])


def test_search_records_by_content(client):
    """Test searching records by content."""
    mock_records = [
        {
            "name": "www.example.com.",
            "type": "A",
            "ttl": 3600,
            "records": [{"content": "192.168.1.1"}],
            "zone": "example.com."
        }
    ]
    
    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.search_records.return_value = async_return(mock_records)
        mock_get_client.return_value.__aenter__.return_value = mock_client
        mock_get_client.return_value.__aexit__.return_value = async_return(None)
        
        response = client.get("/api/dns/records/search?q=192.168&content=true")
    
    assert response.status_code == 200
    data = response.json()
    assert data["filters"]["content_search"] is True
    assert data["total"] == 1
    
    mock_client.search_records.assert_called_once_with(
        query="192.168",
        record_type=None,
        zone_name=None,
        content_search=True,
        limit=100
    )


def test_search_records_with_type_filter(client):
    """Test searching records with type filter."""
    mock_records = [
        {
            "name": "mail.example.com.",
            "type": "MX",
            "ttl": 3600,
            "records": [{"content": "10 mail.example.com."}],
            "zone": "example.com."
        }
    ]
    
    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.search_records.return_value = async_return(mock_records)
        mock_get_client.return_value.__aenter__.return_value = mock_client
        mock_get_client.return_value.__aexit__.return_value = async_return(None)
        
        response = client.get("/api/dns/records/search?q=mail&record_type=MX")
    
    assert response.status_code == 200
    data = response.json()
    assert data["filters"]["record_type"] == "MX"
    assert all(r["type"] == "MX" for r in data["records"])


def test_search_records_in_zone(client):
    """Test searching records within specific zone."""
    mock_records = [
        {
            "name": "www.test.com.",
            "type": "A",
            "ttl": 3600,
            "records": [{"content": "10.0.0.1"}],
            "zone": "test.com."
        }
    ]
    
    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.search_records.return_value = async_return(mock_records)
        mock_get_client.return_value.__aenter__.return_value = mock_client
        mock_get_client.return_value.__aexit__.return_value = async_return(None)
        
        response = client.get("/api/dns/records/search?q=www&zone=test.com.")
    
    assert response.status_code == 200
    data = response.json()
    assert data["filters"]["zone"] == "test.com."
    
    mock_client.search_records.assert_called_once_with(
        query="www",
        record_type=None,
        zone_name="test.com.",
        content_search=False,
        limit=100
    )


def test_filter_zones(client):
    """Test zone filtering functionality."""
    mock_zones = [
        {"name": "example.com.", "kind": "Native", "serial": 2024122001, "record_count": 10},
        {"name": "test.com.", "kind": "Native", "serial": 2024122002, "record_count": 5},
    ]
    
    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.filter_zones.return_value = async_return(mock_zones)
        mock_get_client.return_value.__aenter__.return_value = mock_client
        mock_get_client.return_value.__aexit__.return_value = async_return(None)
        
        filters = {
            "min_records": 5,
            "max_records": 15,
            "has_dnssec": False
        }
        
        response = client.post("/api/dns/zones/filter", json=filters)
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["filters"] == filters
    assert data["sort"]["by"] == "name"
    assert data["sort"]["order"] == "asc"


def test_filter_zones_with_sorting(client):
    """Test zone filtering with custom sorting."""
    mock_zones = [
        {"name": "b.com.", "kind": "Native", "serial": 2024122002, "record_count": 10},
        {"name": "a.com.", "kind": "Native", "serial": 2024122001, "record_count": 20},
    ]
    
    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.filter_zones.return_value = async_return(mock_zones)
        mock_get_client.return_value.__aenter__.return_value = mock_client
        mock_get_client.return_value.__aexit__.return_value = async_return(None)
        
        response = client.post(
            "/api/dns/zones/filter?sort_by=records&sort_order=desc",
            json={}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["sort"]["by"] == "records"
    assert data["sort"]["order"] == "desc"
    
    mock_client.filter_zones.assert_called_once_with(
        filters={},
        sort_by="records",
        sort_order="desc"
    )


def test_filter_zones_by_parent(client):
    """Test filtering zones by parent zone."""
    mock_zones = [
        {"name": "sub1.example.com.", "kind": "Native", "serial": 2024122001},
        {"name": "sub2.example.com.", "kind": "Native", "serial": 2024122002},
    ]
    
    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.filter_zones.return_value = async_return(mock_zones)
        mock_get_client.return_value.__aenter__.return_value = mock_client
        mock_get_client.return_value.__aexit__.return_value = async_return(None)
        
        filters = {"parent_zone": "example.com."}
        
        response = client.post("/api/dns/zones/filter", json=filters)
    
    assert response.status_code == 200
    data = response.json()
    assert data["filters"]["parent_zone"] == "example.com."


def test_search_zones_empty_query(client):
    """Test that empty search query is rejected."""
    response = client.get("/api/dns/zones/search?q=")
    
    assert response.status_code == 422  # Validation error


def test_search_records_empty_query(client):
    """Test that empty record search query is rejected."""
    response = client.get("/api/dns/records/search?q=")
    
    assert response.status_code == 422  # Validation error


def test_search_with_high_limit(client):
    """Test search with limit boundary."""
    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.search_zones.return_value = async_return([])
        mock_get_client.return_value.__aenter__.return_value = mock_client
        mock_get_client.return_value.__aexit__.return_value = async_return(None)
        
        # Test max limit
        response = client.get("/api/dns/zones/search?q=test&limit=500")
        assert response.status_code == 200
        
        # Test over limit
        response = client.get("/api/dns/zones/search?q=test&limit=501")
        assert response.status_code == 422  # Validation error


def test_search_zones_error_handling(client):
    """Test error handling in zone search."""
    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        # Create a mock context manager that returns a client that will raise an error
        mock_client = MagicMock()
        mock_client.search_zones = MagicMock(side_effect=PowerDNSError("Search failed"))
        
        # Setup the context manager
        mock_context = MagicMock()
        mock_context.__aenter__ = MagicMock(return_value=async_return(mock_client))
        mock_context.__aexit__ = MagicMock(return_value=async_return(None))
        mock_get_client.return_value = mock_context
        
        response = client.get("/api/dns/zones/search?q=test")
    
    assert response.status_code == 500
    assert "Search failed" in response.json()["detail"]


def test_search_records_error_handling(client):
    """Test error handling in record search."""
    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        # Create a mock context manager that returns a client that will raise an error
        mock_client = MagicMock()
        mock_client.search_records = MagicMock(side_effect=PowerDNSError("Search failed"))
        
        # Setup the context manager
        mock_context = MagicMock()
        mock_context.__aenter__ = MagicMock(return_value=async_return(mock_client))
        mock_context.__aexit__ = MagicMock(return_value=async_return(None))
        mock_get_client.return_value = mock_context
        
        response = client.get("/api/dns/records/search?q=test")
    
    assert response.status_code == 500
    assert "Search failed" in response.json()["detail"]


def test_filter_zones_error_handling(client):
    """Test error handling in zone filtering."""
    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        # Create a mock context manager that returns a client that will raise an error
        mock_client = MagicMock()
        mock_client.filter_zones = MagicMock(side_effect=PowerDNSError("Filter failed"))
        
        # Setup the context manager
        mock_context = MagicMock()
        mock_context.__aenter__ = MagicMock(return_value=async_return(mock_client))
        mock_context.__aexit__ = MagicMock(return_value=async_return(None))
        mock_get_client.return_value = mock_context
        
        response = client.post("/api/dns/zones/filter", json={})
    
    assert response.status_code == 500
    assert "Filter failed" in response.json()["detail"]