"""
Service/Daemon Mode Operation for Prism Host Client (SCRUM-11)
Provides service/daemon functionality for background operation and system integration.
"""

import os
import signal
import sys
import tempfile
import threading
import time
import logging
from typing import Dict, Any, Optional, Callable
from client.config_manager import ConfigManager
from client.heartbeat_manager import HeartbeatManager
from client.log_manager import LogManager, ErrorHandler


class SignalHandler:
    """
    Handles system signals for graceful service shutdown.
    """

    def __init__(self, shutdown_callback: Callable[[], None]):
        """
        Initialize SignalHandler with shutdown callback.

        Args:
            shutdown_callback: Function to call when shutdown signal received
        """
        self._shutdown_callback = shutdown_callback
        self._logger = logging.getLogger(__name__)

    def register_handlers(self) -> None:
        """
        Register signal handlers for graceful shutdown.
        """
        # Register handlers for common shutdown signals
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)

        # On Windows, also handle SIGBREAK
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, self._handle_shutdown_signal)

        self._logger.info("Signal handlers registered for graceful shutdown")

    def _handle_shutdown_signal(self, signum: int, frame) -> None:
        """
        Handle shutdown signals by calling the shutdown callback.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name
        self._logger.info(f"Received shutdown signal: {signal_name}")

        try:
            self._shutdown_callback()
        except Exception as e:
            self._logger.error(f"Error during shutdown: {e}")


class DaemonProcess:
    """
    Manages daemon/service process operations including PID file management.
    """

    def __init__(self, pid_file: Optional[str] = None, daemonize: bool = True):
        """
        Initialize DaemonProcess.

        Args:
            pid_file: Path to PID file for process tracking
            daemonize: Whether to actually daemonize the process
        """
        self._pid_file = pid_file or os.path.join(tempfile.gettempdir(), "prism-client.pid")
        self._daemonize = daemonize
        self._logger = logging.getLogger(__name__)

    def create_pid_file(self) -> None:
        """
        Create PID file with current process ID.

        Raises:
            RuntimeError: If service is already running
        """
        # Check if PID file exists and process is running
        if os.path.exists(self._pid_file):
            try:
                with open(self._pid_file, "r") as f:
                    existing_pid = int(f.read().strip())

                # Check if the process is actually running
                try:
                    os.kill(existing_pid, 0)
                    # Process exists, service is running
                    raise RuntimeError(f"Service is already running (PID: {existing_pid})")
                except (OSError, ProcessLookupError):
                    # Process doesn't exist, remove stale PID file
                    self.cleanup_pid_file()
            except (ValueError, IOError):
                # Invalid PID file, remove it
                self.cleanup_pid_file()

        # Ensure directory exists
        pid_dir = os.path.dirname(os.path.abspath(self._pid_file))
        if pid_dir and not os.path.exists(pid_dir):
            os.makedirs(pid_dir, exist_ok=True)

        # Write current PID
        with open(self._pid_file, "w") as f:
            f.write(str(os.getpid()))

        self._logger.info(f"Created PID file: {self._pid_file}")

    def cleanup_pid_file(self) -> None:
        """
        Remove PID file during shutdown.
        """
        if os.path.exists(self._pid_file):
            try:
                os.unlink(self._pid_file)
                self._logger.info(f"Removed PID file: {self._pid_file}")
            except OSError as e:
                self._logger.warning(f"Failed to remove PID file: {e}")

    def is_running(self) -> bool:
        """
        Check if daemon is currently running based on PID file.

        Returns:
            True if running, False otherwise
        """
        if not os.path.exists(self._pid_file):
            return False

        try:
            with open(self._pid_file, "r") as f:
                pid = int(f.read().strip())

            # Check if process with PID is still running
            try:
                os.kill(pid, 0)  # Signal 0 doesn't kill, just checks if process exists
                return True
            except (OSError, ProcessLookupError):
                # Process doesn't exist, remove stale PID file
                self.cleanup_pid_file()
                return False

        except (ValueError, IOError):
            # Invalid PID file, consider not running
            return False

    def get_pid(self) -> Optional[int]:
        """
        Get PID from PID file.

        Returns:
            Process ID if running, None otherwise
        """
        if not os.path.exists(self._pid_file):
            return None

        try:
            with open(self._pid_file, "r") as f:
                return int(f.read().strip())
        except (ValueError, IOError):
            return None

    def daemonize(self) -> None:
        """
        Daemonize the current process (Unix-style double fork).

        Note: This is a simplified daemonization for demonstration.
        Production use should consider a full daemonization library.
        """
        if not self._daemonize:
            return

        try:
            # First fork
            pid = os.fork()
            if pid > 0:
                sys.exit(0)  # Parent exits
        except OSError as e:
            self._logger.error(f"First fork failed: {e}")
            sys.exit(1)

        # Decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        try:
            # Second fork
            pid = os.fork()
            if pid > 0:
                sys.exit(0)  # Parent exits
        except OSError as e:
            self._logger.error(f"Second fork failed: {e}")
            sys.exit(1)

        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()

        # Redirect to /dev/null
        with open("/dev/null", "r") as f:
            os.dup2(f.fileno(), sys.stdin.fileno())
        with open("/dev/null", "w") as f:
            os.dup2(f.fileno(), sys.stdout.fileno())
        with open("/dev/null", "w") as f:
            os.dup2(f.fileno(), sys.stderr.fileno())


class ServiceManager:
    """
    Main service manager that coordinates all client components in service/daemon mode.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize ServiceManager with configuration.

        Args:
            config: Configuration dictionary
        """
        self._config = config
        self._validate_config()

        # Service configuration
        service_config = config.get("service", {})
        self._service_name = service_config.get("name", "prism-client")
        self._service_description = service_config.get("description", "Prism Host Client Service")

        # Initialize components
        self._log_manager: Optional[LogManager] = None
        self._error_handler: Optional[ErrorHandler] = None
        self._heartbeat_manager: Optional[HeartbeatManager] = None
        self._daemon: Optional[DaemonProcess] = None
        self._signal_handler: Optional[SignalHandler] = None

        # Service state
        self._shutdown_event = threading.Event()
        self._running = False

        # Setup daemon process
        pid_file = service_config.get("pid_file", os.path.join(tempfile.gettempdir(), f"{self._service_name}.pid"))
        self._daemon = DaemonProcess(
            pid_file=pid_file, daemonize=False
        )  # Default to non-daemon for testing

    @classmethod
    def from_config_file(cls, config_file: str) -> "ServiceManager":
        """
        Create ServiceManager from configuration file.

        Args:
            config_file: Path to configuration file

        Returns:
            Configured ServiceManager instance
        """
        config_manager = ConfigManager()
        config = config_manager.load_config(config_file)
        return cls(config)

    def _validate_config(self) -> None:
        """
        Validate service configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        required_sections = ["server"]
        for section in required_sections:
            if section not in self._config:
                raise ValueError(f"Missing required configuration section: {section}")

    def setup_logging(self) -> None:
        """
        Setup logging system for service operation.
        """
        self._log_manager = LogManager(self._config)
        self._log_manager.setup_logging()
        self._error_handler = ErrorHandler(self._log_manager)

    def start_service(self) -> None:
        """
        Start the service in daemon mode.

        Raises:
            RuntimeError: If service is already running
        """
        if self._daemon.is_running():
            raise RuntimeError(f"Service {self._service_name} is already running")

        # Setup logging first
        if not self._log_manager:
            self.setup_logging()

        self._log_manager.log_info(
            "Starting Prism client service",
            component="ServiceManager",
            service_name=self._service_name,
        )

        try:
            # Create PID file
            self._daemon.create_pid_file()

            # Setup signal handlers for graceful shutdown
            self._signal_handler = SignalHandler(self.shutdown)
            self._signal_handler.register_handlers()

            # Initialize heartbeat manager
            self._heartbeat_manager = HeartbeatManager(self._config)

            # Mark as running
            self._running = True

            self._log_manager.log_info(
                "Service started successfully", component="ServiceManager", pid=os.getpid()
            )

        except Exception as e:
            self._error_handler.handle_exception(
                e, component="ServiceManager", operation="start_service"
            )
            raise

    def stop_service(self) -> None:
        """
        Stop the running service.
        """
        if not self._daemon.is_running():
            return

        self._log_manager.log_info("Stopping service", component="ServiceManager")

        self.shutdown()

    def run(self) -> None:
        """
        Main service run loop.
        """
        if not self._running:
            raise RuntimeError("Service not started. Call start_service() first.")

        self._log_manager.log_info("Starting main service loop", component="ServiceManager")

        # Start heartbeat manager
        self._heartbeat_manager.start()

        # Main service loop
        try:
            while not self._shutdown_event.is_set():
                # Service runs in background, heartbeat manager handles periodic tasks
                time.sleep(1)  # Check shutdown event every second

        except Exception as e:
            self._error_handler.handle_exception(
                e, component="ServiceManager", operation="main_loop"
            )
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """
        Gracefully shutdown the service and all components.
        """
        if not self._running and not self._shutdown_event.is_set():
            return

        if self._log_manager:
            self._log_manager.log_info("Initiating graceful shutdown", component="ServiceManager")

        # Signal shutdown
        self._shutdown_event.set()
        self._running = False

        try:
            # Stop heartbeat manager
            if self._heartbeat_manager and hasattr(self._heartbeat_manager, "stop"):
                self._heartbeat_manager.stop()
                if self._log_manager:
                    self._log_manager.log_info(
                        "Heartbeat manager stopped", component="ServiceManager"
                    )

            # Cleanup PID file
            if self._daemon:
                self._daemon.cleanup_pid_file()

            # Shutdown logging
            if self._log_manager:
                self._log_manager.log_info("Service shutdown complete", component="ServiceManager")
                self._log_manager.shutdown()

        except Exception as e:
            # Use basic logging if log manager is unavailable
            print(f"Error during shutdown: {e}", file=sys.stderr)

    def get_service_status(self) -> Dict[str, Any]:
        """
        Get current service status information.

        Returns:
            Dictionary with service status details
        """
        is_running = self._daemon.is_running()
        pid = self._daemon.get_pid() if is_running else None

        return {
            "name": self._service_name,
            "description": self._service_description,
            "running": is_running,
            "pid": pid,
            "pid_file": self._daemon._pid_file if self._daemon else None,
            "config": {
                "server": self._config.get("server", {}),
                "heartbeat": self._config.get("heartbeat", {}),
                "logging": self._config.get("logging", {}),
            },
        }

    def install_service(self) -> None:
        """
        Install service for automatic startup (platform-specific).

        Note: This is a placeholder for platform-specific service installation.
        Production implementation would create systemd, Windows Service, or launchd files.
        """
        platform = sys.platform

        if platform.startswith("linux"):
            self._install_systemd_service()
        elif platform == "win32":
            self._install_windows_service()
        elif platform == "darwin":
            self._install_launchd_service()
        else:
            raise NotImplementedError(f"Service installation not supported on {platform}")

    def _install_systemd_service(self) -> None:
        """Install systemd service unit file."""
        service_content = f"""[Unit]
Description={self._service_description}
After=network.target

[Service]
Type=forking
ExecStart={sys.executable} -m client.service_manager --config /etc/prism/client.yaml --daemon
PIDFile={self._daemon._pid_file}
Restart=always
RestartSec=10
User=prism
Group=prism

[Install]
WantedBy=multi-user.target
"""

        service_file = f"/etc/systemd/system/{self._service_name}.service"

        if self._log_manager:
            self._log_manager.log_info(
                "Installing systemd service", component="ServiceManager", service_file=service_file
            )

        # Note: In production, this would require sudo privileges
        print(f"Systemd service file content for {service_file}:")
        print(service_content)

    def _install_windows_service(self) -> None:
        """Install Windows service."""
        if self._log_manager:
            self._log_manager.log_info("Installing Windows service", component="ServiceManager")

        # Note: Would use pywin32 or similar for actual Windows service installation
        print(f"Windows service installation for {self._service_name}")

    def _install_launchd_service(self) -> None:
        """Install macOS launchd service."""
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.prism.{self._service_name}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>-m</string>
        <string>client.service_manager</string>
        <string>--config</string>
        <string>/usr/local/etc/prism/client.yaml</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
"""

        plist_file = f"/Library/LaunchDaemons/com.prism.{self._service_name}.plist"

        if self._log_manager:
            self._log_manager.log_info(
                "Installing launchd service", component="ServiceManager", plist_file=plist_file
            )

        print(f"Launchd plist content for {plist_file}:")
        print(plist_content)

    def __enter__(self) -> "ServiceManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit with automatic cleanup."""
        self.shutdown()

    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.shutdown()
        except Exception:
            pass  # Ignore errors during destruction
