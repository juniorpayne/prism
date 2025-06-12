#!/usr/bin/env python3
"""
Integration tests for PowerDNS and Prism Server (SCRUM-51)
Tests the complete DNS workflow with a real PowerDNS instance.
"""

import asyncio
import os
import socket
import time
from typing import Dict, Optional

import dns.resolver
import pytest
import pytest_asyncio
from sqlalchemy import select

from server.config import Config
from server.connection_handler import ConnectionHandler
from server.database.connection import DatabaseManager
from server.database.models import Host
from server.database.operations import HostOperations
from server.dns_manager import PowerDNSClient, create_dns_client
from server.message_validator import MessageValidator
from server.registration_processor import RegistrationProcessor
from server.server_stats import ServerStats


@pytest.mark.integration
class TestDNSIntegration:
    """Integration tests for DNS operations."""

    @pytest.fixture
    def integration_config(self):
        """Create integration test configuration."""
        return {
            "server": {
                "host": "0.0.0.0",
                "tcp_port": 8080,
                "api_port": 8081,
            },
            "database": {
                "path": "/tmp/test_dns_integration.db",
                "connection_pool_size": 5,
            },
            "powerdns": {
                "enabled": True,
                "api_url": os.getenv("POWERDNS_API_URL", "http://localhost:8053/api/v1"),
                "api_key": os.getenv("POWERDNS_API_KEY", "test-api-key"),
                "default_zone": "test.prism.local.",
                "default_ttl": 60,
                "timeout": 10,
                "retry_attempts": 3,
            },
            "registration": {
                "enable_ip_tracking": True,
                "rate_limit_per_minute": 100,
            },
        }

    @pytest_asyncio.fixture
    async def db_manager(self, integration_config):
        """Create database manager for tests."""
        db = DatabaseManager(integration_config["database"])
        await db.initialize()
        yield db
        await db.close()
        # Cleanup
        if os.path.exists(integration_config["database"]["path"]):
            os.remove(integration_config["database"]["path"])

    @pytest_asyncio.fixture
    async def dns_client(self, integration_config):
        """Create PowerDNS client."""
        client = create_dns_client(integration_config)
        async with client:
            yield client

    @pytest_asyncio.fixture
    async def host_ops(self, db_manager):
        """Create host operations instance."""
        return HostOperations(db_manager)

    @pytest.mark.asyncio
    async def test_dns_zone_setup(self, dns_client):
        """Test that DNS zone can be created."""
        zone = "test.prism.local."
        
        # Check if zone exists
        exists = await dns_client.zone_exists(zone)
        
        if not exists:
            # Create zone
            result = await dns_client.create_zone(zone)
            assert result["status"] in ["created", "exists"]
        
        # Verify zone exists
        exists = await dns_client.zone_exists(zone)
        assert exists is True

    @pytest.mark.asyncio
    async def test_host_registration_creates_dns_record(self, integration_config, db_manager, dns_client, host_ops):
        """Test that host registration creates DNS record."""
        # Setup
        hostname = f"test-host-{int(time.time())}"
        ip_address = "10.0.1.100"
        
        # Register host
        registration_processor = RegistrationProcessor(integration_config, host_ops)
        result = await registration_processor.process_registration(hostname, ip_address)
        
        assert result["status"] == "new_registration"
        
        # Give DNS time to sync
        await asyncio.sleep(1)
        
        # Verify DNS record exists
        record = await dns_client.get_record(hostname, "A")
        assert record is not None
        assert record["records"][0]["content"] == ip_address
        
        # Verify database has DNS info
        async with db_manager.get_session() as session:
            stmt = select(Host).where(Host.hostname == hostname)
            result = await session.execute(stmt)
            host = result.scalar_one_or_none()
            
            assert host is not None
            assert host.dns_zone == integration_config["powerdns"]["default_zone"]
            assert host.dns_sync_status == "pending"  # Would be "synced" if handler ran

    @pytest.mark.asyncio
    async def test_ip_update_updates_dns_record(self, dns_client, host_ops):
        """Test that IP updates trigger DNS updates."""
        hostname = f"test-update-{int(time.time())}"
        initial_ip = "10.0.2.100"
        updated_ip = "10.0.2.200"
        
        # Create initial record
        await dns_client.create_a_record(hostname, initial_ip)
        
        # Create host in database
        host_ops.create_host(hostname, initial_ip)
        
        # Update IP
        success = host_ops.update_host_ip(hostname, updated_ip)
        assert success is True
        
        # Update DNS
        await dns_client.update_record(hostname, updated_ip, "A")
        
        # Verify DNS record updated
        await asyncio.sleep(1)
        record = await dns_client.get_record(hostname, "A")
        assert record is not None
        assert record["records"][0]["content"] == updated_ip

    @pytest.mark.asyncio
    async def test_host_deletion_removes_dns_record(self, dns_client, host_ops):
        """Test that host deletion removes DNS record."""
        hostname = f"test-delete-{int(time.time())}"
        ip_address = "10.0.3.100"
        
        # Create DNS record
        await dns_client.create_a_record(hostname, ip_address)
        
        # Verify it exists
        record = await dns_client.get_record(hostname, "A")
        assert record is not None
        
        # Delete record
        await dns_client.delete_record(hostname, "A")
        
        # Verify it's gone
        await asyncio.sleep(1)
        record = await dns_client.get_record(hostname, "A")
        assert record is None

    @pytest.mark.asyncio
    async def test_bulk_registration_performance(self, dns_client, host_ops):
        """Test performance of bulk host registrations."""
        num_hosts = 10
        base_hostname = f"bulk-test-{int(time.time())}"
        
        start_time = time.time()
        
        # Create multiple hosts concurrently
        tasks = []
        for i in range(num_hosts):
            hostname = f"{base_hostname}-{i}"
            ip = f"10.0.4.{i+1}"
            tasks.append(dns_client.create_a_record(hostname, ip))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Check results
        successful = sum(1 for r in results if not isinstance(r, Exception))
        assert successful == num_hosts
        
        # Performance assertion (should complete in reasonable time)
        assert duration < 10.0  # 10 seconds for 10 hosts
        
        print(f"Bulk registration: {num_hosts} hosts in {duration:.2f}s ({num_hosts/duration:.1f} hosts/sec)")

    @pytest.mark.asyncio
    async def test_dns_failover_handling(self, integration_config, host_ops):
        """Test handling when PowerDNS is unavailable."""
        # Create client with bad URL
        bad_config = integration_config.copy()
        bad_config["powerdns"]["api_url"] = "http://nonexistent:8053/api/v1"
        bad_config["powerdns"]["timeout"] = 1
        bad_config["powerdns"]["retry_attempts"] = 1
        
        bad_client = create_dns_client(bad_config)
        
        # Try to create record (should fail gracefully)
        hostname = f"failover-test-{int(time.time())}"
        
        try:
            result = await bad_client.create_a_record(hostname, "10.0.5.100")
            # If PowerDNS is disabled, this returns success
            assert result["status"] == "disabled"
        except Exception:
            # Expected when PowerDNS is unreachable
            pass
        
        await bad_client.close()

    @pytest.mark.asyncio
    async def test_ipv6_record_creation(self, dns_client):
        """Test IPv6 AAAA record creation."""
        hostname = f"ipv6-test-{int(time.time())}"
        ipv6_address = "2001:db8::1"
        
        # Create AAAA record
        result = await dns_client.create_aaaa_record(hostname, ipv6_address)
        assert result["status"] == "success"
        
        # Verify record exists
        await asyncio.sleep(1)
        record = await dns_client.get_record(hostname, "AAAA")
        assert record is not None
        assert record["records"][0]["content"] == ipv6_address

    @pytest.mark.asyncio
    async def test_concurrent_updates_same_host(self, dns_client):
        """Test concurrent updates to the same host."""
        hostname = f"concurrent-test-{int(time.time())}"
        
        # Create multiple concurrent updates
        tasks = []
        for i in range(5):
            ip = f"10.0.6.{i+1}"
            tasks.append(dns_client.create_a_record(hostname, ip))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed (last write wins)
        successful = sum(1 for r in results if not isinstance(r, Exception))
        assert successful == 5
        
        # Verify final state
        record = await dns_client.get_record(hostname, "A")
        assert record is not None
        # Should have one of the IPs (race condition determines which)
        assert record["records"][0]["content"].startswith("10.0.6.")

    @pytest.mark.asyncio
    async def test_special_characters_in_dns(self, dns_client):
        """Test handling of special characters in DNS names."""
        test_cases = [
            ("host-with-dash", True),
            ("host.with.dots", False),  # Dots are zone separators
            ("host_underscore", True),   # Underscores allowed in some configs
            ("123numeric", True),
            ("-startdash", False),       # Can't start with dash
            ("enddash-", False),         # Can't end with dash
        ]
        
        for hostname, should_succeed in test_cases:
            test_hostname = f"{hostname}-{int(time.time())}"
            
            try:
                result = await dns_client.create_a_record(test_hostname, "10.0.7.1")
                if should_succeed:
                    assert result["status"] == "success"
                else:
                    # Should have failed
                    pytest.fail(f"Expected {test_hostname} to fail but succeeded")
            except Exception as e:
                if should_succeed:
                    pytest.fail(f"Expected {test_hostname} to succeed but failed: {e}")

    @pytest.mark.asyncio
    async def test_ttl_configuration(self, dns_client):
        """Test TTL configuration for DNS records."""
        hostname = f"ttl-test-{int(time.time())}"
        custom_ttl = 120
        
        # Create record with custom TTL
        result = await dns_client.create_a_record(
            hostname, "10.0.8.1", ttl=custom_ttl
        )
        assert result["status"] == "success"
        
        # Verify TTL
        record = await dns_client.get_record(hostname, "A")
        assert record is not None
        assert record["ttl"] == custom_ttl

    @pytest.mark.asyncio
    async def test_zone_validation(self, dns_client):
        """Test zone validation and error handling."""
        hostname = f"zone-test-{int(time.time())}"
        
        # Try to create record in non-existent zone
        try:
            await dns_client.create_a_record(
                hostname, "10.0.9.1", zone="nonexistent.zone."
            )
            pytest.fail("Expected error for non-existent zone")
        except Exception as e:
            # Expected error
            assert "404" in str(e) or "Not Found" in str(e)

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("RUN_PERFORMANCE_TESTS"),
        reason="Performance tests disabled by default"
    )
    async def test_dns_query_performance(self, dns_client):
        """Test DNS query performance under load."""
        # Create test record
        hostname = f"perf-test-{int(time.time())}"
        await dns_client.create_a_record(hostname, "10.0.10.1")
        
        # Wait for propagation
        await asyncio.sleep(1)
        
        # Configure resolver
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [os.getenv("POWERDNS_IP", "localhost")]
        resolver.port = int(os.getenv("POWERDNS_PORT", "5353"))
        
        # Measure query performance
        query_times = []
        num_queries = 100
        
        for _ in range(num_queries):
            start = time.time()
            try:
                resolver.resolve(f"{hostname}.test.prism.local", "A")
                query_time = time.time() - start
                query_times.append(query_time)
            except Exception:
                pass  # Ignore failures for performance test
        
        if query_times:
            avg_time = sum(query_times) / len(query_times)
            max_time = max(query_times)
            min_time = min(query_times)
            
            print(f"\nDNS Query Performance:")
            print(f"  Queries: {len(query_times)}/{num_queries}")
            print(f"  Avg: {avg_time*1000:.2f}ms")
            print(f"  Min: {min_time*1000:.2f}ms")
            print(f"  Max: {max_time*1000:.2f}ms")
            
            # Performance assertions
            assert avg_time < 0.1  # Average under 100ms
            assert max_time < 0.5  # Max under 500ms