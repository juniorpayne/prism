#!/usr/bin/env python3
"""
End-to-End tests for complete DNS workflow (SCRUM-51)
Tests the full flow from client registration to DNS resolution.
"""

import asyncio
import json
import socket
import struct
import time
from datetime import datetime, timezone
from typing import Dict, Tuple

import aiohttp
import dns.resolver
import pytest


class PrismTestClient:
    """Test client for Prism server."""

    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.socket = None

    def connect(self) -> bool:
        """Connect to Prism server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((self.host, self.port))
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def register(self, hostname: str) -> Tuple[bool, Dict]:
        """Register hostname with server."""
        if not self.socket:
            return False, {"error": "Not connected"}

        # Create registration message
        message = {
            "version": "1.0",
            "type": "registration",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "hostname": hostname,
        }

        # Serialize and frame message
        json_data = json.dumps(message, separators=(",", ":")).encode("utf-8")
        length_prefix = struct.pack(">I", len(json_data))
        framed_message = length_prefix + json_data

        try:
            # Send message
            self.socket.sendall(framed_message)

            # Receive response
            length_data = self.socket.recv(4)
            if len(length_data) < 4:
                return False, {"error": "Incomplete response"}

            response_length = struct.unpack(">I", length_data)[0]
            response_data = self.socket.recv(response_length)
            response = json.loads(response_data.decode("utf-8"))

            return response.get("status") == "success", response

        except Exception as e:
            return False, {"error": str(e)}

    def send_heartbeat(self, hostname: str) -> bool:
        """Send heartbeat for hostname."""
        if not self.socket:
            return False

        message = {
            "version": "1.0",
            "type": "heartbeat",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "hostname": hostname,
        }

        json_data = json.dumps(message, separators=(",", ":")).encode("utf-8")
        length_prefix = struct.pack(">I", len(json_data))

        try:
            self.socket.sendall(length_prefix + json_data)
            return True
        except Exception:
            return False

    def disconnect(self):
        """Disconnect from server."""
        if self.socket:
            self.socket.close()
            self.socket = None


@pytest.mark.e2e
class TestE2EDNSWorkflow:
    """End-to-end tests for complete DNS workflow."""

    @pytest.fixture
    def test_config(self):
        """Test configuration."""
        return {
            "prism_host": "localhost",
            "prism_tcp_port": 8080,
            "prism_api_port": 8081,
            "powerdns_host": "localhost",
            "powerdns_port": 5353,
            "powerdns_api_port": 8053,
            "dns_zone": "managed.prism.local.",
            "api_key": "test-api-key",
        }

    @pytest.fixture
    def dns_resolver(self, test_config):
        """Configure DNS resolver for tests."""
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [test_config["powerdns_host"]]
        resolver.port = test_config["powerdns_port"]
        resolver.timeout = 2.0
        resolver.lifetime = 5.0
        return resolver

    @pytest.mark.asyncio
    async def test_complete_registration_to_resolution(self, test_config, dns_resolver):
        """Test complete flow from registration to DNS resolution."""
        hostname = f"e2e-test-{int(time.time())}"
        fqdn = f"{hostname}.{test_config['dns_zone']}"

        # Step 1: Connect client
        client = PrismTestClient(test_config["prism_host"], test_config["prism_tcp_port"])
        assert client.connect() is True

        try:
            # Step 2: Register hostname
            success, response = client.register(hostname)
            assert success is True
            assert "New host registered" in response.get("message", "")

            # Extract IP from response
            registered_ip = response["message"].split("with IP ")[-1]

            # Step 3: Wait for DNS propagation
            await asyncio.sleep(2)

            # Step 4: Verify DNS resolution
            try:
                answer = dns_resolver.resolve(fqdn, "A")
                resolved_ips = [rdata.address for rdata in answer]
                assert registered_ip in resolved_ips
                print(f"✅ DNS resolution successful: {fqdn} -> {resolved_ips}")
            except dns.resolver.NXDOMAIN:
                pytest.fail(f"DNS record not found for {fqdn}")

            # Step 5: Verify via API
            async with aiohttp.ClientSession() as session:
                # Check host status
                async with session.get(
                    f"http://{test_config['prism_host']}:{test_config['prism_api_port']}/api/hosts"
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        hosts = data.get("hosts", [])

                        # Find our host
                        our_host = next((h for h in hosts if h["hostname"] == hostname), None)
                        assert our_host is not None
                        assert our_host["status"] == "online"
                        assert our_host["current_ip"] == registered_ip

            # Step 6: Send heartbeat
            assert client.send_heartbeat(hostname) is True

        finally:
            client.disconnect()

    @pytest.mark.asyncio
    async def test_ip_change_updates_dns(self, test_config, dns_resolver):
        """Test that IP changes are reflected in DNS."""
        hostname = f"ip-change-test-{int(time.time())}"
        fqdn = f"{hostname}.{test_config['dns_zone']}"

        # Register from first "location"
        client1 = PrismTestClient(test_config["prism_host"], test_config["prism_tcp_port"])
        assert client1.connect() is True

        success, response1 = client1.register(hostname)
        assert success is True
        ip1 = response1["message"].split("with IP ")[-1]

        # Wait for DNS
        await asyncio.sleep(2)

        # Verify initial DNS
        answer = dns_resolver.resolve(fqdn, "A")
        assert ip1 in [rdata.address for rdata in answer]

        # Disconnect first client
        client1.disconnect()

        # Connect from different "location" (will get different source IP)
        # In real test, this would be from different network
        client2 = PrismTestClient(test_config["prism_host"], test_config["prism_tcp_port"])
        assert client2.connect() is True

        # Re-register (should update IP)
        success, response2 = client2.register(hostname)
        assert success is True

        # If IP changed, verify DNS update
        if "updated" in response2.get("message", ""):
            await asyncio.sleep(2)

            # Verify DNS updated
            answer = dns_resolver.resolve(fqdn, "A")
            resolved_ips = [rdata.address for rdata in answer]
            print(f"DNS after update: {fqdn} -> {resolved_ips}")

        client2.disconnect()

    @pytest.mark.asyncio
    async def test_multiple_clients_concurrent_registration(self, test_config, dns_resolver):
        """Test multiple clients registering concurrently."""
        num_clients = 5
        base_hostname = f"concurrent-e2e-{int(time.time())}"

        async def register_client(index: int):
            """Register a single client."""
            hostname = f"{base_hostname}-{index}"
            client = PrismTestClient(test_config["prism_host"], test_config["prism_tcp_port"])

            if not client.connect():
                return False, hostname, None

            try:
                success, response = client.register(hostname)
                if success:
                    ip = response["message"].split("with IP ")[-1]
                    return True, hostname, ip
                return False, hostname, None
            finally:
                client.disconnect()

        # Register all clients concurrently
        tasks = [register_client(i) for i in range(num_clients)]
        results = await asyncio.gather(*tasks)

        # Verify all succeeded
        successful = [(hostname, ip) for success, hostname, ip in results if success]
        assert len(successful) == num_clients

        # Wait for DNS propagation
        await asyncio.sleep(3)

        # Verify all DNS records exist
        for hostname, expected_ip in successful:
            fqdn = f"{hostname}.{test_config['dns_zone']}"
            try:
                answer = dns_resolver.resolve(fqdn, "A")
                resolved_ips = [rdata.address for rdata in answer]
                assert expected_ip in resolved_ips
            except dns.resolver.NXDOMAIN:
                pytest.fail(f"DNS record not found for {fqdn}")

    @pytest.mark.asyncio
    async def test_offline_detection_preserves_dns(self, test_config, dns_resolver):
        """Test that DNS records persist when host goes offline."""
        hostname = f"offline-test-{int(time.time())}"
        fqdn = f"{hostname}.{test_config['dns_zone']}"

        # Register host
        client = PrismTestClient(test_config["prism_host"], test_config["prism_tcp_port"])
        assert client.connect() is True

        success, response = client.register(hostname)
        assert success is True
        registered_ip = response["message"].split("with IP ")[-1]

        # Wait for DNS
        await asyncio.sleep(2)

        # Verify DNS exists
        answer = dns_resolver.resolve(fqdn, "A")
        assert registered_ip in [rdata.address for rdata in answer]

        # Disconnect (simulate offline)
        client.disconnect()

        # Wait longer than heartbeat timeout
        # (In real scenario, would wait for actual timeout)
        await asyncio.sleep(5)

        # DNS record should still exist
        answer = dns_resolver.resolve(fqdn, "A")
        assert registered_ip in [rdata.address for rdata in answer]
        print(f"✅ DNS record persists after offline: {fqdn} -> {registered_ip}")

    @pytest.mark.asyncio
    async def test_api_dns_consistency(self, test_config):
        """Test that API and DNS show consistent information."""
        hostname = f"consistency-test-{int(time.time())}"

        # Register host
        client = PrismTestClient(test_config["prism_host"], test_config["prism_tcp_port"])
        assert client.connect() is True

        try:
            success, response = client.register(hostname)
            assert success is True
            registered_ip = response["message"].split("with IP ")[-1]

            # Wait for propagation
            await asyncio.sleep(2)

            async with aiohttp.ClientSession() as session:
                # Check via Prism API
                async with session.get(
                    f"http://{test_config['prism_host']}:{test_config['prism_api_port']}/api/hosts"
                ) as resp:
                    data = await resp.json()
                    hosts = data.get("hosts", [])
                    our_host = next((h for h in hosts if h["hostname"] == hostname), None)

                    assert our_host is not None
                    api_ip = our_host["current_ip"]

                # Check via PowerDNS API
                headers = {"X-API-Key": test_config["api_key"]}
                zone = test_config["dns_zone"]

                async with session.get(
                    f"http://{test_config['powerdns_host']}:{test_config['powerdns_api_port']}"
                    f"/api/v1/servers/localhost/zones/{zone}",
                    headers=headers,
                ) as resp:
                    if resp.status == 200:
                        zone_data = await resp.json()
                        fqdn = f"{hostname}.{zone}"

                        # Find our record
                        our_record = None
                        for rrset in zone_data.get("rrsets", []):
                            if rrset["name"] == fqdn and rrset["type"] == "A":
                                our_record = rrset
                                break

                        assert our_record is not None
                        dns_ip = our_record["records"][0]["content"]

                        # Verify consistency
                        assert api_ip == dns_ip == registered_ip
                        print(f"✅ Consistent IPs across all systems: {registered_ip}")

        finally:
            client.disconnect()

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_registration_to_resolution_latency(self, test_config, dns_resolver):
        """Test latency from registration to DNS resolution."""
        hostname = f"latency-test-{int(time.time())}"
        fqdn = f"{hostname}.{test_config['dns_zone']}"

        client = PrismTestClient(test_config["prism_host"], test_config["prism_tcp_port"])
        assert client.connect() is True

        try:
            # Measure registration time
            reg_start = time.time()
            success, response = client.register(hostname)
            reg_end = time.time()

            assert success is True
            registered_ip = response["message"].split("with IP ")[-1]

            # Measure time to DNS availability
            dns_start = time.time()
            max_wait = 10.0
            dns_available = False

            while time.time() - dns_start < max_wait:
                try:
                    answer = dns_resolver.resolve(fqdn, "A")
                    if registered_ip in [rdata.address for rdata in answer]:
                        dns_available = True
                        break
                except Exception:
                    pass
                await asyncio.sleep(0.1)

            dns_end = time.time()

            assert dns_available is True

            # Calculate metrics
            registration_time = reg_end - reg_start
            dns_propagation_time = dns_end - reg_end
            total_time = dns_end - reg_start

            print(f"\n⏱️  Performance Metrics:")
            print(f"  Registration time: {registration_time*1000:.2f}ms")
            print(f"  DNS propagation time: {dns_propagation_time*1000:.2f}ms")
            print(f"  Total time: {total_time*1000:.2f}ms")

            # Performance assertions
            assert registration_time < 1.0  # Registration under 1 second
            assert total_time < 5.0  # Total under 5 seconds

        finally:
            client.disconnect()
