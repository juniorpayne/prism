#!/usr/bin/env python3
"""
Authentication service for user registration and verification.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import uuid4

import bcrypt
from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.models import (
    EmailVerificationToken,
    Organization,
    RefreshToken,
    User,
    UserOrganization,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Service for handling authentication operations."""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against hash.

        Args:
            plain_password: Plain text password
            hashed_password: Bcrypt hash

        Returns:
            True if password matches
        """
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

    @staticmethod
    def generate_verification_token() -> str:
        """Generate secure random token for email verification."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_slug(name: str) -> str:
        """
        Generate URL-safe slug from name.

        Args:
            name: Organization or user name

        Returns:
            URL-safe slug
        """
        # Simple slug generation - can be enhanced
        slug = name.lower().strip()
        slug = "".join(c if c.isalnum() or c == "-" else "-" for c in slug)
        slug = "-".join(filter(None, slug.split("-")))
        return slug[:100]  # Max 100 chars

    async def register_user(
        self, db: AsyncSession, email: str, username: str, password: str
    ) -> Tuple[User, EmailVerificationToken]:
        """
        Register a new user with email verification.

        Args:
            db: Database session
            email: User email
            username: Username
            password: Plain text password

        Returns:
            Tuple of (User, EmailVerificationToken)

        Raises:
            HTTPException: If email or username already exists
        """
        # Check if email or username already exists
        existing = await db.execute(
            select(User).where(or_(User.email == email.lower(), User.username == username.lower()))
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email or username already registered")

        # Create user
        user = User(
            email=email.lower(),
            username=username.lower(),
            password_hash=self.hash_password(password),
        )
        db.add(user)

        # Flush to get user ID
        await db.flush()

        # Create verification token
        token = EmailVerificationToken(
            user_id=user.id,
            token=self.generate_verification_token(),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        db.add(token)

        # Commit to get IDs
        await db.commit()
        await db.refresh(user)
        await db.refresh(token)

        logger.info(f"User registered: {user.username} ({user.email})")

        return user, token

    async def verify_email(self, db: AsyncSession, token: str) -> User:
        """
        Verify user email with token.

        Args:
            db: Database session
            token: Verification token

        Returns:
            Verified user

        Raises:
            HTTPException: If token is invalid, expired, or already used
        """
        # Find token
        result = await db.execute(
            select(EmailVerificationToken).where(EmailVerificationToken.token == token)
        )
        verification_token = result.scalar_one_or_none()

        if not verification_token:
            raise HTTPException(status_code=400, detail="Invalid verification token")

        if verification_token.is_expired():
            raise HTTPException(status_code=400, detail="Verification token has expired")

        if verification_token.is_used():
            raise HTTPException(status_code=400, detail="Verification token has already been used")

        # Get user
        result = await db.execute(select(User).where(User.id == verification_token.user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.email_verified:
            raise HTTPException(status_code=400, detail="Email already verified")

        # Mark email as verified
        user.email_verified = True
        user.email_verified_at = datetime.now(timezone.utc)

        # Mark token as used
        verification_token.used_at = datetime.now(timezone.utc)

        # Create default organization for user
        org = await self._create_default_organization(db, user)

        await db.commit()
        await db.refresh(user)

        logger.info(f"Email verified for user: {user.username}")

        return user

    async def _create_default_organization(self, db: AsyncSession, user: User) -> Organization:
        """
        Create default organization for new user.

        Args:
            db: Database session
            user: User to create org for

        Returns:
            Created organization
        """
        # Generate unique slug
        base_slug = self.generate_slug(f"{user.username}-org")
        slug = base_slug
        counter = 1

        while True:
            existing = await db.execute(select(Organization).where(Organization.slug == slug))
            if not existing.scalar_one_or_none():
                break
            slug = f"{base_slug}-{counter}"
            counter += 1

        # Create organization
        org = Organization(name=f"{user.username}'s Organization", slug=slug, owner_id=user.id)
        db.add(org)

        # Flush to get organization ID
        await db.flush()

        # Add user as owner
        membership = UserOrganization(user_id=user.id, org_id=org.id, role="owner")
        db.add(membership)

        logger.info(f"Created default organization for user: {user.username}")

        return org

    async def authenticate_user(
        self, db: AsyncSession, username_or_email: str, password: str
    ) -> Optional[User]:
        """
        Authenticate user with username/email and password.

        Args:
            db: Database session
            username_or_email: Username or email
            password: Plain text password

        Returns:
            User if authenticated, None otherwise
        """
        # Find user by username or email
        result = await db.execute(
            select(User).where(
                or_(
                    User.email == username_or_email.lower(),
                    User.username == username_or_email.lower(),
                )
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        if not self.verify_password(password, user.password_hash):
            return None

        if not user.is_active:
            return None

        if not user.email_verified:
            raise HTTPException(
                status_code=400, detail="Email not verified. Please check your email."
            )

        return user

    async def get_user_organizations(self, db: AsyncSession, user_id: str) -> list[tuple[Organization, str]]:
        """
        Get user's organizations with roles.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            List of tuples (Organization, role)
        """
        result = await db.execute(
            select(Organization, UserOrganization.role)
            .join(UserOrganization, Organization.id == UserOrganization.org_id)
            .where(UserOrganization.user_id == user_id)
        )

        return result.all()
