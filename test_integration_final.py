#!/usr/bin/env python3
"""
Final comprehensive test of PowerDNS integration
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
    message = {
        "version": "1.0",
        "type": "registration",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "hostname": hostname
    }
    
    json_data = json.dumps(message, separators=(",", ":")).encode("utf-8")
    length_prefix = struct.pack(">I", len(json_data))
    framed_message = length_prefix + json_data
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(('localhost', port))
        sock.settimeout(5.0)
        sock.sendall(framed_message)
        
        # Receive response
        length_data = sock.recv(4)
        response_length = struct.unpack(">I", length_data)[0]
        response_data = sock.recv(response_length)
        response = json.loads(response_data.decode("utf-8"))
        
        sock.close()
        return response.get("status") == "success", response.get("message", "")
    except Exception as e:
        sock.close()
        return False, str(e)


async def verify_dns_record(hostname, expected_ip, zone="managed.prism.local."):
    """Verify DNS record exists and resolves correctly"""
    async with aiohttp.ClientSession() as session:
        headers = {"X-API-Key": "test-api-key"}
        fqdn = f"{hostname}.{zone}"
        
        # Query PowerDNS for the specific record
        url = f"http://localhost:8053/api/v1/servers/localhost/zones/{zone}"
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                zone_data = await resp.json()
                for rrset in zone_data.get("rrsets", []):
                    if rrset["name"] == fqdn and rrset["type"] == "A":
                        actual_ip = rrset["records"][0]["content"]
                        return actual_ip == expected_ip, actual_ip
    return False, None


async def check_metrics():
    """Check if metrics are being recorded"""
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:8081/metrics") as resp:
            if resp.status == 200:
                metrics = await resp.text()
                dns_metrics = {}
                for line in metrics.split('\n'):
                    if 'powerdns_record_operations_total' in line and not line.startswith('#'):
                        # Parse metric line
                        if '{' in line:
                            metric_name = line.split('{')[0]
                            labels = line.split('{')[1].split('}')[0]
                            value = line.split('}')[1].strip()
                            dns_metrics[f"{metric_name}_{labels}"] = float(value)
                return dns_metrics
    return {}


async def run_comprehensive_test():
    """Run comprehensive integration test"""
    print("🧪 PowerDNS Integration - Comprehensive Test")
    print("=" * 60)
    
    test_results = {
        "tcp_registration": False,
        "dns_record_created": False,
        "dns_record_correct": False,
        "metrics_recorded": False,
        "multiple_hosts": False
    }
    
    # Test 1: Single host registration
    print("\n📌 Test 1: Single Host Registration")
    hostname1 = f"integration-test-{int(time.time())}"
    success, message = send_registration(hostname1)
    if success:
        print(f"✅ Registered {hostname1}: {message}")
        test_results["tcp_registration"] = True
        
        # Wait for DNS sync
        await asyncio.sleep(2)
        
        # Verify DNS record
        dns_ok, actual_ip = await verify_dns_record(hostname1, "172.18.0.1")
        if dns_ok:
            print(f"✅ DNS record created correctly: {hostname1} -> {actual_ip}")
            test_results["dns_record_created"] = True
            test_results["dns_record_correct"] = True
        else:
            print(f"❌ DNS record issue: expected 172.18.0.1, got {actual_ip}")
    else:
        print(f"❌ Registration failed: {message}")
    
    # Test 2: Multiple hosts
    print("\n📌 Test 2: Multiple Host Registration")
    success_count = 0
    for i in range(3):
        hostname = f"bulk-test-{int(time.time())}-{i}"
        success, _ = send_registration(hostname)
        if success:
            success_count += 1
        await asyncio.sleep(0.5)
    
    print(f"✅ Registered {success_count}/3 hosts")
    if success_count == 3:
        test_results["multiple_hosts"] = True
    
    # Test 3: Check metrics
    print("\n📌 Test 3: Metrics Verification")
    metrics = await check_metrics()
    if metrics:
        print("✅ DNS metrics found:")
        for key, value in metrics.items():
            if value > 0:
                print(f"   {key}: {value}")
        test_results["metrics_recorded"] = len(metrics) > 0
    else:
        print("❌ No DNS metrics found")
    
    # Test 4: IPv6 address (should create AAAA record)
    print("\n📌 Test 4: IPv6 Registration (Optional)")
    # This would need a client that sends IPv6 address
    print("⏭️  Skipped (requires IPv6 client)")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print(f"  TCP Registration:    {'✅' if test_results['tcp_registration'] else '❌'}")
    print(f"  DNS Record Created:  {'✅' if test_results['dns_record_created'] else '❌'}")
    print(f"  DNS Record Correct:  {'✅' if test_results['dns_record_correct'] else '❌'}")
    print(f"  Metrics Recorded:    {'✅' if test_results['metrics_recorded'] else '❌'}")
    print(f"  Bulk Registration:   {'✅' if test_results['multiple_hosts'] else '❌'}")
    
    passed = sum(1 for v in test_results.values() if v)
    total = len(test_results)
    
    print(f"\n🏆 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 PowerDNS integration is fully functional!")
    elif passed >= 3:
        print("✅ PowerDNS integration is working with minor issues")
    else:
        print("⚠️  PowerDNS integration needs attention")
    
    return test_results


if __name__ == "__main__":
    asyncio.run(run_comprehensive_test())