#!/usr/bin/env python3
"""
Database Models for Prism DNS Server (SCRUM-13)
SQLAlchemy models for host registration data.
"""

import re
import ipaddress
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index, create_engine, event
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import validates
from typing import Optional


# Create the declarative base
Base = declarative_base()


class Host(Base):
    """
    Host model for storing client registration data.

    Represents a client host that registers with the DNS server,
    tracking hostname, IP address, and online status.
    """

    __tablename__ = "hosts"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Host identification
    hostname = Column(String(255), nullable=False, unique=True, index=True)
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

    def __init__(self, hostname: str, current_ip: str, **kwargs):
        """
        Initialize Host instance with validation.

        Args:
            hostname: Client hostname
            current_ip: Client IP address
            **kwargs: Additional fields
        """
        # Validate inputs
        self.validate_hostname(hostname)
        self.validate_ip(current_ip)

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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Create additional indexes for performance
Index("idx_hostname_status", Host.hostname, Host.status)
Index("idx_last_seen_status", Host.last_seen, Host.status)


# Event listeners for automatic timestamp updates
@event.listens_for(Host, "before_update")
def update_timestamps(mapper, connection, target):
    """Update timestamps before update operations."""
    target.updated_at = datetime.now(timezone.utc)


# Database schema version for migrations
SCHEMA_VERSION = 1
