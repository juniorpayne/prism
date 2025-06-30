#!/usr/bin/env python3
"""
Unit tests for console email formatter enhancements (V2).
"""

import os
from unittest.mock import patch

import pytest
from colorama import Fore, Style

from server.auth.email_providers import EmailMessage
from server.auth.email_providers.console_formatter import (
    ASCIIBoxFormatter,
    ConsoleFormatter,
    LinkHighlighter,
)


class TestASCIIBoxFormatterV2:
    """Test ASCII art box formatter (V2)."""

    def test_rounded_box_style(self):
        """Test the rounded box style."""
        formatter = ASCIIBoxFormatter()
        box = formatter.create_box("Test", style="rounded", width=15)
        assert "╭" in box
        assert "─" in box
        assert "╮" in box
        assert "╰" in box
        assert "╯" in box

    def test_box_with_color(self):
        """Test that the box has color."""
        formatter = ASCIIBoxFormatter()
        box = formatter.create_box("Test", style="rounded", width=15, color=Fore.GREEN)
        assert Fore.GREEN in box
        assert Style.RESET_ALL in box


class TestLinkHighlighterV2:
    """Test link highlighting and extraction (V2)."""

    def test_format_link_with_more_colors(self):
        """Test link formatting with more colors."""
        highlighter = LinkHighlighter()

        link = {
            "url": "http://example.com/verify?token=123",
            "type": "verification",
            "text": "Verify Email",
        }

        formatted = highlighter.format_link(link, use_color=True)
        assert Fore.GREEN in formatted

        link["type"] = "password_reset"
        formatted = highlighter.format_link(link, use_color=True)
        assert Fore.YELLOW in formatted

        link["type"] = "other"
        formatted = highlighter.format_link(link, use_color=True)
        assert Fore.BLUE in formatted


class TestConsoleFormatterV2:
    """Test main console formatter (V2)."""

    def test_format_welcome_email(self):
        """Test formatting of welcome email."""
        formatter = ConsoleFormatter()

        message = EmailMessage(
            to=["user@example.com"],
            subject="Welcome to our service!",
            html_body="<p>Welcome!</p>",
            text_body="Welcome!",
        )

        output = formatter.format_email(message)

        assert "WELCOME EMAIL" in output
        assert "🎉" in output

    def test_format_email_with_color(self):
        """Test that the email has color."""
        formatter = ConsoleFormatter()

        message = EmailMessage(
            to=["user@example.com"],
            subject="Test",
            html_body="<p>Test</p>",
            text_body="Test",
        )

        with patch(
            "server.auth.email_providers.console_formatter.TerminalColorDetector.supports_color",
            return_value=True,
        ):
            output = formatter.format_email(message)

        assert Fore.CYAN in output
        assert Style.RESET_ALL in output
