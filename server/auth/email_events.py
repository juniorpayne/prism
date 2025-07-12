#!/usr/bin/env python3
"""
Database models for email events (bounces, complaints, suppressions).
"""

import enum
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID

from server.database.models import Base


class BounceType(enum.Enum):
    """Types of email bounces."""

    PERMANENT = "permanent"
    TRANSIENT = "transient"
    UNDETERMINED = "undetermined"


class EmailBounce(Base):
    """Records email bounce events from AWS SES."""

    __tablename__ = "email_bounces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), nullable=False, index=True)
    bounce_type = Column(Enum(BounceType), nullable=False)
    bounce_subtype = Column(String(50))
    message_id = Column(String(255))
    feedback_id = Column(String(255), unique=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    diagnostic_code = Column(Text)
    reporting_mta = Column(String(255))
    suppressed = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class EmailComplaint(Base):
    """Records email complaint events from AWS SES."""

    __tablename__ = "email_complaints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), nullable=False, index=True)
    complaint_type = Column(String(50))  # e.g., 'abuse', 'fraud'
    message_id = Column(String(255))
    feedback_id = Column(String(255), unique=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    user_agent = Column(String(255))
    suppressed = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class EmailSuppression(Base):
    """Maintains list of suppressed email addresses."""

    __tablename__ = "email_suppressions"

    email = Column(String(255), primary_key=True)
    reason = Column(String(50), nullable=False)  # 'bounce', 'complaint', 'manual'
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True))  # Optional expiry for transient bounces

    def is_active(self) -> bool:
        """Check if suppression is currently active."""
        if self.expires_at is None:
            return True
        return datetime.now(timezone.utc) < self.expires_at
