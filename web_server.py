#!/usr/bin/env python3
"""
Simple HTTP server for Prism DNS Web Interface
Development server to serve static files and proxy API requests
"""

import argparse
import asyncio
import json
import os
import sys
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests


class PrismWebHandler(SimpleHTTPRequestHandler):
    """Custom handler for Prism DNS web interface"""

    def __init__(self, *args, api_base_url="http://localhost:8081", **kwargs):
        self.api_base_url = api_base_url
        super().__init__(*args, **kwargs)

    def end_headers(self):
        # Add CORS headers for development
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)

        # API proxy
        if parsed_path.path.startswith("/api/"):
            self.proxy_api_request("GET")
            return

        # Serve static files
        if parsed_path.path == "/":
            self.path = "/index.html"

        super().do_GET()

    def proxy_api_request(self, method="GET"):
        """Proxy API requests to the backend server"""
        try:
            parsed_path = urlparse(self.path)
            api_url = f"{self.api_base_url}{parsed_path.path}"

            if parsed_path.query:
                api_url += f"?{parsed_path.query}"

            # Make request to API server
            if method == "GET":
                response = requests.get(api_url, timeout=10)
            else:
                response = requests.request(method, api_url, timeout=10)

            # Send response back to client
            self.send_response(response.status_code)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            self.wfile.write(response.content)

        except requests.exceptions.ConnectionError:
            # API server not available
            self.send_response(503)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            error_response = {
                "error": "API server unavailable",
                "message": "The DNS server API is not accessible. Please ensure the server is running.",
                "status": 503,
            }
            self.wfile.write(json.dumps(error_response).encode())

        except requests.exceptions.Timeout:
            # API request timeout
            self.send_response(504)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            error_response = {
                "error": "API request timeout",
                "message": "The API request timed out. Please try again.",
                "status": 504,
            }
            self.wfile.write(json.dumps(error_response).encode())

        except Exception as e:
            # Other errors
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            error_response = {
                "error": "Internal server error",
                "message": f"An error occurred: {str(e)}",
                "status": 500,
            }
            self.wfile.write(json.dumps(error_response).encode())

    def log_message(self, format, *args):
        """Custom log format"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {format % args}")


def create_handler_class(api_base_url):
    """Create handler class with API URL"""

    class Handler(PrismWebHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, api_base_url=api_base_url, **kwargs)

    return Handler


def check_api_server(api_url):
    """Check if API server is running"""
    try:
        response = requests.get(f"{api_url}/api/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def main():
    parser = argparse.ArgumentParser(description="Prism DNS Web Interface Server")
    parser.add_argument(
        "--port", type=int, default=8080, help="Port to serve web interface (default: 8080)"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8081",
        help="Backend API URL (default: http://localhost:8081)",
    )
    parser.add_argument("--web-dir", default="web", help="Web files directory (default: web)")
    parser.add_argument("--check-api", action="store_true", help="Check API server before starting")

    args = parser.parse_args()

    # Validate web directory
    web_dir = Path(args.web_dir)
    if not web_dir.exists():
        print(f"❌ Web directory '{web_dir}' does not exist")
        sys.exit(1)

    index_file = web_dir / "index.html"
    if not index_file.exists():
        print(f"❌ index.html not found in '{web_dir}'")
        sys.exit(1)

    # Check API server if requested
    if args.check_api:
        print(f"🔍 Checking API server at {args.api_url}...")
        if check_api_server(args.api_url):
            print(f"✅ API server is running")
        else:
            print(f"⚠️  API server not accessible at {args.api_url}")
            print(f"   Web interface will show connection errors until API is available")

    # Change to web directory
    os.chdir(web_dir)

    # Create server
    handler_class = create_handler_class(args.api_url)

    try:
        with HTTPServer(("", args.port), handler_class) as httpd:
            print(f"🚀 Prism DNS Web Interface Server")
            print(f"   Web Interface: http://localhost:{args.port}")
            print(f"   API Backend:   {args.api_url}")
            print(f"   Web Files:     {web_dir.absolute()}")
            print(f"   Press Ctrl+C to stop")
            print()

            httpd.serve_forever()

    except KeyboardInterrupt:
        print(f"\n🛑 Server stopped by user")
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ Port {args.port} is already in use")
            print(f"   Try a different port with --port")
        else:
            print(f"❌ Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
