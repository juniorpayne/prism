"""
Logging and Error Handling for Prism Host Client (SCRUM-10)
Provides comprehensive logging system with structured output and error handling.
"""

import logging
import logging.handlers
import os
import sys
import traceback
from typing import Dict, Any, Optional, Union
from client.config_manager import ConfigManager


class LogManager:
    """
    Manages comprehensive logging for the Prism client.
    Provides structured logging with configurable levels, outputs, and rotation.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the LogManager with configuration.
        
        Args:
            config: Configuration dictionary containing logging settings
        """
        logging_config = config.get('logging', {})
        
        self._level = logging_config.get('level', 'INFO').upper()
        self._log_file = logging_config.get('file')
        self._console_enabled = logging_config.get('console', True)
        self._max_size = logging_config.get('max_size', 10 * 1024 * 1024)  # 10MB default
        self._backup_count = logging_config.get('backup_count', 5)
        self._log_format = logging_config.get(
            'format', 
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
        
        self._logger = None
        self._file_handler = None
        self._console_handler = None

    @classmethod
    def from_config_file(cls, config_file: str) -> 'LogManager':
        """
        Create LogManager from configuration file.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            Configured LogManager instance
        """
        config_manager = ConfigManager()
        config = config_manager.load_config(config_file)
        return cls(config)

    def setup_logging(self) -> None:
        """
        Set up the logging system with configured handlers and formatters.
        """
        # Clear any existing component loggers
        for name in list(logging.Logger.manager.loggerDict.keys()):
            if name.startswith('prism.client.'):
                logger = logging.getLogger(name)
                logger.handlers.clear()
        
        # Create main logger
        self._logger = logging.getLogger('prism.client')
        self._logger.setLevel(getattr(logging, self._level))
        
        # Clear any existing handlers
        self._logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(self._log_format)
        
        # Setup file handler with rotation
        if self._log_file:
            self._setup_file_handler(formatter)
        
        # Setup console handler
        if self._console_enabled:
            self._setup_console_handler(formatter)
        
        # Prevent propagation to root logger
        self._logger.propagate = False

    def _setup_file_handler(self, formatter: logging.Formatter) -> None:
        """Setup rotating file handler."""
        # Ensure log directory exists
        log_dir = os.path.dirname(os.path.abspath(self._log_file))
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Create rotating file handler
        self._file_handler = logging.handlers.RotatingFileHandler(
            self._log_file,
            maxBytes=self._max_size,
            backupCount=self._backup_count,
            encoding='utf-8'
        )
        self._file_handler.setLevel(getattr(logging, self._level))
        self._file_handler.setFormatter(formatter)
        self._logger.addHandler(self._file_handler)

    def _setup_console_handler(self, formatter: logging.Formatter) -> None:
        """Setup console handler."""
        self._console_handler = logging.StreamHandler(sys.stdout)
        self._console_handler.setLevel(getattr(logging, self._level))
        self._console_handler.setFormatter(formatter)
        self._logger.addHandler(self._console_handler)

    def log_debug(self, message: str, **kwargs) -> None:
        """
        Log debug message with optional context.
        
        Args:
            message: Log message
            **kwargs: Additional context information
        """
        self._log_with_context(logging.DEBUG, message, **kwargs)

    def log_info(self, message: str, **kwargs) -> None:
        """
        Log info message with optional context.
        
        Args:
            message: Log message
            **kwargs: Additional context information
        """
        self._log_with_context(logging.INFO, message, **kwargs)

    def log_warning(self, message: str, **kwargs) -> None:
        """
        Log warning message with optional context.
        
        Args:
            message: Log message
            **kwargs: Additional context information
        """
        self._log_with_context(logging.WARNING, message, **kwargs)

    def log_error(self, message: str, error: Optional[Exception] = None, **kwargs) -> None:
        """
        Log error message with optional exception and context.
        
        Args:
            message: Log message
            error: Optional exception object
            **kwargs: Additional context information
        """
        if error:
            kwargs['exception'] = str(error)
            kwargs['exception_type'] = type(error).__name__
        
        self._log_with_context(logging.ERROR, message, **kwargs)

    def _log_with_context(self, level: int, message: str, **kwargs) -> None:
        """
        Log message with structured context information.
        
        Args:
            level: Logging level
            message: Log message
            **kwargs: Context information
        """
        if not self._logger:
            self.setup_logging()
        
        try:
            # Format context information
            context_parts = []
            component = kwargs.get('component', None)
            
            for key, value in kwargs.items():
                # Handle different types of values safely
                if value is not None:
                    if isinstance(value, (str, int, float, bool)):
                        context_parts.append(f"{key}={value}")
                    else:
                        context_parts.append(f"{key}={str(value)}")
            
            # Combine message with context
            if context_parts:
                full_message = f"{message} ({', '.join(context_parts)})"
            else:
                full_message = message
            
            # Use component-specific logger if specified
            if component:
                logger_name = f'prism.client.{component.lower()}'
                component_logger = logging.getLogger(logger_name)
                
                # Ensure component logger inherits configuration
                if not component_logger.handlers:
                    component_logger.setLevel(self._logger.level)
                    for handler in self._logger.handlers:
                        component_logger.addHandler(handler)
                    component_logger.propagate = False
                
                component_logger.log(level, full_message)
            else:
                # Use main logger
                self._logger.log(level, full_message)
            
            # Force flush to ensure immediate write
            for handler in self._logger.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
            
        except Exception as e:
            # Fallback logging to prevent crashes
            fallback_logger = logging.getLogger('prism.fallback')
            fallback_logger.error(f"Logging error: {e}")

    def rotate_logs(self) -> None:
        """
        Manually trigger log rotation.
        """
        if self._file_handler and hasattr(self._file_handler, 'doRollover'):
            self._file_handler.doRollover()

    def get_log_info(self) -> Dict[str, Any]:
        """
        Get information about current logging configuration.
        
        Returns:
            Dictionary with logging configuration details
        """
        return {
            'level': self._level,
            'file': self._log_file,
            'console': self._console_enabled,
            'max_size': self._max_size,
            'backup_count': self._backup_count,
            'format': self._log_format,
            'handlers': len(self._logger.handlers) if self._logger else 0
        }

    def shutdown(self) -> None:
        """
        Shutdown logging system and cleanup resources.
        """
        if self._logger:
            for handler in self._logger.handlers[:]:
                handler.close()
                self._logger.removeHandler(handler)


class ErrorHandler:
    """
    Handles errors and exceptions with comprehensive logging and recovery suggestions.
    """

    def __init__(self, log_manager: LogManager):
        """
        Initialize ErrorHandler with LogManager.
        
        Args:
            log_manager: LogManager instance for error logging
        """
        self._log_manager = log_manager
        
        # Error recovery suggestions
        self._recovery_suggestions = {
            ConnectionError: "Check network connectivity and server availability. Verify server host and port configuration.",
            ConnectionRefusedError: "Ensure server is running and accessible. Check firewall settings.",
            TimeoutError: "Increase connection timeout or check network latency. Server may be overloaded.",
            FileNotFoundError: "Verify file path exists and is accessible. Check file permissions.",
            PermissionError: "Check file/directory permissions. Run with appropriate privileges.",
            ValueError: "Verify input parameters are valid and within expected ranges.",
            RuntimeError: "Check system resources and dependencies. Review recent configuration changes."
        }

    def handle_exception(self, 
                        exception: Exception, 
                        component: str = "unknown",
                        operation: str = "unknown",
                        **context) -> None:
        """
        Handle exception with comprehensive logging and recovery suggestions.
        
        Args:
            exception: Exception to handle
            component: Component where error occurred
            operation: Operation that caused the error
            **context: Additional context information
        """
        try:
            # Get exception details
            exception_type = type(exception).__name__
            exception_message = str(exception)
            
            # Get traceback
            tb_lines = traceback.format_exc().splitlines()
            
            # Log the error with context
            self._log_manager.log_error(
                f"Exception in {component} during {operation}: {exception_message}",
                error=exception,
                component=component,
                operation=operation,
                exception_type=exception_type,
                traceback=tb_lines[-3:] if len(tb_lines) > 3 else tb_lines,
                **context
            )
            
            # Log recovery suggestions
            suggestions = self._get_recovery_suggestions(exception)
            if suggestions:
                self._log_manager.log_info(
                    f"Recovery suggestions for {exception_type}: {suggestions}",
                    component=component
                )
            
        except Exception as e:
            # Fallback error handling to prevent cascading failures
            print(f"Critical error in ErrorHandler: {e}", file=sys.stderr)

    def _get_recovery_suggestions(self, exception: Exception) -> str:
        """
        Get recovery suggestions for specific exception types.
        
        Args:
            exception: Exception to get suggestions for
            
        Returns:
            Recovery suggestion string
        """
        exception_type = type(exception)
        
        # Check exact type first
        if exception_type in self._recovery_suggestions:
            return self._recovery_suggestions[exception_type]
        
        # Check parent types
        for error_type, suggestion in self._recovery_suggestions.items():
            if isinstance(exception, error_type):
                return suggestion
        
        # Default suggestion
        return "Check system logs for more details. Verify configuration and network connectivity."

    def create_error_context(self, **kwargs) -> Dict[str, Any]:
        """
        Create standardized error context information.
        
        Args:
            **kwargs: Context information
            
        Returns:
            Standardized error context dictionary
        """
        context = {
            'timestamp': logging.Formatter().formatTime(logging.LogRecord(
                name='', level=0, pathname='', lineno=0, msg='', args=(), exc_info=None
            )),
            'pid': os.getpid(),
        }
        context.update(kwargs)
        return context