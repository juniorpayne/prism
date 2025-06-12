#!/usr/bin/env python3
"""Test script for PowerDNS setup."""

import os
import subprocess
import sys
import time

import requests

# Configuration
API_KEY = os.environ.get("PDNS_API_KEY", "changeme")
API_URL = "http://localhost:8053/api/v1"
TEST_ZONE = "test.prism.local."
TEST_HOSTNAME = "testhost"
TEST_IP = "192.168.1.100"


def check_containers():
    """Check if PowerDNS containers are running."""
    print("Checking containers...")
    result = subprocess.run(
        ["docker", "compose", "-f", "docker-compose.powerdns.yml", "ps"],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    return "powerdns-server" in result.stdout and "running" in result.stdout


def test_api_health():
    """Test PowerDNS API health."""
    print("\nTesting API health...")
    headers = {"X-API-Key": API_KEY}

    try:
        response = requests.get(f"{API_URL}/servers/localhost", headers=headers)
        if response.status_code == 200:
            print("✅ API is healthy")
            return True
        else:
            print(f"❌ API returned status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        return False


def create_test_zone():
    """Create a test zone."""
    print(f"\nCreating test zone: {TEST_ZONE}")
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

    zone_data = {
        "name": TEST_ZONE,
        "kind": "Native",
        "nameservers": [f"ns1.{TEST_ZONE}", f"ns2.{TEST_ZONE}"],
    }

    try:
        response = requests.post(
            f"{API_URL}/servers/localhost/zones", headers=headers, json=zone_data
        )
        if response.status_code in [201, 204]:
            print(f"✅ Zone {TEST_ZONE} created successfully")
            return True
        else:
            print(f"❌ Failed to create zone: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Zone creation failed: {e}")
        return False


def add_test_record():
    """Add a test A record."""
    print(f"\nAdding test record: {TEST_HOSTNAME}.{TEST_ZONE} -> {TEST_IP}")
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

    record_data = {
        "rrsets": [
            {
                "name": f"{TEST_HOSTNAME}.{TEST_ZONE}",
                "type": "A",
                "changetype": "REPLACE",
                "records": [{"content": TEST_IP, "disabled": False}],
            }
        ]
    }

    try:
        response = requests.patch(
            f"{API_URL}/servers/localhost/zones/{TEST_ZONE}", headers=headers, json=record_data
        )
        if response.status_code in [200, 204]:
            print(f"✅ Record created successfully")
            return True
        else:
            print(f"❌ Failed to create record: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Record creation failed: {e}")
        return False


def test_dns_resolution():
    """Test DNS resolution using dig."""
    print(f"\nTesting DNS resolution for {TEST_HOSTNAME}.{TEST_ZONE}")

    result = subprocess.run(
        ["dig", "@localhost", "-p", "53", f"{TEST_HOSTNAME}.{TEST_ZONE}", "+short"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0 and TEST_IP in result.stdout:
        print(f"✅ DNS resolution successful: {result.stdout.strip()}")
        return True
    else:
        print(f"❌ DNS resolution failed: {result.stderr}")
        return False


def main():
    """Run all tests."""
    print("PowerDNS Test Suite")
    print("==================")

    # Check if containers are running
    if not check_containers():
        print("\n⚠️  PowerDNS containers are not running!")
        print("Run: docker compose -f docker-compose.powerdns.yml up -d")
        sys.exit(1)

    # Wait a bit for services to be ready
    print("\nWaiting for services to be ready...")
    time.sleep(5)

    # Run tests
    tests = [test_api_health, create_test_zone, add_test_record, test_dns_resolution]

    results = []
    for test in tests:
        results.append(test())

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    passed = sum(results)
    total = len(results)
    print(f"✅ Passed: {passed}/{total}")

    if passed == total:
        print("\n🎉 All tests passed! PowerDNS is working correctly.")
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
