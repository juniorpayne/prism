"""
Integration test for Configuration Management System (SCRUM-9)
Tests the complete configuration workflow.
"""

import tempfile
import os
import pytest
from client.config_manager import ConfigManager, ConfigValidationError


def test_complete_configuration_workflow():
    """Test the complete configuration loading and validation workflow."""
    # Create a temporary config file
    config_content = """
server:
  host: integration.test.com
  port: 9999
  timeout: 5
heartbeat:
  interval: 30
logging:
  level: DEBUG
  file: integration.log
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        config_file = f.name
    
    try:
        config_manager = ConfigManager()
        
        # Load and validate configuration
        config = config_manager.load_config(config_file)
        
        # Test all getter methods
        server_config = config_manager.get_server_config(config)
        heartbeat_config = config_manager.get_heartbeat_config(config)
        logging_config = config_manager.get_logging_config(config)
        
        # Verify server configuration
        assert server_config['host'] == 'integration.test.com'
        assert server_config['port'] == 9999
        assert server_config['timeout'] == 5
        
        # Verify heartbeat configuration
        assert heartbeat_config['interval'] == 30
        
        # Verify logging configuration
        assert logging_config['level'] == 'DEBUG'
        assert logging_config['file'] == 'integration.log'
        
    finally:
        os.unlink(config_file)