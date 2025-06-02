#!/usr/bin/env python3
"""
Server Configuration Management (SCRUM-18)
YAML-based configuration system with validation and environment overrides.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Exception raised for configuration validation errors."""
    pass


class ConfigFileError(Exception):
    """Exception raised for configuration file errors."""
    pass


def validate_port(port: int) -> int:
    """
    Validate port number.
    
    Args:
        port: Port number to validate
        
    Returns:
        Validated port number
        
    Raises:
        ValueError: If port is invalid
    """
    if not isinstance(port, int) or port <= 0 or port > 65535:
        raise ValueError(f"Invalid port number: {port}. Must be between 1 and 65535")
    return port


def validate_path(path: str) -> str:
    """
    Validate and normalize file path.
    
    Args:
        path: File path to validate
        
    Returns:
        Normalized path
    """
    if not isinstance(path, str) or not path.strip():
        raise ValueError("Path must be a non-empty string")
    
    # Expand user home directory
    expanded_path = os.path.expanduser(path)
    
    # Normalize path
    normalized_path = os.path.normpath(expanded_path)
    
    return normalized_path


def validate_log_level(level: str) -> str:
    """
    Validate log level.
    
    Args:
        level: Log level to validate
        
    Returns:
        Validated log level (uppercase)
        
    Raises:
        ValueError: If log level is invalid
    """
    if not isinstance(level, str):
        raise ValueError("Log level must be a string")
    
    level_upper = level.upper()
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    
    if level_upper not in valid_levels:
        raise ValueError(f"Invalid log level: {level}. Must be one of: {valid_levels}")
    
    return level_upper


@dataclass
class ServerConfigSection:
    """Server configuration section."""
    tcp_port: int = 8080
    api_port: int = 8081
    host: str = "0.0.0.0"
    max_connections: int = 1000
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        try:
            self.tcp_port = validate_port(self.tcp_port)
            self.api_port = validate_port(self.api_port)
        except ValueError as e:
            raise ConfigValidationError(str(e))
        
        if not isinstance(self.host, str):
            raise ConfigValidationError("Host must be a string")
        
        if not isinstance(self.max_connections, int) or self.max_connections <= 0:
            raise ConfigValidationError("max_connections must be a positive integer")


@dataclass
class DatabaseConfig:
    """Database configuration section."""
    path: str = "./hosts.db"
    connection_pool_size: int = 20
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        try:
            self.path = validate_path(self.path)
        except ValueError as e:
            raise ConfigValidationError(str(e))
        
        if not isinstance(self.connection_pool_size, int) or self.connection_pool_size <= 0:
            raise ConfigValidationError("connection_pool_size must be a positive integer")


@dataclass
class HeartbeatConfig:
    """Heartbeat configuration section."""
    check_interval: int = 30
    timeout_multiplier: int = 2
    grace_period: int = 30
    cleanup_after_days: int = 30
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not isinstance(self.check_interval, int) or self.check_interval <= 0:
            raise ConfigValidationError("check_interval must be a positive integer")
        
        if not isinstance(self.timeout_multiplier, int) or self.timeout_multiplier <= 0:
            raise ConfigValidationError("timeout_multiplier must be a positive integer")
        
        if not isinstance(self.grace_period, int) or self.grace_period < 0:
            raise ConfigValidationError("grace_period must be a non-negative integer")
        
        if not isinstance(self.cleanup_after_days, int) or self.cleanup_after_days <= 0:
            raise ConfigValidationError("cleanup_after_days must be a positive integer")


@dataclass
class LoggingConfig:
    """Logging configuration section."""
    level: str = "INFO"
    file: str = "./server.log"
    max_size: int = 104857600  # 100MB
    backup_count: int = 5
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        try:
            self.level = validate_log_level(self.level)
            self.file = validate_path(self.file)
        except ValueError as e:
            raise ConfigValidationError(str(e))
        
        if not isinstance(self.max_size, int) or self.max_size <= 0:
            raise ConfigValidationError("max_size must be a positive integer")
        
        if not isinstance(self.backup_count, int) or self.backup_count < 0:
            raise ConfigValidationError("backup_count must be a non-negative integer")


@dataclass
class APIConfig:
    """API configuration section."""
    enable_cors: bool = True
    cors_origins: list = field(default_factory=lambda: [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080"
    ])
    request_timeout: int = 30
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not isinstance(self.enable_cors, bool):
            raise ConfigValidationError("enable_cors must be a boolean")
        
        if not isinstance(self.cors_origins, list):
            raise ConfigValidationError("cors_origins must be a list")
        
        if not isinstance(self.request_timeout, int) or self.request_timeout <= 0:
            raise ConfigValidationError("request_timeout must be a positive integer")


class ServerConfiguration:
    """
    Main server configuration management class.
    
    Handles YAML configuration loading, validation, and environment variable overrides.
    """
    
    def __init__(self, config_dict: Dict[str, Any]):
        """
        Initialize configuration from dictionary.
        
        Args:
            config_dict: Configuration dictionary
        """
        # Apply environment variable overrides
        config_dict = self._apply_environment_overrides(config_dict)
        
        # Initialize configuration sections
        try:
            self.server = ServerConfigSection(**config_dict.get('server', {}))
            self.database = DatabaseConfig(**config_dict.get('database', {}))
            self.heartbeat = HeartbeatConfig(**config_dict.get('heartbeat', {}))
            self.logging = LoggingConfig(**config_dict.get('logging', {}))
            self.api = APIConfig(**config_dict.get('api', {}))
            
        except TypeError as e:
            raise ConfigValidationError(f"Configuration initialization error: {e}")
        
        logger.info("Server configuration initialized successfully")
    
    @classmethod
    def from_file(cls, config_file: str) -> 'ServerConfiguration':
        """
        Load configuration from YAML file.
        
        Args:
            config_file: Path to YAML configuration file
            
        Returns:
            ServerConfiguration instance
            
        Raises:
            ConfigFileError: If file cannot be loaded or parsed
        """
        try:
            if not os.path.exists(config_file):
                raise ConfigFileError(f"Configuration file not found: {config_file}")
            
            with open(config_file, 'r') as f:
                config_dict = yaml.safe_load(f) or {}
            
            logger.info(f"Configuration loaded from file: {config_file}")
            return cls(config_dict)
            
        except yaml.YAMLError as e:
            raise ConfigFileError(f"Invalid YAML in configuration file {config_file}: {e}")
        except IOError as e:
            raise ConfigFileError(f"Error reading configuration file {config_file}: {e}")
    
    def _apply_environment_overrides(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration.
        
        Environment variables follow the pattern: PRISM_SECTION_KEY
        
        Args:
            config_dict: Original configuration dictionary
            
        Returns:
            Configuration dictionary with environment overrides applied
        """
        # Make a deep copy to avoid modifying original
        import copy
        result = copy.deepcopy(config_dict)
        
        # Environment variable mappings
        env_mappings = {
            'PRISM_SERVER_TCP_PORT': ('server', 'tcp_port', int),
            'PRISM_SERVER_API_PORT': ('server', 'api_port', int),
            'PRISM_SERVER_HOST': ('server', 'host', str),
            'PRISM_SERVER_MAX_CONNECTIONS': ('server', 'max_connections', int),
            'PRISM_DATABASE_PATH': ('database', 'path', str),
            'PRISM_DATABASE_CONNECTION_POOL_SIZE': ('database', 'connection_pool_size', int),
            'PRISM_HEARTBEAT_CHECK_INTERVAL': ('heartbeat', 'check_interval', int),
            'PRISM_HEARTBEAT_TIMEOUT_MULTIPLIER': ('heartbeat', 'timeout_multiplier', int),
            'PRISM_HEARTBEAT_GRACE_PERIOD': ('heartbeat', 'grace_period', int),
            'PRISM_LOGGING_LEVEL': ('logging', 'level', str),
            'PRISM_LOGGING_FILE': ('logging', 'file', str),
            'PRISM_LOGGING_MAX_SIZE': ('logging', 'max_size', int),
            'PRISM_LOGGING_BACKUP_COUNT': ('logging', 'backup_count', int),
        }
        
        for env_var, (section, key, value_type) in env_mappings.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                # Ensure section exists
                if section not in result:
                    result[section] = {}
                
                # Convert value to appropriate type
                try:
                    if value_type == int:
                        result[section][key] = int(env_value)
                    elif value_type == bool:
                        result[section][key] = env_value.lower() in ('true', '1', 'yes', 'on')
                    else:
                        result[section][key] = env_value
                    
                    logger.info(f"Applied environment override: {env_var}={env_value}")
                    
                except ValueError as e:
                    logger.warning(f"Invalid environment variable {env_var}={env_value}: {e}")
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Configuration as dictionary
        """
        return {
            'server': {
                'tcp_port': self.server.tcp_port,
                'api_port': self.server.api_port,
                'host': self.server.host,
                'max_connections': self.server.max_connections
            },
            'database': {
                'path': self.database.path,
                'connection_pool_size': self.database.connection_pool_size
            },
            'heartbeat': {
                'check_interval': self.heartbeat.check_interval,
                'timeout_multiplier': self.heartbeat.timeout_multiplier,
                'grace_period': self.heartbeat.grace_period,
                'cleanup_after_days': self.heartbeat.cleanup_after_days
            },
            'logging': {
                'level': self.logging.level,
                'file': self.logging.file,
                'max_size': self.logging.max_size,
                'backup_count': self.logging.backup_count
            },
            'api': {
                'enable_cors': self.api.enable_cors,
                'cors_origins': self.api.cors_origins,
                'request_timeout': self.api.request_timeout
            }
        }
    
    def validate(self) -> bool:
        """
        Validate entire configuration.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ConfigValidationError: If configuration is invalid
        """
        # Validation is performed during initialization via __post_init__
        # This method can be extended for cross-section validation
        
        # Check for port conflicts
        if self.server.tcp_port == self.server.api_port:
            raise ConfigValidationError("TCP port and API port cannot be the same")
        
        logger.info("Configuration validation completed successfully")
        return True


# Convenience alias for backward compatibility
ServerConfig = ServerConfiguration