#!/usr/bin/env python3
"""
Demo script for Client Network Connection Management (SCRUM-5)
Demonstrates connection management, retry logic, and integration with other components.
"""

import sys
import os
import tempfile
import time

# Add parent directory to path to import client modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from client.connection_manager import ConnectionManager, ConnectionError
from client.config_manager import ConfigManager
from client.message_protocol import MessageProtocol, TCPSender
from client.system_info import SystemInfo


def demo_basic_connection():
    """Demonstrate basic connection functionality."""
    print("=== Basic Connection Demo ===")
    
    config = {
        'server': {
            'host': 'httpbin.org',  # Using a real server for demo
            'port': 80,
            'timeout': 5
        }
    }
    
    try:
        conn_manager = ConnectionManager(config)
        print(f"Attempting to connect to {config['server']['host']}:{config['server']['port']}...")
        
        # This will likely fail since we're not running a server, but shows the error handling
        connection = conn_manager.connect()
        print("✓ Connection successful!")
        
        # Get server info
        server_info = conn_manager.get_server_info()
        print(f"Server info: {server_info}")
        
        conn_manager.disconnect()
        print("✓ Disconnected successfully")
        
    except ConnectionError as e:
        print(f"✗ Connection failed (expected): {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")


def demo_retry_logic():
    """Demonstrate retry logic with exponential backoff."""
    print("\n=== Retry Logic Demo ===")
    
    config = {
        'server': {
            'host': 'unreachable.invalid.domain',  # Invalid domain to trigger retries
            'port': 12345,
            'timeout': 2
        }
    }
    
    try:
        conn_manager = ConnectionManager(config)
        print(f"Attempting connection with retry to {config['server']['host']}...")
        print("This will demonstrate exponential backoff (1s, 2s, 4s delays)...")
        
        start_time = time.time()
        connection = conn_manager.connect_with_retry(max_retries=3)
        
    except ConnectionError as e:
        end_time = time.time()
        elapsed = end_time - start_time
        print(f"✗ All retries failed after {elapsed:.1f} seconds (expected): {e}")
        print("✓ Retry logic with exponential backoff demonstrated")


def demo_config_integration():
    """Demonstrate integration with ConfigManager."""
    print("\n=== Config Integration Demo ===")
    
    # Create a temporary config file
    config_content = """
server:
  host: demo.example.com
  port: 8888
  timeout: 3
heartbeat:
  interval: 45
logging:
  level: DEBUG
  file: demo.log
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        config_file = f.name
    
    try:
        print(f"Loading configuration from {config_file}")
        
        # Create ConnectionManager from config file
        conn_manager = ConnectionManager.from_config_file(config_file)
        
        # Show loaded configuration
        server_info = conn_manager.get_server_info()
        print(f"Loaded server config: {server_info}")
        
        print("✓ Configuration integration working")
        
    except Exception as e:
        print(f"✗ Config integration error: {e}")
    finally:
        os.unlink(config_file)


def demo_message_integration():
    """Demonstrate integration with message protocol."""
    print("\n=== Message Protocol Integration Demo ===")
    
    try:
        # Initialize components
        system_info = SystemInfo()
        protocol = MessageProtocol()
        sender = TCPSender()
        
        # Create a registration message
        hostname = system_info.get_hostname()
        print(f"Creating registration message for hostname: {hostname}")
        
        message = protocol.create_registration_message(hostname)
        print(f"Message: {message}")
        
        # Serialize and frame the message
        serialized = protocol.serialize_message(message)
        framed = sender.frame_message(serialized)
        
        print(f"Serialized size: {len(serialized)} bytes")
        print(f"Framed size: {len(framed)} bytes")
        
        # Show what would be sent over the connection
        print(f"Ready to send {len(framed)} bytes to server")
        print("✓ Message protocol integration working")
        
    except Exception as e:
        print(f"✗ Message integration error: {e}")


def demo_context_manager():
    """Demonstrate context manager usage."""
    print("\n=== Context Manager Demo ===")
    
    config = {
        'server': {
            'host': 'demo.invalid',
            'port': 9999,
            'timeout': 1
        }
    }
    
    try:
        print("Using ConnectionManager as context manager...")
        
        with ConnectionManager(config) as conn_manager:
            print("✓ Context manager entered")
            server_info = conn_manager.get_server_info()
            print(f"Server config: {server_info}")
            
            # Attempt connection (will fail, but demonstrates cleanup)
            try:
                conn_manager.connect()
            except ConnectionError:
                print("✗ Connection failed (expected)")
        
        print("✓ Context manager exited - automatic cleanup performed")
        
    except Exception as e:
        print(f"✗ Context manager error: {e}")


def main():
    """Run all connection management demos."""
    print("=== Prism Client Connection Management Demo ===\n")
    
    try:
        demo_basic_connection()
        demo_retry_logic()
        demo_config_integration()
        demo_message_integration()
        demo_context_manager()
        
        print("\n✅ All connection management demos completed!")
        print("\nNote: Connection failures are expected since no actual server is running.")
        print("The demos show error handling, retry logic, and component integration.")
        
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())