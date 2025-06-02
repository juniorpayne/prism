#!/usr/bin/env python3
"""
Logging Configuration and Setup (SCRUM-18)
Structured logging with rotation and proper formatting.
"""

import logging
import logging.handlers
import os
import sys
from typing import Dict, Any


class LoggingConfigError(Exception):
    """Exception raised for logging configuration errors."""
    pass


class LoggingSetup:
    """
    Logging configuration and setup manager.
    
    Handles log level configuration, file rotation, and structured formatting.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize logging setup.
        
        Args:
            config: Logging configuration dictionary
        """
        self.level_str = config.get('level', 'INFO')
        self.file = config.get('file', './server.log')
        self.max_size = config.get('max_size', 104857600)  # 100MB
        self.backup_count = config.get('backup_count', 5)
        
        # Validate and convert log level
        self.level = self._validate_log_level(self.level_str)
        
        # Validate other parameters
        if not isinstance(self.max_size, int) or self.max_size <= 0:
            raise LoggingConfigError("max_size must be a positive integer")
        
        if not isinstance(self.backup_count, int) or self.backup_count < 0:
            raise LoggingConfigError("backup_count must be a non-negative integer")
    
    def _validate_log_level(self, level: str) -> int:
        """
        Validate and convert log level string to logging constant.
        
        Args:
            level: Log level string
            
        Returns:
            Logging level constant
            
        Raises:
            LoggingConfigError: If log level is invalid
        """
        if not isinstance(level, str):
            raise LoggingConfigError("Log level must be a string")
        
        level_upper = level.upper()
        level_mapping = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        if level_upper not in level_mapping:
            raise LoggingConfigError(
                f"Invalid log level: {level}. Must be one of: {list(level_mapping.keys())}"
            )
        
        return level_mapping[level_upper]
    
    def configure(self) -> None:
        """Configure logging with the specified settings."""
        # Create root logger for the server
        root_logger = logging.getLogger()
        root_logger.setLevel(self.level)
        
        # Clear any existing handlers
        root_logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # Add file handler with rotation
        try:
            # Ensure log directory exists
            log_dir = os.path.dirname(os.path.abspath(self.file))
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                filename=self.file,
                maxBytes=self.max_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(self.level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
        except (IOError, OSError) as e:
            # If file logging fails, log warning but continue
            root_logger.warning(f"Failed to setup file logging: {e}")
        
        # Configure specific loggers
        self._configure_server_loggers()
        
        # Log configuration success
        logging.info(f"Logging configured: level={self.level_str}, file={self.file}")
    
    def _configure_server_loggers(self) -> None:
        """Configure specific loggers for server components."""
        # Server components logger
        server_logger = logging.getLogger('server')
        server_logger.setLevel(self.level)
        
        # Database logger (less verbose by default)
        db_logger = logging.getLogger('server.database')
        db_logger.setLevel(max(self.level, logging.INFO))
        
        # API logger
        api_logger = logging.getLogger('server.api')
        api_logger.setLevel(self.level)
        
        # TCP server logger
        tcp_logger = logging.getLogger('server.tcp')
        tcp_logger.setLevel(self.level)
        
        # Heartbeat monitor logger
        heartbeat_logger = logging.getLogger('server.heartbeat')
        heartbeat_logger.setLevel(self.level)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger with the specified name.
        
        Args:
            name: Logger name
            
        Returns:
            Configured logger instance
        """
        return logging.getLogger(f'server.{name}')
    
    def set_level(self, level: str) -> None:
        """
        Dynamically change logging level.
        
        Args:
            level: New log level string
        """
        new_level = self._validate_log_level(level)
        
        # Update all handlers
        root_logger = logging.getLogger()
        root_logger.setLevel(new_level)
        
        for handler in root_logger.handlers:
            handler.setLevel(new_level)
        
        self.level = new_level
        self.level_str = level.upper()
        
        logging.info(f"Log level changed to: {self.level_str}")
    
    def get_log_stats(self) -> Dict[str, Any]:
        """
        Get logging statistics and configuration.
        
        Returns:
            Dictionary with logging information
        """
        stats = {
            'level': self.level_str,
            'file': self.file,
            'max_size': self.max_size,
            'backup_count': self.backup_count,
            'handlers': []
        }
        
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            handler_info = {
                'type': type(handler).__name__,
                'level': logging.getLevelName(handler.level)
            }
            
            if hasattr(handler, 'baseFilename'):
                handler_info['file'] = handler.baseFilename
            
            if hasattr(handler, 'maxBytes'):
                handler_info['max_bytes'] = handler.maxBytes
                handler_info['backup_count'] = handler.backupCount
            
            stats['handlers'].append(handler_info)
        
        return stats


def setup_logging(config: Dict[str, Any]) -> LoggingSetup:
    """
    Setup logging with the given configuration.
    
    Args:
        config: Logging configuration dictionary
        
    Returns:
        Configured LoggingSetup instance
    """
    log_setup = LoggingSetup(config)
    log_setup.configure()
    return log_setup