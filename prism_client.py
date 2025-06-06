#!/usr/bin/env python3
"""
Prism Host Client - Complete managed DNS client application
Integrates all components: configuration, logging, heartbeat, networking, and service management.
"""

import argparse
import os
import signal
import sys
from typing import Optional

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.config_manager import ConfigManager, ConfigValidationError
from client.log_manager import ErrorHandler, LogManager
from client.service_manager import ServiceManager


class PrismClient:
    """
    Main Prism client application that coordinates all components.
    """

    def __init__(self, config_file: str, daemon_mode: bool = False):
        """
        Initialize Prism client.

        Args:
            config_file: Path to configuration file
            daemon_mode: Whether to run in daemon/service mode
        """
        self.config_file = config_file
        self.daemon_mode = daemon_mode
        self.service_manager: Optional[ServiceManager] = None
        self.log_manager: Optional[LogManager] = None
        self.error_handler: Optional[ErrorHandler] = None

    def initialize(self) -> None:
        """
        Initialize client components.
        """
        try:
            # Load configuration
            config_manager = ConfigManager()
            config = config_manager.load_config(self.config_file)

            # Setup logging
            self.log_manager = LogManager(config)
            self.log_manager.setup_logging()
            self.error_handler = ErrorHandler(self.log_manager)

            # Create service manager
            if self.daemon_mode:
                # In daemon mode, set daemonize flag
                daemon_config = config.setdefault("service", {})
                daemon_config["daemonize"] = True

            self.service_manager = ServiceManager(config)
            self.service_manager._log_manager = self.log_manager
            self.service_manager._error_handler = self.error_handler

            self.log_manager.log_info(
                "Prism client initialized successfully",
                component="PrismClient",
                config_file=self.config_file,
                daemon_mode=self.daemon_mode,
            )

        except ConfigValidationError as e:
            print(f"Configuration error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Initialization error: {e}", file=sys.stderr)
            sys.exit(1)

    def start(self) -> None:
        """
        Start the Prism client.
        """
        try:
            if self.daemon_mode:
                self.log_manager.log_info(
                    "Starting Prism client in daemon mode", component="PrismClient"
                )

                # Start as service
                self.service_manager.start_service()
                self.service_manager.run()
            else:
                self.log_manager.log_info(
                    "Starting Prism client in foreground mode", component="PrismClient"
                )

                # Set up signal handlers for graceful shutdown
                signal.signal(signal.SIGTERM, self._signal_handler)
                signal.signal(signal.SIGINT, self._signal_handler)

                # Run heartbeat manager directly
                from client.heartbeat_manager import HeartbeatManager

                heartbeat_manager = HeartbeatManager(self.service_manager._config)

                try:
                    heartbeat_manager.start()
                    self.log_manager.log_info("Heartbeat manager started", component="PrismClient")

                    # Keep running until interrupted
                    import time

                    while True:
                        time.sleep(1)

                except KeyboardInterrupt:
                    self.log_manager.log_info("Received interrupt signal", component="PrismClient")
                finally:
                    heartbeat_manager.stop()
                    self.log_manager.log_info("Heartbeat manager stopped", component="PrismClient")

        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_exception(e, component="PrismClient", operation="start")
            else:
                print(f"Startup error: {e}", file=sys.stderr)
            sys.exit(1)

    def stop(self) -> None:
        """
        Stop the Prism client.
        """
        if self.service_manager:
            self.log_manager.log_info("Stopping Prism client", component="PrismClient")
            self.service_manager.shutdown()

    def status(self) -> None:
        """
        Show client status.
        """
        if not self.service_manager:
            print("Client not initialized")
            return

        status = self.service_manager.get_service_status()

        print(f"Prism Client Status:")
        print(f"  Service: {status['name']}")
        print(f"  Description: {status['description']}")
        print(f"  Running: {'Yes' if status['running'] else 'No'}")

        if status["running"]:
            print(f"  PID: {status['pid']}")
            print(f"  PID File: {status['pid_file']}")

        print(f"  Configuration:")
        print(
            f"    Server: {status['config']['server']['host']}:{status['config']['server']['port']}"
        )
        print(f"    Heartbeat Interval: {status['config']['heartbeat']['interval']}s")
        print(f"    Log Level: {status['config']['logging']['level']}")

    def _signal_handler(self, signum: int, frame) -> None:
        """
        Handle shutdown signals.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name
        if self.log_manager:
            self.log_manager.log_info(f"Received signal: {signal_name}", component="PrismClient")
        self.stop()
        sys.exit(0)


def create_default_config() -> str:
    """
    Create a default configuration file.

    Returns:
        Path to created configuration file
    """
    config_content = """# Prism Host Client Configuration

# Service configuration
service:
  name: prism-client
  description: "Prism Host Client - Managed DNS Service"
  pid_file: /tmp/prism-client.pid

# Server connection settings
server:
  host: dns.example.com
  port: 8080
  timeout: 10

# Heartbeat settings
heartbeat:
  interval: 60  # seconds

# Logging configuration
logging:
  level: INFO
  file: ./prism-client.log
  console: true
  max_size: 10485760  # 10MB
  backup_count: 5
  format: "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
"""

    config_file = "prism-client.yaml"

    if not os.path.exists(config_file):
        with open(config_file, "w") as f:
            f.write(config_content)
        print(f"Created default configuration file: {config_file}")
    else:
        print(f"Configuration file already exists: {config_file}")

    return config_file


def main():
    """
    Main entry point for Prism client application.
    """
    parser = argparse.ArgumentParser(
        description="Prism Host Client - Managed DNS Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --config client.yaml                    # Run in foreground
  %(prog)s --config client.yaml --daemon           # Run as daemon
  %(prog)s --status --config client.yaml           # Show status
  %(prog)s --stop --config client.yaml             # Stop service
  %(prog)s --create-config                         # Create default config
        """,
    )

    parser.add_argument(
        "--config",
        "-c",
        default="prism-client.yaml",
        help="Configuration file path (default: prism-client.yaml)",
    )

    parser.add_argument("--daemon", "-d", action="store_true", help="Run as daemon/service")

    parser.add_argument("--status", "-s", action="store_true", help="Show service status")

    parser.add_argument("--stop", action="store_true", help="Stop running service")

    parser.add_argument(
        "--create-config", action="store_true", help="Create default configuration file"
    )

    parser.add_argument("--version", "-v", action="version", version="Prism Client 1.0.0")

    args = parser.parse_args()

    # Handle special commands
    if args.create_config:
        create_default_config()
        return 0

    # Check if config file exists
    if not os.path.exists(args.config):
        print(f"Configuration file not found: {args.config}", file=sys.stderr)
        print(f"Create one with: {sys.argv[0]} --create-config", file=sys.stderr)
        return 1

    # Initialize client
    client = PrismClient(args.config, args.daemon)
    client.initialize()

    try:
        if args.status:
            client.status()
        elif args.stop:
            client.stop()
        else:
            client.start()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        client.stop()
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
