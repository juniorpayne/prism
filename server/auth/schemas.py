#!/usr/bin/env python3
"""
Pydantic schemas for authentication requests and responses.
"""

import re
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=12)

    @field_validator("username")
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not re.match(r"^[a-zA-Z0-9_]{3,30}$", v):
            raise ValueError("Username must be 3-30 characters, alphanumeric and underscore only")
        return v.lower()

    @field_validator("password")
    def validate_password(cls, v: str) -> str:
        """Validate password complexity."""
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


class UserResponse(BaseModel):
    """User response model."""

    id: UUID
    email: str
    username: str
    email_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RegisterResponse(BaseModel):
    """Registration response."""

    user: UserResponse
    message: str = "Registration successful. Please check your email to verify your account."


class LoginRequest(BaseModel):
    """Login request."""

    username: str  # Can be username or email
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int = 900  # 15 minutes


LoginResponse = TokenResponse  # Alias for compatibility
RefreshTokenResponse = TokenResponse  # Alias for compatibility


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    """Forgot password request."""

    email: str  # Can be email or username


class ResetPasswordRequest(BaseModel):
    """Reset password request."""

    token: str
    password: str = Field(..., min_length=12)

    @field_validator("password")
    def validate_password(cls, v: str) -> str:
        """Validate password complexity."""
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


class OrganizationResponse(BaseModel):
    """Organization response model."""

    id: UUID
    name: str
    slug: str
    owner_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class UserOrganizationResponse(BaseModel):
    """User's organization with role."""

    organization: OrganizationResponse
    role: str
    joined_at: datetime


class EmailVerificationResponse(BaseModel):
    """Email verification response."""

    message: str = "Email verified successfully. You can now login."
    user: Optional[UserResponse] = None


class PasswordResetResponse(BaseModel):
    """Password reset response."""

    message: str


class ErrorResponse(BaseModel):
    """Error response model."""

    detail: str
    code: Optional[str] = None
    field: Optional[str] = None
