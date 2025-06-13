#!/usr/bin/env python3
"""
Application Settings for Prism DNS Server
Handles configuration for authentication, JWT, and other app settings.
"""

import os
import secrets
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application
    APP_NAME: str = "Prism DNS Server"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")

    # JWT Configuration
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        env="SECRET_KEY",
        description="Secret key for JWT signing. Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Security
    BCRYPT_ROUNDS: int = 12
    TOKEN_BLACKLIST_CLEANUP_HOURS: int = 24
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_ATTEMPT_WINDOW_MINUTES: int = 15

    # Email Configuration (from environment)
    MAIL_USERNAME: Optional[str] = Field(None, env="MAIL_USERNAME")
    MAIL_PASSWORD: Optional[str] = Field(None, env="MAIL_PASSWORD")
    MAIL_FROM: str = Field("noreply@prism-dns.local", env="MAIL_FROM")
    MAIL_PORT: int = Field(587, env="MAIL_PORT")
    MAIL_SERVER: str = Field("smtp.gmail.com", env="MAIL_SERVER")
    MAIL_FROM_NAME: str = Field("Prism DNS", env="MAIL_FROM_NAME")
    MAIL_TLS: bool = Field(True, env="MAIL_TLS")
    MAIL_SSL: bool = Field(False, env="MAIL_SSL")
    USE_CREDENTIALS: bool = Field(True, env="USE_CREDENTIALS")
    VALIDATE_CERTS: bool = Field(True, env="VALIDATE_CERTS")

    # Server URLs
    BASE_URL: str = Field("http://localhost:8081", env="BASE_URL")
    FRONTEND_URL: str = Field("http://localhost:8090", env="FRONTEND_URL")

    # Database
    DATABASE_URL: Optional[str] = Field(None, env="DATABASE_URL")

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def get_database_url(self) -> str:
        """Get database URL with fallback to SQLite."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        # Default to SQLite
        db_path = os.environ.get("PRISM_DATABASE_PATH", "./data/prism.db")
        return f"sqlite+aiosqlite:///{db_path}"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Create settings instance
settings = get_settings()