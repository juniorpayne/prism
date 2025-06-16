#!/usr/bin/env python3
"""
User Profile Management Routes
Provides endpoints for user profile operations including view, update, delete, and activity logs.
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, Field, validator
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.dependencies import get_current_user, get_current_verified_user
from server.auth.models import RefreshToken, TokenBlacklist, User, UserActivity
from server.auth.service import AuthService
from server.auth.utils import verify_password
from server.database.connection import get_async_db

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/users", tags=["users"])

# Response Models
class UserProfileResponse(BaseModel):
    """User profile response model."""
    id: str
    email: EmailStr
    username: str
    full_name: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]
    email_verified: bool
    is_active: bool
    mfa_enabled: bool
    created_at: datetime
    updated_at: datetime
    settings: dict

    class Config:
        from_attributes = True


class UserActivityResponse(BaseModel):
    """User activity response model."""
    id: str
    activity_type: str
    activity_description: str
    ip_address: Optional[str]
    created_at: datetime
    metadata: dict

    class Config:
        from_attributes = True


class UserSettings(BaseModel):
    """User settings model."""
    email_notifications: bool = True
    newsletter: bool = False
    theme: str = Field(default="light", pattern="^(light|dark)$")
    language: str = "en"
    timezone: str = "UTC"
    session_timeout: int = Field(default=30, ge=5, le=1440)  # 5 min to 24 hours


# Request Models
class UserProfileUpdate(BaseModel):
    """User profile update request."""
    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = None

    @validator("avatar_url")
    def validate_avatar_url(cls, v):
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("Avatar URL must be a valid HTTP/HTTPS URL")
        return v


class PasswordChangeRequest(BaseModel):
    """Password change request."""
    current_password: str
    new_password: str

    @validator("new_password")
    def validate_new_password(cls, v):
        # Same validation as registration
        import re
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain number")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Password must contain special character")
        return v


class AccountDeleteRequest(BaseModel):
    """Account deletion request."""
    password: str
    confirmation: str = Field(..., pattern="^DELETE MY ACCOUNT$")


class UserSettingsUpdate(BaseModel):
    """User settings update request."""
    email_notifications: Optional[bool] = None
    newsletter: Optional[bool] = None
    theme: Optional[str] = Field(None, pattern="^(light|dark)$")
    language: Optional[str] = None
    timezone: Optional[str] = None
    session_timeout: Optional[int] = Field(None, ge=5, le=1440)


# Get current user profile
@router.get("/me", response_model=UserProfileResponse, summary="Get current user profile")
async def get_profile(
    current_user: User = Depends(get_current_verified_user),
) -> UserProfileResponse:
    """
    Get the current authenticated user's profile.
    
    Requires email verification.
    """
    return UserProfileResponse(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        bio=current_user.bio,
        avatar_url=current_user.avatar_url,
        email_verified=current_user.email_verified,
        is_active=current_user.is_active,
        mfa_enabled=current_user.mfa_enabled,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        settings=json.loads(current_user.settings) if current_user.settings else {},
    )


# Update user profile
@router.put("/me", response_model=UserProfileResponse, summary="Update user profile")
async def update_profile(
    request: Request,
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_db),
) -> UserProfileResponse:
    """
    Update the current user's profile fields.
    
    Only provided fields will be updated.
    """
    auth_service = AuthService()
    
    # Update only provided fields
    update_data = profile_update.dict(exclude_unset=True)
    
    if update_data:
        for field, value in update_data.items():
            setattr(current_user, field, value)
        
        current_user.updated_at = datetime.now(timezone.utc)
        
        # Log activity
        await auth_service.log_user_activity(
            db=db,
            user_id=current_user.id,
            activity_type="profile_updated",
            activity_description=f"Updated profile fields: {', '.join(update_data.keys())}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"updated_fields": list(update_data.keys())}
        )
        
        await db.commit()
        await db.refresh(current_user)
    
    return UserProfileResponse(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        bio=current_user.bio,
        avatar_url=current_user.avatar_url,
        email_verified=current_user.email_verified,
        is_active=current_user.is_active,
        mfa_enabled=current_user.mfa_enabled,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        settings=json.loads(current_user.settings) if current_user.settings else {},
    )


# Change password
@router.put("/me/password", summary="Change user password")
async def change_password(
    request: Request,
    password_change: PasswordChangeRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Change the current user's password.
    
    Requires current password verification.
    All existing tokens will be invalidated.
    """
    auth_service = AuthService()
    
    # Verify current password
    if not verify_password(password_change.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.password_hash = auth_service.hash_password(password_change.new_password)
    current_user.updated_at = datetime.now(timezone.utc)
    
    # Invalidate all existing refresh tokens for this user
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.is_active == True
        )
    )
    refresh_tokens = result.scalars().all()
    
    for token in refresh_tokens:
        token.is_active = False
        # Add to blacklist
        blacklist_entry = TokenBlacklist(
            token=token.token,
            token_type="refresh",
            expires_at=token.expires_at,
            reason="password_changed"
        )
        db.add(blacklist_entry)
    
    # Log activity
    await auth_service.log_user_activity(
        db=db,
        user_id=current_user.id,
        activity_type="password_changed",
        activity_description="User changed their password",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"tokens_invalidated": len(refresh_tokens)}
    )
    
    await db.commit()
    
    return {
        "message": "Password changed successfully. Please login again with your new password."
    }


# Delete account
@router.delete("/me", summary="Delete user account")
async def delete_account(
    request: Request,
    delete_request: AccountDeleteRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Delete the current user's account.
    
    Requires password verification and confirmation text.
    Account will be soft-deleted (marked as inactive).
    """
    auth_service = AuthService()
    
    # Verify password
    if not verify_password(delete_request.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is incorrect"
        )
    
    # Log activity before deletion
    await auth_service.log_user_activity(
        db=db,
        user_id=current_user.id,
        activity_type="account_deleted",
        activity_description="User deleted their account",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"username": current_user.username, "email": current_user.email}
    )
    
    # Soft delete (mark as inactive)
    current_user.is_active = False
    current_user.updated_at = datetime.now(timezone.utc)
    
    # Invalidate all tokens
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.is_active == True
        )
    )
    refresh_tokens = result.scalars().all()
    
    for token in refresh_tokens:
        token.is_active = False
        # Add to blacklist
        blacklist_entry = TokenBlacklist(
            token=token.token,
            token_type="refresh",
            expires_at=token.expires_at,
            reason="account_deleted"
        )
        db.add(blacklist_entry)
    
    await db.commit()
    
    return {
        "message": "Your account has been deleted successfully."
    }


# Get user activity log
@router.get("/me/activity", response_model=List[UserActivityResponse], summary="Get user activity log")
async def get_activity_log(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_db),
) -> List[UserActivityResponse]:
    """
    Get the current user's activity log with pagination.
    
    Returns activities in reverse chronological order.
    """
    offset = (page - 1) * limit
    
    result = await db.execute(
        select(UserActivity)
        .where(UserActivity.user_id == current_user.id)
        .order_by(desc(UserActivity.created_at))
        .offset(offset)
        .limit(limit)
    )
    activities = result.scalars().all()
    
    return [
        UserActivityResponse(
            id=str(activity.id),
            activity_type=activity.activity_type,
            activity_description=activity.activity_description,
            ip_address=activity.ip_address,
            created_at=activity.created_at,
            metadata=json.loads(activity.activity_metadata) if activity.activity_metadata else {}
        )
        for activity in activities
    ]


# Get user settings
@router.get("/me/settings", response_model=UserSettings, summary="Get user settings")
async def get_settings(
    current_user: User = Depends(get_current_verified_user),
) -> UserSettings:
    """
    Get the current user's settings.
    """
    settings = json.loads(current_user.settings) if current_user.settings else {}
    return UserSettings(**settings)


# Update user settings
@router.put("/me/settings", response_model=UserSettings, summary="Update user settings")
async def update_settings(
    request: Request,
    settings_update: UserSettingsUpdate,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_async_db),
) -> UserSettings:
    """
    Update the current user's settings.
    
    Only provided fields will be updated.
    """
    auth_service = AuthService()
    
    # Get current settings
    current_settings = json.loads(current_user.settings) if current_user.settings else {}
    
    # Update with new values
    update_data = settings_update.dict(exclude_unset=True)
    
    if update_data:
        current_settings.update(update_data)
        
        # Save back to user
        current_user.settings = json.dumps(current_settings)
        current_user.updated_at = datetime.now(timezone.utc)
        
        # Log activity
        await auth_service.log_user_activity(
            db=db,
            user_id=current_user.id,
            activity_type="settings_updated",
            activity_description=f"Updated settings: {', '.join(update_data.keys())}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"updated_fields": list(update_data.keys())}
        )
        
        await db.commit()
    
    return UserSettings(**current_settings)