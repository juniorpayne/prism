#!/usr/bin/env python3
"""
JWT Token Management for Prism DNS Server
Handles creation and validation of access and refresh tokens.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException, status
from jose import JWTError, jwt

from ..settings import get_settings


class JWTHandler:
    """Handles JWT token creation and validation."""

    def __init__(self):
        """Initialize JWT handler with settings."""
        settings = get_settings()
        self.secret_key = settings.SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire = timedelta(minutes=15)
        self.refresh_token_expire = timedelta(days=7)

    def create_access_token(self, user_data: Dict[str, Any]) -> str:
        """
        Create an access token for a user.

        Args:
            user_data: Dictionary containing user information

        Returns:
            Encoded JWT access token
        """
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_data["id"]),
            "email": user_data["email"],
            "username": user_data["username"],
            "organizations": user_data.get("organizations", []),
            "iat": now,
            "exp": now + self.access_token_expire,
            "type": "access",
            "jti": secrets.token_urlsafe(16),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str) -> Tuple[str, str]:
        """
        Create a refresh token for a user.

        Args:
            user_id: User ID

        Returns:
            Tuple of (encoded refresh token, token ID)
        """
        token_id = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + self.refresh_token_expire,
            "type": "refresh",
            "token_id": token_id,
            "jti": secrets.token_urlsafe(16),
        }
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, token_id

    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode and validate a JWT token.

        Args:
            token: Encoded JWT token

        Returns:
            Decoded token payload

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def verify_token_type(self, payload: Dict[str, Any], expected_type: str) -> None:
        """
        Verify that a token has the expected type.

        Args:
            payload: Decoded token payload
            expected_type: Expected token type ("access" or "refresh")

        Raises:
            HTTPException: If token type doesn't match
        """
        if payload.get("type") != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {expected_type}",
                headers={"WWW-Authenticate": "Bearer"},
            )


# Singleton instance
_jwt_handler: Optional[JWTHandler] = None


def get_jwt_handler() -> JWTHandler:
    """Get the singleton JWT handler instance."""
    global _jwt_handler
    if _jwt_handler is None:
        _jwt_handler = JWTHandler()
    return _jwt_handler