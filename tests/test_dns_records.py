#!/usr/bin/env python3
"""
Test DNS Record Management API (SCRUM-118)
Tests for DNS record CRUD operations through the API.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from server.api.app import create_app
from server.auth.dependencies import get_current_verified_user
from server.dns_manager import PowerDNSClient, PowerDNSError


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


@pytest.fixture
def mock_powerdns_client():
    """Mock PowerDNS client."""
    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = AsyncMock(spec=PowerDNSClient)
        mock_get_client.return_value.__aenter__.return_value = mock_client
        yield mock_client


def test_list_zone_records(client, mock_powerdns_client):
    """Test listing records in a zone."""
    # Mock record data
    mock_records = [
        {
            "name": "www.example.com.",
            "type": "A",
            "ttl": 3600,
            "records": [{"content": "192.168.1.1", "disabled": False}],
        },
        {
            "name": "mail.example.com.",
            "type": "MX",
            "ttl": 3600,
            "records": [{"content": "10 mail.example.com.", "disabled": False}],
        },
    ]

    mock_powerdns_client.list_records.return_value = mock_records

    response = client.get("/api/dns/zones/example.com./records")

    assert response.status_code == 200
    data = response.json()
    assert len(data["records"]) == 2
    assert data["records"][0]["name"] == "www.example.com."
    assert data["pagination"]["total"] == 2


def test_list_zone_records_with_filter(client, mock_powerdns_client):
    """Test listing records with type filter."""
    mock_records = [
        {
            "name": "www.example.com.",
            "type": "A",
            "ttl": 3600,
            "records": [{"content": "192.168.1.1", "disabled": False}],
        },
        {
            "name": "ipv6.example.com.",
            "type": "AAAA",
            "ttl": 3600,
            "records": [{"content": "2001:db8::1", "disabled": False}],
        },
    ]

    mock_powerdns_client.list_records.return_value = mock_records

    response = client.get("/api/dns/zones/example.com./records?record_type=A")

    assert response.status_code == 200
    data = response.json()
    assert len(data["records"]) == 1
    assert data["records"][0]["type"] == "A"


def test_get_record_set(client, mock_powerdns_client):
    """Test getting a specific record set."""
    mock_record = {
        "name": "www.example.com.",
        "type": "A",
        "ttl": 3600,
        "records": [{"content": "192.168.1.1", "disabled": False}],
    }

    mock_powerdns_client.get_record_set.return_value = mock_record

    response = client.get("/api/dns/zones/example.com./records/www/A")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "www.example.com."
    assert data["type"] == "A"


def test_get_record_set_not_found(client, mock_powerdns_client):
    """Test getting a non-existent record set."""
    mock_powerdns_client.get_record_set.return_value = None

    response = client.get("/api/dns/zones/example.com./records/nonexistent/A")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_record(client, mock_powerdns_client):
    """Test creating a new record."""
    record_data = {
        "name": "www",
        "type": "A",
        "ttl": 3600,
        "records": [{"content": "192.168.1.1"}, {"content": "192.168.1.2"}],
    }

    mock_powerdns_client.create_or_update_record.return_value = {
        "status": "success",
        "name": "www.example.com.",
        "type": "A",
    }

    response = client.post("/api/dns/zones/example.com./records", json=record_data)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["name"] == "www.example.com."

    # Verify the client was called correctly
    mock_powerdns_client.create_or_update_record.assert_called_once_with(
        zone_name="example.com.",
        name="www.example.com.",
        record_type="A",
        records=record_data["records"],
        ttl=3600,
    )


def test_create_record_validation_error(client, mock_powerdns_client):
    """Test creating a record with invalid data."""
    # Missing record type
    record_data = {"name": "www", "records": [{"content": "192.168.1.1"}]}

    response = client.post("/api/dns/zones/example.com./records", json=record_data)

    assert response.status_code == 400
    assert "Record type is required" in response.json()["detail"]


def test_update_record(client, mock_powerdns_client):
    """Test updating an existing record."""
    update_data = {"records": [{"content": "192.168.1.100"}], "ttl": 7200}

    mock_powerdns_client.create_or_update_record.return_value = {
        "status": "success",
        "name": "www.example.com.",
        "type": "A",
    }

    response = client.put("/api/dns/zones/example.com./records/www/A", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify the client was called correctly
    mock_powerdns_client.create_or_update_record.assert_called_once_with(
        zone_name="example.com.",
        name="www.example.com.",
        record_type="A",
        records=update_data["records"],
        ttl=7200,
    )


def test_delete_record(client, mock_powerdns_client):
    """Test deleting a record."""
    mock_powerdns_client.delete_record_set.return_value = {
        "status": "deleted",
        "name": "www.example.com.",
        "type": "A",
    }

    response = client.delete("/api/dns/zones/example.com./records/www/A")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "deleted"

    # Verify the client was called correctly
    mock_powerdns_client.delete_record_set.assert_called_once_with(
        zone_name="example.com.", name="www.example.com.", record_type="A"
    )


def test_record_type_validation(client, mock_powerdns_client):
    """Test record type-specific validation errors."""
    # Invalid IPv4 address
    record_data = {"name": "www", "type": "A", "records": [{"content": "invalid-ip"}]}

    mock_powerdns_client.create_or_update_record.side_effect = ValueError(
        "Invalid IPv4 address: invalid-ip"
    )

    response = client.post("/api/dns/zones/example.com./records", json=record_data)

    assert response.status_code == 400
    assert "Invalid IPv4 address" in response.json()["detail"]


def test_mx_record_creation(client, mock_powerdns_client):
    """Test creating MX records with priority."""
    record_data = {
        "name": "@",
        "type": "MX",
        "ttl": 3600,
        "records": [{"content": "10 mail.example.com."}, {"content": "20 backup.example.com."}],
    }

    mock_powerdns_client.create_or_update_record.return_value = {
        "status": "success",
        "name": "example.com.",
        "type": "MX",
    }

    response = client.post("/api/dns/zones/example.com./records", json=record_data)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify @ was converted to zone name
    mock_powerdns_client.create_or_update_record.assert_called_once()
    call_args = mock_powerdns_client.create_or_update_record.call_args[1]
    assert call_args["name"] == "@.example.com."


def test_zone_not_found_error(client, mock_powerdns_client):
    """Test error when zone is not found."""
    mock_powerdns_client.list_records.side_effect = PowerDNSError("Zone 'example.com.' not found")

    response = client.get("/api/dns/zones/example.com./records")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_record_without_name(client, mock_powerdns_client):
    """Test creating a record without name field."""
    record_data = {"type": "A", "records": [{"content": "192.168.1.1"}]}

    response = client.post("/api/dns/zones/example.com./records", json=record_data)

    assert response.status_code == 400
    assert "Record name is required" in response.json()["detail"]


def test_create_record_without_records(client, mock_powerdns_client):
    """Test creating a record without records field."""
    record_data = {"name": "www", "type": "A"}

    response = client.post("/api/dns/zones/example.com./records", json=record_data)

    assert response.status_code == 400
    assert "At least one record is required" in response.json()["detail"]
