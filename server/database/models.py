#!/usr/bin/env python3
"""
Database Models for Prism DNS Server (SCRUM-13)
SQLAlchemy models for host registration data.
"""

import ipaddress
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, UniqueConstraint, create_engine, event
from sqlalchemy.orm import declarative_base, validates

# Create the declarative base
Base = declarative_base()


class Host(Base):
    """
    Host model for storing client registration data.

    Represents a client host that registers with the DNS server,
    tracking hostname, IP address, and online status.
    """

    __tablename__ = "hosts"
    
    # Composite unique constraint for user-scoped hostnames (SCRUM-128)
    __table_args__ = (
        UniqueConstraint('hostname', 'created_by', name='uq_hostname_per_user'),
    )

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Host identification
    hostname = Column(String(255), nullable=False, index=True)  # Removed unique=True for user-scoped hostnames
    current_ip = Column(String(45), nullable=False)  # IPv4/IPv6 support

    # Timestamps
    first_seen = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    last_seen = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Status tracking
    status = Column(String(20), nullable=False, default="online", index=True)

    # DNS tracking fields (SCRUM-49)
    dns_zone = Column(String(255), nullable=True)  # DNS zone for this host
    dns_record_id = Column(String(255), nullable=True)  # PowerDNS record identifier
    dns_ttl = Column(Integer, nullable=True)  # Custom TTL for this host
    dns_sync_status = Column(
        String(20), nullable=True, default="pending"
    )  # pending, synced, failed
    dns_last_sync = Column(DateTime(timezone=True), nullable=True)  # Last successful DNS sync

    # Multi-tenancy fields (SCRUM-52)
    org_id = Column(String(36), nullable=True)  # UUID as string for now, will migrate to UUID type
    zone_id = Column(String(36), nullable=True)  # UUID as string for now
    created_by = Column(String(36), nullable=False, index=True)  # User UUID required for isolation (SCRUM-127)

    # Audit timestamps
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __init__(self, hostname: str, current_ip: str, created_by: str = None, **kwargs):
        """
        Initialize Host instance with validation.

        Args:
            hostname: Client hostname
            current_ip: Client IP address
            created_by: User ID who created this host (required)
            **kwargs: Additional fields
        """
        # Validate inputs
        self.validate_hostname(hostname)
        self.validate_ip(current_ip)
        
        # Validate created_by is provided (SCRUM-127)
        if created_by is None and "created_by" not in kwargs:
            raise ValueError("created_by is required for host creation")
        
        # Use provided created_by or from kwargs
        if created_by is not None:
            kwargs["created_by"] = created_by

        # Ensure default status if not provided
        if "status" not in kwargs:
            kwargs["status"] = "online"

        super().__init__(hostname=hostname, current_ip=current_ip, **kwargs)

    def __str__(self) -> str:
        """String representation of Host."""
        return f"Host(hostname='{self.hostname}', ip='{self.current_ip}', status='{self.status}')"

    def __repr__(self) -> str:
        """Detailed string representation of Host."""
        return (
            f"Host(id={self.id}, hostname='{self.hostname}', "
            f"current_ip='{self.current_ip}', status='{self.status}', "
            f"last_seen='{self.last_seen}')"
        )

    @staticmethod
    def validate_hostname(hostname: str) -> None:
        """
        Validate hostname format.

        Args:
            hostname: Hostname to validate

        Raises:
            ValueError: If hostname is invalid
        """
        if not hostname:
            raise ValueError("Hostname cannot be empty")

        if len(hostname) > 255:
            raise ValueError("Hostname too long (max 255 characters)")

        # Basic hostname validation (RFC compliant)
        hostname_pattern = re.compile(
            r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?"
            r"(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
        )

        if not hostname_pattern.match(hostname):
            raise ValueError(f"Invalid hostname format: {hostname}")

    @staticmethod
    def validate_ip(ip_address: str) -> None:
        """
        Validate IP address format.

        Args:
            ip_address: IP address to validate

        Raises:
            ValueError: If IP address is invalid
        """
        if not ip_address:
            raise ValueError("IP address cannot be empty")

        try:
            # This validates both IPv4 and IPv6
            ipaddress.ip_address(ip_address)
        except ValueError as e:
            raise ValueError(f"Invalid IP address format: {ip_address}") from e

    @validates("hostname")
    def validate_hostname_field(self, key: str, hostname: str) -> str:
        """SQLAlchemy validator for hostname field."""
        self.validate_hostname(hostname)
        return hostname

    @validates("current_ip")
    def validate_ip_field(self, key: str, ip_address: str) -> str:
        """SQLAlchemy validator for current_ip field."""
        self.validate_ip(ip_address)
        return ip_address

    @validates("status")
    def validate_status_field(self, key: str, status: str) -> str:
        """SQLAlchemy validator for status field."""
        valid_statuses = ["online", "offline"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of: {valid_statuses}")
        return status

    def is_online(self) -> bool:
        """Check if host is currently online."""
        return self.status == "online"

    def is_offline(self) -> bool:
        """Check if host is currently offline."""
        return self.status == "offline"

    def set_online(self) -> None:
        """Set host status to online."""
        self.status = "online"
        self.last_seen = datetime.now(timezone.utc)

    def set_offline(self) -> None:
        """Set host status to offline."""
        self.status = "offline"

    def update_ip(self, new_ip: str) -> None:
        """
        Update host IP address with validation.

        Args:
            new_ip: New IP address
        """
        self.validate_ip(new_ip)
        self.current_ip = new_ip
        self.last_seen = datetime.now(timezone.utc)

    def update_last_seen(self) -> None:
        """Update the last seen timestamp to current time."""
        self.last_seen = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        """
        Convert Host instance to dictionary.

        Returns:
            Dictionary representation of host
        """
        return {
            "id": self.id,
            "hostname": self.hostname,
            "current_ip": self.current_ip,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "status": self.status,
            "dns_zone": self.dns_zone,
            "dns_record_id": self.dns_record_id,
            "dns_ttl": self.dns_ttl,
            "dns_sync_status": self.dns_sync_status,
            "dns_last_sync": self.dns_last_sync.isoformat() if self.dns_last_sync else None,
            "org_id": self.org_id,
            "zone_id": self.zone_id,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Create additional indexes for performance
Index("idx_hostname_status", Host.hostname, Host.status)
Index("idx_last_seen_status", Host.last_seen, Host.status)


class DNSZoneOwnership(Base):
    """
    DNS Zone ownership model for tracking which zones belong to which users.
    
    This provides a simple way to associate PowerDNS zones with users
    without modifying PowerDNS itself (SCRUM-129).
    """
    
    __tablename__ = "dns_zone_ownership"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Zone identification
    zone_name = Column(String(255), nullable=False, unique=True, index=True)
    
    # User ownership
    created_by = Column(String(36), nullable=False, index=True)  # User UUID
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    
    def __repr__(self):
        """String representation of DNSZoneOwnership."""
        return f"<DNSZoneOwnership(zone_name='{self.zone_name}', created_by='{self.created_by}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert zone to dictionary."""
        return {
            "id": self.id,
            "zone_name": self.zone_name,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Event listeners for automatic timestamp updates
@event.listens_for(Host, "before_update")
def update_timestamps(mapper, connection, target):
    """Update timestamps before update operations."""
    target.updated_at = datetime.now(timezone.utc)


@event.listens_for(DNSZoneOwnership, "before_update")
def update_dns_zone_ownership_timestamps(mapper, connection, target):
    """Update DNS zone ownership timestamps before update operations."""
    target.updated_at = datetime.now(timezone.utc)


# Database schema version for migrations
SCHEMA_VERSION = 7  # Version 7: Add is_admin field to users table (SCRUM-133)
