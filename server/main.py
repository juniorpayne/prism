#!/usr/bin/env python3
"""
Main Server Application (SCRUM-18)
Production-ready server with configuration management and graceful shutdown.
"""

import argparse
import asyncio
import logging
import os
import sys
from typing import Any, Dict, Optional

from server.api.app import create_app
from server.config import ConfigFileError, ConfigValidationError, ServerConfiguration
from server.heartbeat_monitor import create_heartbeat_monitor
from server.logging_setup import LoggingConfigError, setup_logging
from server.signal_handlers import create_signal_handler
from server.tcp_server import TCPServer

logger = logging.getLogger(__name__)


class ServerApplication:
    """
    Main server application class.

    Manages the lifecycle of all server components including TCP server,
    API server, heartbeat monitor, and graceful shutdown.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize server application.

        Args:
            config: Server configuration dictionary or ServerConfiguration instance
        """
        if isinstance(config, dict):
            self.config = ServerConfiguration(config)
        else:
            self.config = config

        # Validate configuration
        self.config.validate()

        # Initialize components
        self.tcp_server: Optional[TCPServer] = None
        self.api_server = None
        self.heartbeat_monitor = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.shutdown_event = asyncio.Event()
        self.signal_handler = None

        logger.info("Server application initialized")

    async def start(self) -> None:
        """Start all server components."""
        logger.info("Starting Prism DNS Server...")

        try:
            # Setup signal handlers
            self.signal_handler = create_signal_handler(self.shutdown, async_mode=True)
            self.signal_handler.setup()

            # Start TCP server
            await self._start_tcp_server()

            # Start API server
            await self._start_api_server()

            # Start heartbeat monitor
            await self._start_heartbeat_monitor()

            logger.info("All server components started successfully")
            logger.info(
                f"TCP server listening on {self.config.server.host}:{self.config.server.tcp_port}"
            )
            logger.info(
                f"API server listening on {self.config.server.host}:{self.config.server.api_port}"
            )

        except Exception as e:
            logger.error(f"Failed to start server components: {e}")
            await self.shutdown()
            raise

    async def _start_tcp_server(self) -> None:
        """Start TCP server for client connections."""
        try:
            self.tcp_server = TCPServer(self.config.to_dict())
            await self.tcp_server.start()
            logger.info(
                f"TCP server started on {self.config.server.host}:{self.config.server.tcp_port}"
            )

        except Exception as e:
            logger.error(f"Failed to start TCP server: {e}")
            raise

    async def _start_api_server(self) -> None:
        """Start API server using uvicorn."""
        try:
            import uvicorn

            # Create FastAPI app
            app = create_app(self.config.to_dict())

            # Configure uvicorn
            uvicorn_config = uvicorn.Config(
                app=app,
                host=self.config.server.host,
                port=self.config.server.api_port,
                log_level=self.config.logging.level.lower(),
                access_log=True,
                loop="asyncio",
            )

            self.api_server = uvicorn.Server(uvicorn_config)

            # Start API server in background task
            api_task = asyncio.create_task(self.api_server.serve())
            logger.info(
                f"API server started on {self.config.server.host}:{self.config.server.api_port}"
            )

        except ImportError:
            logger.warning("uvicorn not available, API server not started")
        except Exception as e:
            logger.error(f"Failed to start API server: {e}")
            raise

    async def _start_heartbeat_monitor(self) -> None:
        """Start heartbeat monitor background task."""
        try:
            self.heartbeat_monitor = create_heartbeat_monitor(self.config.to_dict())

            # Start background monitoring
            self.heartbeat_task = await self.heartbeat_monitor.start_background_monitoring()
            logger.info("Heartbeat monitor started")

        except Exception as e:
            logger.error(f"Failed to start heartbeat monitor: {e}")
            raise

    async def shutdown(self) -> None:
        """Gracefully shutdown all server components."""
        if self.shutdown_event.is_set():
            logger.warning("Shutdown already in progress")
            return

        logger.info("Initiating graceful shutdown...")
        self.shutdown_event.set()

        # Stop heartbeat monitor
        if self.heartbeat_task and not self.heartbeat_task.done():
            logger.info("Stopping heartbeat monitor...")
            await self.heartbeat_monitor.stop_monitoring(self.heartbeat_task)

        # Stop TCP server
        if self.tcp_server:
            logger.info("Stopping TCP server...")
            await self.tcp_server.stop()

        # Stop API server
        if self.api_server:
            logger.info("Stopping API server...")
            self.api_server.should_exit = True
            # Give it a moment to stop gracefully
            await asyncio.sleep(1)

        # Cleanup heartbeat monitor
        if self.heartbeat_monitor:
            self.heartbeat_monitor.cleanup()

        # Cleanup signal handlers
        if self.signal_handler:
            self.signal_handler.cleanup()

        logger.info("Graceful shutdown completed")

    async def run(self) -> None:
        """Run the server until shutdown is requested."""
        await self.start()

        # Wait for shutdown signal
        if hasattr(self.signal_handler, "wait_for_shutdown"):
            await self.signal_handler.wait_for_shutdown()
        else:
            await self.shutdown_event.wait()

        await self.shutdown()


def parse_arguments(args=None) -> argparse.Namespace:
    """
    Parse command line arguments.

    Args:
        args: Arguments to parse (defaults to sys.argv)

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Prism DNS Server - Managed DNS with heartbeat monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --config server.yaml
  %(prog)s --config /etc/prism/server.yaml
  
Environment Variables:
  PRISM_SERVER_TCP_PORT     - Override TCP server port
  PRISM_SERVER_API_PORT     - Override API server port
  PRISM_DATABASE_PATH       - Override database file path
  PRISM_LOGGING_LEVEL       - Override logging level
        """,
    )

    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="server.yaml",
        help="Path to YAML configuration file (default: server.yaml)",
    )

    parser.add_argument("--version", "-v", action="version", version="Prism DNS Server 1.0.0")

    return parser.parse_args(args)


async def main() -> int:
    """
    Main application entry point.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Parse command line arguments
        args = parse_arguments()

        # Load configuration
        try:
            if os.path.exists(args.config):
                config_dict = ServerConfiguration.from_file(args.config).to_dict()
            else:
                # Use default configuration if file doesn't exist
                print(f"Configuration file {args.config} not found, using defaults")
                config_dict = {}

            # Add environment variable to config for API app
            config_dict["server"] = config_dict.get("server", {})
            config_dict["server"]["environment"] = os.getenv("PRISM_ENV", "production")

            config = ServerConfiguration(config_dict)

        except (ConfigFileError, ConfigValidationError) as e:
            print(f"Configuration error: {e}", file=sys.stderr)
            return 1

        # Setup logging
        try:
            setup_logging(config.logging.__dict__)
        except LoggingConfigError as e:
            print(f"Logging configuration error: {e}", file=sys.stderr)
            return 1

        # Create and run server application
        app = ServerApplication(config)
        await app.run()

        return 0

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        return 0
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        return 1


def run() -> None:
    """Entry point for console script."""
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    run()
