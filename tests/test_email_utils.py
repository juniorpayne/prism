#!/usr/bin/env python3
"""
Unit tests for email provider utilities.
"""

import os
from unittest.mock import patch

import pytest

from server.auth.email_providers.utils import (
    create_default_email_config,
    extract_domain_from_email,
    get_email_provider_from_env,
    is_disposable_email,
    sanitize_email_content,
    validate_email_address,
    validate_email_list,
)


class TestEmailValidation:
    """Test email validation functions."""

    def test_validate_email_address_valid(self):
        """Test valid email addresses."""
        valid_emails = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.co.uk",
            "user123@sub.example.com",
            "user_name@example-domain.com",
        ]

        for email in valid_emails:
            assert validate_email_address(email) is True, f"{email} should be valid"

    def test_validate_email_address_invalid(self):
        """Test invalid email addresses."""
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "user@@example.com",
            "user@example",
            "user @example.com",
            "user@example .com",
            "",
        ]

        for email in invalid_emails:
            assert validate_email_address(email) is False, f"{email} should be invalid"

    def test_validate_email_list(self):
        """Test validating a list of email addresses."""
        emails = [
            "valid@example.com",
            "invalid@",
            "also.valid@example.com",
            "not-an-email",
            "good@example.co.uk",
        ]

        invalid = validate_email_list(emails)

        assert len(invalid) == 2
        assert "invalid@" in invalid
        assert "not-an-email" in invalid

    def test_validate_email_list_all_valid(self):
        """Test validating all valid emails."""
        emails = ["user1@example.com", "user2@example.com", "user3@example.com"]

        invalid = validate_email_list(emails)

        assert len(invalid) == 0


class TestEmailContentSanitization:
    """Test email content sanitization."""

    def test_sanitize_email_content_removes_newlines(self):
        """Test that newlines are removed from content."""
        content = "Subject: Test\r\nBcc: hacker@evil.com\r\n\r\nMessage body"
        sanitized = sanitize_email_content(content)

        assert "\r" not in sanitized
        assert "\n" not in sanitized
        # Multiple newlines are replaced with single spaces
        # The exact number of spaces depends on regex implementation
        assert "Subject: Test" in sanitized
        assert "Bcc: hacker@evil.com" in sanitized
        assert "Message body" in sanitized

    def test_sanitize_email_content_strips_whitespace(self):
        """Test that content is stripped."""
        content = "  Some content with spaces  "
        sanitized = sanitize_email_content(content)

        assert sanitized == "Some content with spaces"

    def test_sanitize_email_content_empty(self):
        """Test sanitizing empty content."""
        assert sanitize_email_content("") == ""
        assert sanitize_email_content("   ") == ""


class TestEmailDomainExtraction:
    """Test domain extraction from email addresses."""

    def test_extract_domain_valid(self):
        """Test extracting domain from valid emails."""
        test_cases = [
            ("user@example.com", "example.com"),
            ("user@sub.example.com", "sub.example.com"),
            ("user+tag@example.co.uk", "example.co.uk"),
            ("user.name@my-domain.com", "my-domain.com"),
        ]

        for email, expected_domain in test_cases:
            domain = extract_domain_from_email(email)
            assert domain == expected_domain, f"Expected {expected_domain} from {email}"

    def test_extract_domain_invalid(self):
        """Test extracting domain from invalid emails."""
        invalid_emails = ["not-an-email", "@example.com", "user@", "user@@example.com"]

        for email in invalid_emails:
            domain = extract_domain_from_email(email)
            assert domain is None, f"Should return None for {email}"


class TestDisposableEmailDetection:
    """Test disposable email detection."""

    def test_is_disposable_email_known_domains(self):
        """Test detection of known disposable domains."""
        disposable_emails = [
            "user@mailinator.com",
            "test@guerrillamail.com",
            "temp@10minutemail.com",
            "fake@yopmail.com",
        ]

        for email in disposable_emails:
            assert is_disposable_email(email) is True, f"{email} should be disposable"

    def test_is_disposable_email_regular_domains(self):
        """Test regular domains are not marked as disposable."""
        regular_emails = [
            "user@gmail.com",
            "user@yahoo.com",
            "user@company.com",
            "user@university.edu",
        ]

        for email in regular_emails:
            assert is_disposable_email(email) is False, f"{email} should not be disposable"

    def test_is_disposable_email_case_insensitive(self):
        """Test that detection is case insensitive."""
        assert is_disposable_email("USER@MAILINATOR.COM") is True
        assert is_disposable_email("User@Mailinator.Com") is True


class TestEmailProviderConfiguration:
    """Test email provider configuration from environment."""

    def test_get_email_provider_from_env_default(self):
        """Test default configuration when no env vars are set."""
        with patch.dict(os.environ, {}, clear=True):
            config = get_email_provider_from_env()

            assert config["provider"] == "console"

    def test_get_email_provider_from_env_console(self):
        """Test console provider configuration from env."""
        env_vars = {
            "EMAIL_PROVIDER": "console",
            "EMAIL_CONSOLE_FORMAT": "json",
            "EMAIL_CONSOLE_USE_COLORS": "true",
            "EMAIL_CONSOLE_HIGHLIGHT_LINKS": "false",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = get_email_provider_from_env()

            assert config["provider"] == "console"
            assert config["format"] == "json"
            assert config["use_colors"] is True
            assert config["highlight_links"] is False

    def test_get_email_provider_from_env_smtp(self):
        """Test SMTP provider configuration from env."""
        env_vars = {
            "EMAIL_PROVIDER": "smtp",
            "EMAIL_SMTP_HOST": "smtp.gmail.com",
            "EMAIL_SMTP_PORT": "465",
            "EMAIL_SMTP_USERNAME": "user@gmail.com",
            "EMAIL_SMTP_PASSWORD": "app-password",
            "EMAIL_SMTP_USE_TLS": "false",
            "EMAIL_SMTP_USE_SSL": "true",
            "EMAIL_FROM_ADDRESS": "noreply@example.com",
            "EMAIL_FROM_NAME": "My App",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = get_email_provider_from_env()

            assert config["provider"] == "smtp"
            assert config["host"] == "smtp.gmail.com"
            assert config["port"] == "465"
            assert config["username"] == "user@gmail.com"
            assert config["password"] == "app-password"
            assert config["use_tls"] is False
            assert config["use_ssl"] is True
            assert config["from_email"] == "noreply@example.com"
            assert config["from_name"] == "My App"

    def test_get_email_provider_from_env_case_insensitive(self):
        """Test that provider name is case insensitive."""
        with patch.dict(os.environ, {"EMAIL_PROVIDER": "SMTP"}, clear=True):
            config = get_email_provider_from_env()
            assert config["provider"] == "smtp"

    def test_create_default_email_config(self):
        """Test creating default email configuration."""
        config = create_default_email_config()

        assert config["provider"] == "console"
        assert config["format"] == "pretty"
        assert config["use_colors"] is False
        assert config["highlight_links"] is True
        assert config["from_email"] == "noreply@prism.local"
        assert config["from_name"] == "Prism DNS (Dev)"
