#!/usr/bin/env python3
"""
IP Change Tracker for Prism DNS Server (SCRUM-15)
Tracks and logs IP address changes for hosts.
"""

import asyncio
import logging
import ipaddress
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict

from .database.connection import DatabaseManager
from .database.operations import HostOperations


logger = logging.getLogger(__name__)


@dataclass
class IPChangeEvent:
    """IP change event data structure."""

    hostname: str
    previous_ip: str
    new_ip: str
    change_time: datetime
    change_reason: str
    detection_method: str = "registration"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class IPChangeDetection:
    """IP change detection result."""

    hostname: str
    previous_ip: str
    new_ip: str
    detected_at: datetime

    def is_valid_change(self) -> bool:
        """Check if this represents a valid IP change."""
        return self.previous_ip != self.new_ip


class IPTrackerConfig:
    """Configuration for IP tracker."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize IP tracker configuration."""
        ip_config = config.get("ip_tracking", {})

        self.enable_change_logging = ip_config.get("enable_change_logging", True)
        self.max_history_entries = ip_config.get("max_history_entries", 1000)
        self.cleanup_history_after_days = ip_config.get("cleanup_history_after_days", 90)
        self.enable_validation = ip_config.get("enable_validation", True)
        self.track_private_ips = ip_config.get("track_private_ips", True)

        logger.info(
            f"IP tracker configured: logging={self.enable_change_logging}, "
            f"history_limit={self.max_history_entries}"
        )


class IPTracker:
    """
    IP address change tracking and logging system.

    Provides detection and logging of IP address changes for registered hosts.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize IP tracker.

        Args:
            config: Configuration dictionary
        """
        self.config = IPTrackerConfig(config)

        # Initialize database connection
        self.db_manager = DatabaseManager(config)
        self.db_manager.initialize_schema()
        self.host_ops = HostOperations(self.db_manager)

        # Initialize change history storage (in-memory for prototype)
        # In production, this would be stored in a dedicated database table
        self._change_history: List[IPChangeEvent] = []

        # Statistics
        self._stats = {
            "total_changes_detected": 0,
            "total_changes_logged": 0,
            "ipv4_changes": 0,
            "ipv6_changes": 0,
            "private_ip_changes": 0,
            "public_ip_changes": 0,
        }

        logger.info("IPTracker initialized")

    async def detect_ip_change(self, hostname: str, new_ip: str) -> Optional[IPChangeDetection]:
        """
        Detect IP address change for a host.

        Args:
            hostname: Hostname to check
            new_ip: New IP address to compare

        Returns:
            IPChangeDetection if change detected, None otherwise
        """
        try:
            # Get current host record
            host = self.host_ops.get_host_by_hostname(hostname)

            if host is None:
                # New host, no previous IP to compare
                return None

            if host.current_ip == new_ip:
                # No change detected
                return None

            # IP change detected
            detection = IPChangeDetection(
                hostname=hostname,
                previous_ip=host.current_ip,
                new_ip=new_ip,
                detected_at=datetime.now(timezone.utc),
            )

            self._stats["total_changes_detected"] += 1

            # Update IP type statistics
            await self._update_ip_type_stats(host.current_ip, new_ip)

            logger.info(f"IP change detected: {hostname} {host.current_ip} -> {new_ip}")

            return detection

        except Exception as e:
            logger.error(f"Error detecting IP change for {hostname}: {e}")
            return None

    async def log_ip_change(
        self,
        hostname: str,
        previous_ip: str,
        new_ip: str,
        change_reason: str = "registration",
        detection_method: str = "registration",
    ) -> None:
        """
        Log an IP address change event.

        Args:
            hostname: Hostname that changed
            previous_ip: Previous IP address
            new_ip: New IP address
            change_reason: Reason for the change
            detection_method: How the change was detected
        """
        if not self.config.enable_change_logging:
            return

        try:
            # Create change event
            change_event = IPChangeEvent(
                hostname=hostname,
                previous_ip=previous_ip,
                new_ip=new_ip,
                change_time=datetime.now(timezone.utc),
                change_reason=change_reason,
                detection_method=detection_method,
            )

            # Store in change history
            self._change_history.append(change_event)

            # Maintain history size limit
            if len(self._change_history) > self.config.max_history_entries:
                # Remove oldest entries
                excess_count = len(self._change_history) - self.config.max_history_entries
                self._change_history = self._change_history[excess_count:]

            self._stats["total_changes_logged"] += 1

            logger.info(
                f"IP change logged: {hostname} {previous_ip} -> {new_ip} "
                f"(reason: {change_reason})"
            )

        except Exception as e:
            logger.error(f"Error logging IP change for {hostname}: {e}")

    async def get_ip_change_history(
        self, hostname: str, limit: Optional[int] = None
    ) -> List[IPChangeEvent]:
        """
        Get IP change history for a specific host.

        Args:
            hostname: Hostname to get history for
            limit: Optional limit on number of entries

        Returns:
            List of IPChangeEvent objects
        """
        try:
            # Filter history by hostname
            host_history = [event for event in self._change_history if event.hostname == hostname]

            # Sort by change time (most recent first)
            host_history.sort(key=lambda x: x.change_time, reverse=True)

            # Apply limit if specified
            if limit:
                host_history = host_history[:limit]

            return host_history

        except Exception as e:
            logger.error(f"Error getting IP change history for {hostname}: {e}")
            return []

    async def get_recent_ip_changes(self, limit: int = 100) -> List[IPChangeEvent]:
        """
        Get recent IP changes across all hosts.

        Args:
            limit: Maximum number of changes to return

        Returns:
            List of recent IPChangeEvent objects
        """
        try:
            # Sort all changes by time (most recent first)
            sorted_changes = sorted(self._change_history, key=lambda x: x.change_time, reverse=True)

            # Apply limit
            return sorted_changes[:limit]

        except Exception as e:
            logger.error(f"Error getting recent IP changes: {e}")
            return []

    async def get_ip_change_statistics(self) -> Dict[str, Any]:
        """
        Get IP change statistics.

        Returns:
            Dictionary with statistics
        """
        try:
            # Calculate additional statistics
            total_unique_hosts = len(set(event.hostname for event in self._change_history))

            changes_by_reason = {}
            for event in self._change_history:
                reason = event.change_reason
                changes_by_reason[reason] = changes_by_reason.get(reason, 0) + 1

            # Get time-based statistics
            now = datetime.now(timezone.utc)
            hour_ago = now - timedelta(hours=1)
            day_ago = now - timedelta(days=1)

            changes_last_hour = len(
                [event for event in self._change_history if event.change_time > hour_ago]
            )

            changes_last_day = len(
                [event for event in self._change_history if event.change_time > day_ago]
            )

            stats = self._stats.copy()
            stats.update(
                {
                    "unique_hosts": total_unique_hosts,
                    "changes_by_reason": changes_by_reason,
                    "changes_last_hour": changes_last_hour,
                    "changes_last_day": changes_last_day,
                    "total_history_entries": len(self._change_history),
                }
            )

            return stats

        except Exception as e:
            logger.error(f"Error getting IP change statistics: {e}")
            return self._stats.copy()

    async def cleanup_old_ip_changes(self, older_than_days: int = 90) -> int:
        """
        Clean up old IP change records.

        Args:
            older_than_days: Remove changes older than this many days

        Returns:
            Number of records cleaned up
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=older_than_days)

            # Count entries to be removed
            old_entries = [
                event for event in self._change_history if event.change_time < cutoff_time
            ]

            removed_count = len(old_entries)

            # Remove old entries
            self._change_history = [
                event for event in self._change_history if event.change_time >= cutoff_time
            ]

            if removed_count > 0:
                logger.info(
                    f"Cleaned up {removed_count} old IP change records "
                    f"(older than {older_than_days} days)"
                )

            return removed_count

        except Exception as e:
            logger.error(f"Error cleaning up old IP changes: {e}")
            return 0

    def validate_ip_address(self, ip_str: str) -> bool:
        """
        Validate IP address format.

        Args:
            ip_str: IP address string to validate

        Returns:
            True if valid, False otherwise
        """
        if not self.config.enable_validation:
            return True

        try:
            ip = ipaddress.ip_address(ip_str)

            # Check if we should track private IPs
            if not self.config.track_private_ips and ip.is_private:
                return False

            return True

        except ValueError:
            return False

    async def _update_ip_type_stats(self, previous_ip: str, new_ip: str) -> None:
        """Update statistics based on IP address types."""
        try:
            # Check IP versions
            try:
                prev_ip = ipaddress.ip_address(previous_ip)
                new_ip_obj = ipaddress.ip_address(new_ip)

                if isinstance(prev_ip, ipaddress.IPv4Address) or isinstance(
                    new_ip_obj, ipaddress.IPv4Address
                ):
                    self._stats["ipv4_changes"] += 1

                if isinstance(prev_ip, ipaddress.IPv6Address) or isinstance(
                    new_ip_obj, ipaddress.IPv6Address
                ):
                    self._stats["ipv6_changes"] += 1

                # Check if private/public
                if prev_ip.is_private or new_ip_obj.is_private:
                    self._stats["private_ip_changes"] += 1
                else:
                    self._stats["public_ip_changes"] += 1

            except ValueError:
                # Invalid IP format, skip statistics update
                pass

        except Exception as e:
            logger.error(f"Error updating IP type statistics: {e}")

    async def get_hosts_with_ip_changes(self, time_window_hours: int = 24) -> List[str]:
        """
        Get list of hostnames that had IP changes within time window.

        Args:
            time_window_hours: Time window in hours

        Returns:
            List of hostnames
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)

            recent_changes = [
                event for event in self._change_history if event.change_time > cutoff_time
            ]

            # Get unique hostnames
            hostnames = list(set(event.hostname for event in recent_changes))

            return hostnames

        except Exception as e:
            logger.error(f"Error getting hosts with IP changes: {e}")
            return []

    async def get_most_frequent_ip_changes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get hosts with most frequent IP changes.

        Args:
            limit: Number of hosts to return

        Returns:
            List of dictionaries with hostname and change count
        """
        try:
            # Count changes per hostname
            change_counts = {}
            for event in self._change_history:
                hostname = event.hostname
                change_counts[hostname] = change_counts.get(hostname, 0) + 1

            # Sort by change count
            sorted_hosts = sorted(change_counts.items(), key=lambda x: x[1], reverse=True)

            # Format results
            result = []
            for hostname, count in sorted_hosts[:limit]:
                result.append({"hostname": hostname, "change_count": count})

            return result

        except Exception as e:
            logger.error(f"Error getting most frequent IP changes: {e}")
            return []

    def reset_statistics(self) -> None:
        """Reset all statistics counters."""
        for key in self._stats:
            self._stats[key] = 0

        logger.info("IP tracker statistics reset")

    def clear_history(self) -> None:
        """Clear all IP change history."""
        cleared_count = len(self._change_history)
        self._change_history.clear()

        logger.info(f"Cleared {cleared_count} IP change history entries")

    def get_tracker_status(self) -> Dict[str, Any]:
        """
        Get IP tracker status information.

        Returns:
            Dictionary with tracker status
        """
        return {
            "enabled": self.config.enable_change_logging,
            "validation_enabled": self.config.enable_validation,
            "track_private_ips": self.config.track_private_ips,
            "max_history_entries": self.config.max_history_entries,
            "current_history_size": len(self._change_history),
            "cleanup_after_days": self.config.cleanup_history_after_days,
        }

    def cleanup(self) -> None:
        """Clean up resources."""
        if self.db_manager:
            self.db_manager.cleanup()

        logger.info("IPTracker cleanup completed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()


def create_ip_tracker(config: Dict[str, Any]) -> IPTracker:
    """
    Create an IP tracker instance.

    Args:
        config: Configuration dictionary

    Returns:
        Configured IPTracker instance
    """
    return IPTracker(config)
