#!/usr/bin/env python3
"""
Test TCP registration with user assignment
"""

import asyncio
import json
import socket
import time
from datetime import datetime, timezone

def create_registration_message(hostname):
    """Create a registration message"""
    return {
        "version": "1.0",
        "type": "registration",
        "hostname": hostname,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def send_tcp_message(host, port, message):
    """Send a message to the TCP server"""
    try:
        # Connect to server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        
        # Send message
        message_json = json.dumps(message)
        message_bytes = message_json.encode('utf-8')
        length_bytes = len(message_bytes).to_bytes(4, byteorder='big')
        
        sock.sendall(length_bytes + message_bytes)
        
        # Receive response
        response_length_bytes = sock.recv(4)
        if len(response_length_bytes) == 4:
            response_length = int.from_bytes(response_length_bytes, byteorder='big')
            response_bytes = sock.recv(response_length)
            response = json.loads(response_bytes.decode('utf-8'))
            print(f"Response: {response}")
            return response
        
        sock.close()
        
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    """Test TCP registration"""
    server_host = "localhost"
    server_port = 8080
    
    # Test registration
    test_hostname = f"test-host-{int(time.time())}.example.com"
    print(f"Testing registration for: {test_hostname}")
    
    message = create_registration_message(test_hostname)
    response = send_tcp_message(server_host, server_port, message)
    
    if response and response.get("status") == "success":
        print("✓ Registration successful")
        print(f"  Message: {response.get('message')}")
        
        # Note: The host should now be assigned to system user
        # ID: 00000000-0000-0000-0000-000000000000
        
    else:
        print("✗ Registration failed")
        if response:
            print(f"  Error: {response.get('message')}")

if __name__ == "__main__":
    main()