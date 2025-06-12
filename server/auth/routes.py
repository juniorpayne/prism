#!/usr/bin/env python3
"""
Authentication routes for user registration, login, and email verification.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.email import get_email_service
from server.auth.schemas import (
    EmailVerificationResponse,
    ErrorResponse,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
)
from server.auth.service import AuthService
from server.database.connection import get_async_db

logger = logging.getLogger(__name__)

# Create limiter
limiter = Limiter(key_func=get_remote_address)

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
    email: str,
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
        # TODO: Implement resend verification logic
        # For now, just return the message
        return {"message": response_message}

    except Exception as e:
        logger.error(f"Resend verification error: {e}")
        return {"message": response_message}
