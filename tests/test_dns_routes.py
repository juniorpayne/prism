#!/usr/bin/env python3
"""
Test DNS API Routes (SCRUM-116)
Basic tests for DNS API endpoint functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from server.api.app import create_app
from server.auth.dependencies import get_current_verified_user
from server.auth.models import User
from server.dns_manager import PowerDNSClient


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
    # Create a mock user object with the correct attributes
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

    # Override authentication dependency
    app.dependency_overrides[get_current_verified_user] = lambda: mock_user

    return TestClient(app)


@pytest.fixture
def mock_powerdns_client():
    """Mock PowerDNS client."""
    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = AsyncMock(spec=PowerDNSClient)
        mock_get_client.return_value.__aenter__.return_value = mock_client
        yield mock_client


def test_dns_health_endpoint(client):
    """Test DNS health endpoint."""
    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client._make_request.return_value = {"status": "ok"}
        mock_get_client.return_value.__aenter__.return_value = mock_client

        response = client.get("/api/dns/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["powerdns"] == "connected"


def test_dns_health_endpoint_failure(client):
    """Test DNS health endpoint with PowerDNS failure."""
    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client._make_request.side_effect = Exception("Connection failed")
        mock_get_client.return_value.__aenter__.return_value = mock_client

        response = client.get("/api/dns/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["powerdns"] == "disconnected"


def test_list_zones_endpoint(client, mock_powerdns_client):
    """Test list zones endpoint."""
    # Mock response data
    mock_zones = [
        {
            "id": "example.com.",
            "name": "example.com.",
            "kind": "Native",
            "serial": 2024122001,
            "rrsets": [
                {
                    "name": "example.com.",
                    "type": "SOA",
                    "records": [{"content": "ns1.example.com."}],
                },
                {
                    "name": "example.com.",
                    "type": "NS",
                    "records": [{"content": "ns1.example.com."}],
                },
            ],
        }
    ]

    mock_powerdns_client._make_request.return_value = mock_zones

    response = client.get("/api/dns/zones")

    assert response.status_code == 200
    data = response.json()
    assert "zones" in data
    assert "pagination" in data
    assert len(data["zones"]) == 1
    assert data["zones"][0]["name"] == "example.com."
    assert data["zones"][0]["record_count"] == 2  # SOA + NS


def test_list_zones_with_search(client, mock_powerdns_client):
    """Test list zones with search parameter."""
    mock_zones = [
        {"id": "example.com.", "name": "example.com.", "kind": "Native", "rrsets": []},
        {"id": "test.com.", "name": "test.com.", "kind": "Native", "rrsets": []},
    ]

    mock_powerdns_client._make_request.return_value = mock_zones

    response = client.get("/api/dns/zones?search=example")

    assert response.status_code == 200
    data = response.json()
    assert len(data["zones"]) == 1
    assert data["zones"][0]["name"] == "example.com."


def test_get_zone_endpoint(client, mock_powerdns_client):
    """Test get specific zone endpoint."""
    mock_zone = {
        "id": "example.com.",
        "name": "example.com.",
        "kind": "Native",
        "serial": 2024122001,
        "rrsets": [
            {"name": "example.com.", "type": "SOA", "records": [{"content": "ns1.example.com."}]},
            {"name": "example.com.", "type": "NS", "records": [{"content": "ns1.example.com."}]},
        ],
    }

    mock_powerdns_client._make_request.return_value = mock_zone

    response = client.get("/api/dns/zones/example.com.")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "example.com."
    assert data["record_count"] == 2


def test_get_zone_not_found(client, mock_powerdns_client):
    """Test get zone that doesn't exist."""
    from server.dns_manager import PowerDNSAPIError

    mock_powerdns_client._make_request.side_effect = PowerDNSAPIError("Not Found", status_code=404)

    response = client.get("/api/dns/zones/nonexistent.com.")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_list_zones_unauthenticated(test_config):
    """Test list zones without authentication."""
    # Create client without authentication override
    app = create_app(test_config)
    client = TestClient(app)

    response = client.get("/api/dns/zones")

    # Should return 403 Forbidden (FastAPI default for missing auth)
    assert response.status_code == 403


def test_list_zones_pagination(client, mock_powerdns_client):
    """Test list zones with pagination."""
    # Create mock zones
    mock_zones = []
    for i in range(100):
        mock_zones.append(
            {"id": f"test{i}.com.", "name": f"test{i}.com.", "kind": "Native", "rrsets": []}
        )

    mock_powerdns_client._make_request.return_value = mock_zones

    response = client.get("/api/dns/zones?page=2&limit=25")

    assert response.status_code == 200
    data = response.json()
    assert len(data["zones"]) == 25
    assert data["pagination"]["page"] == 2
    assert data["pagination"]["limit"] == 25
    assert data["pagination"]["total"] == 100
    assert data["pagination"]["pages"] == 4


def test_list_zones_sorting(client, mock_powerdns_client):
    """Test list zones with sorting."""
    mock_zones = [
        {"id": "zebra.com.", "name": "zebra.com.", "kind": "Native", "rrsets": []},
        {"id": "alpha.com.", "name": "alpha.com.", "kind": "Native", "rrsets": []},
    ]

    mock_powerdns_client._make_request.return_value = mock_zones

    response = client.get("/api/dns/zones?sort=name&order=asc")

    assert response.status_code == 200
    data = response.json()
    assert len(data["zones"]) == 2
    assert data["zones"][0]["name"] == "alpha.com."
    assert data["zones"][1]["name"] == "zebra.com."


def test_powerdns_connection_error(client, mock_powerdns_client):
    """Test PowerDNS connection error handling."""
    from server.dns_manager import PowerDNSConnectionError

    mock_powerdns_client._make_request.side_effect = PowerDNSConnectionError("Connection failed")

    response = client.get("/api/dns/zones")

    assert response.status_code == 503
    data = response.json()
    assert "service unavailable" in data["detail"].lower()


def test_rate_limiting(client, mock_powerdns_client):
    """Test rate limiting on DNS endpoints."""
    mock_powerdns_client._make_request.return_value = []

    # Make many requests quickly
    success_count = 0
    rate_limited_count = 0

    for i in range(10):
        response = client.get("/api/dns/zones")
        if response.status_code == 200:
            success_count += 1
        elif response.status_code == 429:
            rate_limited_count += 1

    # Should have some successful requests
    assert success_count > 0
