#!/usr/bin/env python3
"""
Extended unit tests for PowerDNS API Client (SCRUM-51)
Additional test coverage for edge cases and error scenarios.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, call

import aiohttp
import pytest
from aiohttp import ClientError, ClientTimeout

from server.dns_manager import (
    PowerDNSAPIError,
    PowerDNSClient,
    PowerDNSConnectionError,
    PowerDNSError,
)


class TestPowerDNSClientExtended:
    """Extended tests for PowerDNS client edge cases."""

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
            }
        }

    @pytest.fixture
    def client(self, config):
        """Create PowerDNS client instance."""
        return PowerDNSClient(config)

    @pytest.mark.asyncio
    async def test_url_trailing_slash_handling(self):
        """Test that base URL trailing slash is handled correctly."""
        # Without trailing slash
        config1 = {
            "powerdns": {
                "enabled": True,
                "api_url": "http://localhost:8053/api/v1",
            }
        }
        client1 = PowerDNSClient(config1)
        assert client1.base_url.endswith("/")
        
        # With trailing slash
        config2 = {
            "powerdns": {
                "enabled": True,
                "api_url": "http://localhost:8053/api/v1/",
            }
        }
        client2 = PowerDNSClient(config2)
        assert client2.base_url.endswith("/")
        assert client2.base_url.count("/") == config2["powerdns"]["api_url"].count("/")

    @pytest.mark.asyncio
    async def test_special_characters_in_hostname(self, client):
        """Test handling of special characters in hostname."""
        special_hostnames = [
            "host-with-dash",
            "host_with_underscore",
            "123-numeric-start",
            "very-long-hostname-that-exceeds-normal-length-limits-but-should-still-work",
        ]
        
        for hostname in special_hostnames:
            with patch.object(client, "_make_request", return_value={}):
                result = await client.create_a_record(hostname, "192.168.1.100")
                assert result["status"] == "success"
                assert result["fqdn"] == f"{hostname}.test.local."

    @pytest.mark.asyncio
    async def test_ipv6_address_validation(self, client):
        """Test various IPv6 address formats."""
        valid_ipv6_addresses = [
            "2001:db8::1",
            "2001:0db8:0000:0000:0000:0000:0000:0001",
            "::1",
            "fe80::1",
            "2001:db8:85a3::8a2e:370:7334",
        ]
        
        for ipv6 in valid_ipv6_addresses:
            with patch.object(client, "_make_request", return_value={}):
                result = await client.create_aaaa_record("host1", ipv6)
                assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client):
        """Test handling of concurrent API requests."""
        mock_response = {}
        
        with patch.object(client, "_make_request", return_value=mock_response) as mock_request:
            # Create multiple concurrent requests
            tasks = [
                client.create_a_record(f"host{i}", f"192.168.1.{i}")
                for i in range(10)
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 10
            assert all(r["status"] == "success" for r in results)
            assert mock_request.call_count == 10

    @pytest.mark.asyncio
    async def test_timeout_handling(self, client):
        """Test request timeout handling."""
        mock_session = AsyncMock()
        mock_session.request.side_effect = ClientTimeout("Request timeout")
        
        with patch.object(client, "_get_session", return_value=mock_session):
            with pytest.raises(PowerDNSConnectionError) as exc_info:
                await client._make_request("GET", "/test")
            
            assert "Failed to connect" in str(exc_info.value)
            # Should retry 3 times
            assert mock_session.request.call_count == 3

    @pytest.mark.asyncio
    async def test_session_reuse(self, client):
        """Test that session is reused across requests."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "{}"
        mock_session.request.return_value.__aenter__.return_value = mock_response
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            # First request creates session
            await client._make_request("GET", "/test1")
            session1 = client._session
            
            # Second request reuses session
            await client._make_request("GET", "/test2")
            session2 = client._session
            
            assert session1 is session2
            assert session1 is mock_session

    @pytest.mark.asyncio
    async def test_zone_trailing_dot_normalization(self, client):
        """Test zone name normalization with trailing dots."""
        test_cases = [
            ("zone.com", "zone.com."),
            ("zone.com.", "zone.com."),
            ("sub.zone.com", "sub.zone.com."),
            ("sub.zone.com.", "sub.zone.com."),
        ]
        
        for input_zone, expected_zone in test_cases:
            with patch.object(client, "_make_request", return_value={}):
                result = await client.create_a_record("host", "192.168.1.1", zone=input_zone)
                assert result["zone"] == expected_zone

    @pytest.mark.asyncio
    async def test_fqdn_handling(self, client):
        """Test handling of fully qualified domain names."""
        # Test with FQDN as hostname
        with patch.object(client, "_make_request", return_value={}) as mock_request:
            await client.create_a_record("host.example.com.", "192.168.1.100")
            
            rrsets = mock_request.call_args[1]["json_data"]["rrsets"]
            # Should use FQDN as-is, not append zone
            assert rrsets[0]["name"] == "host.example.com."

    @pytest.mark.asyncio
    async def test_error_response_parsing(self, client):
        """Test parsing of various error response formats."""
        error_responses = [
            ('{"error": "Not found"}', {"error": "Not found"}),
            ('{"message": "Invalid request"}', {"message": "Invalid request"}),
            ("Plain text error", {"error": "Plain text error"}),
            ("", {}),
            ("null", {}),
        ]
        
        mock_session = AsyncMock()
        
        for response_text, expected_data in error_responses:
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_response.text.return_value = response_text
            mock_session.request.return_value.__aenter__.return_value = mock_response
            
            with patch.object(client, "_get_session", return_value=mock_session):
                with pytest.raises(PowerDNSAPIError) as exc_info:
                    await client._make_request("GET", "/test")
                
                assert exc_info.value.response_data == expected_data

    @pytest.mark.asyncio
    async def test_api_key_header(self, client):
        """Test that API key is correctly included in headers."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "{}"
        mock_session.request.return_value.__aenter__.return_value = mock_response
        
        with patch.object(client, "_get_session", return_value=mock_session):
            await client._make_request("GET", "/test")
            
            # Check headers in session creation
            assert client._headers["X-API-Key"] == "test-api-key"

    @pytest.mark.asyncio
    async def test_batch_operations(self, client):
        """Test batch record operations."""
        hosts = [
            ("host1", "192.168.1.1"),
            ("host2", "192.168.1.2"),
            ("host3", "192.168.1.3"),
        ]
        
        with patch.object(client, "_make_request", return_value={}) as mock_request:
            # Simulate batch operation
            for hostname, ip in hosts:
                await client.create_a_record(hostname, ip)
            
            assert mock_request.call_count == len(hosts)

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, client):
        """Test that metrics are properly recorded."""
        with patch("server.dns_manager.get_metrics_collector") as mock_metrics:
            mock_collector = MagicMock()
            mock_metrics.return_value = mock_collector
            
            # Successful operation
            with patch.object(client, "_make_request", return_value={}):
                await client.create_a_record("host1", "192.168.1.100")
                mock_collector.record_powerdns_record_operation.assert_called_with(
                    "create", "A", "success"
                )
            
            # Failed operation
            with patch.object(client, "_make_request", side_effect=Exception("Test error")):
                with pytest.raises(Exception):
                    await client.create_a_record("host2", "192.168.1.101")
                mock_collector.record_powerdns_record_operation.assert_called_with(
                    "create", "A", "failed"
                )

    @pytest.mark.asyncio
    async def test_empty_zone_handling(self, client):
        """Test handling of empty zone parameter."""
        with patch.object(client, "_make_request", return_value={}):
            # Empty string should use default zone
            result = await client.create_a_record("host1", "192.168.1.100", zone="")
            assert result["zone"] == client.default_zone
            
            # None should use default zone
            result = await client.create_a_record("host2", "192.168.1.101", zone=None)
            assert result["zone"] == client.default_zone

    @pytest.mark.asyncio
    async def test_record_update_idempotency(self, client):
        """Test that record updates are idempotent."""
        with patch.object(client, "_make_request", return_value={}) as mock_request:
            # Update same record multiple times
            for _ in range(3):
                await client.create_a_record("host1", "192.168.1.100")
            
            # All calls should use REPLACE changetype
            for call in mock_request.call_args_list:
                rrsets = call[1]["json_data"]["rrsets"]
                assert rrsets[0]["changetype"] == "REPLACE"

    @pytest.mark.asyncio
    async def test_connection_pool_cleanup(self, client):
        """Test proper cleanup of connection pool."""
        mock_session = AsyncMock()
        client._session = mock_session
        
        await client.close()
        
        mock_session.close.assert_called_once()
        assert client._session is None

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self, client):
        """Test retry logic with exponential backoff."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "{}"
        
        # Fail twice, succeed on third
        mock_session.request.side_effect = [
            ClientError("Failed"),
            ClientError("Failed"),
            mock_response,
        ]
        
        with patch.object(client, "_get_session", return_value=mock_session):
            with patch("asyncio.sleep") as mock_sleep:
                await client._make_request("GET", "/test")
                
                # Check exponential backoff delays
                expected_delays = [
                    client.retry_delay,
                    client.retry_delay * 2,
                ]
                actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
                assert actual_delays == expected_delays

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, client):
        """Test handling of invalid JSON responses."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "Invalid JSON {"
        mock_session.request.return_value.__aenter__.return_value = mock_response
        
        with patch.object(client, "_get_session", return_value=mock_session):
            with pytest.raises(PowerDNSError):
                await client._make_request("GET", "/test")