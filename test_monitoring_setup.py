#!/usr/bin/env python3
"""
Test script to verify PowerDNS monitoring setup
"""

import asyncio
import sys

import aiohttp


async def check_endpoint(session, name, url, expected_content=None):
    """Check if an endpoint is accessible."""
    try:
        async with session.get(url, timeout=5) as resp:
            if resp.status == 200:
                content = await resp.text()
                if expected_content and expected_content not in content:
                    print(f"❌ {name}: Unexpected content")
                    return False
                print(f"✅ {name}: OK (status {resp.status})")
                return True
            else:
                print(f"❌ {name}: Failed (status {resp.status})")
                return False
    except Exception as e:
        print(f"❌ {name}: Error - {e}")
        return False


async def main():
    """Run monitoring setup verification."""
    print("🔍 PowerDNS Monitoring Setup Verification")
    print("=" * 50)

    results = []

    async with aiohttp.ClientSession() as session:
        # Check PowerDNS API (would need to be running)
        print("\n📌 Checking PowerDNS API...")
        results.append(
            await check_endpoint(
                session, "PowerDNS API", "http://localhost:8053/api/v1/servers", "localhost"
            )
        )

        # Check monitoring endpoints (if deployed)
        print("\n📌 Checking Monitoring Endpoints...")

        # PowerDNS Exporter
        results.append(
            await check_endpoint(
                session, "PowerDNS Exporter", "http://localhost:9120/metrics", "powerdns_"
            )
        )

        # DNS Monitor
        results.append(
            await check_endpoint(
                session, "DNS Monitor", "http://localhost:9121/metrics", "dns_monitor_"
            )
        )

        # Prometheus
        results.append(
            await check_endpoint(session, "Prometheus", "http://localhost:9090/-/healthy", None)
        )

        # Grafana
        results.append(
            await check_endpoint(session, "Grafana", "http://localhost:3000/api/health", None)
        )

    # Summary
    print("\n" + "=" * 50)
    print("📊 Summary:")
    success = sum(1 for r in results if r)
    total = len(results)

    if success == total:
        print(f"✅ All monitoring components accessible ({success}/{total})")
        return 0
    else:
        print(f"⚠️  Some components not accessible ({success}/{total})")
        print("\nNote: This is expected if monitoring stack is not deployed.")
        print("Deploy with: docker compose -f docker-compose.monitoring-powerdns.yml up -d")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
