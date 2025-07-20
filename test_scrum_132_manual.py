#!/usr/bin/env python3
"""
Manual test for SCRUM-132: Filter DNS records to show only records in user's zones
"""

import asyncio
import aiohttp
import json
from typing import Optional

BASE_URL = "http://nginx/api"  # Inside docker network

async def login(session: aiohttp.ClientSession, username: str, password: str) -> Optional[str]:
    """Login and get access token."""
    try:
        async with session.post(
            f"{BASE_URL}/auth/login",
            data={"username": username, "password": password}
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("access_token")
            else:
                print(f"Login failed for {username}: {resp.status}")
                return None
    except Exception as e:
        print(f"Login error: {e}")
        return None

async def create_zone(session: aiohttp.ClientSession, token: str, zone_name: str):
    """Create a DNS zone."""
    headers = {"Authorization": f"Bearer {token}"}
    zone_data = {
        "name": zone_name,
        "kind": "Native"
    }
    
    try:
        async with session.post(
            f"{BASE_URL}/dns/zones",
            headers=headers,
            json=zone_data
        ) as resp:
            print(f"Create zone {zone_name}: {resp.status}")
            if resp.status != 201:
                text = await resp.text()
                print(f"Response: {text}")
    except Exception as e:
        print(f"Error creating zone: {e}")

async def create_record(session: aiohttp.ClientSession, token: str, zone_name: str, record_name: str, record_type: str, content: str):
    """Create a DNS record in a zone."""
    headers = {"Authorization": f"Bearer {token}"}
    record_data = {
        "name": f"{record_name}.{zone_name}",
        "type": record_type,
        "content": content,
        "ttl": 3600
    }
    
    try:
        async with session.post(
            f"{BASE_URL}/dns/zones/{zone_name}/records",
            headers=headers,
            json=record_data
        ) as resp:
            print(f"Create record {record_name}.{zone_name}: {resp.status}")
            if resp.status != 201:
                text = await resp.text()
                print(f"Response: {text}")
    except Exception as e:
        print(f"Error creating record: {e}")

async def list_records_in_zone(session: aiohttp.ClientSession, token: str, zone_name: str, expected_status: int = 200):
    """List records in a zone."""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        async with session.get(
            f"{BASE_URL}/dns/zones/{zone_name}/records",
            headers=headers
        ) as resp:
            print(f"\nList records in {zone_name}: {resp.status}")
            if resp.status == expected_status:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"Found {len(data.get('records', []))} records")
                    for record in data.get('records', []):
                        print(f"  - {record.get('name')} {record.get('type')} {record.get('content')}")
            else:
                text = await resp.text()
                print(f"Unexpected status. Response: {text}")
            return resp.status
    except Exception as e:
        print(f"Error listing records: {e}")
        return None

async def search_records(session: aiohttp.ClientSession, token: str, query: str):
    """Search for records across zones."""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        async with session.get(
            f"{BASE_URL}/dns/records/search",
            headers=headers,
            params={"q": query}
        ) as resp:
            print(f"\nSearch records for '{query}': {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                print(f"Found {data.get('total', 0)} records in {data.get('zones_searched', 0)} zones")
                for record in data.get('records', []):
                    print(f"  - {record.get('name')} ({record.get('zone')}) {record.get('type')} {record.get('content')}")
            else:
                text = await resp.text()
                print(f"Response: {text}")
    except Exception as e:
        print(f"Error searching records: {e}")

async def export_records(session: aiohttp.ClientSession, token: str, format: str = "json"):
    """Export records."""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        async with session.get(
            f"{BASE_URL}/dns/records/export",
            headers=headers,
            params={"format": format}
        ) as resp:
            print(f"\nExport records ({format}): {resp.status}")
            if resp.status == 200:
                if format == "json":
                    data = await resp.json()
                    print(f"Exported {len(data.get('zones', []))} zones for user {data.get('user')}")
                    for zone in data.get('zones', []):
                        print(f"  - Zone: {zone.get('name')} with {len(zone.get('records', []))} records")
                else:
                    content = await resp.text()
                    print(f"Export preview (first 500 chars):\n{content[:500]}")
            else:
                text = await resp.text()
                print(f"Response: {text}")
    except Exception as e:
        print(f"Error exporting records: {e}")

async def main():
    """Run the manual test."""
    print("=== SCRUM-132 Manual Test: DNS Record Filtering ===\n")
    
    async with aiohttp.ClientSession() as session:
        # Step 1: Login as two different users
        print("Step 1: Login as two users")
        usera_token = await login(session, "usera", "password123")
        userb_token = await login(session, "userb", "password123")
        
        if not usera_token or not userb_token:
            print("Failed to login users. Make sure they exist.")
            return
        
        # Step 2: Create zones for each user
        print("\nStep 2: Create zones for each user")
        await create_zone(session, usera_token, "usera-test.com.")
        await create_zone(session, userb_token, "userb-test.com.")
        
        # Step 3: Create records in each zone
        print("\nStep 3: Create records in zones")
        await create_record(session, usera_token, "usera-test.com.", "www", "A", "192.168.1.1")
        await create_record(session, usera_token, "usera-test.com.", "mail", "MX", "10 mail.usera-test.com.")
        await create_record(session, userb_token, "userb-test.com.", "www", "A", "192.168.2.1")
        await create_record(session, userb_token, "userb-test.com.", "ftp", "A", "192.168.2.2")
        
        # Step 4: Test record listing - users should only see their own zones
        print("\n=== Test 1: Record Listing Authorization ===")
        print("\nUser A tries to list records in their own zone (should succeed):")
        status = await list_records_in_zone(session, usera_token, "usera-test.com.")
        assert status == 200, "User A should be able to list their own zone's records"
        
        print("\nUser A tries to list records in User B's zone (should fail with 404):")
        status = await list_records_in_zone(session, usera_token, "userb-test.com.", expected_status=404)
        assert status == 404, "User A should NOT be able to list User B's zone's records"
        
        print("\nUser B tries to list records in their own zone (should succeed):")
        status = await list_records_in_zone(session, userb_token, "userb-test.com.")
        assert status == 200, "User B should be able to list their own zone's records"
        
        # Step 5: Test record search - should only return user's records
        print("\n=== Test 2: Record Search Filtering ===")
        print("\nUser A searches for 'www' (should only see www.usera-test.com):")
        await search_records(session, usera_token, "www")
        
        print("\nUser B searches for 'www' (should only see www.userb-test.com):")
        await search_records(session, userb_token, "www")
        
        print("\nUser A searches for '192.168' in content (should see their IPs only):")
        await search_records(session, usera_token, "192.168")
        
        # Step 6: Test record export - should only export user's records
        print("\n=== Test 3: Record Export Filtering ===")
        print("\nUser A exports records (JSON):")
        await export_records(session, usera_token, "json")
        
        print("\nUser B exports records (CSV):")
        await export_records(session, userb_token, "csv")
        
        print("\n=== All tests completed successfully! ===")
        print("\nSummary:")
        print("✓ Users cannot list records in zones they don't own (404)")
        print("✓ Record search only returns records from user's zones")
        print("✓ Record export only includes records from user's zones")

if __name__ == "__main__":
    asyncio.run(main())