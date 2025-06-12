#!/usr/bin/env python3
"""
Unit tests for PowerDNS API Client (SCRUM-49)
Tests DNS client functionality with mocked API responses.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from aiohttp import ClientError

from server.dns_manager import (
    PowerDNSAPIError,
    PowerDNSClient,
    PowerDNSConnectionError,
    create_dns_client,
)


class TestPowerDNSClient:
    """Test PowerDNS client functionality."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return {
            "powerdns": {
                "enabled": True,
                "api_url": "http://localhost:8053/api/v1",
                "api_key": "test-api-key",
                "default_zone": "test.local.",
                "default_ttl": 300,
                "timeout": 5,
                "retry_attempts": 3,
                "retry_delay": 1,
                "record_types": ["A", "AAAA"],
                "auto_ptr": False,
            }
        }

    @pytest.fixture
    def disabled_config(self):
        """Create configuration with PowerDNS disabled."""
        config = self.config()
        config["powerdns"]["enabled"] = False
        return config

    @pytest.fixture
    def client(self, config):
        """Create PowerDNS client instance."""
        return PowerDNSClient(config)

    @pytest.fixture
    def disabled_client(self, disabled_config):
        """Create disabled PowerDNS client instance."""
        return PowerDNSClient(disabled_config)

    def test_client_initialization(self, client):
        """Test client initialization with configuration."""
        assert client.enabled is True
        assert client.base_url == "http://localhost:8053/api/v1"
        assert client.api_key == "test-api-key"
        assert client.default_zone == "test.local."
        assert client.default_ttl == 300
        assert client.timeout == 5
        assert client.retry_attempts == 3

    def test_client_initialization_adds_zone_dot(self):
        """Test that zone dot is added if missing."""
        config = {
            "powerdns": {
                "enabled": True,
                "default_zone": "test.local",  # Missing dot
            }
        }
        client = PowerDNSClient(config)
        assert client.default_zone == "test.local."

    @pytest.mark.asyncio
    async def test_create_a_record_disabled(self, disabled_client):
        """Test creating A record when PowerDNS is disabled."""
        result = await disabled_client.create_a_record("host1", "192.168.1.100")
        assert result == {"status": "disabled"}

    @pytest.mark.asyncio
    async def test_create_a_record_success(self, client):
        """Test successful A record creation."""
        mock_response = AsyncMock()
        mock_response.status = 204
        mock_response.text.return_value = ""

        with patch.object(client, "_make_request", return_value={}) as mock_request:
            result = await client.create_a_record("host1", "192.168.1.100")

            mock_request.assert_called_once_with(
                "PATCH",
                "/servers/localhost/zones/test.local.",
                json_data={
                    "rrsets": [
                        {
                            "name": "host1.test.local.",
                            "type": "A",
                            "ttl": 300,
                            "changetype": "REPLACE",
                            "records": [
                                {
                                    "content": "192.168.1.100",
                                    "disabled": False,
                                }
                            ],
                        }
                    ]
                },
            )

            assert result["status"] == "success"
            assert result["fqdn"] == "host1.test.local."
            assert result["zone"] == "test.local."

    @pytest.mark.asyncio
    async def test_create_a_record_custom_zone_ttl(self, client):
        """Test A record creation with custom zone and TTL."""
        with patch.object(client, "_make_request", return_value={}) as mock_request:
            result = await client.create_a_record(
                "host1", "192.168.1.100", zone="custom.zone.", ttl=600
            )

            rrsets = mock_request.call_args[1]["json_data"]["rrsets"]
            assert rrsets[0]["name"] == "host1.custom.zone."
            assert rrsets[0]["ttl"] == 600
            assert result["zone"] == "custom.zone."

    @pytest.mark.asyncio
    async def test_create_aaaa_record_success(self, client):
        """Test successful AAAA record creation."""
        with patch.object(client, "_make_request", return_value={}) as mock_request:
            result = await client.create_aaaa_record("host1", "2001:db8::1")

            rrsets = mock_request.call_args[1]["json_data"]["rrsets"]
            assert rrsets[0]["type"] == "AAAA"
            assert rrsets[0]["records"][0]["content"] == "2001:db8::1"
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_delete_record_success(self, client):
        """Test successful record deletion."""
        with patch.object(client, "_make_request", return_value={}) as mock_request:
            result = await client.delete_record("host1", "A")

            rrsets = mock_request.call_args[1]["json_data"]["rrsets"]
            assert rrsets[0]["name"] == "host1.test.local."
            assert rrsets[0]["type"] == "A"
            assert rrsets[0]["changetype"] == "DELETE"
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_record_found(self, client):
        """Test getting existing DNS record."""
        mock_zone_data = {
            "rrsets": [
                {
                    "name": "host1.test.local.",
                    "type": "A",
                    "ttl": 300,
                    "records": [{"content": "192.168.1.100", "disabled": False}],
                },
                {
                    "name": "host2.test.local.",
                    "type": "A",
                    "ttl": 300,
                    "records": [{"content": "192.168.1.101", "disabled": False}],
                },
            ]
        }

        with patch.object(client, "_make_request", return_value=mock_zone_data):
            result = await client.get_record("host1", "A")

            assert result is not None
            assert result["name"] == "host1.test.local."
            assert result["type"] == "A"
            assert result["records"][0]["content"] == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_get_record_not_found(self, client):
        """Test getting non-existent DNS record."""
        mock_zone_data = {"rrsets": []}

        with patch.object(client, "_make_request", return_value=mock_zone_data):
            result = await client.get_record("nonexistent", "A")
            assert result is None

    @pytest.mark.asyncio
    async def test_zone_exists_true(self, client):
        """Test checking if zone exists."""
        with patch.object(client, "_make_request", return_value={}):
            exists = await client.zone_exists("test.local.")
            assert exists is True

    @pytest.mark.asyncio
    async def test_zone_exists_false(self, client):
        """Test checking if zone doesn't exist."""
        with patch.object(
            client,
            "_make_request",
            side_effect=PowerDNSAPIError("Not found", status_code=404),
        ):
            exists = await client.zone_exists("nonexistent.zone.")
            assert exists is False

    @pytest.mark.asyncio
    async def test_create_zone_success(self, client):
        """Test successful zone creation."""
        with patch.object(client, "zone_exists", return_value=False):
            with patch.object(client, "_make_request", return_value={}) as mock_request:
                result = await client.create_zone(
                    "new.zone.", ["ns1.example.com.", "ns2.example.com."]
                )

                zone_data = mock_request.call_args[1]["json_data"]
                assert zone_data["name"] == "new.zone."
                assert zone_data["kind"] == "Native"
                assert len(zone_data["rrsets"]) == 2  # SOA and NS records
                assert result["status"] == "created"

    @pytest.mark.asyncio
    async def test_create_zone_already_exists(self, client):
        """Test creating zone that already exists."""
        with patch.object(client, "zone_exists", return_value=True):
            result = await client.create_zone("existing.zone.")
            assert result["status"] == "exists"

    @pytest.mark.asyncio
    async def test_make_request_retry_on_connection_error(self, client):
        """Test request retry on connection errors."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = '{"result": "success"}'

        # First two attempts fail, third succeeds
        mock_session.request.side_effect = [
            ClientError("Connection failed"),
            ClientError("Connection failed"),
            mock_response,
        ]

        with patch.object(client, "_get_session", return_value=mock_session):
            result = await client._make_request("GET", "/test")
            assert result == {"result": "success"}
            assert mock_session.request.call_count == 3

    @pytest.mark.asyncio
    async def test_make_request_max_retries_exceeded(self, client):
        """Test request failure after max retries."""
        mock_session = AsyncMock()
        mock_session.request.side_effect = ClientError("Connection failed")

        with patch.object(client, "_get_session", return_value=mock_session):
            with pytest.raises(PowerDNSConnectionError):
                await client._make_request("GET", "/test")
            assert mock_session.request.call_count == 3

    @pytest.mark.asyncio
    async def test_make_request_api_error(self, client):
        """Test handling of API errors."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.text.return_value = '{"error": "Bad request"}'
        mock_session.request.return_value.__aenter__.return_value = mock_response

        with patch.object(client, "_get_session", return_value=mock_session):
            with pytest.raises(PowerDNSAPIError) as exc_info:
                await client._make_request("POST", "/test")

            assert exc_info.value.status_code == 400
            assert exc_info.value.response_data == {"error": "Bad request"}

    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """Test async context manager functionality."""
        mock_session = AsyncMock()
        client._session = mock_session

        async with client as dns_client:
            assert dns_client is client

        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_record_a_type(self, client):
        """Test update_record for A type."""
        with patch.object(client, "create_a_record") as mock_create:
            await client.update_record("host1", "192.168.1.100", "A")
            mock_create.assert_called_once_with("host1", "192.168.1.100", None, None)

    @pytest.mark.asyncio
    async def test_update_record_aaaa_type(self, client):
        """Test update_record for AAAA type."""
        with patch.object(client, "create_aaaa_record") as mock_create:
            await client.update_record("host1", "2001:db8::1", "AAAA")
            mock_create.assert_called_once_with("host1", "2001:db8::1", None, None)

    @pytest.mark.asyncio
    async def test_update_record_invalid_type(self, client):
        """Test update_record with invalid record type."""
        with pytest.raises(ValueError, match="Unsupported record type"):
            await client.update_record("host1", "192.168.1.100", "MX")

    def test_create_dns_client(self, config):
        """Test factory function."""
        client = create_dns_client(config)
        assert isinstance(client, PowerDNSClient)
        assert client.enabled is True
