#!/usr/bin/env python3
"""
Signal Handlers for Graceful Shutdown (SCRUM-18)
Handles SIGTERM, SIGINT, and other signals for graceful server shutdown.
"""

import asyncio
import logging
import os
import signal
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class SignalHandler:
    """
    Signal handler for graceful server shutdown.

    Handles SIGTERM, SIGINT, and other shutdown signals to ensure
    graceful shutdown of server components.
    """

    def __init__(self, shutdown_callback: Callable[[], None]):
        """
        Initialize signal handler.

        Args:
            shutdown_callback: Function to call when shutdown signal is received
        """
        self.shutdown_callback = shutdown_callback
        self.shutdown_requested = False
        self._original_handlers = {}

        logger.info("Signal handler initialized")

    def setup(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        # Handle common shutdown signals
        signals_to_handle = [
            signal.SIGTERM,  # Termination signal
            signal.SIGINT,  # Interrupt signal (Ctrl+C)
        ]

        # On Unix systems, also handle SIGHUP for reload
        if hasattr(signal, "SIGHUP"):
            signals_to_handle.append(signal.SIGHUP)

        # On Windows, handle SIGBREAK
        if hasattr(signal, "SIGBREAK"):
            signals_to_handle.append(signal.SIGBREAK)

        for sig in signals_to_handle:
            try:
                # Store original handler
                self._original_handlers[sig] = signal.signal(sig, self.handle_shutdown_signal)
                logger.debug(f"Registered signal handler for {sig}")
            except OSError as e:
                logger.warning(f"Could not register handler for signal {sig}: {e}")

        logger.info(f"Signal handlers registered for {len(self._original_handlers)} signals")

    def handle_shutdown_signal(self, signum: int, frame) -> None:
        """
        Handle shutdown signal.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        if self.shutdown_requested:
            logger.warning(f"Received signal {signum} but shutdown already in progress")
            return

        signal_name = signal.Signals(signum).name if hasattr(signal, "Signals") else str(signum)
        logger.info(f"Received shutdown signal: {signal_name} ({signum})")

        self.shutdown_requested = True

        # Call shutdown callback in a thread-safe manner
        try:
            # If we're in an async context, schedule the callback
            if self._is_async_context():
                asyncio.create_task(self._async_shutdown_wrapper())
            else:
                # Call directly in a separate thread to avoid blocking signal handler
                shutdown_thread = threading.Thread(
                    target=self._safe_shutdown_callback, name="shutdown-handler"
                )
                shutdown_thread.daemon = True
                shutdown_thread.start()

        except Exception as e:
            logger.error(f"Error handling shutdown signal: {e}")

    def _is_async_context(self) -> bool:
        """Check if we're in an async context."""
        try:
            asyncio.get_running_loop()
            return True
        except RuntimeError:
            return False

    async def _async_shutdown_wrapper(self) -> None:
        """Wrapper for async shutdown callback."""
        try:
            if asyncio.iscoroutinefunction(self.shutdown_callback):
                await self.shutdown_callback()
            else:
                self.shutdown_callback()
        except Exception as e:
            logger.error(f"Error in async shutdown callback: {e}")

    def _safe_shutdown_callback(self) -> None:
        """Safely execute shutdown callback with error handling."""
        try:
            self.shutdown_callback()
        except Exception as e:
            logger.error(f"Error in shutdown callback: {e}")

    def cleanup(self) -> None:
        """Restore original signal handlers."""
        for sig, original_handler in self._original_handlers.items():
            try:
                signal.signal(sig, original_handler)
                logger.debug(f"Restored original handler for signal {sig}")
            except OSError as e:
                logger.warning(f"Could not restore handler for signal {sig}: {e}")

        self._original_handlers.clear()
        logger.info("Signal handlers cleaned up")

    def force_shutdown(self, timeout: float = 10.0) -> None:
        """
        Force shutdown if graceful shutdown takes too long.

        Args:
            timeout: Maximum time to wait for graceful shutdown
        """
        if not self.shutdown_requested:
            logger.warning("Force shutdown called but no shutdown was requested")
            return

        logger.warning(f"Force shutdown initiated with timeout {timeout}s")

        def force_exit():
            import time

            time.sleep(timeout)
            if self.shutdown_requested:
                logger.critical("Force shutdown timeout exceeded, terminating process")
                os._exit(1)

        force_thread = threading.Thread(target=force_exit, name="force-shutdown")
        force_thread.daemon = True
        force_thread.start()


class AsyncSignalHandler:
    """
    Async-specific signal handler for graceful shutdown.

    Designed specifically for asyncio-based applications.
    """

    def __init__(self, shutdown_callback: Callable[[], None]):
        """
        Initialize async signal handler.

        Args:
            shutdown_callback: Async function to call when shutdown signal is received
        """
        self.shutdown_callback = shutdown_callback
        self.shutdown_requested = False
        self.shutdown_event = asyncio.Event()

        logger.info("Async signal handler initialized")

    def setup(self) -> None:
        """Setup signal handlers for asyncio event loop."""
        try:
            loop = asyncio.get_running_loop()

            # Handle SIGTERM
            loop.add_signal_handler(signal.SIGTERM, self._handle_signal, signal.SIGTERM)

            # Handle SIGINT (Ctrl+C)
            loop.add_signal_handler(signal.SIGINT, self._handle_signal, signal.SIGINT)

            logger.info("Async signal handlers registered")

        except (RuntimeError, NotImplementedError) as e:
            logger.warning(f"Could not setup async signal handlers: {e}")
            # Fallback to regular signal handlers
            self._setup_fallback_handlers()

    def _setup_fallback_handlers(self) -> None:
        """Setup fallback signal handlers for non-Unix systems."""
        regular_handler = SignalHandler(self._sync_shutdown_wrapper)
        regular_handler.setup()

    def _sync_shutdown_wrapper(self) -> None:
        """Wrapper to convert sync signal to async shutdown."""
        if not self.shutdown_requested:
            self.shutdown_requested = True
            self.shutdown_event.set()

            # Schedule async shutdown
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._async_shutdown())
            except RuntimeError:
                logger.warning("Could not schedule async shutdown")

    def _handle_signal(self, signum: int) -> None:
        """
        Handle signal in async context.

        Args:
            signum: Signal number
        """
        if self.shutdown_requested:
            logger.warning(f"Received signal {signum} but shutdown already in progress")
            return

        signal_name = signal.Signals(signum).name if hasattr(signal, "Signals") else str(signum)
        logger.info(f"Received shutdown signal: {signal_name} ({signum})")

        self.shutdown_requested = True
        self.shutdown_event.set()

        # Schedule shutdown callback
        asyncio.create_task(self._async_shutdown())

    async def _async_shutdown(self) -> None:
        """Execute async shutdown callback."""
        try:
            if asyncio.iscoroutinefunction(self.shutdown_callback):
                await self.shutdown_callback()
            else:
                self.shutdown_callback()
        except Exception as e:
            logger.error(f"Error in async shutdown callback: {e}")

    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal to be received."""
        await self.shutdown_event.wait()

    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self.shutdown_requested

    def cleanup(self) -> None:
        """
        Cleanup signal handler resources.

        Note: For AsyncSignalHandler, cleanup is automatic as signal
        handlers are managed by asyncio event loop.
        """
        logger.info("Async signal handler cleanup completed")


def create_signal_handler(
    shutdown_callback: Callable[[], None], async_mode: bool = False
) -> SignalHandler:
    """
    Create appropriate signal handler based on context.

    Args:
        shutdown_callback: Function to call on shutdown
        async_mode: Whether to use async signal handler

    Returns:
        Configured signal handler
    """
    if async_mode:
        return AsyncSignalHandler(shutdown_callback)
    else:
        return SignalHandler(shutdown_callback)
