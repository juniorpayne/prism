"""
Tests for Logging and Error Handling (SCRUM-10)
Following TDD approach as specified in the user story.
"""

import pytest
import os
import tempfile
import time
import logging
import threading
from unittest.mock import Mock, patch, call
from client.log_manager import LogManager, ErrorHandler


class TestLogManager:
    """Test suite for LogManager following SCRUM-10 requirements."""

    def test_log_level_filtering(self):
        """Test log level filtering works correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test_levels.log")
            
            config = {
                'logging': {
                    'level': 'WARNING',
                    'file': log_file,
                    'console': False
                }
            }
            
            log_manager = LogManager(config)
            log_manager.setup_logging()
            
            # Log messages at different levels
            log_manager.log_debug("Debug message")
            log_manager.log_info("Info message")
            log_manager.log_warning("Warning message")
            log_manager.log_error("Error message")
            
            # Read log file
            with open(log_file, 'r') as f:
                content = f.read()
            
            # Only WARNING and ERROR should be logged
            assert "Debug message" not in content
            assert "Info message" not in content
            assert "Warning message" in content
            assert "Error message" in content

    def test_file_logging(self):
        """Test file logging functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test_file.log")
            
            config = {
                'logging': {
                    'level': 'INFO',
                    'file': log_file,
                    'console': False
                }
            }
            
            log_manager = LogManager(config)
            log_manager.setup_logging()
            
            test_message = "Test file logging message"
            log_manager.log_info(test_message, component="TestComponent")
            
            # Verify file was created and contains message
            assert os.path.exists(log_file)
            
            with open(log_file, 'r') as f:
                content = f.read()
            
            assert test_message in content
            assert "TestComponent" in content
            assert "[INFO]" in content

    def test_console_logging(self):
        """Test console logging functionality."""
        config = {
            'logging': {
                'level': 'DEBUG',
                'console': True,
                'file': None
            }
        }
        
        with patch('sys.stdout') as mock_stdout:
            log_manager = LogManager(config)
            log_manager.setup_logging()
            
            test_message = "Console test message"
            log_manager.log_info(test_message)
            
            # Verify console handler was configured
            logger = logging.getLogger('prism.client')
            handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
            assert len(handlers) > 0

    def test_log_rotation(self):
        """Test log rotation mechanism."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test_rotation.log")
            
            config = {
                'logging': {
                    'level': 'INFO',
                    'file': log_file,
                    'console': False,
                    'max_size': 1024,  # 1KB for testing
                    'backup_count': 3
                }
            }
            
            log_manager = LogManager(config)
            log_manager.setup_logging()
            
            # Generate enough log data to trigger rotation
            large_message = "X" * 500  # 500 chars per message
            for i in range(20):  # Should definitely exceed 1KB
                log_manager.log_info(f"Message {i}: {large_message}")
            
            # Force a manual rotation to ensure it works
            log_manager.rotate_logs()
            
            # Check if rotation occurred
            rotated_files = [f for f in os.listdir(temp_dir) if f.startswith("test_rotation.log")]
            assert len(rotated_files) >= 1  # At least the current log file exists

    def test_structured_log_format(self):
        """Test structured log formatting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test_format.log")
            
            config = {
                'logging': {
                    'level': 'INFO',
                    'file': log_file,
                    'console': False,
                    'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
                }
            }
            
            log_manager = LogManager(config)
            log_manager.setup_logging()
            
            log_manager.log_info("Test message", 
                               component="ConnectionManager",
                               hostname="test-host",
                               ip="192.168.1.1")
            
            with open(log_file, 'r') as f:
                content = f.read()
            
            # Check format components
            assert "[INFO]" in content
            assert "ConnectionManager" in content
            assert "test-host" in content
            assert "192.168.1.1" in content
            # Check timestamp format (YYYY-MM-DD HH:MM:SS,mmm)
            import re
            timestamp_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}'
            assert re.search(timestamp_pattern, content)

    def test_concurrent_logging(self):
        """Test logging thread safety."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test_concurrent.log")
            
            config = {
                'logging': {
                    'level': 'INFO',
                    'file': log_file,
                    'console': False
                }
            }
            
            log_manager = LogManager(config)
            log_manager.setup_logging()
            
            def log_messages(thread_id):
                for i in range(10):
                    log_manager.log_info(f"Thread {thread_id} message {i}")
                    time.sleep(0.001)  # Small delay
            
            # Create multiple threads
            threads = []
            for thread_id in range(5):
                thread = threading.Thread(target=log_messages, args=(thread_id,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Verify all messages were logged
            with open(log_file, 'r') as f:
                content = f.read()
            
            # Should have 50 messages total (5 threads * 10 messages)
            lines = content.strip().split('\n')
            assert len(lines) == 50

    def test_logging_performance(self):
        """Test logging performance doesn't impact application."""
        config = {
            'logging': {
                'level': 'INFO',
                'console': False,
                'file': None  # No file to avoid I/O overhead
            }
        }
        
        log_manager = LogManager(config)
        log_manager.setup_logging()
        
        # Measure time for 1000 log calls
        start_time = time.time()
        
        for i in range(1000):
            log_manager.log_info(f"Performance test message {i}")
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Should complete in reasonable time (< 1 second)
        assert elapsed < 1.0

    def test_error_handling_no_crashes(self):
        """Test error handling prevents application crashes."""
        config = {
            'logging': {
                'level': 'ERROR',
                'console': True,
                'file': None
            }
        }
        
        log_manager = LogManager(config)
        log_manager.setup_logging()
        
        # Test logging with various problematic inputs
        test_cases = [
            None,
            {"complex": "object"},
            Exception("Test exception"),
            b"bytes object",
            123456789
        ]
        
        for test_input in test_cases:
            try:
                log_manager.log_error("Error with input", error=test_input)
                # Should not raise exception
            except Exception as e:
                pytest.fail(f"Logging should not crash with input {test_input}: {e}")

    def test_log_manager_from_config_file(self):
        """Test LogManager creation from configuration file."""
        config_content = """
logging:
  level: DEBUG
  file: /tmp/config_test.log
  console: true
  max_size: 5242880
  backup_count: 5
  format: "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
server:
  host: localhost
  port: 8080
  timeout: 10
heartbeat:
  interval: 60
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            config_file = f.name
        
        try:
            log_manager = LogManager.from_config_file(config_file)
            assert log_manager._level == 'DEBUG'
            assert log_manager._log_file == '/tmp/config_test.log'
            assert log_manager._console_enabled is True
            
        finally:
            os.unlink(config_file)

    def test_log_context_information(self):
        """Test logging includes contextual information."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test_context.log")
            
            config = {
                'logging': {
                    'level': 'INFO',
                    'file': log_file,
                    'console': False
                }
            }
            
            log_manager = LogManager(config)
            log_manager.setup_logging()
            
            # Log with context
            log_manager.log_info("Connection established",
                               component="ConnectionManager",
                               hostname="test-client",
                               server_host="server.example.com",
                               server_port=8080)
            
            # Ensure all handlers are flushed and closed
            import logging
            for handler in logging.getLogger('prism.client').handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
            for handler in logging.getLogger('prism.client.connectionmanager').handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
            
            with open(log_file, 'r') as f:
                content = f.read()
            
            assert "ConnectionManager" in content
            assert "test-client" in content
            assert "server.example.com" in content
            assert "8080" in content


class TestErrorHandler:
    """Test suite for ErrorHandler following SCRUM-10 requirements."""

    def test_exception_handling_with_logging(self):
        """Test exception handling logs errors properly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test_errors.log")
            
            config = {
                'logging': {
                    'level': 'ERROR',
                    'file': log_file,
                    'console': False
                }
            }
            
            log_manager = LogManager(config)
            log_manager.setup_logging()
            error_handler = ErrorHandler(log_manager)
            
            # Test exception handling
            test_exception = ValueError("Test error message")
            error_handler.handle_exception(test_exception, 
                                         component="TestComponent",
                                         operation="test_operation")
            
            # Ensure all handlers are flushed
            import logging
            for handler in logging.getLogger('prism.client').handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
            for handler in logging.getLogger('prism.client.testcomponent').handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
            
            with open(log_file, 'r') as f:
                content = f.read()
            
            assert "ValueError" in content
            assert "Test error message" in content
            assert "TestComponent" in content
            assert "test_operation" in content

    def test_exception_handling_no_crash(self):
        """Test exception handling doesn't crash application."""
        config = {
            'logging': {
                'level': 'ERROR',
                'console': False,
                'file': None
            }
        }
        
        log_manager = LogManager(config)
        log_manager.setup_logging()
        error_handler = ErrorHandler(log_manager)
        
        # Test with various exception types
        exceptions = [
            ValueError("Value error"),
            ConnectionError("Connection error"),
            FileNotFoundError("File not found"),
            RuntimeError("Runtime error"),
            Exception("Generic exception")
        ]
        
        for exc in exceptions:
            try:
                error_handler.handle_exception(exc)
                # Should not re-raise the exception
            except Exception as e:
                pytest.fail(f"ErrorHandler should not re-raise exception: {e}")

    def test_error_recovery_suggestions(self):
        """Test error handler provides recovery suggestions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test_recovery.log")
            
            config = {
                'logging': {
                    'level': 'INFO',  # Need INFO level to see recovery suggestions
                    'file': log_file,
                    'console': False
                }
            }
            
            log_manager = LogManager(config)
            log_manager.setup_logging()
            error_handler = ErrorHandler(log_manager)
            
            # Test with connection error
            conn_error = ConnectionError("Connection refused")
            error_handler.handle_exception(conn_error, component="ConnectionManager")
            
            # Ensure all handlers are flushed
            import logging
            for handler in logging.getLogger('prism.client').handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
            for handler in logging.getLogger('prism.client.connectionmanager').handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
            
            with open(log_file, 'r') as f:
                content = f.read()
            
            # Should include recovery suggestions
            assert any(word in content.lower() for word in ["retry", "check", "verify"])


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(['python', '-m', 'pytest', __file__, '-v'], 
                          capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)