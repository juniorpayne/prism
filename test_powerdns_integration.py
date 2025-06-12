#!/usr/bin/env python3
"""
Quick test script for PowerDNS integration
Run this after starting the development environment with PowerDNS
"""

import asyncio
import json
import sys
import time

import aiohttp


async def test_powerdns_api(api_key="test-api-key"):
    """Test PowerDNS API connectivity"""
    print("\n1. Testing PowerDNS API connectivity...")

    async with aiohttp.ClientSession() as session:
        headers = {"X-API-Key": api_key}

        try:
            # Test API endpoint
            async with session.get(
                "http://localhost:8053/api/v1/servers/localhost", headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(
                        f"✅ PowerDNS API is accessible: {data.get('type', 'Unknown')} {data.get('version', 'Unknown')}"
                    )
                else:
                    print(f"❌ PowerDNS API error: {resp.status}")
                    return False

            # Check zones
            async with session.get(
                "http://localhost:8053/api/v1/servers/localhost/zones", headers=headers
            ) as resp:
                if resp.status == 200:
                    zones = await resp.json()
                    print(f"✅ Found {len(zones)} zones")
                    for zone in zones:
                        print(f"   - {zone['name']}")
                    return True
        except Exception as e:
            print(f"❌ Failed to connect to PowerDNS API: {e}")
            return False


async def create_test_zone(api_key="test-api-key", zone_name="managed.prism.local."):
    """Create test zone if it doesn't exist"""
    print(f"\n2. Ensuring zone {zone_name} exists...")

    async with aiohttp.ClientSession() as session:
        headers = {"X-API-Key": api_key, "Content-Type": "application/json"}

        # Check if zone exists
        async with session.get(
            f"http://localhost:8053/api/v1/servers/localhost/zones/{zone_name}", headers=headers
        ) as resp:
            if resp.status == 200:
                print(f"✅ Zone {zone_name} already exists")
                return True

        # Create zone
        zone_data = {
            "name": zone_name,
            "kind": "Native",
            "rrsets": [
                {
                    "name": zone_name,
                    "type": "SOA",
                    "ttl": 3600,
                    "records": [
                        {
                            "content": f"ns1.{zone_name} admin.{zone_name} 1 10800 3600 604800 3600",
                            "disabled": False,
                        }
                    ],
                },
                {
                    "name": zone_name,
                    "type": "NS",
                    "ttl": 3600,
                    "records": [{"content": f"ns1.{zone_name}", "disabled": False}],
                },
            ],
        }

        try:
            async with session.post(
                "http://localhost:8053/api/v1/servers/localhost/zones",
                headers=headers,
                json=zone_data,
            ) as resp:
                if resp.status in (201, 204):
                    print(f"✅ Created zone {zone_name}")
                    return True
                else:
                    error = await resp.text()
                    print(f"❌ Failed to create zone: {error}")
                    return False
        except Exception as e:
            print(f"❌ Error creating zone: {e}")
            return False


async def test_host_registration(hostname="testhost-integration", ip="192.168.100.50"):
    """Test registering a host via Prism API"""
    print(f"\n3. Testing host registration for {hostname}...")

    async with aiohttp.ClientSession() as session:
        # Register host
        host_data = {"hostname": hostname, "ip_address": ip}

        try:
            async with session.post("http://localhost:8081/api/hosts", json=host_data) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Host registered successfully")
                    return True
                else:
                    error = await resp.text()
                    print(f"❌ Failed to register host: {error}")
                    return False
        except Exception as e:
            print(f"❌ Error registering host: {e}")
            return False


async def check_dns_record(
    hostname="testhost-integration", zone="managed.prism.local.", api_key="test-api-key"
):
    """Check if DNS record was created"""
    print(f"\n4. Checking DNS record for {hostname}.{zone}...")

    await asyncio.sleep(1)  # Give it a moment to sync

    async with aiohttp.ClientSession() as session:
        headers = {"X-API-Key": api_key}

        try:
            async with session.get(
                f"http://localhost:8053/api/v1/servers/localhost/zones/{zone}", headers=headers
            ) as resp:
                if resp.status == 200:
                    zone_data = await resp.json()
                    fqdn = f"{hostname}.{zone}"

                    # Look for the record
                    for rrset in zone_data.get("rrsets", []):
                        if rrset["name"].lower() == fqdn.lower():
                            print(
                                f"✅ DNS record found: {rrset['name']} -> {rrset['records'][0]['content']}"
                            )
                            return True

                    print(f"❌ DNS record not found for {fqdn}")
                    return False
        except Exception as e:
            print(f"❌ Error checking DNS record: {e}")
            return False


async def check_metrics():
    """Check Prometheus metrics"""
    print("\n5. Checking metrics...")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:8081/metrics") as resp:
                if resp.status == 200:
                    metrics = await resp.text()

                    # Look for DNS-related metrics
                    dns_metrics = []
                    for line in metrics.split("\n"):
                        if "powerdns" in line or "dns_sync" in line:
                            if not line.startswith("#"):
                                dns_metrics.append(line)

                    if dns_metrics:
                        print("✅ Found DNS metrics:")
                        for metric in dns_metrics[:10]:  # Show first 10
                            print(f"   {metric}")
                    else:
                        print("❌ No DNS metrics found")
                    return True
        except Exception as e:
            print(f"❌ Error checking metrics: {e}")
            return False


async def check_database():
    """Check database for DNS sync status"""
    print("\n6. Checking database DNS sync status...")

    import sqlite3

    try:
        conn = sqlite3.connect("data/prism.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT hostname, current_ip, dns_sync_status, dns_zone, dns_record_id 
            FROM hosts 
            ORDER BY created_at DESC 
            LIMIT 5
        """
        )

        rows = cursor.fetchall()
        if rows:
            print("✅ Recent hosts with DNS status:")
            print(f"{'Hostname':<20} {'IP':<15} {'Sync Status':<12} {'Zone':<25} {'Record ID':<30}")
            print("-" * 100)
            for row in rows:
                print(
                    f"{row[0]:<20} {row[1]:<15} {row[2] or 'N/A':<12} {row[3] or 'N/A':<25} {row[4] or 'N/A':<30}"
                )
        else:
            print("❌ No hosts found in database")

        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return False


async def main():
    """Run all tests"""
    print("🧪 PowerDNS Integration Test Suite")
    print("=" * 50)

    results = []

    # Test PowerDNS API
    results.append(await test_powerdns_api())

    if results[-1]:
        # Create zone if needed
        results.append(await create_test_zone())

        if results[-1]:
            # Test host registration
            results.append(await test_host_registration())

            if results[-1]:
                # Check DNS record
                results.append(await check_dns_record())

    # Always check these
    results.append(await check_metrics())
    results.append(await check_database())

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    passed = sum(1 for r in results if r)
    total = len(results)

    if passed == total:
        print(f"✅ All tests passed! ({passed}/{total})")
    else:
        print(f"❌ Some tests failed: {passed}/{total} passed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
