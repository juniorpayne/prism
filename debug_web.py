#!/usr/bin/env python3
"""
Debug script to test web interface loading
"""

import time
import subprocess
import requests
import sys


def test_api_direct():
    """Test direct API access"""
    print("Testing direct API access...")
    try:
        response = requests.get("http://localhost:8081/api/hosts", timeout=5)
        print(f"Direct API: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Hosts found: {len(data.get('hosts', []))}")
            for host in data.get("hosts", []):
                print(f"  - {host['hostname']}: {host['current_ip']} ({host['status']})")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Direct API Error: {e}")


def test_api_proxy():
    """Test API through web server proxy"""
    print("\nTesting API through web server proxy...")
    try:
        response = requests.get("http://localhost:8090/api/hosts", timeout=5)
        print(f"Proxy API: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Hosts found: {len(data.get('hosts', []))}")
            for host in data.get("hosts", []):
                print(f"  - {host['hostname']}: {host['current_ip']} ({host['status']})")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Proxy API Error: {e}")


def test_web_page():
    """Test web page loading"""
    print("\nTesting web page access...")
    try:
        response = requests.get("http://localhost:8090/", timeout=5)
        print(f"Web page: {response.status_code}")
        if response.status_code == 200:
            print("Web page loads successfully")
            # Check if key elements are present
            html = response.text
            if 'id="loading-hosts"' in html:
                print("✓ Loading hosts element found")
            if 'id="hosts-table-body"' in html:
                print("✓ Hosts table body element found")
            if "js/api.js" in html:
                print("✓ API.js script included")
            if "js/hosts.js" in html:
                print("✓ Hosts.js script included")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Web page Error: {e}")


def test_js_files():
    """Test JavaScript file loading"""
    print("\nTesting JavaScript file access...")
    js_files = ["api.js", "utils.js", "hosts.js", "app.js", "dashboard.js"]
    for js_file in js_files:
        try:
            response = requests.get(f"http://localhost:8090/js/{js_file}", timeout=5)
            print(f"{js_file}: {response.status_code}")
        except Exception as e:
            print(f"{js_file} Error: {e}")


if __name__ == "__main__":
    print("Prism Web Interface Debug Test")
    print("=" * 40)

    test_api_direct()
    test_api_proxy()
    test_web_page()
    test_js_files()

    print(
        "\nDebug complete. If all tests pass, the issue might be in browser JavaScript execution."
    )
    print(
        "Try opening http://localhost:8090/#hosts in a browser and check the developer console for errors."
    )
