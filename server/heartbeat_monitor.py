#!/usr/bin/env python3
"""
Heartbeat Monitor for Prism DNS Server (SCRUM-16)
Monitors host heartbeats and manages host status transitions.
"""

import logging
import asyncio
import time
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

from server.database.connection import DatabaseManager
from server.database.operations import HostOperations
from server.database.models import Host

logger = logging.getLogger(__name__)


class HeartbeatConfigError(Exception):
    """Exception raised for heartbeat configuration errors."""

    pass


@dataclass
class TimeoutResult:
    """Result of heartbeat timeout check operation."""

    hosts_checked: int
    hosts_timed_out: int
    timed_out_hosts: List[str]
    check_duration: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hosts_checked": self.hosts_checked,
            "hosts_timed_out": self.hosts_timed_out,
            "timed_out_hosts": self.timed_out_hosts,
            "check_duration": self.check_duration,
        }


@dataclass
class StatusChangeResult:
    """Result of host status change operation."""

    success: bool
    hosts_processed: int
    hosts_marked_offline: int
    failed_hosts: List[str]
    operation_duration: float


class HeartbeatConfig:
    """Configuration for heartbeat monitor."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize heartbeat configuration."""
        heartbeat_config = config.get("heartbeat", {})

        self.check_interval = heartbeat_config.get("check_interval", 60)
        self.timeout_multiplier = heartbeat_config.get("timeout_multiplier", 2)
        self.grace_period = heartbeat_config.get("grace_period", 30)
        self.max_hosts_per_check = heartbeat_config.get("max_hosts_per_check", 1000)
        self.cleanup_offline_after_days = heartbeat_config.get("cleanup_offline_after_days", 30)

        # Validate configuration
        if self.check_interval < 0:
            raise HeartbeatConfigError("check_interval must be non-negative")
        if self.timeout_multiplier < 1:
            raise HeartbeatConfigError("timeout_multiplier must be >= 1")
        if self.grace_period < 0:
            raise HeartbeatConfigError("grace_period must be non-negative")
        if self.max_hosts_per_check < 1:
            raise HeartbeatConfigError("max_hosts_per_check must be >= 1")
        if self.cleanup_offline_after_days < 1:
            raise HeartbeatConfigError("cleanup_offline_after_days must be >= 1")

        logger.info(
            f"Heartbeat monitor configured: check_interval={self.check_interval}s, "
            f"timeout_multiplier={self.timeout_multiplier}, grace_period={self.grace_period}s"
        )


class HeartbeatMonitor:
    """
    Monitor for tracking host heartbeats and managing status transitions.

    Handles timeout detection, status changes, and monitoring statistics.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize heartbeat monitor.

        Args:
            config: Configuration dictionary
        """
        self.config = HeartbeatConfig(config)
        self.db_manager = DatabaseManager(config)
        self._statistics = {
            "total_checks_performed": 0,
            "total_hosts_timed_out": 0,
            "total_status_changes": 0,
            "last_check_time": None,
            "average_check_duration": 0.0,
            "check_durations": [],
        }

        logger.info("HeartbeatMonitor initialized")

    def calculate_timeout_threshold(
        self, heartbeat_interval: int, grace_period: Optional[int] = None
    ) -> int:
        """
        Calculate timeout threshold for host heartbeats.

        Args:
            heartbeat_interval: Expected heartbeat interval in seconds
            grace_period: Additional grace period in seconds

        Returns:
            Timeout threshold in seconds
        """
        if grace_period is None:
            grace_period = self.config.grace_period

        threshold = (heartbeat_interval * self.config.timeout_multiplier) + grace_period

        logger.debug(
            f"Calculated timeout threshold: {threshold}s "
            f"(interval={heartbeat_interval} * multiplier={self.config.timeout_multiplier} + grace={grace_period})"
        )

        return threshold

    async def check_host_timeouts(
        self, heartbeat_interval: int = 60, limit: Optional[int] = None
    ) -> TimeoutResult:
        """
        Check for hosts that have timed out.

        Args:
            heartbeat_interval: Expected heartbeat interval in seconds
            limit: Maximum number of hosts to check (optional)

        Returns:
            TimeoutResult with check statistics
        """
        start_time = time.time()

        if limit is None:
            limit = self.config.max_hosts_per_check

        # Calculate timeout threshold
        timeout_threshold = self.calculate_timeout_threshold(heartbeat_interval)
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=timeout_threshold)

        logger.debug(f"Checking for hosts with last_seen before {cutoff_time}")

        # Get all online hosts to check (up to limit)
        all_hosts = await self.get_all_online_hosts(limit)

        # Filter for hosts that have actually timed out
        # Ensure timezone compatibility
        timed_out_hosts = []
        for host in all_hosts:
            host_last_seen = host.last_seen
            if host_last_seen.tzinfo is None:
                # If host.last_seen is naive, make it UTC
                host_last_seen = host_last_seen.replace(tzinfo=timezone.utc)
            if host_last_seen < cutoff_time:
                timed_out_hosts.append(host)
        timed_out_hostnames = [host.hostname for host in timed_out_hosts if host.status == "online"]

        check_duration = time.time() - start_time

        # Update statistics
        self._statistics["total_checks_performed"] += 1
        self._statistics["last_check_time"] = datetime.now(timezone.utc).isoformat()
        self._statistics["check_durations"].append(check_duration)

        # Calculate rolling average (keep last 100 measurements)
        if len(self._statistics["check_durations"]) > 100:
            self._statistics["check_durations"] = self._statistics["check_durations"][-100:]

        self._statistics["average_check_duration"] = sum(self._statistics["check_durations"]) / len(
            self._statistics["check_durations"]
        )

        result = TimeoutResult(
            hosts_checked=len(all_hosts),
            hosts_timed_out=len(timed_out_hostnames),
            timed_out_hosts=timed_out_hostnames,
            check_duration=check_duration,
        )

        logger.info(
            f"Heartbeat check completed: {result.hosts_checked} hosts checked, "
            f"{result.hosts_timed_out} timed out in {result.check_duration:.3f}s"
        )

        return result

    async def mark_hosts_offline(
        self, hostnames: List[str], reason: str = "heartbeat_timeout"
    ) -> StatusChangeResult:
        """
        Mark hosts as offline.

        Args:
            hostnames: List of hostnames to mark offline
            reason: Reason for status change

        Returns:
            StatusChangeResult with operation statistics
        """
        start_time = time.time()

        hosts_processed = 0
        hosts_marked_offline = 0
        failed_hosts = []

        try:
            self.db_manager.initialize_schema()
            host_ops = HostOperations(self.db_manager)

            for hostname in hostnames:
                try:
                    hosts_processed += 1

                    # Get current host
                    host = host_ops.get_host_by_hostname(hostname)
                    if host and host.status == "online":
                        # Mark offline
                        if host_ops.mark_host_offline(hostname):
                            hosts_marked_offline += 1
                            logger.debug(f"Marked host '{hostname}' offline (reason: {reason})")
                        else:
                            failed_hosts.append(hostname)

                except Exception as e:
                    logger.error(f"Failed to mark host '{hostname}' offline: {e}")
                    failed_hosts.append(hostname)

        except Exception as e:
            logger.error(f"Error during mark_hosts_offline operation: {e}")
            return StatusChangeResult(
                success=False,
                hosts_processed=hosts_processed,
                hosts_marked_offline=hosts_marked_offline,
                failed_hosts=failed_hosts,
                operation_duration=time.time() - start_time,
            )

        # Update statistics
        self._statistics["total_status_changes"] += hosts_marked_offline
        self._statistics["total_hosts_timed_out"] += hosts_marked_offline

        operation_duration = time.time() - start_time

        result = StatusChangeResult(
            success=len(failed_hosts) == 0,
            hosts_processed=hosts_processed,
            hosts_marked_offline=hosts_marked_offline,
            failed_hosts=failed_hosts,
            operation_duration=operation_duration,
        )

        logger.info(
            f"Status change operation completed: {hosts_marked_offline}/{hosts_processed} hosts marked offline "
            f"in {operation_duration:.3f}s"
        )

        return result

    async def get_all_online_hosts(self, limit: Optional[int] = None) -> List[Host]:
        """
        Get all online hosts.

        Args:
            limit: Maximum number of hosts to return

        Returns:
            List of Host objects
        """
        try:
            self.db_manager.initialize_schema()
            host_ops = HostOperations(self.db_manager)

            with host_ops.db_manager.get_session() as session:
                query = session.query(Host).filter(Host.status == "online")

                if limit:
                    query = query.limit(limit)

                hosts = query.all()

                logger.debug(f"Found {len(hosts)} online hosts")

                return hosts

        except Exception as e:
            logger.error(f"Error getting online hosts: {e}")
            return []

    async def get_hosts_by_last_seen(
        self, cutoff_time: datetime, limit: Optional[int] = None
    ) -> List[Host]:
        """
        Get hosts filtered by last seen time.

        Args:
            cutoff_time: Only return hosts last seen before this time
            limit: Maximum number of hosts to return

        Returns:
            List of Host objects
        """
        try:
            self.db_manager.initialize_schema()
            host_ops = HostOperations(self.db_manager)

            with host_ops.db_manager.get_session() as session:
                query = session.query(Host).filter(Host.last_seen < cutoff_time)

                if limit:
                    query = query.limit(limit)

                hosts = query.all()

                logger.debug(f"Found {len(hosts)} hosts with last_seen before {cutoff_time}")

                return hosts

        except Exception as e:
            logger.error(f"Error getting hosts by last_seen: {e}")
            return []

    async def get_monitoring_statistics(self) -> Dict[str, Any]:
        """
        Get monitoring statistics.

        Returns:
            Dictionary with monitoring statistics
        """
        return {
            "total_checks_performed": self._statistics["total_checks_performed"],
            "total_hosts_timed_out": self._statistics["total_hosts_timed_out"],
            "total_status_changes": self._statistics["total_status_changes"],
            "last_check_time": self._statistics["last_check_time"],
            "average_check_duration": round(self._statistics["average_check_duration"], 3),
            "config": {
                "check_interval": self.config.check_interval,
                "timeout_multiplier": self.config.timeout_multiplier,
                "grace_period": self.config.grace_period,
                "max_hosts_per_check": self.config.max_hosts_per_check,
            },
        }

    async def start_monitoring(self, heartbeat_interval: int = 60) -> None:
        """
        Start background monitoring loop.

        Args:
            heartbeat_interval: Expected client heartbeat interval
        """
        logger.info(
            f"Starting heartbeat monitoring loop (check every {self.config.check_interval}s)"
        )

        while True:
            try:
                # Check for timeouts
                timeout_result = await self.check_host_timeouts(heartbeat_interval)

                # Mark timed out hosts as offline
                if timeout_result.timed_out_hosts:
                    status_result = await self.mark_hosts_offline(
                        timeout_result.timed_out_hosts, "heartbeat_timeout"
                    )

                    if not status_result.success:
                        logger.warning(
                            f"Some hosts failed to be marked offline: {status_result.failed_hosts}"
                        )

                # Wait for next check
                await asyncio.sleep(self.config.check_interval)

            except asyncio.CancelledError:
                logger.info("Heartbeat monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Error in heartbeat monitoring loop: {e}")
                await asyncio.sleep(self.config.check_interval)

    async def start_background_monitoring(self, heartbeat_interval: int = 60) -> asyncio.Task:
        """
        Start background monitoring as an asyncio task.

        Args:
            heartbeat_interval: Expected client heartbeat interval

        Returns:
            asyncio.Task for the monitoring loop
        """
        logger.info("Starting background heartbeat monitoring task")

        task = asyncio.create_task(self.start_monitoring(heartbeat_interval))
        task.set_name("heartbeat_monitor")

        return task

    async def stop_monitoring(self, task: asyncio.Task) -> None:
        """
        Stop background monitoring task.

        Args:
            task: The monitoring task to stop
        """
        logger.info("Stopping heartbeat monitoring task")

        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info("Heartbeat monitoring task cancelled successfully")

    async def schedule_periodic_cleanup(self, cleanup_interval_hours: int = 24) -> asyncio.Task:
        """
        Schedule periodic cleanup of old offline hosts.

        Args:
            cleanup_interval_hours: How often to run cleanup (in hours)

        Returns:
            asyncio.Task for the cleanup loop
        """
        logger.info(f"Starting periodic cleanup task (every {cleanup_interval_hours} hours)")

        async def cleanup_loop():
            while True:
                try:
                    await self.cleanup_old_offline_hosts()
                    await asyncio.sleep(cleanup_interval_hours * 3600)  # Convert hours to seconds
                except asyncio.CancelledError:
                    logger.info("Periodic cleanup cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in periodic cleanup: {e}")
                    await asyncio.sleep(3600)  # Wait 1 hour before retry

        task = asyncio.create_task(cleanup_loop())
        task.set_name("heartbeat_cleanup")

        return task

    async def cleanup_old_offline_hosts(self) -> int:
        """
        Clean up hosts that have been offline for too long.

        Returns:
            Number of hosts cleaned up
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(
                days=self.config.cleanup_offline_after_days
            )

            self.db_manager.initialize_schema()
            host_ops = HostOperations(self.db_manager)

            with host_ops.db_manager.get_session() as session:
                # Find hosts that are offline and haven't been seen for the configured period
                old_offline_hosts = (
                    session.query(Host)
                    .filter(Host.status == "offline", Host.last_seen < cutoff_time)
                    .all()
                )

                cleaned_count = 0
                for host in old_offline_hosts:
                    try:
                        session.delete(host)
                        cleaned_count += 1
                        logger.debug(f"Cleaned up old offline host: {host.hostname}")
                    except Exception as e:
                        logger.error(f"Error cleaning up host {host.hostname}: {e}")

                session.commit()

                if cleaned_count > 0:
                    logger.info(f"Cleaned up {cleaned_count} old offline hosts")

                return cleaned_count

        except Exception as e:
            logger.error(f"Error during cleanup of old offline hosts: {e}")
            return 0

    def cleanup(self):
        """Cleanup monitor resources."""
        if hasattr(self, "db_manager"):
            self.db_manager.cleanup()


def create_heartbeat_monitor(config: Dict[str, Any]) -> HeartbeatMonitor:
    """
    Create a heartbeat monitor instance.

    Args:
        config: Configuration dictionary

    Returns:
        Configured HeartbeatMonitor instance
    """
    return HeartbeatMonitor(config)
