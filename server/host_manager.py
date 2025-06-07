#!/usr/bin/env python3
"""
Host Manager for Prism DNS Server (SCRUM-15)
Advanced host record management and operations.
"""

import asyncio
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .database.connection import DatabaseManager
from .database.models import Host
from .database.operations import HostOperations

logger = logging.getLogger(__name__)


@dataclass
class HostRegistrationResult:
    """Result of a host registration operation."""

    success: bool
    action: str  # created, updated_ip, updated_timestamp, reactivated, error
    hostname: str
    ip_address: str
    previous_ip: Optional[str] = None
    previous_status: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class HostInfo:
    """Host information data structure."""

    hostname: str
    current_ip: str
    status: str
    first_seen: datetime
    last_seen: datetime
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert host info to dictionary."""
        return asdict(self)

    @classmethod
    def from_host_model(cls, host: Host) -> "HostInfo":
        """Create HostInfo from database Host model."""
        return cls(
            hostname=host.hostname,
            current_ip=host.current_ip,
            status=host.status,
            first_seen=host.first_seen,
            last_seen=host.last_seen,
            created_at=getattr(host, "created_at", None),
            updated_at=getattr(host, "updated_at", None),
        )


class HostManagerConfig:
    """Configuration for host manager."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize host manager configuration."""
        host_config = config.get("host_management", {})

        self.status_check_interval = host_config.get("status_check_interval", 30)
        self.offline_threshold_multiplier = host_config.get("offline_threshold_multiplier", 2)
        self.cleanup_offline_after_days = host_config.get("cleanup_offline_after_days", 30)
        self.enable_auto_cleanup = host_config.get("enable_auto_cleanup", True)
        self.max_hosts_per_operation = host_config.get("max_hosts_per_operation", 1000)

        logger.info(
            f"Host manager configured: status_check={self.status_check_interval}s, "
            f"cleanup_after={self.cleanup_offline_after_days}d"
        )


class HostManager:
    """
    Advanced host record management.

    Provides high-level operations for host registration, status management,
    and maintenance operations.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize host manager.

        Args:
            config: Configuration dictionary
        """
        self.config = HostManagerConfig(config)

        # Initialize database connection
        self.db_manager = DatabaseManager(config)
        self.db_manager.initialize_schema()
        self.host_ops = HostOperations(self.db_manager)

        # Statistics
        self._stats = {
            "hosts_created": 0,
            "hosts_updated": 0,
            "hosts_reactivated": 0,
            "hosts_deleted": 0,
            "ip_changes_processed": 0,
            "status_changes_processed": 0,
        }

        logger.info("HostManager initialized")

    async def register_host(self, hostname: str, ip_address: str) -> HostRegistrationResult:
        """
        Register or update a host.

        Args:
            hostname: Hostname to register
            ip_address: IP address to associate

        Returns:
            HostRegistrationResult with operation details
        """
        try:
            # Check if host exists
            existing_host = self.host_ops.get_host_by_hostname(hostname)

            if existing_host is None:
                # Create new host
                new_host = self.host_ops.create_host(hostname, ip_address)
                if new_host:
                    self._stats["hosts_created"] += 1

                    logger.info(f"Created new host: {hostname} ({ip_address})")

                    return HostRegistrationResult(
                        success=True,
                        action="created",
                        hostname=hostname,
                        ip_address=ip_address,
                        message=f"New host created with IP {ip_address}",
                    )
                else:
                    return HostRegistrationResult(
                        success=False,
                        action="error",
                        hostname=hostname,
                        ip_address=ip_address,
                        message="Failed to create host record",
                    )
            else:
                # Update existing host
                return await self._update_existing_host(existing_host, hostname, ip_address)

        except Exception as e:
            logger.error(f"Error registering host {hostname}: {e}")
            return HostRegistrationResult(
                success=False,
                action="error",
                hostname=hostname,
                ip_address=ip_address,
                message=f"Registration error: {str(e)}",
            )

    async def _update_existing_host(
        self, existing_host: Host, hostname: str, ip_address: str
    ) -> HostRegistrationResult:
        """
        Update existing host record.

        Args:
            existing_host: Existing host record
            hostname: Hostname
            ip_address: New IP address

        Returns:
            HostRegistrationResult with operation details
        """
        previous_ip = existing_host.current_ip
        previous_status = existing_host.status

        # Check if host was offline and is now coming back online
        if existing_host.status == "offline":
            # Reactivation
            if existing_host.current_ip != ip_address:
                # IP changed during offline period
                success = self.host_ops.update_host_ip(hostname, ip_address)
                if success:
                    self.host_ops.update_host_last_seen(hostname)
                    self._stats["hosts_reactivated"] += 1
                    self._stats["ip_changes_processed"] += 1

                    logger.info(
                        f"Host reactivated with IP change: {hostname} "
                        f"{previous_ip} -> {ip_address}"
                    )

                    return HostRegistrationResult(
                        success=True,
                        action="reactivated",
                        hostname=hostname,
                        ip_address=ip_address,
                        previous_ip=previous_ip,
                        previous_status=previous_status,
                        message=f"Host reactivated with IP change from {previous_ip}",
                    )
            else:
                # Same IP, just reactivation
                success = self.host_ops.update_host_last_seen(hostname)
                if success:
                    self._stats["hosts_reactivated"] += 1

                    logger.info(f"Host reactivated: {hostname} ({ip_address})")

                    return HostRegistrationResult(
                        success=True,
                        action="reactivated",
                        hostname=hostname,
                        ip_address=ip_address,
                        previous_status=previous_status,
                        message="Host reactivated",
                    )

        elif existing_host.current_ip != ip_address:
            # IP address changed
            success = self.host_ops.update_host_ip(hostname, ip_address)
            if success:
                self.host_ops.update_host_last_seen(hostname)
                self._stats["ip_changes_processed"] += 1

                logger.info(f"IP address updated: {hostname} {previous_ip} -> {ip_address}")

                return HostRegistrationResult(
                    success=True,
                    action="updated_ip",
                    hostname=hostname,
                    ip_address=ip_address,
                    previous_ip=previous_ip,
                    message=f"IP updated from {previous_ip}",
                )
        else:
            # Same IP, just timestamp update
            success = self.host_ops.update_host_last_seen(hostname)
            if success:
                self._stats["hosts_updated"] += 1

                logger.debug(f"Timestamp updated: {hostname} ({ip_address})")

                return HostRegistrationResult(
                    success=True,
                    action="updated_timestamp",
                    hostname=hostname,
                    ip_address=ip_address,
                    message="Last seen timestamp updated",
                )

        # If we get here, the update failed
        return HostRegistrationResult(
            success=False,
            action="error",
            hostname=hostname,
            ip_address=ip_address,
            message="Failed to update host record",
        )

    async def get_host_info(self, hostname: str) -> Optional[HostInfo]:
        """
        Get detailed host information.

        Args:
            hostname: Hostname to look up

        Returns:
            HostInfo object or None if not found
        """
        try:
            host = self.host_ops.get_host_by_hostname(hostname)
            if host:
                return HostInfo.from_host_model(host)
            return None

        except Exception as e:
            logger.error(f"Error getting host info for {hostname}: {e}")
            return None

    async def list_hosts_by_status(self, status: str) -> List[HostInfo]:
        """
        List hosts by status.

        Args:
            status: Status to filter by ('online', 'offline')

        Returns:
            List of HostInfo objects
        """
        try:
            hosts = self.host_ops.get_hosts_by_status(status)
            return [HostInfo.from_host_model(host) for host in hosts]

        except Exception as e:
            logger.error(f"Error listing hosts by status {status}: {e}")
            return []

    async def list_all_hosts(self, limit: Optional[int] = None) -> List[HostInfo]:
        """
        List all hosts.

        Args:
            limit: Optional limit on number of hosts to return

        Returns:
            List of HostInfo objects
        """
        try:
            hosts = self.host_ops.get_all_hosts()

            if limit:
                hosts = hosts[:limit]

            return [HostInfo.from_host_model(host) for host in hosts]

        except Exception as e:
            logger.error(f"Error listing all hosts: {e}")
            return []

    async def get_host_count(self) -> int:
        """
        Get total number of hosts.

        Returns:
            Total host count
        """
        try:
            return self.host_ops.get_host_count()
        except Exception as e:
            logger.error(f"Error getting host count: {e}")
            return 0

    async def get_host_count_by_status(self, status: str) -> int:
        """
        Get number of hosts by status.

        Args:
            status: Status to count ('online', 'offline')

        Returns:
            Number of hosts with specified status
        """
        try:
            return self.host_ops.get_host_count_by_status(status)
        except Exception as e:
            logger.error(f"Error getting host count by status {status}: {e}")
            return 0

    async def host_exists(self, hostname: str) -> bool:
        """
        Check if host exists.

        Args:
            hostname: Hostname to check

        Returns:
            True if host exists, False otherwise
        """
        try:
            return self.host_ops.host_exists(hostname)
        except Exception as e:
            logger.error(f"Error checking if host exists {hostname}: {e}")
            return False

    async def delete_host(self, hostname: str) -> bool:
        """
        Delete a host.

        Args:
            hostname: Hostname to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get host info before deletion for logging
            host_info = await self.get_host_info(hostname)

            # Delete the host (this method would need to be added to HostOperations)
            success = await self._delete_host_from_database(hostname)

            if success:
                self._stats["hosts_deleted"] += 1

                if host_info:
                    logger.info(f"Host deleted: {hostname} ({host_info.current_ip})")
                else:
                    logger.info(f"Host deleted: {hostname}")

                return True
            else:
                logger.warning(f"Failed to delete host: {hostname}")
                return False

        except Exception as e:
            logger.error(f"Error deleting host {hostname}: {e}")
            return False

    async def _delete_host_from_database(self, hostname: str) -> bool:
        """Delete host from database."""
        try:
            # Use the database session directly since this operation
            # isn't available in HostOperations yet
            from .database.models import Host

            with self.host_ops.db_manager.get_session() as session:
                host = session.query(Host).filter(Host.hostname == hostname).first()
                if host:
                    session.delete(host)
                    session.commit()
                    return True
                return False

        except Exception as e:
            logger.error(f"Database error deleting host {hostname}: {e}")
            return False

    async def cleanup_old_hosts(self, older_than_days: Optional[int] = None) -> int:
        """
        Clean up old offline hosts.

        Args:
            older_than_days: Days to consider for cleanup (uses config default if None)

        Returns:
            Number of hosts cleaned up
        """
        if older_than_days is None:
            older_than_days = self.config.cleanup_offline_after_days

        try:
            cleaned_count = self.host_ops.cleanup_old_hosts(older_than_days)

            if cleaned_count > 0:
                logger.info(
                    f"Cleaned up {cleaned_count} old hosts (offline > {older_than_days} days)"
                )

            return cleaned_count

        except Exception as e:
            logger.error(f"Error cleaning up old hosts: {e}")
            return 0

    async def mark_host_offline(self, hostname: str) -> bool:
        """
        Mark a host as offline.

        Args:
            hostname: Hostname to mark offline

        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.host_ops.mark_host_offline(hostname)

            if success:
                self._stats["status_changes_processed"] += 1
                logger.info(f"Host marked offline: {hostname}")

            return success

        except Exception as e:
            logger.error(f"Error marking host offline {hostname}: {e}")
            return False

    async def get_hosts_last_seen_before(self, cutoff_time: datetime) -> List[HostInfo]:
        """
        Get hosts last seen before a specific time.

        Args:
            cutoff_time: Cutoff time for last seen

        Returns:
            List of HostInfo objects
        """
        try:
            # This would require a new method in HostOperations
            hosts = await self._get_hosts_before_time(cutoff_time)
            return [HostInfo.from_host_model(host) for host in hosts]

        except Exception as e:
            logger.error(f"Error getting hosts before time {cutoff_time}: {e}")
            return []

    async def _get_hosts_before_time(self, cutoff_time: datetime) -> List[Host]:
        """Get hosts from database with last_seen before cutoff time."""
        try:
            from .database.models import Host

            with self.host_ops.db_manager.get_session() as session:
                hosts = session.query(Host).filter(Host.last_seen < cutoff_time).all()

                return hosts

        except Exception as e:
            logger.error(f"Database error getting hosts before time: {e}")
            return []

    def get_host_manager_stats(self) -> Dict[str, Any]:
        """
        Get host manager statistics.

        Returns:
            Dictionary with statistics
        """
        return self._stats.copy()

    def reset_statistics(self) -> None:
        """Reset all statistics counters."""
        for key in self._stats:
            self._stats[key] = 0

        logger.info("Host manager statistics reset")

    async def get_host_summary(self) -> Dict[str, Any]:
        """
        Get summary of all host information.

        Returns:
            Dictionary with host summary statistics
        """
        try:
            total_hosts = await self.get_host_count()
            online_hosts = await self.get_host_count_by_status("online")
            offline_hosts = await self.get_host_count_by_status("offline")

            return {
                "total_hosts": total_hosts,
                "online_hosts": online_hosts,
                "offline_hosts": offline_hosts,
                "host_manager_stats": self.get_host_manager_stats(),
            }

        except Exception as e:
            logger.error(f"Error getting host summary: {e}")
            return {"total_hosts": 0, "online_hosts": 0, "offline_hosts": 0, "error": str(e)}

    def cleanup(self) -> None:
        """Clean up resources."""
        if self.db_manager:
            self.db_manager.cleanup()

        logger.info("HostManager cleanup completed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()


def create_host_manager(config: Dict[str, Any]) -> HostManager:
    """
    Create a host manager instance.

    Args:
        config: Configuration dictionary

    Returns:
        Configured HostManager instance
    """
    return HostManager(config)
