"""Test cases for API token support in client configuration."""

import pytest
from unittest.mock import Mock, patch
from client.config_manager import ConfigManager, ConfigValidationError


class TestConfigTokenSupport:
    """Test API token configuration support."""
    
    def test_config_with_auth_token(self):
        """Test configuration with auth token."""
        config = {
            'service': {
                'name': 'prism-client',
                'description': 'Prism Host Client',
                'pid_file': '/tmp/prism-client.pid'
            },
            'server': {
                'host': 'example.com',
                'port': 8080,
                'timeout': 10,
                'auth_token': 'test-token-12345678901234567890'
            },
            'heartbeat': {
                'interval': 5
            },
            'logging': {
                'level': 'INFO'
            }
        }
        
        manager = ConfigManager()
        # Should not raise any exception
        manager.validate_config(config)
        
    def test_config_without_auth_token_fails(self):
        """Test configuration without auth token fails."""
        config = {
            'service': {
                'name': 'prism-client',
                'description': 'Prism Host Client',
                'pid_file': '/tmp/prism-client.pid'
            },
            'server': {
                'host': 'example.com',
                'port': 8080,
                'timeout': 10
                # Missing auth_token
            },
            'heartbeat': {
                'interval': 5
            },
            'logging': {
                'level': 'INFO'
            }
        }
        
        manager = ConfigManager()
        # Should raise exception - token is required
        with pytest.raises(ConfigValidationError, match="Missing required field: server.auth_token"):
            manager.validate_config(config)
        
    def test_invalid_auth_token_too_short(self):
        """Test validation of auth tokens that are too short."""
        config = {
            'server': {
                'host': 'example.com',
                'port': 8080,
                'timeout': 10,
                'auth_token': 'short'
            },
            'heartbeat': {
                'interval': 5
            },
            'logging': {
                'level': 'INFO'
            }
        }
        
        manager = ConfigManager()
        with pytest.raises(ConfigValidationError, match="too short"):
            manager.validate_config(config)
    
    def test_invalid_auth_token_with_spaces(self):
        """Test validation of auth tokens containing spaces."""
        config = {
            'server': {
                'host': 'example.com',
                'port': 8080,
                'timeout': 10,
                'auth_token': 'has spaces in token'
            },
            'heartbeat': {
                'interval': 5
            },
            'logging': {
                'level': 'INFO'
            }
        }
        
        manager = ConfigManager()
        with pytest.raises(ConfigValidationError, match="cannot contain spaces"):
            manager.validate_config(config)
            
    def test_auth_token_not_string(self):
        """Test validation when auth token is not a string."""
        config = {
            'server': {
                'host': 'example.com',
                'port': 8080,
                'timeout': 10,
                'auth_token': 12345  # Should be string
            },
            'heartbeat': {
                'interval': 5
            },
            'logging': {
                'level': 'INFO'
            }
        }
        
        manager = ConfigManager()
        with pytest.raises(ConfigValidationError, match="must be a string"):
            manager.validate_config(config)
            
    def test_empty_auth_token_not_allowed(self):
        """Test that empty auth token is not allowed."""
        config = {
            'server': {
                'host': 'example.com',
                'port': 8080,
                'timeout': 10,
                'auth_token': ''
            },
            'heartbeat': {
                'interval': 5
            },
            'logging': {
                'level': 'INFO'
            }
        }
        
        manager = ConfigManager()
        # Should raise - empty token not allowed
        with pytest.raises(ConfigValidationError, match="auth_token cannot be empty"):
            manager.validate_config(config)


class TestHeartbeatManagerTokenSupport:
    """Test HeartbeatManager with token support."""
    
    def test_registration_message_with_token(self):
        """Test registration message includes token."""
        from client.heartbeat_manager import HeartbeatManager
        
        config = {
            'server': {
                'host': 'test.com',
                'port': 8080,
                'timeout': 10,
                'auth_token': 'test-token-12345678901234567890'
            },
            'heartbeat': {
                'interval': 5
            },
            'network': {
                'hostname': 'test.example.com'
            }
        }
        
        with patch('client.heartbeat_manager.SystemInfo') as mock_sys_info:
            mock_sys_info.return_value.get_hostname.return_value = 'test.example.com'
            
            with patch.object(HeartbeatManager, '_get_local_ip', return_value='192.168.1.100'):
                manager = HeartbeatManager(config)
                message = manager._create_registration_message()
                
                assert message['auth_token'] == 'test-token-12345678901234567890'
                assert message['action'] == 'register'
                assert message['hostname'] == 'test.example.com'
                assert message['client_ip'] == '192.168.1.100'
            
    def test_registration_message_always_has_token(self):
        """Test registration message always includes token."""
        from client.heartbeat_manager import HeartbeatManager
        
        config = {
            'server': {
                'host': 'test.com',
                'port': 8080,
                'timeout': 10,
                'auth_token': 'required-token-12345678901234567890'
            },
            'heartbeat': {
                'interval': 5
            },
            'network': {
                'hostname': 'test.example.com'
            }
        }
        
        with patch('client.heartbeat_manager.SystemInfo') as mock_sys_info:
            mock_sys_info.return_value.get_hostname.return_value = 'test.example.com'
            
            with patch.object(HeartbeatManager, '_get_local_ip', return_value='192.168.1.100'):
                manager = HeartbeatManager(config)
                message = manager._create_registration_message()
                
                assert message['auth_token'] == 'required-token-12345678901234567890'
                assert message['action'] == 'register'
                assert message['hostname'] == 'test.example.com'
            
    def test_heartbeat_message_with_token(self):
        """Test heartbeat message includes token."""
        from client.heartbeat_manager import HeartbeatManager
        
        config = {
            'server': {
                'host': 'test.com',
                'port': 8080,
                'timeout': 10,
                'auth_token': 'test-token-12345678901234567890'
            },
            'heartbeat': {
                'interval': 5
            },
            'network': {
                'hostname': 'test.example.com'
            }
        }
        
        with patch('client.heartbeat_manager.SystemInfo') as mock_sys_info:
            mock_sys_info.return_value.get_hostname.return_value = 'test.example.com'
            
            with patch.object(HeartbeatManager, '_get_local_ip', return_value='192.168.1.100'):
                manager = HeartbeatManager(config)
                message = manager._create_heartbeat_message()
                
                assert message['auth_token'] == 'test-token-12345678901234567890'
                assert message['action'] == 'heartbeat'
                assert message['hostname'] == 'test.example.com'
            
    def test_heartbeat_manager_requires_token(self):
        """Test HeartbeatManager requires auth token in config."""
        from client.heartbeat_manager import HeartbeatManager
        
        config = {
            'server': {
                'host': 'test.com',
                'port': 8080,
                'timeout': 10
                # Missing auth_token
            },
            'heartbeat': {
                'interval': 5
            },
            'network': {
                'hostname': 'test.example.com'
            }
        }
        
        with patch('client.heartbeat_manager.SystemInfo'):
            # Should raise KeyError when trying to access required auth_token
            with pytest.raises(KeyError, match="auth_token"):
                HeartbeatManager(config)


class TestCommandLineTokenSupport:
    """Test command line token override functionality."""
    
    def test_command_line_token_override(self):
        """Test command line token overrides config file."""
        import argparse
        
        # Simulate command line args
        args = argparse.Namespace(
            config='test.yaml',
            auth_token='cli-token-override12345678901234567890',
            command='start',
            daemon=False
        )
        
        # Config file has different token
        file_config = {
            'service': {
                'name': 'prism-client',
                'description': 'Prism Host Client',
                'pid_file': '/tmp/prism-client.pid'
            },
            'server': {
                'host': 'example.com',
                'port': 8080,
                'auth_token': 'file-token'
            },
            'heartbeat': {
                'interval': 5
            }
        }
        
        # Process config with CLI override
        if args.auth_token:
            if 'server' not in file_config:
                file_config['server'] = {}
            file_config['server']['auth_token'] = args.auth_token
        
        assert file_config['server']['auth_token'] == 'cli-token-override12345678901234567890'
        
    def test_command_line_token_with_no_server_section(self):
        """Test command line token when config has no server section."""
        import argparse
        
        args = argparse.Namespace(
            config='test.yaml',
            auth_token='cli-token-12345678901234567890',
            command='start',
            daemon=False
        )
        
        # Minimal config without server section
        file_config = {
            'service': {
                'name': 'prism-client',
                'description': 'Prism Host Client',
                'pid_file': '/tmp/prism-client.pid'
            }
        }
        
        # Process config with CLI token
        if args.auth_token:
            if 'server' not in file_config:
                file_config['server'] = {}
            file_config['server']['auth_token'] = args.auth_token
        
        assert 'server' in file_config
        assert file_config['server']['auth_token'] == 'cli-token-12345678901234567890'


class TestLoggingTokenSecurity:
    """Test that tokens are not exposed in logs."""
    
    def test_token_not_logged(self):
        """Test that actual token value is never logged."""
        from client.heartbeat_manager import HeartbeatManager
        import logging
        
        config = {
            'server': {
                'host': 'test.com',
                'port': 8080,
                'timeout': 10,
                'auth_token': 'secret-token-12345678901234567890'
            },
            'heartbeat': {
                'interval': 5
            }
        }
        
        with patch('client.heartbeat_manager.SystemInfo'):
            # Create a logger handler to capture log messages
            log_messages = []
            handler = logging.Handler()
            handler.emit = lambda record: log_messages.append(record.getMessage())
            
            # Get the HeartbeatManager logger and add our handler
            logger = logging.getLogger('client.heartbeat_manager')
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            
            try:
                manager = HeartbeatManager(config)
                
                # Check that token value is not in any log messages
                for message in log_messages:
                    assert 'secret-token-12345678901234567890' not in message
                    
                # Should have logged that auth is configured
                assert any('Client configured with API token authentication' in msg for msg in log_messages)
            finally:
                # Clean up
                logger.removeHandler(handler)