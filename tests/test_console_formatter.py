#!/usr/bin/env python3
"""
Unit tests for console email formatter enhancements.
"""

import os
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from server.auth.email_providers import ConsoleEmailProvider, EmailMessage
from server.auth.email_providers.console_formatter import (
    ASCIIBoxFormatter,
    ConsoleFormatter,
    LinkHighlighter,
    TerminalColorDetector,
)


class TestTerminalColorDetector:
    """Test terminal color support detection."""

    def test_detect_tty_support(self):
        """Test TTY support detection."""
        # Mock TTY - create new detector for each test
        with patch("sys.stdout.isatty", return_value=True):
            detector = TerminalColorDetector()
            assert detector.supports_color() is True

        # Mock non-TTY
        with patch("sys.stdout.isatty", return_value=False):
            detector = TerminalColorDetector()
            assert detector.supports_color() is False

    def test_detect_docker_environment(self):
        """Test Docker environment detection."""
        # In Docker container
        with patch("os.path.exists", return_value=True):
            detector = TerminalColorDetector()
            assert detector.is_docker() is True
            # Docker should disable colors by default
            with patch("sys.stdout.isatty", return_value=True):
                detector2 = TerminalColorDetector()
                assert detector2.supports_color() is False

        # Not in Docker
        with patch("os.path.exists", return_value=False):
            detector = TerminalColorDetector()
            assert detector.is_docker() is False

    def test_force_color_environment(self):
        """Test FORCE_COLOR environment variable."""
        with patch.dict(os.environ, {"FORCE_COLOR": "1"}):
            detector = TerminalColorDetector()
            assert detector.supports_color() is True

        with patch.dict(os.environ, {"FORCE_COLOR": "0"}):
            detector = TerminalColorDetector()
            assert detector.supports_color() is False

    def test_ci_environment_detection(self):
        """Test CI environment detection."""
        # GitHub Actions
        with patch.dict(os.environ, {"CI": "true", "GITHUB_ACTIONS": "true"}):
            detector = TerminalColorDetector()
            assert detector.is_ci() is True
            assert detector.supports_color() is False

        # Generic CI
        with patch.dict(os.environ, {"CI": "true"}, clear=True):
            detector = TerminalColorDetector()
            assert detector.is_ci() is True

    def test_term_environment(self):
        """Test TERM environment variable."""
        # Dumb terminal
        with patch.dict(os.environ, {"TERM": "dumb"}):
            with patch("sys.stdout.isatty", return_value=True):
                detector = TerminalColorDetector()
                assert detector.supports_color() is False

        # Color terminal
        with patch.dict(os.environ, {"TERM": "xterm-256color"}):
            with patch("sys.stdout.isatty", return_value=True):
                detector = TerminalColorDetector()
                assert detector.supports_color() is True


class TestASCIIBoxFormatter:
    """Test ASCII art box formatter."""

    def test_simple_box(self):
        """Test simple box creation."""
        formatter = ASCIIBoxFormatter()

        box = formatter.create_box("Test Content", width=20)
        lines = box.split("\n")

        assert lines[0] == "┌" + "─" * 18 + "┐"
        assert lines[1] == "│ Test Content     │"
        assert lines[2] == "└" + "─" * 18 + "┘"

    def test_box_with_title(self):
        """Test box with title."""
        formatter = ASCIIBoxFormatter()

        box = formatter.create_box("Content", title="Title", width=30)
        lines = box.split("\n")

        assert "Title" in lines[0]
        assert "┌" in lines[0]
        assert "┐" in lines[0]
        assert "│ Content" in lines[1]

    def test_multiline_content(self):
        """Test box with multiline content."""
        formatter = ASCIIBoxFormatter()

        content = "Line 1\nLine 2\nLine 3"
        box = formatter.create_box(content, width=20)
        lines = box.split("\n")

        assert len(lines) == 5  # Top + 3 content + bottom
        assert "│ Line 1" in lines[1]
        assert "│ Line 2" in lines[2]
        assert "│ Line 3" in lines[3]

    def test_box_styles(self):
        """Test different box styles."""
        formatter = ASCIIBoxFormatter()

        # Double style
        box = formatter.create_box("Test", style="double", width=15)
        assert "╔" in box
        assert "═" in box
        assert "╗" in box

        # Simple style
        box = formatter.create_box("Test", style="simple", width=15)
        assert "+" in box
        assert "-" in box

    def test_highlight_box(self):
        """Test highlighted box for important content."""
        formatter = ASCIIBoxFormatter()

        box = formatter.create_highlight_box("IMPORTANT", width=25)
        lines = box.split("\n")

        # Should have emphasis markers
        assert any("!" in line or "►" in line for line in lines)

    def test_auto_width(self):
        """Test automatic width calculation."""
        formatter = ASCIIBoxFormatter()

        content = "This is a longer piece of content"
        box = formatter.create_box(content)
        lines = box.split("\n")

        # Box should be wide enough for content
        assert len(lines[1]) > len(content)


class TestLinkHighlighter:
    """Test link highlighting and extraction."""

    def test_extract_verification_link(self):
        """Test verification link extraction."""
        highlighter = LinkHighlighter()

        html = """
        <p>Click here to verify:</p>
        <a href="http://localhost:8090/verify-email?token=abc123xyz">Verify Email</a>
        """

        links = highlighter.extract_links(html)
        assert len(links) == 1
        assert links[0]["url"] == "http://localhost:8090/verify-email?token=abc123xyz"
        assert links[0]["type"] == "verification"
        assert links[0]["token"] == "abc123xyz"

    def test_extract_password_reset_link(self):
        """Test password reset link extraction."""
        highlighter = LinkHighlighter()

        html = """
        <a href="https://example.com/reset-password?token=reset456">Reset Password</a>
        """

        links = highlighter.extract_links(html)
        assert len(links) == 1
        assert links[0]["type"] == "password_reset"
        assert links[0]["token"] == "reset456"

    def test_extract_multiple_links(self):
        """Test extraction of multiple links."""
        highlighter = LinkHighlighter()

        html = """
        <a href="http://example.com/verify?token=123">Verify</a>
        <a href="http://example.com/unsubscribe">Unsubscribe</a>
        <a href="http://example.com/reset?token=456">Reset</a>
        """

        links = highlighter.extract_links(html)
        assert len(links) == 3

        # Should identify types correctly
        types = [link["type"] for link in links]
        assert "verification" in types
        assert "password_reset" in types
        assert "unsubscribe" in types

    def test_format_link_plain(self):
        """Test plain link formatting."""
        highlighter = LinkHighlighter()

        link = {
            "url": "http://example.com/verify?token=123",
            "type": "verification",
            "text": "Verify Email",
        }

        formatted = highlighter.format_link(link, use_color=False)
        assert "http://example.com/verify?token=123" in formatted
        assert "Verify Email" in formatted

    def test_format_link_with_color(self):
        """Test link formatting with color."""
        highlighter = LinkHighlighter()

        link = {
            "url": "http://example.com/verify?token=123",
            "type": "verification",
            "text": "Verify Email",
        }

        formatted = highlighter.format_link(link, use_color=True)
        # Should contain ANSI color codes
        assert "\033[" in formatted

    def test_create_copy_friendly_block(self):
        """Test copy-friendly link block creation."""
        highlighter = LinkHighlighter()

        link = {"url": "http://example.com/verify?token=abc123xyz789", "type": "verification"}

        block = highlighter.create_copy_block(link)
        lines = block.split("\n")

        # Should have clear delimiters
        assert "COPY" in block  # Check in the whole block
        assert "http://example.com/verify?token=abc123xyz789" in block
        # URL should be in the output for easy copying
        assert "http://example.com/verify?token=abc123xyz789" in block


class TestConsoleFormatter:
    """Test main console formatter."""

    def test_format_verification_email(self):
        """Test formatting of verification email."""
        formatter = ConsoleFormatter()

        message = EmailMessage(
            to=["user@example.com"],
            subject="Verify your email",
            html_body='<a href="http://localhost:8090/verify-email?token=abc123">Verify</a>',
            text_body="Click link to verify",
        )

        output = formatter.format_email(message)

        # Should have clear sections
        assert "EMAIL VERIFICATION" in output
        assert "abc123" in output
        assert "http://localhost:8090/verify-email?token=abc123" in output
        assert "COPY" in output  # Copy-friendly section

    def test_format_password_reset_email(self):
        """Test formatting of password reset email."""
        formatter = ConsoleFormatter()

        message = EmailMessage(
            to=["user@example.com"],
            subject="Reset your password",
            html_body='<a href="http://example.com/reset?token=xyz789">Reset Password</a>',
            text_body="Reset your password",
        )

        output = formatter.format_email(message)

        assert "PASSWORD RESET" in output
        assert "xyz789" in output
        assert "http://example.com/reset?token=xyz789" in output

    def test_docker_formatting(self):
        """Test Docker-specific formatting."""
        formatter = ConsoleFormatter()

        with patch(
            "server.auth.email_providers.console_formatter.TerminalColorDetector.is_docker",
            return_value=True,
        ):
            message = EmailMessage(
                to=["user@example.com"], subject="Test", html_body="<p>Test content</p>"
            )

            output = formatter.format_email(message)

            # Should not have color codes in Docker
            assert "\033[" not in output
            # Should have Docker-specific note
            assert "Docker" in output or "container" in output.lower()

    def test_terminal_width_detection(self):
        """Test terminal width detection and adjustment."""
        formatter = ConsoleFormatter()

        # Mock narrow terminal - create mock object with columns attribute
        mock_size = MagicMock()
        mock_size.columns = 40
        mock_size.lines = 24

        with patch("shutil.get_terminal_size", return_value=mock_size):
            message = EmailMessage(
                to=["user@example.com"],
                subject="Test with very long subject line that should wrap",
                html_body="Content",
            )

            output = formatter.format_email(message)
            lines = output.split("\n")

            # Most lines should fit within terminal width
            # Some box characters might extend slightly beyond
            long_lines = [line for line in lines if len(line) > 40]
            # Should have very few lines exceeding width
            assert len(long_lines) < 5  # Allow a few long lines for box edges

    def test_format_with_emojis(self):
        """Test emoji usage in formatting."""
        formatter = ConsoleFormatter()

        message = EmailMessage(
            to=["user@example.com"], subject="Welcome!", html_body="<p>Welcome to our service!</p>"
        )

        output = formatter.format_email(message)

        # Should have appropriate emojis (check for welcome emoji)
        assert "🎉" in output  # Welcome email emoji

    def test_format_security_alert(self):
        """Test security alert formatting."""
        formatter = ConsoleFormatter()

        message = EmailMessage(
            to=["user@example.com"],
            subject="Security Alert - New Device Login",
            html_body="<p>New login from IP: 192.168.1.1</p>",
        )

        output = formatter.format_email(message)

        # Should have security indicators
        assert "SECURITY" in output or "⚠️" in output
        assert "192.168.1.1" in output

    def test_quick_actions_section(self):
        """Test quick actions section generation."""
        formatter = ConsoleFormatter()

        message = EmailMessage(
            to=["user@example.com"],
            subject="Verify your email",
            html_body='<a href="http://localhost:8090/verify-email?token=abc123">Verify</a>',
        )

        output = formatter.format_email(message)

        # Should have quick actions
        assert "Quick Actions" in output or "What to do" in output
        # Should mention API endpoint
        assert "/api/auth/verify-email" in output
        # Should mention database command for dev
        assert "sqlite3" in output or "UPDATE users" in output


class TestConsoleProviderIntegration:
    """Test integration with console email provider."""

    @pytest.mark.asyncio
    async def test_enhanced_console_output(self):
        """Test enhanced console output in provider."""
        # Capture stdout
        captured_output = StringIO()

        provider = ConsoleEmailProvider(
            {"use_colors": True, "highlight_links": True, "enhanced_formatting": True}
        )

        message = EmailMessage(
            to=["test@example.com"],
            subject="Verify your email",
            html_body='<a href="http://localhost:8090/verify-email?token=test123">Click to verify</a>',
        )

        with patch("sys.stdout", captured_output):
            result = await provider.send_email(message)

        output = captured_output.getvalue()

        assert result.success
        assert "EMAIL VERIFICATION" in output
        assert "test123" in output
        assert "http://localhost:8090/verify-email?token=test123" in output
        # Should have formatting elements
        assert "═" in output or "─" in output  # Box drawing characters

    @pytest.mark.asyncio
    async def test_fallback_formatting(self):
        """Test fallback formatting when enhanced features unavailable."""
        provider = ConsoleEmailProvider(
            {"use_colors": False, "enhanced_formatting": False}  # Disable enhanced formatting
        )

        message = EmailMessage(
            to=["test@example.com"], subject="Test", html_body="<p>Test content</p>"
        )

        captured_output = StringIO()
        with patch("sys.stdout", captured_output):
            result = await provider.send_email(message)

        output = captured_output.getvalue()

        assert result.success
        # Should still be readable without fancy formatting
        assert "test@example.com" in output
        assert "Test" in output
        # Should use simple separators
        assert "=" in output  # Simple formatting uses = separators
