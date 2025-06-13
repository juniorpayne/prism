#!/usr/bin/env python3
"""
Test fixtures for authentication tests.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.models import User, Organization, UserOrganization
from server.auth.utils import hash_password
from server.auth.jwt_handler import get_jwt_handler


@pytest_asyncio.fixture
async def verified_user(db_session: AsyncSession) -> User:
    """Create a verified user for testing."""
    user = User(
        email="test@example.com",
        username="testuser",
        password_hash=hash_password("TestPassword123!"),
        email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def unverified_user(db_session: AsyncSession) -> User:
    """Create an unverified user for testing."""
    user = User(
        email="unverified@example.com",
        username="unverified",
        password_hash=hash_password("TestPassword123!"),
        email_verified=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def verified_user_with_org(db_session: AsyncSession) -> tuple[User, Organization]:
    """Create a verified user with an organization."""
    user = User(
        email="owner@example.com",
        username="owner",
        password_hash=hash_password("TestPassword123!"),
        email_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    org = Organization(
        name="Test Organization",
        slug="test-org",
        owner_id=user.id,
    )
    db_session.add(org)
    await db_session.flush()
    
    membership = UserOrganization(
        user_id=user.id,
        org_id=org.id,
        role="owner",
    )
    db_session.add(membership)
    
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(org)
    
    return user, org


@pytest.fixture
def auth_headers(verified_user: User) -> dict:
    """Create authorization headers with a valid access token."""
    jwt_handler = get_jwt_handler()
    access_token = jwt_handler.create_access_token(
        {
            "id": str(verified_user.id),
            "email": verified_user.email,
            "username": verified_user.username,
            "organizations": [],
        }
    )
    return {"Authorization": f"Bearer {access_token}"}