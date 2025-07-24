#!/bin/bash

# Simple script to run web tests
echo "Starting test server on port 8000..."
echo "Open http://localhost:8000/tests/test-token-management-ui.html in your browser"
echo "Press Ctrl+C to stop the server"

cd /home/junior/managedDns/web
python3 -m http.server 8000