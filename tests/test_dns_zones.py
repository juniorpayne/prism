#!/usr/bin/env python3
"""
Test DNS Zone CRUD Operations (SCRUM-117)
Comprehensive tests for zone management functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from server.api.app import create_app
from server.auth.dependencies import get_current_verified_user
from server.dns_manager import PowerDNSAPIError, PowerDNSClient, PowerDNSConnectionError


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
    mock.id = "test-user-id"
    mock.email = "test@example.com"
    mock.username = "testuser"
    mock.is_active = True
    mock.is_admin = False
    mock.email_verified = True
    return mock


@pytest.fixture
def client(test_config, mock_user):
    """Test client fixture with authentication override."""
    app = create_app(test_config)
    app.dependency_overrides[get_current_verified_user] = lambda: mock_user
    return TestClient(app)


@pytest.fixture
def mock_powerdns_client():
    """Mock PowerDNS client."""
    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = AsyncMock(spec=PowerDNSClient)
        mock_get_client.return_value.__aenter__.return_value = mock_client
        yield mock_client


def test_create_zone_success(client, mock_powerdns_client):
    """Test successful zone creation."""
    zone_data = {
        "name": "example.com.",
        "kind": "Native",
        "nameservers": ["ns1.example.com.", "ns2.example.com."],
    }

    mock_powerdns_client.validate_zone_name.return_value = (True, None)
    mock_powerdns_client.get_zone_details.return_value = None  # Zone doesn't exist
    mock_powerdns_client.create_zone.return_value = {"status": "created", "zone": "example.com."}

    response = client.post("/api/dns/zones", json=zone_data)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "created"
    assert data["zone"] == "example.com."

    # Verify method calls
    mock_powerdns_client.validate_zone_name.assert_called_once_with("example.com.")
    mock_powerdns_client.get_zone_details.assert_called_once_with("example.com.")
    mock_powerdns_client.create_zone.assert_called_once()


def test_create_zone_invalid_name(client, mock_powerdns_client):
    """Test zone creation with invalid name."""
    zone_data = {
        "name": "example.com",  # Missing trailing dot
        "kind": "Native",
        "nameservers": ["ns1.example.com.", "ns2.example.com."],
    }

    mock_powerdns_client.validate_zone_name.return_value = (
        False,
        "Zone name must end with a dot (.)",
    )

    response = client.post("/api/dns/zones", json=zone_data)

    assert response.status_code == 400
    data = response.json()
    assert "Zone name must end with a dot" in data["detail"]


def test_create_zone_already_exists(client, mock_powerdns_client):
    """Test zone creation when zone already exists."""
    zone_data = {
        "name": "example.com.",
        "kind": "Native",
        "nameservers": ["ns1.example.com.", "ns2.example.com."],
    }

    mock_powerdns_client.validate_zone_name.return_value = (True, None)
    mock_powerdns_client.get_zone_details.return_value = {"name": "example.com."}  # Zone exists

    response = client.post("/api/dns/zones", json=zone_data)

    assert response.status_code == 409
    data = response.json()
    assert "already exists" in data["detail"]


def test_update_zone_success(client, mock_powerdns_client):
    """Test successful zone update."""
    zone_id = "example.com."
    update_data = {
        "kind": "Master",
        "dnssec": True,
    }

    mock_powerdns_client.get_zone_details.return_value = {"name": "example.com.", "kind": "Native"}
    mock_powerdns_client.update_zone.return_value = {"status": "updated", "zone": "example.com."}

    response = client.put(f"/api/dns/zones/{zone_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "updated"
    assert data["zone"] == "example.com."

    # Verify method calls
    mock_powerdns_client.get_zone_details.assert_called_once_with(zone_id)
    mock_powerdns_client.update_zone.assert_called_once_with(zone_id, update_data)


def test_update_zone_not_found(client, mock_powerdns_client):
    """Test zone update when zone doesn't exist."""
    zone_id = "nonexistent.com."
    update_data = {"kind": "Master"}

    mock_powerdns_client.get_zone_details.return_value = None

    response = client.put(f"/api/dns/zones/{zone_id}", json=update_data)

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"]


def test_delete_zone_success(client, mock_powerdns_client):
    """Test successful zone deletion."""
    zone_id = "example.com."

    mock_powerdns_client.get_zone_details.return_value = {"name": "example.com."}
    mock_powerdns_client.delete_zone.return_value = {"status": "deleted", "zone": "example.com."}

    response = client.delete(f"/api/dns/zones/{zone_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "deleted"
    assert data["zone"] == "example.com."

    # Verify method calls
    mock_powerdns_client.get_zone_details.assert_called_once_with(zone_id)
    mock_powerdns_client.delete_zone.assert_called_once_with(zone_id)


def test_delete_zone_not_found(client, mock_powerdns_client):
    """Test zone deletion when zone doesn't exist."""
    zone_id = "nonexistent.com."

    mock_powerdns_client.get_zone_details.return_value = None

    response = client.delete(f"/api/dns/zones/{zone_id}")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"]


def test_zone_operations_connection_error(client, mock_powerdns_client):
    """Test zone operations with PowerDNS connection error."""
    zone_data = {
        "name": "example.com.",
        "kind": "Native",
        "nameservers": ["ns1.example.com.", "ns2.example.com."],
    }

    mock_powerdns_client.validate_zone_name.return_value = (True, None)
    mock_powerdns_client.get_zone_details.side_effect = PowerDNSConnectionError("Connection failed")

    response = client.post("/api/dns/zones", json=zone_data)

    assert response.status_code == 503
    data = response.json()
    assert "service unavailable" in data["detail"].lower()


def test_zone_operations_api_error(client, mock_powerdns_client):
    """Test zone operations with PowerDNS API error."""
    zone_id = "example.com."

    mock_powerdns_client.get_zone_details.side_effect = PowerDNSAPIError(
        "API Error", status_code=400
    )

    response = client.delete(f"/api/dns/zones/{zone_id}")

    assert response.status_code == 400
    data = response.json()
    assert "API Error" in data["detail"]


# Test zone validation
def test_zone_name_validation():
    """Test zone name validation logic."""
    from server.dns_manager import PowerDNSClient

    config = {
        "server": {"tcp_port": 8080, "api_port": 8081, "host": "localhost"},
        "database": {"path": ":memory:"},
        "powerdns": {"enabled": True, "api_url": "http://localhost", "api_key": "test"},
    }
    client = PowerDNSClient(config)

    # Valid zone names
    assert client.validate_zone_name("example.com.")[0] is True
    assert client.validate_zone_name("sub.example.com.")[0] is True
    assert client.validate_zone_name("test-zone.org.")[0] is True
    assert client.validate_zone_name("123.example.com.")[0] is True

    # Invalid zone names
    assert client.validate_zone_name("example.com")[0] is False  # Missing dot
    assert client.validate_zone_name("")[0] is False  # Empty
    assert client.validate_zone_name("example..com.")[0] is False  # Double dot
    assert client.validate_zone_name("-example.com.")[0] is False  # Starts with hyphen
    assert client.validate_zone_name("example-.com.")[0] is False  # Ends with hyphen
    assert client.validate_zone_name("a" * 64 + ".com.")[0] is False  # Label too long


def test_soa_record_validation():
    """Test SOA record validation logic."""
    from server.dns_manager import PowerDNSClient

    config = {
        "server": {"tcp_port": 8080, "api_port": 8081, "host": "localhost"},
        "database": {"path": ":memory:"},
        "powerdns": {"enabled": True, "api_url": "http://localhost", "api_key": "test"},
    }
    client = PowerDNSClient(config)

    # Valid SOA record
    valid_soa = "ns1.example.com. admin.example.com. 2024010101 3600 1800 604800 86400"
    assert client.validate_soa_record(valid_soa)[0] is True

    # Invalid SOA records
    invalid_soa = (
        "ns1.example.com admin.example.com 2024010101 3600 1800 604800 86400"  # Missing dots
    )
    assert client.validate_soa_record(invalid_soa)[0] is False

    invalid_soa = (
        "ns1.example.com. admin.example.com. abc 3600 1800 604800 86400"  # Non-numeric serial
    )
    assert client.validate_soa_record(invalid_soa)[0] is False

    invalid_soa = "ns1.example.com. admin.example.com. 2024010101 3600 1800"  # Missing fields
    assert client.validate_soa_record(invalid_soa)[0] is False


def test_zone_hierarchy_detection():
    """Test zone hierarchy detection logic."""
    from server.dns_manager import PowerDNSClient

    config = {
        "server": {"tcp_port": 8080, "api_port": 8081, "host": "localhost"},
        "database": {"path": ":memory:"},
        "powerdns": {"enabled": True, "api_url": "http://localhost", "api_key": "test"},
    }
    client = PowerDNSClient(config)

    existing_zones = ["example.com.", "sub.example.com.", "test.example.com.", "other.org."]

    # Test child zone
    hierarchy = client.detect_zone_hierarchy("api.sub.example.com.", existing_zones)
    assert hierarchy["parent"] == "sub.example.com."
    assert hierarchy["children"] == []
    assert hierarchy["level"] == 1

    # Test parent zone
    hierarchy = client.detect_zone_hierarchy("com.", existing_zones)
    assert hierarchy["parent"] is None
    assert "example.com." in hierarchy["children"]
    assert hierarchy["level"] == 0

    # Test zone with both parent and children
    hierarchy = client.detect_zone_hierarchy("example.com.", existing_zones)
    assert hierarchy["parent"] is None  # No parent in the list
    assert "sub.example.com." in hierarchy["children"]
    assert "test.example.com." in hierarchy["children"]
    assert hierarchy["level"] == 0
