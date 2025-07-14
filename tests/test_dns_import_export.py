#!/usr/bin/env python3
"""
Test DNS Import/Export API (SCRUM-120)
Tests for DNS zone import and export functionality.
"""

from asyncio import Future
from unittest.mock import MagicMock, patch

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


@pytest.fixture
def sample_zones():
    """Sample zone data for testing."""
    return [
        {
            "id": "example.com.",
            "name": "example.com.",
            "kind": "Native",
            "serial": 2024122001,
            "dnssec": False,
            "rrsets": [
                {
                    "name": "example.com.",
                    "type": "SOA",
                    "ttl": 3600,
                    "records": [
                        {
                            "content": "ns1.example.com. admin.example.com. 2024122001 3600 600 86400 3600",
                            "disabled": False,
                        }
                    ],
                },
                {
                    "name": "example.com.",
                    "type": "NS",
                    "ttl": 3600,
                    "records": [
                        {"content": "ns1.example.com.", "disabled": False},
                        {"content": "ns2.example.com.", "disabled": False},
                    ],
                },
                {
                    "name": "www.example.com.",
                    "type": "A",
                    "ttl": 300,
                    "records": [{"content": "192.168.1.1", "disabled": False}],
                },
            ],
        }
    ]


def test_export_zones_json(client, sample_zones):
    """Test exporting zones in JSON format."""
    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.export_zones.return_value = async_return(
            {"format": "json", "version": "1.0", "zones": sample_zones}
        )

        mock_context = MagicMock()
        mock_context.__aenter__ = MagicMock(return_value=async_return(mock_client))
        mock_context.__aexit__ = MagicMock(return_value=async_return(None))
        mock_get_client.return_value = mock_context

        response = client.get("/api/dns/export/zones?format=json")

    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "json"
    assert data["version"] == "1.0"
    assert len(data["zones"]) == 1
    assert data["zones"][0]["name"] == "example.com."

    # Verify export was called correctly
    mock_client.export_zones.assert_called_once_with(
        zone_names=None, format="json", include_dnssec=True
    )


def test_export_zones_bind(client):
    """Test exporting zones in BIND format."""
    bind_data = """; Zone: example.com.
; Exported from PowerDNS

example.com.	3600	IN	SOA	ns1.example.com. admin.example.com. 2024122001 3600 600 86400 3600
example.com.	3600	IN	NS	ns1.example.com.
example.com.	3600	IN	NS	ns2.example.com.
www.example.com.	300	IN	A	192.168.1.1
"""

    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.export_zones.return_value = async_return({"format": "bind", "data": bind_data})

        mock_context = MagicMock()
        mock_context.__aenter__ = MagicMock(return_value=async_return(mock_client))
        mock_context.__aexit__ = MagicMock(return_value=async_return(None))
        mock_get_client.return_value = mock_context

        response = client.get("/api/dns/export/zones?format=bind")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert "Content-Disposition" in response.headers
    assert "dns-export.bind" in response.headers["Content-Disposition"]
    assert response.text == bind_data


def test_export_zones_csv(client):
    """Test exporting zones in CSV format."""
    csv_data = """zone,name,type,ttl,content,disabled
example.com.,example.com.,SOA,3600,"ns1.example.com. admin.example.com. 2024122001 3600 600 86400 3600",False
example.com.,example.com.,NS,3600,ns1.example.com.,False
example.com.,example.com.,NS,3600,ns2.example.com.,False
example.com.,www.example.com.,A,300,192.168.1.1,False
"""

    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.export_zones.return_value = async_return({"format": "csv", "data": csv_data})

        mock_context = MagicMock()
        mock_context.__aenter__ = MagicMock(return_value=async_return(mock_client))
        mock_context.__aexit__ = MagicMock(return_value=async_return(None))
        mock_get_client.return_value = mock_context

        response = client.get("/api/dns/export/zones?format=csv")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert "Content-Disposition" in response.headers
    assert "dns-export.csv" in response.headers["Content-Disposition"]


def test_export_specific_zones(client):
    """Test exporting specific zones only."""
    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.export_zones.return_value = async_return(
            {"format": "json", "version": "1.0", "zones": []}
        )

        mock_context = MagicMock()
        mock_context.__aenter__ = MagicMock(return_value=async_return(mock_client))
        mock_context.__aexit__ = MagicMock(return_value=async_return(None))
        mock_get_client.return_value = mock_context

        response = client.get("/api/dns/export/zones?zones=example.com.,test.com.")

    assert response.status_code == 200

    # Verify specific zones were requested
    mock_client.export_zones.assert_called_once_with(
        zone_names=["example.com.", "test.com."], format="json", include_dnssec=True
    )


def test_import_zones_json(client):
    """Test importing zones in JSON format."""
    import_data = {
        "data": '{"zones": [{"name": "test.com.", "kind": "Native", "rrsets": []}]}',
        "format": "json",
        "mode": "merge",
    }

    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.import_zones.return_value = async_return(
            {
                "status": "success",
                "mode": "merge",
                "zones_processed": 1,
                "zones_created": 1,
                "zones_updated": 0,
                "zones_skipped": 0,
                "records_added": 0,
                "errors": [],
            }
        )

        mock_context = MagicMock()
        mock_context.__aenter__ = MagicMock(return_value=async_return(mock_client))
        mock_context.__aexit__ = MagicMock(return_value=async_return(None))
        mock_get_client.return_value = mock_context

        response = client.post("/api/dns/import/zones", json=import_data)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["zones_processed"] == 1
    assert data["zones_created"] == 1

    # Verify import was called correctly
    mock_client.import_zones.assert_called_once_with(
        data=import_data["data"], format="json", mode="merge", dry_run=False
    )


def test_import_zones_bind(client):
    """Test importing zones in BIND format."""
    bind_data = """$ORIGIN example.com.
$TTL 3600

@	IN	SOA	ns1.example.com. admin.example.com. (
			2024122001	; serial
			3600		; refresh
			600		; retry
			86400		; expire
			3600		; minimum
			)

@	IN	NS	ns1.example.com.
@	IN	NS	ns2.example.com.

www	IN	A	192.168.1.1
"""

    import_data = {"data": bind_data, "format": "bind", "mode": "replace"}

    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.import_zones.return_value = async_return(
            {
                "status": "success",
                "mode": "replace",
                "zones_processed": 1,
                "zones_created": 0,
                "zones_updated": 1,
                "zones_skipped": 0,
                "records_added": 3,
                "errors": [],
            }
        )

        mock_context = MagicMock()
        mock_context.__aenter__ = MagicMock(return_value=async_return(mock_client))
        mock_context.__aexit__ = MagicMock(return_value=async_return(None))
        mock_get_client.return_value = mock_context

        response = client.post("/api/dns/import/zones", json=import_data)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["zones_updated"] == 1
    assert data["records_added"] == 3


def test_import_preview(client):
    """Test previewing import without applying changes."""
    import_data = {
        "data": '{"zones": [{"name": "preview.com.", "kind": "Native", "rrsets": []}]}',
        "format": "json",
        "mode": "merge",
    }

    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.import_zones.return_value = async_return(
            {
                "status": "preview",
                "mode": "merge",
                "zones_processed": 1,
                "zones_created": 1,
                "zones_updated": 0,
                "zones_skipped": 0,
                "records_added": 0,
                "errors": [],
            }
        )

        mock_context = MagicMock()
        mock_context.__aenter__ = MagicMock(return_value=async_return(mock_client))
        mock_context.__aexit__ = MagicMock(return_value=async_return(None))
        mock_get_client.return_value = mock_context

        response = client.post("/api/dns/import/preview", json=import_data)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "preview"

    # Verify dry_run was set to True
    mock_client.import_zones.assert_called_once_with(
        data=import_data["data"], format="json", mode="merge", dry_run=True
    )


def test_import_with_validation_errors(client):
    """Test import with validation errors."""
    import_data = {
        "data": '{"zones": [{"name": "invalid zone", "kind": "Native", "rrsets": []}]}',
        "format": "json",
        "mode": "merge",
    }

    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.import_zones.return_value = async_return(
            {
                "status": "error",
                "errors": ["Zone invalid zone: Zone name must end with a dot (.)"],
                "zones_parsed": 1,
            }
        )

        mock_context = MagicMock()
        mock_context.__aenter__ = MagicMock(return_value=async_return(mock_client))
        mock_context.__aexit__ = MagicMock(return_value=async_return(None))
        mock_get_client.return_value = mock_context

        response = client.post("/api/dns/import/zones", json=import_data)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert len(data["errors"]) == 1
    assert "Zone name must end with a dot" in data["errors"][0]


def test_import_skip_mode(client):
    """Test import with skip mode for existing zones."""
    import_data = {
        "data": '{"zones": [{"name": "existing.com.", "kind": "Native", "rrsets": []}]}',
        "format": "json",
        "mode": "skip",
    }

    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.import_zones.return_value = async_return(
            {
                "status": "success",
                "mode": "skip",
                "zones_processed": 1,
                "zones_created": 0,
                "zones_updated": 0,
                "zones_skipped": 1,
                "records_added": 0,
                "errors": [],
            }
        )

        mock_context = MagicMock()
        mock_context.__aenter__ = MagicMock(return_value=async_return(mock_client))
        mock_context.__aexit__ = MagicMock(return_value=async_return(None))
        mock_get_client.return_value = mock_context

        response = client.post("/api/dns/import/zones", json=import_data)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["zones_skipped"] == 1


def test_export_invalid_format(client):
    """Test export with invalid format."""
    response = client.get("/api/dns/export/zones?format=invalid")

    # Should get error from PowerDNSClient
    assert response.status_code == 400


def test_import_missing_data(client):
    """Test import without data."""
    import_data = {"format": "json", "mode": "merge"}

    response = client.post("/api/dns/import/zones", json=import_data)

    assert response.status_code == 400
    assert "Import data is required" in response.json()["detail"]


def test_import_invalid_mode(client):
    """Test import with invalid mode."""
    import_data = {"data": '{"zones": []}', "format": "json", "mode": "invalid"}

    response = client.post("/api/dns/import/zones", json=import_data)

    assert response.status_code == 400
    assert "Invalid import mode" in response.json()["detail"]


def test_export_error_handling(client):
    """Test error handling during export."""
    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = MagicMock()

        # Create a coroutine that raises the exception
        async def mock_export_zones(*args, **kwargs):
            raise PowerDNSError("Export failed")

        mock_client.export_zones = mock_export_zones

        mock_context = MagicMock()
        mock_context.__aenter__ = MagicMock(return_value=async_return(mock_client))
        mock_context.__aexit__ = MagicMock(return_value=async_return(None))
        mock_get_client.return_value = mock_context

        response = client.get("/api/dns/export/zones")

    assert response.status_code == 500
    assert "Export failed" in response.json()["detail"]


def test_import_error_handling(client):
    """Test error handling during import."""
    import_data = {"data": '{"zones": []}', "format": "json", "mode": "merge"}

    with patch("server.api.routes.dns.get_powerdns_client") as mock_get_client:
        mock_client = MagicMock()

        # Create a coroutine that raises the exception
        async def mock_import_zones(*args, **kwargs):
            raise PowerDNSError("Import failed")

        mock_client.import_zones = mock_import_zones

        mock_context = MagicMock()
        mock_context.__aenter__ = MagicMock(return_value=async_return(mock_client))
        mock_context.__aexit__ = MagicMock(return_value=async_return(None))
        mock_get_client.return_value = mock_context

        response = client.post("/api/dns/import/zones", json=import_data)

    assert response.status_code == 500
    assert "Import failed" in response.json()["detail"]
