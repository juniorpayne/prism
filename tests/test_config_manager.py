"""
Tests for Configuration Management System (SCRUM-9)
Following TDD approach as specified in the user story.
"""

import pytest
import tempfile
import os
import yaml
from unittest.mock import patch, mock_open
from client.config_manager import ConfigManager, ConfigValidationError


class TestConfigManager:
    """Test suite for ConfigManager following SCRUM-9 requirements."""

    def test_load_valid_configuration(self):
        """Test loading a valid YAML configuration file."""
        config_data = {
            "server": {"host": "test.example.com", "port": 9090, "timeout": 15},
            "heartbeat": {"interval": 30},
            "logging": {"level": "DEBUG", "file": "test.log"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name

        try:
            config_manager = ConfigManager()
            config = config_manager.load_config(config_file)

            assert config["server"]["host"] == "test.example.com"
            assert config["server"]["port"] == 9090
            assert config["server"]["timeout"] == 15
            assert config["heartbeat"]["interval"] == 30
            assert config["logging"]["level"] == "DEBUG"
            assert config["logging"]["file"] == "test.log"
        finally:
            os.unlink(config_file)

    def test_load_missing_configuration_file(self):
        """Test behavior when configuration file is missing."""
        config_manager = ConfigManager()
        config = config_manager.load_config("/nonexistent/config.yaml")

        # Should return default configuration
        default_config = config_manager.get_default_config()
        assert config == default_config

    def test_default_configuration_values(self):
        """Test that default configuration has expected values."""
        config_manager = ConfigManager()
        config = config_manager.get_default_config()

        assert config["server"]["host"] == "localhost"
        assert config["server"]["port"] == 8080
        assert config["server"]["timeout"] == 10
        assert config["heartbeat"]["interval"] == 60
        assert config["logging"]["level"] == "INFO"
        assert config["logging"]["file"] == "client.log"

    def test_configuration_validation_success(self):
        """Test successful configuration validation."""
        valid_config = {
            "server": {"host": "example.com", "port": 8080, "timeout": 10},
            "heartbeat": {"interval": 60},
            "logging": {"level": "INFO", "file": "client.log"},
        }

        config_manager = ConfigManager()
        # Should not raise any exception
        config_manager.validate_config(valid_config)

    def test_configuration_validation_missing_fields(self):
        """Test configuration validation with missing required fields."""
        invalid_config = {
            "server": {
                "host": "example.com"
                # Missing port and timeout
            },
            "heartbeat": {"interval": 60},
            # Missing logging section
        }

        config_manager = ConfigManager()
        with pytest.raises(ConfigValidationError) as exc_info:
            config_manager.validate_config(invalid_config)

        assert "Missing required" in str(exc_info.value)

    def test_configuration_validation_invalid_types(self):
        """Test configuration validation with invalid data types."""
        invalid_config = {
            "server": {
                "host": "example.com",
                "port": "invalid_port",  # Should be int
                "timeout": 10,
            },
            "heartbeat": {"interval": "invalid_interval"},  # Should be int
            "logging": {"level": "INFO", "file": "client.log"},
        }

        config_manager = ConfigManager()
        with pytest.raises(ConfigValidationError) as exc_info:
            config_manager.validate_config(invalid_config)

        assert "Invalid type" in str(exc_info.value)

    def test_configuration_file_parsing_yaml(self):
        """Test YAML file parsing functionality."""
        yaml_content = """
server:
  host: yaml.example.com
  port: 7070
  timeout: 20
heartbeat:
  interval: 45
logging:
  level: WARNING
  file: yaml.log
"""

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=yaml_content)),
        ):
            config_manager = ConfigManager()
            config = config_manager.load_config("test.yaml")

            assert config["server"]["host"] == "yaml.example.com"
            assert config["server"]["port"] == 7070
            assert config["heartbeat"]["interval"] == 45
            assert config["logging"]["level"] == "WARNING"

    def test_configuration_error_messages(self):
        """Test that configuration errors provide meaningful messages."""
        config_manager = ConfigManager()

        # Test missing server section
        invalid_config = {
            "heartbeat": {"interval": 60},
            "logging": {"level": "INFO", "file": "test.log"},
        }

        with pytest.raises(ConfigValidationError) as exc_info:
            config_manager.validate_config(invalid_config)

        error_message = str(exc_info.value)
        assert "server" in error_message.lower()
        assert "missing" in error_message.lower()

    def test_get_server_config(self):
        """Test extraction of server configuration section."""
        config_manager = ConfigManager()
        full_config = config_manager.get_default_config()
        server_config = config_manager.get_server_config(full_config)

        assert "host" in server_config
        assert "port" in server_config
        assert "timeout" in server_config
        assert server_config["host"] == "localhost"
        assert server_config["port"] == 8080

    def test_get_heartbeat_config(self):
        """Test extraction of heartbeat configuration section."""
        config_manager = ConfigManager()
        full_config = config_manager.get_default_config()
        heartbeat_config = config_manager.get_heartbeat_config(full_config)

        assert "interval" in heartbeat_config
        assert heartbeat_config["interval"] == 60
