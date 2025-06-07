#!/usr/bin/env python3
"""
Tests for Server Configuration Management (SCRUM-18)
Test-driven development for configuration, logging, and deployment.
"""

import logging
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import yaml


class TestServerConfig:
    """Test server configuration management."""

    def test_config_class_exists(self):
        """Test that ServerConfig class exists."""
        try:
            from server.config import ServerConfig

            assert callable(ServerConfig)
        except ImportError:
            pytest.fail("ServerConfig should be importable from server.config")

    def test_config_initialization_from_dict(self):
        """Test configuration initialization from dictionary."""
        from server.config import ServerConfig

        config_dict = {
            "server": {
                "tcp_port": 8080,
                "api_port": 8081,
                "host": "0.0.0.0",
                "max_connections": 1000,
            },
            "database": {"path": "./hosts.db", "connection_pool_size": 20},
            "heartbeat": {
                "check_interval": 30,
                "timeout_multiplier": 2,
                "grace_period": 30,
                "cleanup_after_days": 30,
            },
            "logging": {
                "level": "INFO",
                "file": "./server.log",
                "max_size": 104857600,
                "backup_count": 5,
            },
        }

        config = ServerConfig(config_dict)

        assert config.server.tcp_port == 8080
        assert config.server.api_port == 8081
        assert config.server.host == "0.0.0.0"
        assert config.server.max_connections == 1000
        assert config.database.path == "hosts.db"  # Path normalization removes ./
        assert config.database.connection_pool_size == 20
        assert config.heartbeat.check_interval == 30
        assert config.logging.level == "INFO"

    def test_config_initialization_from_yaml_file(self):
        """Test configuration initialization from YAML file."""
        from server.config import ServerConfig

        # Create temporary YAML file
        config_data = {
            "server": {
                "tcp_port": 9090,
                "api_port": 9091,
                "host": "127.0.0.1",
                "max_connections": 500,
            },
            "database": {"path": "/tmp/test.db", "connection_pool_size": 10},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            yaml_file = f.name

        try:
            config = ServerConfig.from_file(yaml_file)

            assert config.server.tcp_port == 9090
            assert config.server.api_port == 9091
            assert config.server.host == "127.0.0.1"
            assert config.server.max_connections == 500
            assert config.database.path == "/tmp/test.db"
            assert config.database.connection_pool_size == 10
        finally:
            os.unlink(yaml_file)

    def test_config_defaults(self):
        """Test that configuration provides sensible defaults."""
        from server.config import ServerConfig

        config = ServerConfig({})

        # Test server defaults
        assert isinstance(config.server.tcp_port, int)
        assert isinstance(config.server.api_port, int)
        assert isinstance(config.server.host, str)
        assert isinstance(config.server.max_connections, int)

        # Test database defaults
        assert isinstance(config.database.path, str)
        assert isinstance(config.database.connection_pool_size, int)

        # Test heartbeat defaults
        assert isinstance(config.heartbeat.check_interval, int)
        assert isinstance(config.heartbeat.timeout_multiplier, int)

        # Test logging defaults
        assert isinstance(config.logging.level, str)
        assert config.logging.level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    def test_config_validation(self):
        """Test configuration validation."""
        from server.config import ConfigValidationError, ServerConfig

        # Test invalid port
        with pytest.raises(ConfigValidationError):
            ServerConfig({"server": {"tcp_port": -1}})  # Invalid port

        # Test invalid log level
        with pytest.raises(ConfigValidationError):
            ServerConfig({"logging": {"level": "INVALID"}})  # Invalid log level

        # Test invalid connection pool size
        with pytest.raises(ConfigValidationError):
            ServerConfig({"database": {"connection_pool_size": 0}})  # Invalid pool size

    def test_config_environment_variable_overrides(self):
        """Test configuration overrides via environment variables."""
        from server.config import ServerConfig

        config_dict = {
            "server": {"tcp_port": 8080, "host": "0.0.0.0"},
            "database": {"path": "./hosts.db"},
        }

        # Test environment variable overrides
        with patch.dict(
            os.environ,
            {
                "PRISM_SERVER_TCP_PORT": "9999",
                "PRISM_SERVER_HOST": "127.0.0.1",
                "PRISM_DATABASE_PATH": "/custom/path.db",
            },
        ):
            config = ServerConfig(config_dict)

            assert config.server.tcp_port == 9999
            assert config.server.host == "127.0.0.1"
            assert config.database.path == "/custom/path.db"

    def test_config_to_dict(self):
        """Test converting configuration to dictionary."""
        from server.config import ServerConfig

        config_dict = {
            "server": {"tcp_port": 8080, "api_port": 8081},
            "database": {"path": "./hosts.db"},
        }

        config = ServerConfig(config_dict)
        result_dict = config.to_dict()

        assert isinstance(result_dict, dict)
        assert "server" in result_dict
        assert "database" in result_dict
        assert result_dict["server"]["tcp_port"] == 8080
        assert result_dict["server"]["api_port"] == 8081

    def test_config_merge_with_defaults(self):
        """Test configuration merging with defaults."""
        from server.config import ServerConfig

        # Provide partial configuration
        partial_config = {"server": {"tcp_port": 9999}}  # Override only one field

        config = ServerConfig(partial_config)

        # Should have our override
        assert config.server.tcp_port == 9999

        # Should have defaults for other fields
        assert hasattr(config.server, "api_port")
        assert hasattr(config.server, "host")
        assert hasattr(config.server, "max_connections")

    def test_config_file_not_found(self):
        """Test handling of missing configuration file."""
        from server.config import ConfigFileError, ServerConfig

        with pytest.raises(ConfigFileError):
            ServerConfig.from_file("/nonexistent/config.yaml")

    def test_config_invalid_yaml(self):
        """Test handling of invalid YAML file."""
        from server.config import ConfigFileError, ServerConfig

        # Create file with invalid YAML
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            invalid_yaml_file = f.name

        try:
            with pytest.raises(ConfigFileError):
                ServerConfig.from_file(invalid_yaml_file)
        finally:
            os.unlink(invalid_yaml_file)


class TestLoggingSetup:
    """Test logging configuration and setup."""

    def test_logging_setup_class_exists(self):
        """Test that LoggingSetup class exists."""
        try:
            from server.logging_setup import LoggingSetup

            assert callable(LoggingSetup)
        except ImportError:
            pytest.fail("LoggingSetup should be importable from server.logging_setup")

    def test_logging_configuration(self):
        """Test logging configuration setup."""
        from server.logging_setup import LoggingSetup

        logging_config = {
            "level": "INFO",
            "file": "./test.log",
            "max_size": 1048576,  # 1MB
            "backup_count": 3,
        }

        log_setup = LoggingSetup(logging_config)

        assert log_setup.level == logging.INFO
        assert log_setup.file == "./test.log"
        assert log_setup.max_size == 1048576
        assert log_setup.backup_count == 3

    def test_logging_setup_configure(self):
        """Test logging setup configuration."""
        from server.logging_setup import LoggingSetup

        logging_config = {
            "level": "DEBUG",
            "file": "./test.log",
            "max_size": 1048576,
            "backup_count": 2,
        }

        log_setup = LoggingSetup(logging_config)
        log_setup.configure()

        # Verify logger is configured
        logger = logging.getLogger("server")
        assert logger.level == logging.DEBUG

    def test_logging_level_validation(self):
        """Test logging level validation."""
        from server.logging_setup import LoggingConfigError, LoggingSetup

        # Test invalid log level
        with pytest.raises(LoggingConfigError):
            LoggingSetup({"level": "INVALID_LEVEL"})

    def test_logging_file_rotation(self):
        """Test log file rotation configuration."""
        from server.logging_setup import LoggingSetup

        logging_config = {
            "level": "INFO",
            "file": "./rotate.log",
            "max_size": 1024,  # Small size for testing
            "backup_count": 5,
        }

        log_setup = LoggingSetup(logging_config)
        log_setup.configure()

        # Test that rotating file handler is configured
        # Check root logger since that's where file handler is added
        root_logger = logging.getLogger()
        handlers = [h for h in root_logger.handlers if hasattr(h, "maxBytes")]
        assert len(handlers) > 0
        assert handlers[0].maxBytes == 1024


class TestSignalHandlers:
    """Test signal handling for graceful shutdown."""

    def test_signal_handler_class_exists(self):
        """Test that SignalHandler class exists."""
        try:
            from server.signal_handlers import SignalHandler

            assert callable(SignalHandler)
        except ImportError:
            pytest.fail("SignalHandler should be importable from server.signal_handlers")

    def test_signal_handler_initialization(self):
        """Test signal handler initialization."""
        from server.signal_handlers import SignalHandler

        shutdown_callback = MagicMock()
        handler = SignalHandler(shutdown_callback)

        assert handler.shutdown_callback == shutdown_callback
        assert not handler.shutdown_requested

    def test_signal_handler_setup(self):
        """Test signal handler setup."""
        import signal

        from server.signal_handlers import SignalHandler

        shutdown_callback = MagicMock()
        handler = SignalHandler(shutdown_callback)

        # Setup signal handlers
        handler.setup()

        # Verify signal handlers are registered
        assert signal.signal(signal.SIGTERM, signal.SIG_DFL) != signal.SIG_DFL
        assert signal.signal(signal.SIGINT, signal.SIG_DFL) != signal.SIG_DFL

    def test_signal_handler_graceful_shutdown(self):
        """Test graceful shutdown signal handling."""
        from server.signal_handlers import SignalHandler

        shutdown_callback = MagicMock()
        handler = SignalHandler(shutdown_callback)

        # Simulate signal
        handler.handle_shutdown_signal(15, None)  # SIGTERM

        assert handler.shutdown_requested
        shutdown_callback.assert_called_once()

    def test_signal_handler_multiple_signals(self):
        """Test handling multiple shutdown signals."""
        from server.signal_handlers import SignalHandler

        shutdown_callback = MagicMock()
        handler = SignalHandler(shutdown_callback)

        # First signal
        handler.handle_shutdown_signal(15, None)
        assert shutdown_callback.call_count == 1

        # Second signal should not call callback again
        handler.handle_shutdown_signal(2, None)  # SIGINT
        assert shutdown_callback.call_count == 1


class TestMainServer:
    """Test main server application."""

    def test_main_server_class_exists(self):
        """Test that main server application exists."""
        try:
            from server.main import main

            assert callable(main)
        except ImportError:
            pytest.fail("main function should be importable from server.main")

    def test_command_line_argument_parsing(self):
        """Test command line argument parsing."""
        from server.main import parse_arguments

        # Test default arguments
        args = parse_arguments(["--config", "test.yaml"])
        assert args.config == "test.yaml"

    def test_config_file_parameter(self):
        """Test --config parameter handling."""
        from server.main import parse_arguments

        args = parse_arguments(["--config", "/path/to/config.yaml"])
        assert args.config == "/path/to/config.yaml"

    def test_server_startup_sequence(self):
        """Test server startup sequence."""
        from server.main import ServerApplication

        config_dict = {
            "server": {"tcp_port": 8080, "api_port": 8081},
            "database": {"path": ":memory:"},
            "logging": {"level": "INFO"},
        }

        app = ServerApplication(config_dict)

        assert app.config is not None
        assert hasattr(app, "tcp_server")
        assert hasattr(app, "api_server")

    def test_server_graceful_shutdown(self):
        """Test server graceful shutdown."""
        from server.main import ServerApplication

        config_dict = {
            "server": {"tcp_port": 8080, "api_port": 8081},
            "database": {"path": ":memory:"},
        }

        app = ServerApplication(config_dict)

        # Test shutdown method exists and is callable
        assert hasattr(app, "shutdown")
        assert callable(app.shutdown)


class TestConfigValidation:
    """Test configuration validation logic."""

    def test_port_validation(self):
        """Test port number validation."""
        from server.config import validate_port

        # Valid ports
        assert validate_port(8080) == 8080
        assert validate_port(80) == 80
        assert validate_port(65535) == 65535

        # Invalid ports
        with pytest.raises(ValueError):
            validate_port(-1)

        with pytest.raises(ValueError):
            validate_port(0)

        with pytest.raises(ValueError):
            validate_port(65536)

    def test_path_validation(self):
        """Test file path validation."""
        from server.config import validate_path

        # Valid paths (normalization removes ./)
        assert validate_path("./test.db") == "test.db"
        assert validate_path("/tmp/hosts.db") == "/tmp/hosts.db"

        # Test path normalization
        assert validate_path("~/test.db").startswith("/")

    def test_log_level_validation(self):
        """Test log level validation."""
        from server.config import validate_log_level

        # Valid levels
        assert validate_log_level("DEBUG") == "DEBUG"
        assert validate_log_level("INFO") == "INFO"
        assert validate_log_level("WARNING") == "WARNING"
        assert validate_log_level("ERROR") == "ERROR"
        assert validate_log_level("CRITICAL") == "CRITICAL"

        # Case insensitive
        assert validate_log_level("info") == "INFO"
        assert validate_log_level("Debug") == "DEBUG"

        # Invalid levels
        with pytest.raises(ValueError):
            validate_log_level("INVALID")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
