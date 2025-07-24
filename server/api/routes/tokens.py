#!/usr/bin/env python3
"""
Token Generation API Endpoints (SCRUM-137)
Provides endpoints for creating and managing API tokens for TCP client authentication.
"""

import json
import secrets
import string
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.dependencies import get_current_verified_user
from server.auth.models import User, APIToken, UserActivity
from server.database.connection import get_async_db
from server.utils.rate_limit import check_rate_limit

# Create router
router = APIRouter(prefix="/v1/tokens", tags=["tokens"])


# Request/Response Models
class TokenCreateRequest(BaseModel):
    """Request model for token creation."""
    name: str = Field(..., min_length=1, max_length=255)
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)


class TokenResponse(BaseModel):
    """Response model for token creation (includes plain token)."""
    id: str
    name: str
    token: str  # Only returned on creation
    expires_at: Optional[datetime]
    created_at: datetime


class TokenListResponse(BaseModel):
    """Response model for listing tokens (no plain token)."""
    id: str
    name: str
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime


@router.post("", response_model=TokenResponse)
async def create_token(
    request: TokenCreateRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_db)
) -> TokenResponse:
    """Generate a new API token for TCP client authentication."""
    # Rate limiting check
    recent_tokens = await db.execute(
        select(APIToken).where(
            APIToken.user_id == current_user.id,
            APIToken.created_at > datetime.now(timezone.utc) - timedelta(hours=1)
        )
    )
    recent_count = len(recent_tokens.scalars().all())
    
    if recent_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 10 tokens per hour."
        )
    
    # Generate secure random token
    alphabet = string.ascii_letters + string.digits
    plain_token = ''.join(secrets.choice(alphabet) for _ in range(32))
    
    # Calculate expiration
    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_in_days)
    
    # Create token record
    api_token = APIToken(
        user_id=current_user.id,
        name=request.name,
        token_hash=APIToken.hash_token(plain_token),
        expires_at=expires_at
    )
    
    db.add(api_token)
    await db.commit()
    await db.refresh(api_token)
    
    return TokenResponse(
        id=str(api_token.id),
        name=api_token.name,
        token=plain_token,  # Return plain token only once
        expires_at=api_token.expires_at,
        created_at=api_token.created_at
    )


@router.get("", response_model=List[TokenListResponse])
async def list_tokens(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_db)
) -> List[TokenListResponse]:
    """List all API tokens for the current user."""
    result = await db.execute(
        select(APIToken)
        .where(APIToken.user_id == current_user.id)
        .order_by(APIToken.created_at.desc())
    )
    tokens = result.scalars().all()
    
    return [
        TokenListResponse(
            id=str(token.id),
            name=token.name,
            last_used_at=token.last_used_at,
            expires_at=token.expires_at,
            is_active=token.is_active,
            created_at=token.created_at
        )
        for token in tokens
    ]


@router.delete("/{token_id}")
async def revoke_token(
    token_id: str,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Revoke an API token."""
    # Validate UUID format
    try:
        token_uuid = UUID(token_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token ID format"
        )
    
    # Find token
    result = await db.execute(
        select(APIToken).where(
            APIToken.id == token_uuid,
            APIToken.user_id == current_user.id
        )
    )
    token = result.scalar_one_or_none()
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )
    
    if not token.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token is already revoked"
        )
    
    # Revoke token
    token.is_active = False
    token.revoked_at = datetime.now(timezone.utc)
    token.revoked_by = current_user.id
    
    # Log the revocation
    activity = UserActivity(
        user_id=current_user.id,
        activity_type="token_revoked",
        activity_description=f"Revoked API token: {token.name}",
        activity_metadata=json.dumps({
            "token_id": str(token.id),
            "token_name": token.name
        })
    )
    db.add(activity)
    
    await db.commit()
    
    # Send notification email (if implemented)
    # if current_user.email_verified:
    #     await send_token_revoked_email(current_user, token)
    
    return {
        "message": "Token revoked successfully",
        "token_id": str(token.id),
        "revoked_at": token.revoked_at.isoformat()
    }


@router.post("/revoke-all")
async def revoke_all_tokens(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Emergency endpoint to revoke all user's tokens."""
    # Rate limit this endpoint heavily
    if not await check_rate_limit(f"revoke_all:{current_user.id}", max_attempts=1, window=3600):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. You can only revoke all tokens once per hour."
        )
    
    # Revoke all active tokens
    result = await db.execute(
        select(APIToken).where(
            APIToken.user_id == current_user.id,
            APIToken.is_active == True
        )
    )
    tokens = result.scalars().all()
    
    revoked_count = 0
    for token in tokens:
        token.is_active = False
        token.revoked_at = datetime.now(timezone.utc)
        token.revoked_by = current_user.id
        revoked_count += 1
    
    # Log the bulk revocation
    if revoked_count > 0:
        activity = UserActivity(
            user_id=current_user.id,
            activity_type="all_tokens_revoked",
            activity_description=f"Revoked all {revoked_count} API tokens",
            activity_metadata=json.dumps({
                "revoked_count": revoked_count
            })
        )
        db.add(activity)
    
    await db.commit()
    
    # Send notification (if implemented)
    # if current_user.email_verified and revoked_count > 0:
    #     await send_all_tokens_revoked_email(current_user, revoked_count)
    
    return {
        "message": f"Revoked {revoked_count} tokens",
        "revoked_count": revoked_count
    }