#!/usr/bin/env python3
"""
Unit tests for email template system.
"""

import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from server.auth.email_providers.exceptions import EmailTemplateError
from server.auth.email_templates.service import EmailTemplateService, get_template_service


class TestEmailTemplateService:
    """Test cases for EmailTemplateService."""

    @pytest.fixture
    def template_service(self):
        """Create an email template service instance."""
        return EmailTemplateService(app_name="Test App", app_url="https://testapp.com")

    def test_initialization(self, template_service):
        """Test template service initialization."""
        assert template_service.app_name == "Test App"
        assert template_service.app_url == "https://testapp.com"
        assert template_service.support_email == "support@prism.thepaynes.ca"
        assert template_service.env is not None

    def test_base_context(self, template_service):
        """Test base context generation."""
        context = template_service._get_base_context()

        assert context["app_name"] == "Test App"
        assert context["app_url"] == "https://testapp.com"
        assert context["support_email"] == "support@prism.thepaynes.ca"
        assert context["current_year"] == datetime.now().year
        assert context["logo_url"] == "https://testapp.com/assets/logo.png"

    @pytest.mark.asyncio
    async def test_render_email_verification(self, template_service):
        """Test rendering email verification template."""
        context = {
            "username": "testuser",
            "verification_url": "https://testapp.com/verify?token=abc123",
            "expiry_hours": 24,
        }

        html, text = await template_service.render_email("email_verification/verify_email", context)

        # Check HTML content
        assert "Welcome to Test App!" in html
        assert "testuser" in html
        assert "https://testapp.com/verify?token=abc123" in html
        assert "Verify Email Address" in html
        assert "24 hours" in html

        # Check text content
        assert "Welcome to Test App!" in text
        assert "testuser" in text
        assert "https://testapp.com/verify?token=abc123" in text
        assert "24 hours" in text

    @pytest.mark.asyncio
    async def test_render_password_reset(self, template_service):
        """Test rendering password reset template."""
        context = {
            "username": "testuser",
            "reset_url": "https://testapp.com/reset?token=xyz789",
            "expiry_hours": 1,
            "request_ip": "192.168.1.1",
        }

        html, text = await template_service.render_email("password_reset/reset_request", context)

        # Check HTML content
        assert "Reset Your Password" in html
        assert "testuser" in html
        assert "https://testapp.com/reset?token=xyz789" in html
        assert "1 hour" in html
        assert "192.168.1.1" in html

        # Check text content
        assert "Reset Your Password" in text
        assert "testuser" in text
        assert "https://testapp.com/reset?token=xyz789" in text

    @pytest.mark.asyncio
    async def test_render_password_changed(self, template_service):
        """Test rendering password changed notification."""
        context = {
            "username": "testuser",
            "change_date": "2025-06-17 10:30 AM",
            "change_ip": "192.168.1.1",
            "device_info": "Chrome on Windows",
        }

        html, text = await template_service.render_email("password_reset/reset_success", context)

        # Check content
        assert "Password Changed Successfully" in html
        assert "Password Changed Successfully" in text
        assert "2025-06-17 10:30 AM" in html
        assert "192.168.1.1" in html
        assert "Chrome on Windows" in html

    @pytest.mark.asyncio
    async def test_render_welcome_email(self, template_service):
        """Test rendering welcome email."""
        context = {
            "username": "newuser",
        }

        html, text = await template_service.render_email("welcome/welcome", context)

        # Check content
        assert "Welcome to Test App, newuser!" in html
        assert "Welcome to Test App, newuser!" in text
        assert "Getting Started" in html
        assert "Install the Prism Client" in html
        assert "Go to Dashboard" in html

    @pytest.mark.asyncio
    async def test_render_security_alert(self, template_service):
        """Test rendering security alert email."""
        context = {
            "username": "testuser",
            "login_date": "2025-06-17 3:45 PM",
            "device_info": "iPhone",
            "browser_info": "Safari 17",
            "login_ip": "203.0.113.45",
            "location": "San Francisco, CA",
        }

        html, text = await template_service.render_email("security/new_device", context)

        # Check content
        assert "New Device Login Detected" in html
        assert "New Device Login Detected" in text
        assert "iPhone" in html
        assert "Safari 17" in html
        assert "203.0.113.45" in html
        assert "San Francisco, CA" in html
        assert "Secure Your Account" in html

    @pytest.mark.asyncio
    async def test_render_account_deletion(self, template_service):
        """Test rendering account deletion confirmation."""
        context = {
            "username": "deleteduser",
            "email": "deleted@example.com",
            "deletion_date": "2025-06-17",
            "request_ip": "192.168.1.1",
        }

        html, text = await template_service.render_email("account/deletion_confirm", context)

        # Check content
        assert "Your Account Has Been Deleted" in html
        assert "Your Account Has Been Deleted" in text
        assert "deleted@example.com" in html
        assert "2025-06-17" in html
        assert "cannot be undone" in html

    @pytest.mark.asyncio
    async def test_template_not_found(self, template_service):
        """Test handling of missing template."""
        with pytest.raises(EmailTemplateError) as exc_info:
            await template_service.render_email("nonexistent/template")

        assert "Email template not found" in str(exc_info.value)
        assert exc_info.value.details["template_name"] == "nonexistent/template"

    @pytest.mark.asyncio
    async def test_auto_generate_text_from_html(self, template_service):
        """Test auto-generation of text from HTML when text template is missing."""
        # Create a test HTML template without corresponding text template
        test_html = """
        <html>
        <body>
            <h1>Test Email</h1>
            <p>This is a <strong>test</strong> email.</p>
            <a href="https://example.com">Click here</a>
        </body>
        </html>
        """

        with patch.object(template_service.env, "get_template") as mock_get_template:
            # Mock HTML template exists
            html_template = MagicMock()
            html_template.render.return_value = test_html

            # Mock text template not found
            def side_effect(template_name):
                if template_name.endswith(".html"):
                    return html_template
                else:
                    from jinja2 import TemplateNotFound

                    raise TemplateNotFound(template_name)

            mock_get_template.side_effect = side_effect

            html, text = await template_service.render_email("test/email", {})

            # Check that text was generated from HTML
            assert "Test Email" in text
            assert "test email" in text
            assert "Click here" in text
            assert "<strong>" not in text  # HTML tags should be removed

    @pytest.mark.asyncio
    async def test_css_inlining(self, template_service):
        """Test CSS inlining for email compatibility."""
        # Test that _inline_css method works
        html_with_style = """
        <html>
        <head>
            <style>
                .button { background-color: blue; color: white; }
            </style>
        </head>
        <body>
            <a class="button">Click me</a>
        </body>
        </html>
        """

        inlined = template_service._inline_css(html_with_style)

        # Should have inlined styles
        assert "style=" in inlined
        # Original style tag should be removed
        assert "<style>" not in inlined or "keep_style_tags" in inlined

    def test_get_available_templates(self, template_service):
        """Test getting list of available templates."""
        templates = template_service.get_available_templates()

        # Check that all our templates are found
        expected_templates = [
            "base/base.html",
            "base/base.txt",
            "email_verification/verify_email.html",
            "email_verification/verify_email.txt",
            "password_reset/reset_request.html",
            "password_reset/reset_request.txt",
            "password_reset/reset_success.html",
            "password_reset/reset_success.txt",
            "welcome/welcome.html",
            "welcome/welcome.txt",
            "security/new_device.html",
            "security/new_device.txt",
            "account/deletion_confirm.html",
            "account/deletion_confirm.txt",
        ]

        for expected in expected_templates:
            assert expected in templates

    def test_validate_template(self, template_service):
        """Test template validation."""
        # Valid templates
        assert template_service.validate_template("email_verification/verify_email") is True
        assert template_service.validate_template("password_reset/reset_request") is True

        # Invalid template
        assert template_service.validate_template("nonexistent/template") is False

    def test_singleton_pattern(self):
        """Test that get_template_service returns singleton."""
        service1 = get_template_service()
        service2 = get_template_service()

        assert service1 is service2

    @pytest.mark.asyncio
    async def test_template_inheritance(self, template_service):
        """Test that templates properly inherit from base template."""
        html, text = await template_service.render_email(
            "email_verification/verify_email",
            {
                "username": "testuser",
                "verification_url": "https://test.com/verify",
            },
        )

        # Check base template elements are present
        assert "<!DOCTYPE html>" in html
        assert "Test App" in html  # From base template
        assert "© " in html  # Copyright from base
        assert "support@prism.thepaynes.ca" in html  # Support email from base

        # Check text base elements
        assert "Test App" in text
        assert "================" in text  # Separator from base
        assert "© " in text

    @pytest.mark.asyncio
    async def test_context_sanitization(self, template_service):
        """Test that email content is sanitized."""
        context = {
            "username": "test\r\nBcc: hacker@evil.com\r\n\r\nuser",
            "verification_url": "https://test.com/verify",
        }

        html, text = await template_service.render_email("email_verification/verify_email", context)

        # Check that newlines are removed (sanitized)
        assert "\r\n" not in html
        assert "\r\n" not in text
        assert "Bcc: hacker@evil.com" not in html.replace(" ", "")

    @pytest.mark.asyncio
    async def test_template_with_missing_context(self, template_service):
        """Test rendering with missing context variables."""
        # Render with minimal context
        html, text = await template_service.render_email(
            "email_verification/verify_email",
            {
                "verification_url": "https://test.com/verify",
            },
        )

        # Should use defaults
        assert "Hi there," in html  # Default username
        assert "24 hours" in html  # Default expiry

    @pytest.mark.asyncio
    async def test_template_rendering_error(self, template_service):
        """Test handling of template rendering errors."""
        with patch.object(template_service.env, "get_template") as mock_get_template:
            # Mock template that raises error during render
            mock_template = MagicMock()
            mock_template.render.side_effect = Exception("Render error")
            mock_get_template.return_value = mock_template

            with pytest.raises(EmailTemplateError) as exc_info:
                await template_service.render_email("test/template", {})

            assert "Failed to render email template" in str(exc_info.value)
