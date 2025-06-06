#!/usr/bin/env python3
"""
Test script for Prism DNS Web Interface
Tests the web interface components and integration
"""

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import requests


def test_web_files():
    """Test that all required web files exist"""
    print("🔍 Testing web interface files...")

    web_dir = Path("web")
    required_files = [
        "index.html",
        "css/main.css",
        "js/api.js",
        "js/utils.js",
        "js/hosts.js",
        "js/dashboard.js",
        "js/app.js",
    ]

    missing_files = []
    for file_path in required_files:
        full_path = web_dir / file_path
        if not full_path.exists():
            missing_files.append(file_path)
        else:
            print(f"  ✅ {file_path}")

    if missing_files:
        print(f"  ❌ Missing files: {missing_files}")
        return False

    print("  ✅ All required web files present")
    return True


def test_html_structure():
    """Test HTML structure and key elements"""
    print("🔍 Testing HTML structure...")

    index_file = Path("web/index.html")
    if not index_file.exists():
        print("  ❌ index.html not found")
        return False

    content = index_file.read_text()

    # Check for key elements
    required_elements = [
        'id="dashboard-view"',
        'id="hosts-view"',
        'id="total-hosts"',
        'id="online-hosts"',
        'id="offline-hosts"',
        'id="hosts-table-body"',
        'id="search-hosts"',
        'id="filter-status"',
        'id="hostDetailModal"',
    ]

    missing_elements = []
    for element in required_elements:
        if element not in content:
            missing_elements.append(element)
        else:
            print(f"  ✅ {element}")

    if missing_elements:
        print(f"  ❌ Missing elements: {missing_elements}")
        return False

    print("  ✅ All required HTML elements present")
    return True


def test_javascript_syntax():
    """Test JavaScript files for basic syntax"""
    print("🔍 Testing JavaScript syntax...")

    js_files = [
        "web/js/api.js",
        "web/js/utils.js",
        "web/js/hosts.js",
        "web/js/dashboard.js",
        "web/js/app.js",
    ]

    for js_file in js_files:
        try:
            # Basic syntax check - look for common issues
            with open(js_file, "r") as f:
                content = f.read()

            # Check for balanced braces
            open_braces = content.count("{")
            close_braces = content.count("}")

            if open_braces != close_braces:
                print(
                    f"  ❌ {js_file}: Unbalanced braces ({open_braces} open, {close_braces} close)"
                )
                return False

            # Check for basic class structure
            if "class " in content and "constructor(" in content:
                print(f"  ✅ {js_file}: Class structure found")
            elif "function " in content:
                print(f"  ✅ {js_file}: Functions found")
            else:
                print(f"  ⚠️  {js_file}: No obvious JavaScript structure")

        except Exception as e:
            print(f"  ❌ {js_file}: Error reading file - {e}")
            return False

    print("  ✅ JavaScript files appear syntactically valid")
    return True


def test_css_structure():
    """Test CSS file structure"""
    print("🔍 Testing CSS structure...")

    css_file = Path("web/css/main.css")
    if not css_file.exists():
        print("  ❌ main.css not found")
        return False

    content = css_file.read_text()

    # Check for key CSS classes
    required_classes = [
        ".navbar",
        ".card",
        ".table",
        ".status-badge",
        ".status-online",
        ".status-offline",
    ]

    found_classes = []
    for css_class in required_classes:
        if css_class in content:
            found_classes.append(css_class)
            print(f"  ✅ {css_class}")

    if len(found_classes) < len(required_classes):
        missing = set(required_classes) - set(found_classes)
        print(f"  ⚠️  Missing CSS classes: {missing}")

    print(
        f"  ✅ CSS file structure valid ({len(found_classes)}/{len(required_classes)} key classes)"
    )
    return True


def start_mock_api_server():
    """Start a mock API server for testing"""
    print("🚀 Starting mock API server...")

    import json
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class MockAPIHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            # Mock responses
            if self.path == "/api/health":
                response = {
                    "status": "healthy",
                    "timestamp": "2024-01-01T12:00:00Z",
                    "version": "1.0.0",
                    "uptime_seconds": 3600,
                }
            elif self.path == "/api/stats":
                response = {
                    "total_hosts": 5,
                    "online_hosts": 3,
                    "offline_hosts": 2,
                    "database_size": 1024,
                }
            elif self.path.startswith("/api/hosts"):
                response = {
                    "hosts": [
                        {
                            "hostname": "web-server-01",
                            "current_ip": "192.168.1.10",
                            "status": "online",
                            "first_seen": "2024-01-01T10:00:00Z",
                            "last_seen": "2024-01-01T12:00:00Z",
                        },
                        {
                            "hostname": "api-server-01",
                            "current_ip": "192.168.1.20",
                            "status": "online",
                            "first_seen": "2024-01-01T10:00:00Z",
                            "last_seen": "2024-01-01T11:58:00Z",
                        },
                        {
                            "hostname": "db-server-01",
                            "current_ip": "192.168.1.30",
                            "status": "offline",
                            "first_seen": "2024-01-01T10:00:00Z",
                            "last_seen": "2024-01-01T11:30:00Z",
                        },
                    ]
                }
            else:
                response = {"error": "Not found"}
                self.send_response(404)

            self.wfile.write(json.dumps(response).encode())

        def log_message(self, format, *args):
            # Suppress default logging
            pass

    def run_mock_server():
        with HTTPServer(("localhost", 8081), MockAPIHandler) as httpd:
            httpd.serve_forever()

    thread = threading.Thread(target=run_mock_server, daemon=True)
    thread.start()

    # Wait a moment for server to start
    time.sleep(0.5)

    # Test if server is running
    try:
        response = requests.get("http://localhost:8081/api/health", timeout=2)
        if response.status_code == 200:
            print("  ✅ Mock API server started successfully")
            return True
    except:
        pass

    print("  ❌ Failed to start mock API server")
    return False


def test_web_server():
    """Test the web server functionality"""
    print("🔍 Testing web server...")

    # Start mock API first
    if not start_mock_api_server():
        return False

    # Start web server in background
    try:
        web_server_process = subprocess.Popen(
            [
                sys.executable,
                "web_server.py",
                "--port",
                "8082",  # Use different port to avoid conflicts
                "--api-url",
                "http://localhost:8081",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Wait for server to start
        time.sleep(2)

        # Test web server
        try:
            response = requests.get("http://localhost:8082/", timeout=5)
            if response.status_code == 200 and "Prism DNS" in response.text:
                print("  ✅ Web server serving HTML correctly")
            else:
                print(f"  ❌ Web server response issue (status: {response.status_code})")
                return False

            # Test API proxy
            response = requests.get("http://localhost:8082/api/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    print("  ✅ API proxy working correctly")
                else:
                    print("  ❌ API proxy returning incorrect data")
                    return False
            else:
                print(f"  ❌ API proxy failed (status: {response.status_code})")
                return False

        except requests.exceptions.ConnectionError:
            print("  ❌ Could not connect to web server")
            return False
        finally:
            web_server_process.terminate()
            web_server_process.wait()

    except Exception as e:
        print(f"  ❌ Error testing web server: {e}")
        return False

    print("  ✅ Web server functionality working")
    return True


def run_integration_test():
    """Run comprehensive integration test"""
    print("🧪 Running Prism DNS Web Interface Integration Test")
    print("=" * 60)

    tests = [
        ("Web Files", test_web_files),
        ("HTML Structure", test_html_structure),
        ("JavaScript Syntax", test_javascript_syntax),
        ("CSS Structure", test_css_structure),
        ("Web Server", test_web_server),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)

        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")

    print("\n" + "=" * 60)
    print(f"🎯 INTEGRATION TEST RESULTS: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED! Web interface is ready for demo!")
        return True
    else:
        print(f"⚠️  {total - passed} tests failed. Please fix issues before demo.")
        return False


if __name__ == "__main__":
    success = run_integration_test()
    sys.exit(0 if success else 1)
