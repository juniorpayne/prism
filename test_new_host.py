#!/usr/bin/env python3
"""
Test PowerDNS integration with a completely new host
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
    print(f"\n🔷 Registering new host: {hostname}")
    
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
        
        sock.sendall(framed_message)
        
        # Receive response with length prefix
        length_data = sock.recv(4)
        if len(length_data) < 4:
            print("❌ Incomplete response")
            return False
            
        response_length = struct.unpack(">I", length_data)[0]
        
        # Read the actual response
        response_data = b""
        while len(response_data) < response_length:
            chunk = sock.recv(response_length - len(response_data))
            if not chunk:
                break
            response_data += chunk
        
        # Parse response
        response = json.loads(response_data.decode("utf-8"))
        
        if response.get("status") == "success":
            print(f"✅ Registration successful: {response.get('message')}")
            # Close connection immediately after registration
            sock.close()
            return True
        else:
            print(f"❌ Registration failed: {response.get('message', 'Unknown error')}")
            sock.close()
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sock.close()
        return False


async def check_dns_record(hostname, zone="managed.prism.local.", api_key="test-api-key"):
    """Check if DNS record was created"""
    print(f"\n🔍 Checking DNS record for {hostname}.{zone}")
    
    await asyncio.sleep(2)  # Give it time to sync
    
    async with aiohttp.ClientSession() as session:
        headers = {"X-API-Key": api_key}
        
        try:
            # Get zone data
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
                            print(f"✅ DNS A record found!")
                            print(f"   Name: {rrset['name']}")
                            print(f"   Type: {rrset['type']}")
                            print(f"   TTL: {rrset['ttl']}")
                            print(f"   IP: {rrset['records'][0]['content']}")
                            return True
                    
                    print(f"❌ DNS record not found")
                    # List all A records
                    a_records = [r for r in zone_data.get("rrsets", []) if r["type"] == "A"]
                    if a_records:
                        print(f"\nExisting A records in zone:")
                        for r in a_records:
                            print(f"  - {r['name']} -> {r['records'][0]['content'] if r['records'] else 'no content'}")
                    
        except Exception as e:
            print(f"❌ Error checking DNS: {e}")
            
    return False


async def check_database(hostname):
    """Check database for specific host"""
    print(f"\n📊 Checking database for {hostname}")
    
    import sqlite3
    try:
        conn = sqlite3.connect('data/hosts.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT hostname, current_ip, dns_sync_status, dns_zone, dns_record_id, dns_last_sync
            FROM hosts 
            WHERE hostname = ?
        """, (hostname,))
        
        row = cursor.fetchone()
        if row:
            print(f"✅ Host found in database:")
            print(f"   Hostname: {row[0]}")
            print(f"   IP: {row[1]}")
            print(f"   DNS Status: {row[2] or 'null'}")
            print(f"   DNS Zone: {row[3] or 'null'}")
            print(f"   DNS Record ID: {row[4] or 'null'}")
            print(f"   Last Sync: {row[5] or 'null'}")
            return True
        else:
            print(f"❌ Host not found in database")
        
        conn.close()
    except Exception as e:
        print(f"❌ Database error: {e}")
    
    return False


async def check_server_logs():
    """Check server logs for DNS operations"""
    print("\n📜 Checking server logs for DNS operations...")
    
    import subprocess
    result = subprocess.run(
        ["docker", "compose", "-f", "docker-compose.test-final.yml", "logs", "prism-server"],
        capture_output=True,
        text=True
    )
    
    # Look for DNS-related log lines
    dns_logs = []
    for line in result.stdout.split('\n'):
        if any(term in line for term in ['dns_manager', 'PowerDNS', 'DNS record', 'Creating A record']):
            dns_logs.append(line)
    
    if dns_logs:
        print("Recent DNS-related logs:")
        for log in dns_logs[-10:]:  # Last 10 DNS logs
            print(f"  {log}")
    else:
        print("No DNS-related logs found")


async def main():
    """Run the test with a new unique hostname"""
    # Generate unique hostname
    timestamp = int(time.time())
    hostname = f"dns-test-{timestamp}"
    
    print(f"🧪 PowerDNS Integration Test - New Host Registration")
    print("=" * 60)
    print(f"Test hostname: {hostname}")
    
    # Test 1: Register new host
    if send_registration(hostname):
        # Test 2: Check DNS record
        dns_ok = await check_dns_record(hostname)
        
        # Test 3: Check database
        db_ok = await check_database(hostname)
        
        # Test 4: Check logs
        await check_server_logs()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 Test Summary:")
        print(f"  ✅ Registration successful")
        print(f"  {'✅' if dns_ok else '❌'} DNS record {'created' if dns_ok else 'not created'}")
        print(f"  {'✅' if db_ok else '❌'} Database entry {'found' if db_ok else 'not found'}")
        
        if dns_ok and db_ok:
            print("\n🎉 PowerDNS integration is working perfectly!")
        else:
            print("\n⚠️  PowerDNS integration needs investigation")
    else:
        print("\n❌ Registration failed")


if __name__ == "__main__":
    asyncio.run(main())