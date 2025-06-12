#!/usr/bin/env python3
"""
Test PowerDNS integration using the correct TCP protocol
"""

import asyncio
import socket
import json
import struct
import time
import aiohttp
from datetime import datetime, timezone


def send_registration(hostname, port=8080):
    """Register a host using the correct protocol"""
    print(f"\nRegistering {hostname} via TCP...")
    
    # Create registration message
    message = {
        "version": "1.0",
        "type": "registration",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "hostname": hostname
    }
    
    # Serialize to JSON
    json_data = json.dumps(message, separators=(",", ":")).encode("utf-8")
    
    # Add length prefix (4 bytes, big-endian)
    length = len(json_data)
    length_prefix = struct.pack(">I", length)
    framed_message = length_prefix + json_data
    
    # Connect and send
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(('localhost', port))
        sock.settimeout(5.0)
        
        print(f"Sending registration message: {message}")
        sock.sendall(framed_message)
        
        # Receive response with length prefix
        # First read 4 bytes for length
        length_data = sock.recv(4)
        if len(length_data) < 4:
            print("❌ Incomplete response length")
            return False, None
            
        response_length = struct.unpack(">I", length_data)[0]
        print(f"Expecting response of {response_length} bytes")
        
        # Read the actual response
        response_data = b""
        while len(response_data) < response_length:
            chunk = sock.recv(response_length - len(response_data))
            if not chunk:
                break
            response_data += chunk
        
        # Parse response
        response = json.loads(response_data.decode("utf-8"))
        print(f"Response: {response}")
        
        if response.get("status") == "success":
            print(f"✅ Successfully registered {hostname}")
            return True, sock
        else:
            print(f"❌ Registration failed: {response.get('message', 'Unknown error')}")
            sock.close()
            return False, None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sock.close()
        return False, None


async def check_dns_record(hostname, zone="managed.prism.local.", api_key="test-api-key"):
    """Check if DNS record was created"""
    print(f"\nChecking DNS record for {hostname}.{zone}...")
    
    await asyncio.sleep(2)  # Give it time to sync
    
    async with aiohttp.ClientSession() as session:
        headers = {"X-API-Key": api_key}
        
        try:
            # Check the zone exists
            async with session.get(
                f"http://localhost:8053/api/v1/servers/localhost/zones/{zone}",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    zone_data = await resp.json()
                    fqdn = f"{hostname}.{zone}"
                    
                    # Look for the record
                    for rrset in zone_data.get("rrsets", []):
                        if rrset["name"].lower() == fqdn.lower() and rrset["type"] == "A":
                            print(f"✅ DNS A record found: {rrset['name']} -> {rrset['records'][0]['content']}")
                            return True
                    
                    print(f"❌ DNS record not found for {fqdn}")
                    # Show what records exist
                    a_records = [r for r in zone_data.get("rrsets", []) if r["type"] == "A"]
                    if a_records:
                        print("Existing A records:")
                        for r in a_records[:5]:
                            print(f"  - {r['name']}")
                elif resp.status == 404:
                    print(f"❌ Zone {zone} not found")
                else:
                    print(f"❌ API error: {resp.status}")
                    
        except Exception as e:
            print(f"❌ Error checking DNS: {e}")
            
    return False


async def check_database():
    """Check database for DNS sync status"""
    print("\nChecking database DNS sync status...")
    
    import sqlite3
    try:
        conn = sqlite3.connect('data/hosts.db')
        cursor = conn.cursor()
        
        # Check if DNS columns exist
        cursor.execute("PRAGMA table_info(hosts)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'dns_sync_status' not in columns:
            print("⚠️  DNS columns not present in database (migration may be pending)")
        else:
            cursor.execute("""
                SELECT hostname, current_ip, dns_sync_status, dns_zone, dns_last_sync
                FROM hosts 
                WHERE hostname LIKE 'test-%'
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            
            rows = cursor.fetchall()
            if rows:
                print("✅ Recent test hosts:")
                print(f"{'Hostname':<20} {'IP':<15} {'DNS Status':<12} {'Zone':<30}")
                print("-" * 80)
                for row in rows:
                    print(f"{row[0]:<20} {row[1]:<15} {row[2] or 'N/A':<12} {row[3] or 'N/A':<30}")
            else:
                print("No test hosts found yet")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False


async def check_metrics():
    """Check Prometheus metrics for DNS operations"""
    print("\nChecking metrics...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:8081/metrics") as resp:
                if resp.status == 200:
                    metrics = await resp.text()
                    
                    # Look for DNS-related metrics
                    dns_lines = []
                    for line in metrics.split('\n'):
                        if any(term in line for term in ['powerdns', 'dns_sync', 'dns_record']):
                            if not line.startswith('#'):
                                dns_lines.append(line)
                    
                    if dns_lines:
                        print("✅ DNS metrics found:")
                        for line in dns_lines[:10]:
                            print(f"  {line}")
                    else:
                        print("⚠️  No DNS metrics found (may not be implemented yet)")
                        
        except Exception as e:
            print(f"❌ Metrics error: {e}")


async def main():
    """Run the complete test"""
    print("🧪 PowerDNS Integration Test")
    print("=" * 50)
    
    # Test 1: Register host
    success, sock = send_registration("test-powerdns-host")
    
    if success:
        try:
            # Test 2: Check DNS record
            dns_ok = await check_dns_record("test-powerdns-host")
            
            # Test 3: Check database
            db_ok = await check_database()
            
            # Test 4: Check metrics
            await check_metrics()
            
            # Send heartbeat to keep connection alive
            print("\nSending heartbeat...")
            heartbeat = {
                "version": "1.0",
                "type": "heartbeat",
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "hostname": "test-powerdns-host"
            }
            json_data = json.dumps(heartbeat).encode("utf-8")
            length_prefix = struct.pack(">I", len(json_data))
            sock.sendall(length_prefix + json_data)
            
            await asyncio.sleep(1)
            
        finally:
            sock.close()
            print("\nConnection closed")
            
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Results:")
        print(f"  Registration: ✅")
        print(f"  DNS Record: {'✅' if dns_ok else '❌'}")
        print(f"  Database: {'✅' if db_ok else '⚠️ Check manually'}")
        
        if dns_ok:
            print("\n✅ PowerDNS integration is working!")
        else:
            print("\n⚠️  DNS record creation needs investigation")
    else:
        print("\n❌ Registration failed - cannot continue tests")


if __name__ == "__main__":
    asyncio.run(main())