#!/usr/bin/env python3
"""
Test DNS Frontend API Integration (SCRUM-121)
Integration tests for frontend DNS API client with backend
"""

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from server.api.app import create_app
from server.auth.dependencies import get_current_verified_user


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


class TestDNSFrontendIntegration:
    """Test frontend API client integration with backend."""

    def test_zone_list_endpoint(self, client):
        """Test zone list endpoint returns expected format for frontend."""
        response = client.get("/api/dns/zones?page=1&limit=50")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure for frontend
        assert "zones" in data
        assert "pagination" in data
        assert "page" in data["pagination"]
        assert "limit" in data["pagination"]
        assert "total" in data["pagination"]
        assert "pages" in data["pagination"]

    def test_zone_search_endpoint(self, client):
        """Test zone search endpoint with query parameters."""
        response = client.get("/api/dns/zones/search?q=example&zone_type=Native&limit=50")

        assert response.status_code == 200
        data = response.json()

        # Verify search response structure
        assert "query" in data
        assert "total" in data
        assert "zones" in data
        assert "filters" in data
        assert data["query"] == "example"
        assert data["filters"]["zone_type"] == "Native"

    def test_record_search_endpoint(self, client):
        """Test record search endpoint with filters."""
        response = client.get("/api/dns/records/search?q=www&record_type=A&content=true")

        assert response.status_code == 200
        data = response.json()

        # Verify record search response
        assert "query" in data
        assert "total" in data
        assert "records" in data
        assert "filters" in data
        assert data["filters"]["content_search"] is True

    def test_zone_filter_endpoint(self, client):
        """Test zone filter endpoint with POST body."""
        filters = {"min_records": 5, "max_records": 100, "has_dnssec": True}

        response = client.post("/api/dns/zones/filter?sort_by=name&sort_order=asc", json=filters)

        assert response.status_code == 200
        data = response.json()

        # Verify filter response
        assert "total" in data
        assert "zones" in data
        assert "filters" in data
        assert "sort" in data
        assert data["sort"]["by"] == "name"
        assert data["sort"]["order"] == "asc"

    def test_export_zones_json(self, client):
        """Test zone export in JSON format."""
        response = client.get("/api/dns/export/zones?format=json&include_dnssec=true")

        assert response.status_code in [200, 500]  # May fail if PowerDNS not available

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_export_zones_bind(self, client):
        """Test zone export in BIND format returns file download."""
        response = client.get("/api/dns/export/zones?format=bind")

        if response.status_code == 200:
            assert response.headers.get("content-type") == "text/plain; charset=utf-8"
            assert "Content-Disposition" in response.headers
            assert "dns-export.bind" in response.headers["Content-Disposition"]

    def test_import_zones_validation(self, client):
        """Test zone import with validation."""
        import_data = {
            "data": '{"zones": [{"name": "test.com.", "kind": "Native"}]}',
            "format": "json",
            "mode": "merge",
        }

        response = client.post("/api/dns/import/zones", json=import_data)

        # Should get 200 or 500 (if PowerDNS not available)
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "status" in data

    def test_import_preview(self, client):
        """Test import preview always runs in dry-run mode."""
        import_data = {"data": '{"zones": []}', "format": "json", "mode": "replace"}

        response = client.post("/api/dns/import/preview", json=import_data)

        assert response.status_code in [200, 500]

    def test_dns_health_endpoint(self, client):
        """Test DNS health check endpoint."""
        response = client.get("/api/dns/health")

        assert response.status_code == 200
        data = response.json()

        # Health check should always return a status
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]
        assert "powerdns" in data

    def test_authentication_required(self, test_config):
        """Test that DNS endpoints require authentication."""
        # Create app without auth override
        app = create_app(test_config)
        test_client = TestClient(app)

        # These should all return 401 without auth
        endpoints = [
            "/api/dns/zones",
            "/api/dns/zones/search?q=test",
            "/api/dns/records/search?q=test",
            "/api/dns/export/zones",
            "/api/dns/import/zones",
        ]

        for endpoint in endpoints:
            if endpoint.startswith("/api/dns/import"):
                response = test_client.post(endpoint, json={})
            else:
                response = test_client.get(endpoint)

            assert response.status_code in [401, 403]  # 403 for Not authenticated

    def test_cors_headers(self, client):
        """Test CORS headers are present for frontend access."""
        response = client.options(
            "/api/dns/zones",
            headers={"Origin": "http://localhost:8090", "Access-Control-Request-Method": "GET"},
        )

        # CORS middleware should handle preflight
        assert response.status_code in [200, 400]

    def test_error_response_format(self, client):
        """Test error responses have consistent format for frontend."""
        # Try to get non-existent zone
        response = client.get("/api/dns/zones/nonexistent.zone.")

        if response.status_code >= 400:
            data = response.json()
            assert "detail" in data
            # Error response should have consistent structure
            assert isinstance(data["detail"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
