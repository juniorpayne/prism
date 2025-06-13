#!/usr/bin/env python3
"""
Authentication Utilities
Helper functions for password hashing and token management.
"""

import hashlib
import secrets
from typing import Optional

import bcrypt

from ..settings import get_settings


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    settings = get_settings()
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches, False otherwise
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def hash_token(token: str) -> str:
    """
    Create a SHA256 hash of a token for storage.

    Args:
        token: Token to hash

    Returns:
        Hashed token
    """
    return hashlib.sha256(token.encode()).hexdigest()


def generate_token(length: int = 32) -> str:
    """
    Generate a secure random token.

    Args:
        length: Token length in bytes

    Returns:
        URL-safe token string
    """
    return secrets.token_urlsafe(length)


def generate_verification_code(length: int = 6) -> str:
    """
    Generate a numeric verification code.

    Args:
        length: Code length

    Returns:
        Numeric code string
    """
    return "".join(secrets.choice("0123456789") for _ in range(length))