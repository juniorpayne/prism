#!/usr/bin/env python3
"""
Authentication Dependencies for FastAPI
Provides dependency injection for authentication and authorization.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_async_db as get_db
from ..settings import get_settings
from .jwt_handler import get_jwt_handler
from .models import RefreshToken, TokenBlacklist, User, UserOrganization

# Security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials
        db: Database session

    Returns:
        Authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    jwt_handler = get_jwt_handler()

    try:
        payload = jwt_handler.decode_token(token)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify token type
    jwt_handler.verify_token_type(payload, "access")

    # Check if token is blacklisted
    jti = payload.get("jti")
    if jti:
        blacklisted = await db.execute(
            select(TokenBlacklist).where(
                TokenBlacklist.jti == jti,
                TokenBlacklist.expires_at > datetime.now(timezone.utc),
            )
        )
        if blacklisted.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Get user from database
    user_id = UUID(payload["sub"])
    user = await db.execute(select(User).where(User.id == user_id))
    user = user.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current user and ensure email is verified.

    Args:
        current_user: Current authenticated user

    Returns:
        Verified user

    Raises:
        HTTPException: If user email is not verified
    """
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email address.",
        )
    return current_user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise None.

    Args:
        credentials: Optional HTTP Bearer token credentials
        db: Database session

    Returns:
        User if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        # Reuse the main authentication logic
        return await get_current_user(
            HTTPAuthorizationCredentials(
                scheme=credentials.scheme, credentials=credentials.credentials
            ),
            db,
        )
    except HTTPException:
        return None


def require_role(allowed_roles: list[str]):
    """
    Dependency factory for role-based access control.

    Args:
        allowed_roles: List of allowed role names

    Returns:
        Dependency function that checks user roles
    """

    async def role_checker(
        current_user: User = Depends(get_current_verified_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        """Check if user has required role in any organization."""
        # Get user's roles across all organizations
        user_roles = await db.execute(
            select(UserOrganization.role).where(UserOrganization.user_id == current_user.id)
        )
        roles = [r[0] for r in user_roles]

        if not any(role in allowed_roles for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this operation",
            )

        return current_user

    return role_checker


# Common role dependencies
require_admin = require_role(["admin", "owner"])
require_owner = require_role(["owner"])
