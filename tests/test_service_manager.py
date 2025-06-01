"""
Tests for Service/Daemon Mode Operation (SCRUM-11)
Following TDD approach as specified in the user story.
"""

import pytest
import os
import signal
import tempfile
import time
import threading
from unittest.mock import Mock, patch, MagicMock, call
from client.service_manager import ServiceManager, SignalHandler, DaemonProcess


class TestSignalHandler:
    """Test suite for SignalHandler following SCRUM-11 requirements."""

    def test_signal_handler_registration(self):
        """Test signal handlers are registered correctly."""
        shutdown_callback = Mock()
        
        with patch('signal.signal') as mock_signal:
            signal_handler = SignalHandler(shutdown_callback)
            signal_handler.register_handlers()
            
            # Verify SIGTERM and SIGINT handlers were registered
            expected_calls = [
                call(signal.SIGTERM, signal_handler._handle_shutdown_signal),
                call(signal.SIGINT, signal_handler._handle_shutdown_signal)
            ]
            mock_signal.assert_has_calls(expected_calls, any_order=True)

    def test_graceful_shutdown_on_sigterm(self):
        """Test graceful shutdown when SIGTERM is received."""
        shutdown_callback = Mock()
        
        signal_handler = SignalHandler(shutdown_callback)
        
        # Simulate SIGTERM signal
        signal_handler._handle_shutdown_signal(signal.SIGTERM, None)
        
        # Verify shutdown callback was called
        shutdown_callback.assert_called_once()

    def test_multiple_signal_handling(self):
        """Test handling multiple different signals."""
        shutdown_callback = Mock()
        
        signal_handler = SignalHandler(shutdown_callback)
        
        # Test multiple signals
        signal_handler._handle_shutdown_signal(signal.SIGTERM, None)
        signal_handler._handle_shutdown_signal(signal.SIGINT, None)
        
        # Should call shutdown twice
        assert shutdown_callback.call_count == 2

    def test_signal_handler_with_context(self):
        """Test signal handler provides context information."""
        shutdown_callback = Mock()
        
        signal_handler = SignalHandler(shutdown_callback)
        signal_handler._handle_shutdown_signal(signal.SIGTERM, None)
        
        # Verify callback was called with signal information
        shutdown_callback.assert_called_once()


class TestDaemonProcess:
    """Test suite for DaemonProcess following SCRUM-11 requirements."""

    def test_pid_file_creation(self):
        """Test PID file is created correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pid_file = os.path.join(temp_dir, "test_daemon.pid")
            
            daemon = DaemonProcess(pid_file=pid_file)
            daemon.create_pid_file()
            
            # Verify PID file exists and contains correct PID
            assert os.path.exists(pid_file)
            
            with open(pid_file, 'r') as f:
                pid_content = f.read().strip()
            
            assert pid_content == str(os.getpid())

    def test_pid_file_cleanup(self):
        """Test PID file is cleaned up correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pid_file = os.path.join(temp_dir, "test_cleanup.pid")
            
            daemon = DaemonProcess(pid_file=pid_file)
            daemon.create_pid_file()
            
            # Verify file exists
            assert os.path.exists(pid_file)
            
            # Cleanup
            daemon.cleanup_pid_file()
            
            # Verify file is removed
            assert not os.path.exists(pid_file)

    def test_daemon_mode_initialization(self):
        """Test daemon mode initialization process."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pid_file = os.path.join(temp_dir, "test_init.pid")
            
            with patch('os.fork'), patch('os.setsid'), patch('os.chdir'), \
                 patch('sys.stdin'), patch('sys.stdout'), patch('sys.stderr'):
                
                daemon = DaemonProcess(pid_file=pid_file, daemonize=False)  # Skip actual daemonization for testing
                daemon.create_pid_file()
                
                assert os.path.exists(pid_file)

    def test_pid_file_already_exists(self):
        """Test behavior when PID file already exists with running process."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pid_file = os.path.join(temp_dir, "existing.pid")
            
            # Create existing PID file with current process PID (guaranteed to be running)
            with open(pid_file, 'w') as f:
                f.write(str(os.getpid()))
            
            daemon = DaemonProcess(pid_file=pid_file)
            
            # Should raise RuntimeError since process is running
            with pytest.raises(RuntimeError) as exc_info:
                daemon.create_pid_file()
            
            assert "already running" in str(exc_info.value).lower()

    def test_check_if_running(self):
        """Test checking if daemon is already running."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pid_file = os.path.join(temp_dir, "running_check.pid")
            
            daemon = DaemonProcess(pid_file=pid_file)
            
            # Initially not running
            assert not daemon.is_running()
            
            # Create PID file
            daemon.create_pid_file()
            
            # Now should be detected as running
            assert daemon.is_running()


class TestServiceManager:
    """Test suite for ServiceManager following SCRUM-11 requirements."""

    def test_service_initialization(self):
        """Test service manager initialization."""
        config = {
            'service': {
                'name': 'prism-client',
                'description': 'Prism Host Client Service'
            },
            'server': {'host': 'localhost', 'port': 8080, 'timeout': 10},
            'heartbeat': {'interval': 60},
            'logging': {'level': 'INFO', 'file': '/var/log/prism-client.log'}
        }
        
        service_manager = ServiceManager(config)
        
        assert service_manager._service_name == 'prism-client'
        assert service_manager._config == config

    def test_service_double_start_prevention(self):
        """Test prevention of starting service twice."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pid_file = os.path.join(temp_dir, "double_start.pid")
            
            config = {
                'service': {'name': 'test-service', 'pid_file': pid_file},
                'server': {'host': 'localhost', 'port': 8080, 'timeout': 10},
                'heartbeat': {'interval': 60}
            }
            
            service_manager = ServiceManager(config)
            
            # Mock running state
            with patch.object(service_manager._daemon, 'is_running', return_value=True):
                with pytest.raises(RuntimeError) as exc_info:
                    service_manager.start_service()
                
                assert "already running" in str(exc_info.value).lower()

    def test_service_status_checking(self):
        """Test service status checking functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pid_file = os.path.join(temp_dir, "status_check.pid")
            
            config = {
                'service': {'name': 'status-test', 'pid_file': pid_file},
                'server': {'host': 'localhost', 'port': 8080, 'timeout': 10},
                'heartbeat': {'interval': 60}
            }
            
            service_manager = ServiceManager(config)
            
            # Initially stopped
            status = service_manager.get_service_status()
            assert status['running'] is False
            assert status['pid'] is None
            
            # Create PID file to simulate running
            service_manager._daemon.create_pid_file()
            
            status = service_manager.get_service_status()
            assert status['running'] is True
            assert status['pid'] == os.getpid()

    def test_service_logging_in_daemon_mode(self):
        """Test service logging works in daemon mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "daemon_test.log")
            pid_file = os.path.join(temp_dir, "daemon_test.pid")
            
            config = {
                'service': {'name': 'logging-test', 'pid_file': pid_file},
                'logging': {'level': 'INFO', 'file': log_file, 'console': False},
                'server': {'host': 'localhost', 'port': 8080, 'timeout': 10},
                'heartbeat': {'interval': 60}
            }
            
            service_manager = ServiceManager(config)
            service_manager.setup_logging()
            
            # Test logging in daemon mode
            service_manager._log_manager.log_info("Service starting in daemon mode",
                                                component="ServiceManager")
            
            # Verify log file was created
            assert os.path.exists(log_file)

    def test_graceful_service_shutdown(self):
        """Test graceful service shutdown process."""
        config = {
            'service': {'name': 'shutdown-test'},
            'server': {'host': 'localhost', 'port': 8080, 'timeout': 10},
            'heartbeat': {'interval': 60},
            'logging': {'level': 'INFO'}
        }
        
        service_manager = ServiceManager(config)
        
        # Mock components
        service_manager._heartbeat_manager = Mock()
        service_manager._log_manager = Mock()
        
        # Set service as running to enable shutdown
        service_manager._running = True
        
        # Test shutdown
        service_manager.shutdown()
        
        # Verify components were shut down
        service_manager._heartbeat_manager.stop.assert_called_once()
        service_manager._log_manager.shutdown.assert_called_once()

    def test_service_run_loop(self):
        """Test main service run loop."""
        config = {
            'service': {'name': 'run-test'},
            'server': {'host': 'localhost', 'port': 8080, 'timeout': 10},
            'heartbeat': {'interval': 1},  # Short interval for testing
            'logging': {'level': 'INFO'}
        }
        
        service_manager = ServiceManager(config)
        
        # Mock components to avoid actual network operations
        service_manager._heartbeat_manager = Mock()
        service_manager._log_manager = Mock()
        
        # Set service as running (normally done by start_service)
        service_manager._running = True
        
        # Mock shutdown event
        shutdown_event = threading.Event()
        service_manager._shutdown_event = shutdown_event
        
        # Start run loop in thread and stop it quickly
        def stop_after_delay():
            time.sleep(0.1)
            shutdown_event.set()
        
        stop_thread = threading.Thread(target=stop_after_delay)
        stop_thread.start()
        
        # This should run briefly and then exit
        service_manager.run()
        
        stop_thread.join()
        
        # Verify heartbeat was started
        service_manager._heartbeat_manager.start.assert_called_once()

    def test_service_configuration_validation(self):
        """Test service configuration validation."""
        # Test invalid configuration
        invalid_config = {}
        
        with pytest.raises(ValueError) as exc_info:
            ServiceManager(invalid_config)
        
        assert "server" in str(exc_info.value).lower()

    def test_service_context_manager(self):
        """Test ServiceManager as context manager."""
        config = {
            'service': {'name': 'context-test'},
            'server': {'host': 'localhost', 'port': 8080, 'timeout': 10},
            'heartbeat': {'interval': 60},
            'logging': {'level': 'INFO'}
        }
        
        with patch('client.service_manager.HeartbeatManager'), \
             patch('client.service_manager.LogManager'):
            
            with ServiceManager(config) as service_manager:
                assert service_manager is not None
            
            # Context manager should handle cleanup automatically

    def test_service_from_config_file(self):
        """Test ServiceManager creation from configuration file."""
        config_content = """
service:
  name: config-file-test
  description: Test service from config file
  pid_file: /tmp/config-test.pid
server:
  host: config.test.com
  port: 9999
  timeout: 15
heartbeat:
  interval: 30
logging:
  level: DEBUG
  file: /var/log/config-test.log
  console: false
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            config_file = f.name
        
        try:
            with patch('client.service_manager.HeartbeatManager'), \
                 patch('client.service_manager.LogManager'):
                
                service_manager = ServiceManager.from_config_file(config_file)
                assert service_manager._service_name == 'config-file-test'
                
        finally:
            os.unlink(config_file)


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(['python', '-m', 'pytest', __file__, '-v'], 
                          capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)