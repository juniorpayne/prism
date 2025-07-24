#!/usr/bin/env python3
"""
Authentication models for Prism DNS Server (SCRUM-53).
SQLAlchemy models for user authentication and organizations.
"""

import re
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

import sqlalchemy
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import CHAR, TypeDecorator


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as stringified hex values.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return str(value)
        else:
            if not isinstance(value, uuid4.__class__.__bases__[0]):
                return str(value)
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid4.__class__.__bases__[0]):
                from uuid import UUID

                return UUID(value)
            else:
                return value


from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates

# Import the existing Base from database models
from server.database.models import Base


class User(Base):
    """
    User model for authentication and account management.

    Represents a user account with email verification and organization membership.
    """

    __tablename__ = "users"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Authentication fields
    email = Column(String(255), nullable=False, unique=True, index=True)
    username = Column(String(30), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)

    # Email verification
    email_verified = Column(Boolean, default=False, nullable=False)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String(255), nullable=True)

    # Profile fields
    full_name = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Settings (JSON field for flexible configuration)
    settings = Column(Text, nullable=True, default="{}")  # Will store JSON

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

    # Relationships
    organizations_owned = relationship(
        "Organization", back_populates="owner", foreign_keys="Organization.owner_id"
    )
    organization_memberships = relationship(
        "UserOrganization", back_populates="user", cascade="all, delete-orphan"
    )
    email_verification_tokens = relationship(
        "EmailVerificationToken", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_tokens = relationship(
        "PasswordResetToken", back_populates="user", cascade="all, delete-orphan"
    )
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    activities = relationship("UserActivity", back_populates="user", cascade="all, delete-orphan")
    tcp_tokens = relationship("APIToken", back_populates="user", cascade="all, delete-orphan", foreign_keys="APIToken.user_id")

    @validates("email")
    def validate_email_field(self, key: str, email: str) -> str:
        """Validate email format."""
        email = email.lower().strip()
        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        if not email_pattern.match(email):
            raise ValueError(f"Invalid email format: {email}")
        return email

    @validates("username")
    def validate_username_field(self, key: str, username: str) -> str:
        """Validate username format."""
        username = username.lower().strip()
        if not re.match(r"^[a-zA-Z0-9_]{3,30}$", username):
            raise ValueError("Username must be 3-30 characters, alphanumeric and underscore only")
        return username

    def __str__(self) -> str:
        """String representation of User."""
        return f"User(username='{self.username}', email='{self.email}')"

    def __repr__(self) -> str:
        """Detailed string representation of User."""
        return (
            f"User(id={self.id}, username='{self.username}', "
            f"email='{self.email}', verified={self.email_verified})"
        )

    def has_admin_privileges(self) -> bool:
        """Check if user has admin privileges."""
        return self.is_admin and self.is_active

    def to_dict(self) -> dict:
        """Convert User instance to dictionary."""
        import json

        return {
            "id": str(self.id),
            "email": self.email,
            "username": self.username,
            "email_verified": self.email_verified,
            "email_verified_at": (
                self.email_verified_at.isoformat() if self.email_verified_at else None
            ),
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "mfa_enabled": self.mfa_enabled,
            "full_name": self.full_name,
            "bio": self.bio,
            "avatar_url": self.avatar_url,
            "settings": json.loads(self.settings) if self.settings else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Organization(Base):
    """
    Organization model for multi-tenancy.

    Represents an organization that owns DNS zones and hosts.
    """

    __tablename__ = "organizations"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Organization details
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)

    # Ownership
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Settings (JSON field for flexible configuration)
    settings = Column(Text, nullable=True)  # Will store JSON

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

    # Relationships
    owner = relationship("User", back_populates="organizations_owned")
    user_memberships = relationship(
        "UserOrganization", back_populates="organization", cascade="all, delete-orphan"
    )
    dns_zones = relationship("DNSZone", back_populates="organization", cascade="all, delete-orphan")

    @validates("slug")
    def validate_slug_field(self, key: str, slug: str) -> str:
        """Validate slug format."""
        slug = slug.lower().strip()
        if not re.match(r"^[a-z0-9-]{3,100}$", slug):
            raise ValueError(
                "Slug must be 3-100 characters, lowercase alphanumeric and hyphen only"
            )
        return slug

    def __str__(self) -> str:
        """String representation of Organization."""
        return f"Organization(name='{self.name}', slug='{self.slug}')"

    def to_dict(self) -> dict:
        """Convert Organization instance to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "slug": self.slug,
            "owner_id": str(self.owner_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserOrganization(Base):
    """
    User-Organization association model with roles.

    Represents a user's membership and role in an organization.
    """

    __tablename__ = "user_organizations"

    # Composite primary key
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    org_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )

    # Role in organization
    role = Column(String(50), nullable=False, default="member")

    # Timestamps
    joined_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="organization_memberships")
    organization = relationship("Organization", back_populates="user_memberships")

    # Valid roles
    VALID_ROLES = ["owner", "admin", "member", "viewer"]

    @validates("role")
    def validate_role_field(self, key: str, role: str) -> str:
        """Validate role value."""
        if role not in self.VALID_ROLES:
            raise ValueError(f"Invalid role: {role}. Must be one of: {self.VALID_ROLES}")
        return role


class EmailVerificationToken(Base):
    """
    Email verification token model.

    Stores tokens for email verification with expiration.
    """

    __tablename__ = "email_verification_tokens"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Token details
    token = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="email_verification_tokens")

    def is_expired(self) -> bool:
        """Check if token is expired."""
        now = datetime.now(timezone.utc)
        # Ensure expires_at is timezone-aware
        if self.expires_at.tzinfo is None:
            # If naive, assume UTC
            expires_at = self.expires_at.replace(tzinfo=timezone.utc)
        else:
            expires_at = self.expires_at
        return now > expires_at

    def is_used(self) -> bool:
        """Check if token has been used."""
        return self.used_at is not None


class RefreshToken(Base):
    """
    JWT refresh token storage.

    Stores refresh tokens for session management.
    """

    __tablename__ = "refresh_tokens"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Token details
    token_id = Column(String(255), nullable=False, unique=True, index=True)
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)  # Support IPv4/IPv6

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

    def is_valid(self) -> bool:
        """Check if token is valid (not expired or revoked)."""
        now = datetime.now(timezone.utc)
        return self.expires_at > now and self.revoked_at is None


class PasswordResetToken(Base):
    """
    Password reset token model.

    Stores tokens for password reset with expiration.
    """

    __tablename__ = "password_reset_tokens"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Token details
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="password_reset_tokens")

    def is_valid(self) -> bool:
        """Check if token is valid (not expired or used)."""
        now = datetime.now(timezone.utc)
        return self.expires_at > now and self.used_at is None


class TokenBlacklist(Base):
    """
    Token blacklist for emergency token revocation.

    Stores JTIs of tokens that should be rejected.
    """

    __tablename__ = "token_blacklist"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Token data
    jti = Column(String(255), unique=True, nullable=False, index=True)
    token_type = Column(String(20), nullable=False)  # "access" or "refresh"
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Metadata
    blacklisted_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    reason = Column(Text, nullable=True)


class APIKey(Base):
    """
    API key model for programmatic access.

    Stores API keys for authentication without username/password.
    """

    __tablename__ = "api_keys"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # User and organization reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    org_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )

    # Key details
    key_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    permissions = Column(Text, nullable=True)  # JSON field
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Usage tracking
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="api_keys")

    def is_valid(self) -> bool:
        """Check if API key is valid (not expired)."""
        if self.expires_at is None:
            return True
        return datetime.now(timezone.utc) < self.expires_at


class DNSZone(Base):
    """
    DNS Zone model for zone management.

    Represents a DNS zone owned by an organization.
    """

    __tablename__ = "dns_zones"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Organization reference
    org_id = Column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )

    # Zone details
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False, default="master")  # master, slave
    powerdns_zone_id = Column(String(255), nullable=True)

    # Audit
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Settings (JSON field)
    settings = Column(Text, nullable=True)

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

    # Relationships
    organization = relationship("Organization", back_populates="dns_zones")

    # Unique constraint
    __table_args__ = (UniqueConstraint("org_id", "name", name="_org_zone_uc"),)

    def __str__(self) -> str:
        """String representation of DNSZone."""
        return f"DNSZone(name='{self.name}', type='{self.type}')"


class UserActivity(Base):
    """
    User activity log for tracking user actions.

    Logs important user activities like registration, login, logout,
    profile updates, password changes, etc.
    """

    __tablename__ = "user_activities"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Activity details
    activity_type = Column(String(50), nullable=False)  # e.g., 'registration', 'login', 'logout'
    activity_description = Column(String(255), nullable=False)

    # Request metadata
    ip_address = Column(String(45), nullable=True)  # Supports IPv6
    user_agent = Column(String(500), nullable=True)

    # Additional data (JSON field for flexibility)
    activity_metadata = Column(Text, nullable=True, default="{}")  # Will store JSON

    # Timestamp
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="activities")

    def __str__(self) -> str:
        """String representation of UserActivity."""
        return f"UserActivity(user_id='{self.user_id}', type='{self.activity_type}')"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        import json

        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "activity_type": self.activity_type,
            "activity_description": self.activity_description,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "metadata": json.loads(self.activity_metadata) if self.activity_metadata else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Create indexes for performance
Index("idx_users_email_verified", User.email, User.email_verified)
Index("idx_email_verification_tokens_expires", EmailVerificationToken.expires_at)
Index("idx_refresh_tokens_user_expires", RefreshToken.user_id, RefreshToken.expires_at)
Index("idx_password_reset_tokens_expires", PasswordResetToken.expires_at)
Index("idx_api_keys_user_org", APIKey.user_id, APIKey.org_id)


class APIToken(Base):
    """
    API tokens for TCP client authentication.
    
    Simple token-based authentication for TCP clients to register hosts.
    Follows KISS principle - no JWT, just secure random tokens with DB lookups.
    """

    __tablename__ = "api_tokens"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Token details
    name = Column(String(255), nullable=False)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)

    # Usage tracking
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    last_used_ip = Column(String(45), nullable=True)  # Support IPv6

    # Security
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Revocation tracking
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

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

    # Relationships
    user = relationship("User", back_populates="tcp_tokens", foreign_keys=[user_id])

    def is_valid(self) -> bool:
        """Check if token is valid (active, not revoked, and not expired)."""
        if not self.is_active:
            return False
        if self.revoked_at is not None:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    @staticmethod
    def hash_token(plain_token: str) -> str:
        """Hash a plain text token using bcrypt."""
        import bcrypt
        return bcrypt.hashpw(plain_token.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def verify_token(self, plain_token: str) -> bool:
        """Verify a plain text token against the hash."""
        import bcrypt
        return bcrypt.checkpw(plain_token.encode('utf-8'), self.token_hash.encode('utf-8'))

    def __str__(self) -> str:
        """String representation of APIToken."""
        return f"APIToken(name='{self.name}', user_id='{self.user_id}')"

    def __repr__(self) -> str:
        """Detailed string representation of APIToken."""
        return (
            f"APIToken(id={self.id}, name='{self.name}', "
            f"user_id={self.user_id}, is_active={self.is_active})"
        )


# Create index for APIToken
Index("idx_api_tokens_user_id", APIToken.user_id)
Index("idx_api_tokens_last_used", APIToken.last_used_at)


# Event listeners for automatic timestamp updates
@event.listens_for(User, "before_update")
@event.listens_for(Organization, "before_update")
@event.listens_for(DNSZone, "before_update")
@event.listens_for(APIToken, "before_update")
def update_timestamps(mapper, connection, target):
    """Update timestamps before update operations."""
    target.updated_at = datetime.now(timezone.utc)
