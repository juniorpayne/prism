"""
Configuration Management System for Prism Host Client (SCRUM-9)
Handles loading, validation, and management of client configuration.
"""

import yaml
import os
from typing import Dict, Any, Optional


class ConfigValidationError(Exception):
    """Custom exception for configuration validation errors."""

    pass


class ConfigManager:
    """
    Manages configuration loading, validation, and access for the host client.
    Supports YAML configuration files with fallback to default values.
    """

    def __init__(self):
        """Initialize the ConfigManager."""
        self._default_config = {
            "server": {"host": "localhost", "port": 8080, "timeout": 10},
            "heartbeat": {"interval": 60},
            "logging": {"level": "INFO", "file": "client.log"},
        }

    def load_config(self, file_path: str) -> Dict[str, Any]:
        """
        Load configuration from a YAML file.

        Args:
            file_path: Path to the configuration file

        Returns:
            Dictionary containing the configuration

        Note:
            If file doesn't exist, returns default configuration.
        """
        if not os.path.exists(file_path):
            return self.get_default_config()

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if config is None:
                return self.get_default_config()

            # Validate the loaded configuration
            self.validate_config(config)
            return config

        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Invalid YAML format: {e}")
        except Exception as e:
            raise ConfigValidationError(f"Error loading configuration: {e}")

    def get_default_config(self) -> Dict[str, Any]:
        """
        Get the default configuration.

        Returns:
            Dictionary containing default configuration values
        """
        # Return a deep copy to prevent modification of the original
        import copy

        return copy.deepcopy(self._default_config)

    def validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validate configuration structure and data types.

        Args:
            config: Configuration dictionary to validate

        Raises:
            ConfigValidationError: If configuration is invalid
        """
        # Check required top-level sections
        required_sections = ["server", "heartbeat", "logging"]
        for section in required_sections:
            if section not in config:
                raise ConfigValidationError(f"Missing required section: {section}")

        # Validate server section
        server_config = config["server"]
        required_server_fields = ["host", "port", "timeout"]
        for field in required_server_fields:
            if field not in server_config:
                raise ConfigValidationError(f"Missing required field: server.{field}")

        # Validate data types for server section
        if not isinstance(server_config["host"], str):
            raise ConfigValidationError("Invalid type for server.host: must be string")
        if not isinstance(server_config["port"], int):
            raise ConfigValidationError("Invalid type for server.port: must be integer")
        if not isinstance(server_config["timeout"], int):
            raise ConfigValidationError("Invalid type for server.timeout: must be integer")

        # Validate heartbeat section
        heartbeat_config = config["heartbeat"]
        if "interval" not in heartbeat_config:
            raise ConfigValidationError("Missing required field: heartbeat.interval")
        if not isinstance(heartbeat_config["interval"], int):
            raise ConfigValidationError("Invalid type for heartbeat.interval: must be integer")

        # Validate logging section
        logging_config = config["logging"]
        required_logging_fields = ["level"]
        for field in required_logging_fields:
            if field not in logging_config:
                raise ConfigValidationError(f"Missing required field: logging.{field}")

        if not isinstance(logging_config["level"], str):
            raise ConfigValidationError("Invalid type for logging.level: must be string")

        # File field is optional
        if "file" in logging_config and not isinstance(logging_config["file"], str):
            raise ConfigValidationError("Invalid type for logging.file: must be string")

        # Validate logging level values
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if logging_config["level"] not in valid_levels:
            raise ConfigValidationError(
                f"Invalid logging level: {logging_config['level']}. "
                f"Must be one of: {', '.join(valid_levels)}"
            )

        # Validate value ranges
        if server_config["port"] < 1 or server_config["port"] > 65535:
            raise ConfigValidationError("Invalid server.port: must be between 1 and 65535")
        if server_config["timeout"] < 1:
            raise ConfigValidationError("Invalid server.timeout: must be positive")
        if heartbeat_config["interval"] < 1:
            raise ConfigValidationError("Invalid heartbeat.interval: must be positive")

    def get_server_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract server configuration section.

        Args:
            config: Full configuration dictionary

        Returns:
            Server configuration section
        """
        return config["server"]

    def get_heartbeat_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract heartbeat configuration section.

        Args:
            config: Full configuration dictionary

        Returns:
            Heartbeat configuration section
        """
        return config["heartbeat"]

    def get_logging_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract logging configuration section.

        Args:
            config: Full configuration dictionary

        Returns:
            Logging configuration section
        """
        return config["logging"]
