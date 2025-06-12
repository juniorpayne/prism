#!/usr/bin/env python3
"""
Authentication configuration and settings.
"""

import os
from typing import Any, Dict

# Default settings
DEFAULT_SETTINGS = {
    # Email settings
    "email_enabled": os.getenv("EMAIL_ENABLED", "false").lower() == "true",
    "email_host": os.getenv("EMAIL_HOST", "smtp.gmail.com"),
    "email_port": int(os.getenv("EMAIL_PORT", "587")),
    "email_username": os.getenv("EMAIL_USERNAME", ""),
    "email_password": os.getenv("EMAIL_PASSWORD", ""),
    "email_from": os.getenv("EMAIL_FROM", "noreply@prismdns.com"),
    "email_from_name": os.getenv("EMAIL_FROM_NAME", "Prism DNS"),
    "email_use_tls": os.getenv("EMAIL_USE_TLS", "true").lower() == "true",
    # Frontend URL for email links
    "frontend_url": os.getenv("FRONTEND_URL", "http://localhost:8090"),
    # Security settings
    "secret_key": os.getenv("SECRET_KEY", "change-this-in-production"),
    "jwt_algorithm": os.getenv("JWT_ALGORITHM", "HS256"),
    "access_token_expire_minutes": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")),
    "refresh_token_expire_days": int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")),
    # Registration settings
    "registration_enabled": os.getenv("REGISTRATION_ENABLED", "true").lower() == "true",
    "require_email_verification": os.getenv("REQUIRE_EMAIL_VERIFICATION", "true").lower() == "true",
    "email_verification_expiry_hours": int(os.getenv("EMAIL_VERIFICATION_EXPIRY_HOURS", "24")),
}


def get_settings() -> Dict[str, Any]:
    """Get authentication settings."""
    return DEFAULT_SETTINGS
