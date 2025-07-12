#!/usr/bin/env python3
"""
Authentication routes for user registration, login, and email verification.
"""

import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.dependencies import get_current_user, get_current_verified_user
from server.auth.email import get_email_service
from server.auth.jwt_handler import get_jwt_handler
from server.auth.models import PasswordResetToken, RefreshToken, User
from server.auth.schemas import (
    EmailVerificationResponse,
    ErrorResponse,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    PasswordResetResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    UserResponse,
)
from server.auth.service import AuthService
from server.auth.utils import hash_token, verify_password
from server.database.connection import get_async_db

logger = logging.getLogger(__name__)

# Create limiter
limiter = Limiter(key_func=get_remote_address)

# Create auth service instance
auth_service = AuthService()

# Create router
router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={400: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)

# Initialize services
auth_service = AuthService()


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=201,
    summary="Register new user",
    description="Register a new user account with email verification",
)
@limiter.limit("5 per hour")
async def register(
    request: Request,
    register_data: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
) -> RegisterResponse:
    """
    Register a new user account.

    - **email**: Valid email address (will receive verification email)
    - **username**: 3-30 characters, alphanumeric and underscore only
    - **password**: Minimum 12 characters with complexity requirements

    After registration, a verification email will be sent to the provided email address.
    The user must verify their email before they can log in.
    """
    try:
        # Register user
        user, token = await auth_service.register_user(
            db=db,
            email=register_data.email,
            username=register_data.username,
            password=register_data.password,
        )

        # Log registration activity
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        await auth_service.log_user_activity(
            db=db,
            user_id=user.id,
            activity_type="registration",
            activity_description=f"User {user.username} registered with email {user.email}",
            ip_address=client_ip,
            user_agent=user_agent,
            metadata={"email": user.email, "username": user.username, "email_verified": False},
        )

        # Commit the activity log with the user registration
        await db.commit()

        # Send verification email in background
        email_service = get_email_service()
        background_tasks.add_task(
            email_service.send_verification_email,
            email=user.email,
            username=user.username,
            token=token.token,
        )

        # Return response
        return RegisterResponse(
            user=UserResponse.model_validate(user),
            message="Registration successful. Please check your email to verify your account.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="An error occurred during registration")


@router.get(
    "/verify-email/{token}",
    response_model=EmailVerificationResponse,
    summary="Verify email address",
    description="Verify email address using the token sent via email",
)
async def verify_email(
    token: str, db: AsyncSession = Depends(get_async_db)
) -> EmailVerificationResponse:
    """
    Verify email address using verification token.

    - **token**: Verification token from email

    This endpoint verifies the user's email address and activates their account.
    After successful verification, the user can log in to their account.
    """
    try:
        # Verify email
        user = await auth_service.verify_email(db=db, token=token)

        return EmailVerificationResponse(
            message="Email verified successfully. You can now login.",
            user=UserResponse.model_validate(user),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        raise HTTPException(status_code=500, detail="An error occurred during email verification")


@router.post(
    "/resend-verification",
    response_model=dict,
    summary="Resend verification email",
    description="Resend email verification link",
)
@limiter.limit("3 per hour")
async def resend_verification(
    request: Request,
    data: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Resend verification email.

    - **email**: Email address to resend verification to

    This endpoint allows users to request a new verification email if they
    didn't receive the original one or if it expired.
    """
    # Always return the same response to prevent email enumeration
    response_message = (
        "If the email exists and is unverified, a new verification email has been sent."
    )

    try:
        email = data.get("email", "").lower().strip()
        if not email:
            return {"message": response_message}

        # Find user by email
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        # Only send if user exists and is not verified
        if user and not user.email_verified:
            # Generate new verification token
            verification_token = auth_service.generate_verification_token()
            
            # Update user with new token
            user.email_verification_token = hash_token(verification_token)
            user.email_verification_sent_at = datetime.now(timezone.utc)
            await db.commit()

            # Send verification email
            email_service = await get_email_service()
            background_tasks.add_task(
                email_service.send_verification_email,
                user.email,
                user.username,
                verification_token,
            )

        return {"message": response_message}

    except Exception as e:
        logger.error(f"Resend verification error: {e}")
        return {"message": response_message}


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login",
    description="Login with username/email and password to get JWT tokens",
)
@limiter.limit("5 per minute" if os.getenv("TESTING") != "true" else "100 per minute")
async def login(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
) -> LoginResponse:
    """
    Login with username/email and password.

    - **username**: Username or email address
    - **password**: User password

    Returns JWT access and refresh tokens on successful authentication.
    The access token expires in 15 minutes and should be used for API requests.
    The refresh token expires in 7 days and can be used to get new access tokens.
    """
    # Authenticate user
    user = await auth_service.authenticate_user(
        db=db, username_or_email=login_data.username, password=login_data.password
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.email_verified:
        raise HTTPException(
            status_code=403,
            detail="Email not verified. Please verify your email before logging in.",
        )

    # Get user organizations
    orgs = await auth_service.get_user_organizations(db, user.id)

    # Create tokens
    jwt_handler = get_jwt_handler()
    access_token = jwt_handler.create_access_token(
        {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "organizations": [
                {"id": str(org.id), "slug": org.slug, "role": role} for org, role in orgs
            ],
        }
    )

    refresh_token, token_id = jwt_handler.create_refresh_token(str(user.id))

    # Store refresh token
    db_token = RefreshToken(
        user_id=user.id,
        token_id=token_id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        user_agent=request.headers.get("User-Agent"),
        ip_address=request.client.host if request.client else None,
    )
    db.add(db_token)
    await db.commit()

    # Set secure cookie for refresh token (optional)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,  # 7 days
    )

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=900,  # 15 minutes
    )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    summary="Refresh access token",
    description="Get new access token using refresh token",
)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_async_db),
) -> RefreshTokenResponse:
    """
    Get new access token using refresh token.

    - **refresh_token**: Valid refresh token

    Returns a new access token. The refresh token remains valid until it expires.
    """
    jwt_handler = get_jwt_handler()

    try:
        payload = jwt_handler.decode_token(refresh_data.refresh_token)
    except HTTPException:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify token type
    jwt_handler.verify_token_type(payload, "refresh")

    # Verify refresh token in database
    from uuid import UUID

    from sqlalchemy import select

    user_id = UUID(payload["sub"])
    db_token = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_id == payload["token_id"],
            RefreshToken.user_id == user_id,
            RefreshToken.expires_at > datetime.now(timezone.utc),
            RefreshToken.revoked_at.is_(None),
        )
    )
    db_token = db_token.scalar_one_or_none()

    if not db_token:
        raise HTTPException(
            status_code=401,
            detail="Refresh token not found or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last used
    db_token.last_used_at = datetime.now(timezone.utc)

    # Get user and create new access token
    from uuid import UUID

    user_id = UUID(payload["sub"])
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    orgs = await auth_service.get_user_organizations(db, user.id)

    access_token = jwt_handler.create_access_token(
        {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "organizations": [
                {"id": str(org.id), "slug": org.slug, "role": role} for org, role in orgs
            ],
        }
    )

    await db.commit()

    return RefreshTokenResponse(access_token=access_token, token_type="Bearer", expires_in=900)


@router.post(
    "/logout",
    response_model=dict,
    summary="Logout",
    description="Logout and revoke refresh tokens",
)
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Logout and revoke all user's refresh tokens.

    Requires a valid access token. This will invalidate all refresh tokens
    for the user, effectively logging them out from all devices.
    """
    from sqlalchemy import update

    # Revoke all user's refresh tokens
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == current_user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()

    # Clear refresh token cookie
    response.delete_cookie(key="refresh_token")

    return {"message": "Logged out successfully"}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get current authenticated user information",
)
async def get_me(
    current_user: User = Depends(get_current_verified_user),
) -> UserResponse:
    """
    Get current authenticated user information.

    Requires a valid access token and verified email address.
    """
    return UserResponse.model_validate(current_user)


@router.post(
    "/forgot-password",
    response_model=dict,
    summary="Request password reset",
    description="Request a password reset email",
)
@limiter.limit("3 per hour" if os.getenv("TESTING") != "true" else "100 per minute")
async def forgot_password(
    request: Request,
    forgot_data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Request password reset email.

    - **email**: Email address or username

    This endpoint always returns the same message to prevent user enumeration.
    If the email/username exists and is verified, a reset email will be sent.
    """
    # Always return same message to prevent enumeration
    response_message = "If the email exists, a password reset link has been sent."

    try:
        # Find user by email or username
        from sqlalchemy import or_

        result = await db.execute(
            select(User).where(
                or_(
                    User.email == forgot_data.email.lower(),
                    User.username == forgot_data.email.lower(),
                )
            )
        )
        user = result.scalar_one_or_none()

        if user and user.email_verified and user.is_active:
            # Generate reset token
            import secrets

            token = secrets.token_urlsafe(32)
            token_hash = hash_token(token)

            # Store token
            reset_token = PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            )
            db.add(reset_token)
            await db.commit()

            # Send email in background
            email_service = get_email_service()
            background_tasks.add_task(
                email_service.send_password_reset_email,
                email=user.email,
                username=user.username,
                token=token,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            )

            logger.info(f"Password reset requested for user: {user.username}")

    except Exception as e:
        logger.error(f"Password reset error: {e}")
        # Don't reveal error to user

    return {"message": response_message}


@router.post(
    "/reset-password",
    response_model=PasswordResetResponse,
    summary="Reset password",
    description="Reset password using token from email",
)
async def reset_password(
    request: Request,
    reset_data: ResetPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
) -> PasswordResetResponse:
    """
    Reset password using token.

    - **token**: Reset token from email
    - **password**: New password (min 12 chars with complexity requirements)

    After successful reset, all refresh tokens are invalidated.
    """
    # Verify token
    token_hash = hash_token(reset_data.token)

    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.expires_at > datetime.now(timezone.utc),
            PasswordResetToken.used_at.is_(None),
        )
    )
    reset_token = result.scalar_one_or_none()

    if not reset_token:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token",
        )

    # Get user
    user = await db.get(User, reset_token.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token",
        )

    # Update password
    from server.auth.utils import hash_password

    user.password_hash = hash_password(reset_data.password)
    user.updated_at = datetime.now(timezone.utc)

    # Mark token as used
    reset_token.used_at = datetime.now(timezone.utc)

    # Invalidate all refresh tokens
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )

    await db.commit()

    # Send confirmation email
    email_service = get_email_service()
    background_tasks.add_task(
        email_service.send_password_changed_email,
        email=user.email,
        username=user.username,
    )

    logger.info(f"Password reset successful for user: {user.username}")

    return PasswordResetResponse(message="Password reset successfully")
