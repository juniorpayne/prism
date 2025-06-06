#!/usr/bin/env python3
"""
Database CRUD Operations for Prism DNS Server (SCRUM-13)
Host record management and database operations.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import and_, or_, func, desc

from .models import Host
from .connection import DatabaseManager


logger = logging.getLogger(__name__)


class HostOperations:
    """
    CRUD operations for Host records.

    Provides comprehensive database operations for managing host registrations,
    including creation, updates, queries, and maintenance operations.
    """

    def __init__(self, database_manager: DatabaseManager):
        """
        Initialize host operations.

        Args:
            database_manager: Database manager instance
        """
        self.db_manager = database_manager

    def create_host(self, hostname: str, ip_address: str) -> Optional[Host]:
        """
        Create a new host record.

        Args:
            hostname: Client hostname
            ip_address: Client IP address

        Returns:
            Created Host instance or None if creation failed

        Raises:
            ValueError: If hostname or IP address is invalid
            IntegrityError: If hostname already exists
        """
        try:
            with self.db_manager.get_session() as session:
                # Create new host instance
                host = Host(hostname=hostname, current_ip=ip_address, status="online")

                session.add(host)
                session.flush()  # Get the ID without committing

                logger.info(f"Created new host: {hostname} ({ip_address})")
                return host

        except IntegrityError as e:
            logger.error(f"Host already exists: {hostname}")
            raise
        except ValueError as e:
            logger.error(f"Invalid host data: {e}")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error creating host {hostname}: {e}")
            return None

    def get_host_by_hostname(self, hostname: str) -> Optional[Host]:
        """
        Retrieve host by hostname.

        Args:
            hostname: Hostname to search for

        Returns:
            Host instance or None if not found
        """
        try:
            with self.db_manager.get_session() as session:
                host = session.query(Host).filter(Host.hostname == hostname).first()
                return host

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving host {hostname}: {e}")
            return None

    def get_host_by_id(self, host_id: int) -> Optional[Host]:
        """
        Retrieve host by ID.

        Args:
            host_id: Host ID to search for

        Returns:
            Host instance or None if not found
        """
        try:
            with self.db_manager.get_session() as session:
                host = session.query(Host).filter(Host.id == host_id).first()
                return host

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving host ID {host_id}: {e}")
            return None

    def update_host_ip(self, hostname: str, new_ip: str) -> bool:
        """
        Update host IP address.

        Args:
            hostname: Hostname to update
            new_ip: New IP address

        Returns:
            True if update successful, False otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                host = session.query(Host).filter(Host.hostname == hostname).first()

                if not host:
                    logger.warning(f"Host not found for IP update: {hostname}")
                    return False

                old_ip = host.current_ip
                host.update_ip(new_ip)

                if old_ip != new_ip:
                    logger.info(f"Updated IP for {hostname}: {old_ip} -> {new_ip}")

                return True

        except ValueError as e:
            logger.error(f"Invalid IP address for {hostname}: {e}")
            return False
        except SQLAlchemyError as e:
            logger.error(f"Database error updating IP for {hostname}: {e}")
            return False

    def update_host_last_seen(self, hostname: str) -> bool:
        """
        Update host last seen timestamp.

        Args:
            hostname: Hostname to update

        Returns:
            True if update successful, False otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                host = session.query(Host).filter(Host.hostname == hostname).first()

                if not host:
                    logger.warning(f"Host not found for last_seen update: {hostname}")
                    return False

                host.update_last_seen()
                host.set_online()  # Ensure host is marked online

                return True

        except SQLAlchemyError as e:
            logger.error(f"Database error updating last_seen for {hostname}: {e}")
            return False

    def get_all_hosts(self, limit: Optional[int] = None, offset: int = 0) -> List[Host]:
        """
        Retrieve all hosts with optional pagination.

        Args:
            limit: Maximum number of hosts to return
            offset: Number of hosts to skip

        Returns:
            List of Host instances
        """
        try:
            with self.db_manager.get_session() as session:
                query = session.query(Host).order_by(desc(Host.last_seen))

                if offset > 0:
                    query = query.offset(offset)

                if limit:
                    query = query.limit(limit)

                hosts = query.all()
                return hosts

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving all hosts: {e}")
            return []

    def get_hosts_by_status(self, status: str, limit: Optional[int] = None) -> List[Host]:
        """
        Retrieve hosts by status.

        Args:
            status: Host status ('online' or 'offline')
            limit: Maximum number of hosts to return

        Returns:
            List of Host instances
        """
        try:
            with self.db_manager.get_session() as session:
                query = (
                    session.query(Host).filter(Host.status == status).order_by(desc(Host.last_seen))
                )

                if limit:
                    query = query.limit(limit)

                hosts = query.all()
                return hosts

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving hosts by status {status}: {e}")
            return []

    def mark_host_offline(self, hostname: str) -> bool:
        """
        Mark host as offline.

        Args:
            hostname: Hostname to mark offline

        Returns:
            True if update successful, False otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                host = session.query(Host).filter(Host.hostname == hostname).first()

                if not host:
                    logger.warning(f"Host not found for offline marking: {hostname}")
                    return False

                if host.is_online():
                    host.set_offline()
                    logger.info(f"Marked host offline: {hostname}")

                return True

        except SQLAlchemyError as e:
            logger.error(f"Database error marking host offline {hostname}: {e}")
            return False

    def mark_hosts_offline_by_timeout(self, timeout_threshold: datetime) -> int:
        """
        Mark hosts offline based on timeout threshold.

        Args:
            timeout_threshold: Hosts with last_seen before this time are marked offline

        Returns:
            Number of hosts marked offline
        """
        try:
            with self.db_manager.get_session() as session:
                # Find online hosts that have timed out
                timed_out_hosts = (
                    session.query(Host)
                    .filter(and_(Host.status == "online", Host.last_seen < timeout_threshold))
                    .all()
                )

                count = 0
                for host in timed_out_hosts:
                    host.set_offline()
                    count += 1
                    logger.info(f"Marked host offline due to timeout: {host.hostname}")

                return count

        except SQLAlchemyError as e:
            logger.error(f"Database error marking hosts offline by timeout: {e}")
            return 0

    def cleanup_old_hosts(self, older_than_days: int) -> int:
        """
        Remove hosts that have been offline for a specified period.

        Args:
            older_than_days: Remove hosts offline for more than this many days

        Returns:
            Number of hosts removed
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)

            with self.db_manager.get_session() as session:
                # Find old offline hosts
                old_hosts = (
                    session.query(Host)
                    .filter(and_(Host.status == "offline", Host.last_seen < cutoff_date))
                    .all()
                )

                count = len(old_hosts)

                for host in old_hosts:
                    logger.info(f"Removing old offline host: {host.hostname}")
                    session.delete(host)

                return count

        except SQLAlchemyError as e:
            logger.error(f"Database error cleaning up old hosts: {e}")
            return 0

    def host_exists(self, hostname: str) -> bool:
        """
        Check if host exists in database.

        Args:
            hostname: Hostname to check

        Returns:
            True if host exists, False otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                exists = session.query(Host).filter(Host.hostname == hostname).first() is not None
                return exists

        except SQLAlchemyError as e:
            logger.error(f"Database error checking host existence {hostname}: {e}")
            return False

    def get_host_count(self) -> int:
        """
        Get total number of hosts.

        Returns:
            Total host count
        """
        try:
            with self.db_manager.get_session() as session:
                count = session.query(func.count(Host.id)).scalar()
                return count or 0

        except SQLAlchemyError as e:
            logger.error(f"Database error getting host count: {e}")
            return 0

    def get_host_count_by_status(self, status: str) -> int:
        """
        Get number of hosts by status.

        Args:
            status: Host status to count

        Returns:
            Number of hosts with specified status
        """
        try:
            with self.db_manager.get_session() as session:
                count = session.query(func.count(Host.id)).filter(Host.status == status).scalar()
                return count or 0

        except SQLAlchemyError as e:
            logger.error(f"Database error getting host count by status {status}: {e}")
            return 0

    def get_hosts_by_ip_pattern(self, ip_pattern: str) -> List[Host]:
        """
        Get hosts matching IP pattern.

        Args:
            ip_pattern: IP pattern to match (supports SQL LIKE patterns)

        Returns:
            List of matching hosts
        """
        try:
            with self.db_manager.get_session() as session:
                hosts = (
                    session.query(Host)
                    .filter(Host.current_ip.like(ip_pattern))
                    .order_by(Host.hostname)
                    .all()
                )

                return hosts

        except SQLAlchemyError as e:
            logger.error(f"Database error searching hosts by IP pattern {ip_pattern}: {e}")
            return []

    def get_recently_seen_hosts(self, hours: int = 24) -> List[Host]:
        """
        Get hosts seen within the specified time period.

        Args:
            hours: Time period in hours

        Returns:
            List of recently seen hosts
        """
        try:
            since_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            with self.db_manager.get_session() as session:
                hosts = (
                    session.query(Host)
                    .filter(Host.last_seen >= since_time)
                    .order_by(desc(Host.last_seen))
                    .all()
                )

                return hosts

        except SQLAlchemyError as e:
            logger.error(f"Database error getting recently seen hosts: {e}")
            return []

    def get_host_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive host statistics.

        Returns:
            Dictionary with various host statistics
        """
        try:
            with self.db_manager.get_session() as session:
                total_hosts = session.query(func.count(Host.id)).scalar() or 0
                online_hosts = (
                    session.query(func.count(Host.id)).filter(Host.status == "online").scalar() or 0
                )
                offline_hosts = (
                    session.query(func.count(Host.id)).filter(Host.status == "offline").scalar()
                    or 0
                )

                # Recent activity (last 24 hours)
                since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
                recent_hosts = (
                    session.query(func.count(Host.id)).filter(Host.last_seen >= since_24h).scalar()
                    or 0
                )

                # Oldest and newest hosts
                oldest_host = session.query(Host).order_by(Host.first_seen).first()
                newest_host = session.query(Host).order_by(desc(Host.first_seen)).first()

                return {
                    "total_hosts": total_hosts,
                    "online_hosts": online_hosts,
                    "offline_hosts": offline_hosts,
                    "recent_activity_24h": recent_hosts,
                    "oldest_host_date": oldest_host.first_seen.isoformat() if oldest_host else None,
                    "newest_host_date": newest_host.first_seen.isoformat() if newest_host else None,
                }

        except SQLAlchemyError as e:
            logger.error(f"Database error getting host statistics: {e}")
            return {
                "total_hosts": 0,
                "online_hosts": 0,
                "offline_hosts": 0,
                "recent_activity_24h": 0,
                "oldest_host_date": None,
                "newest_host_date": None,
            }
