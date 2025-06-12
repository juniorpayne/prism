#!/usr/bin/env python3
"""
Direct test of PowerDNS integration through TCP registration
"""

import asyncio
import json
import socket
import time

import aiohttp


def register_host_tcp(hostname, port=8080):
    """Register a host via TCP connection"""
    print(f"\nRegistering {hostname} via TCP...")

    # Connect to TCP server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(("localhost", port))
        local_ip = sock.getsockname()[0]
        print(f"Connected from {local_ip}")

        # Send registration
        message = f"REGISTER:{hostname}\n"
        sock.sendall(message.encode())

        # Receive response
        response = sock.recv(1024).decode().strip()
        print(f"Registration response: {response}")

        if response.startswith("REGISTERED"):
            print(f"✅ Successfully registered {hostname}")
            return True, sock
        else:
            print(f"❌ Registration failed: {response}")
            return False, None
    except Exception as e:
        print(f"❌ TCP connection error: {e}")
        return False, None


async def check_dns_record(
    hostname="testhost-tcp", zone="managed.prism.local.", api_key="test-api-key"
):
    """Check if DNS record was created"""
    print(f"\nChecking DNS record for {hostname}.{zone}...")

    await asyncio.sleep(2)  # Give it time to sync

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


async def check_database():
    """Check database for DNS sync status"""
    print("\nChecking database DNS sync status...")

    import sqlite3

    try:
        conn = sqlite3.connect("data/hosts.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT hostname, current_ip, dns_sync_status, dns_zone, dns_record_id 
            FROM hosts 
            WHERE hostname LIKE 'testhost-%'
            ORDER BY created_at DESC 
            LIMIT 5
        """
        )

        rows = cursor.fetchall()
        if rows:
            print("✅ Recent test hosts with DNS status:")
            print(f"{'Hostname':<20} {'IP':<15} {'Sync Status':<12} {'Zone':<25} {'Record ID':<30}")
            print("-" * 100)
            for row in rows:
                print(
                    f"{row[0]:<20} {row[1]:<15} {row[2] or 'N/A':<12} {row[3] or 'N/A':<25} {row[4] or 'N/A':<30}"
                )
        else:
            print("❌ No test hosts found in database")

        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return False


async def main():
    """Run the test"""
    print("🧪 PowerDNS Integration Test (TCP Registration)")
    print("=" * 50)

    # Test 1: Register via TCP
    success, sock = register_host_tcp("testhost-tcp-1")

    if success:
        # Test 2: Check DNS record
        dns_ok = await check_dns_record("testhost-tcp-1")

        # Test 3: Check database
        db_ok = await check_database()

        # Keep connection alive briefly
        await asyncio.sleep(2)

        # Close connection
        sock.close()
        print("\nClosed TCP connection")

        # Summary
        print("\n" + "=" * 50)
        if dns_ok and db_ok:
            print("✅ PowerDNS integration working correctly!")
        else:
            print("❌ PowerDNS integration has issues")
    else:
        print("❌ TCP registration failed")


if __name__ == "__main__":
    asyncio.run(main())
