#!/usr/bin/env python3
"""
Enhanced console formatting for email output.

Provides terminal color detection, ASCII art formatting, and
link highlighting for better developer experience.
"""

import os
import re
import shutil
import sys
from typing import Any, Dict, List, Optional, Tuple

from server.auth.email_providers.base import EmailMessage


class TerminalColorDetector:
    """Detects terminal color support and environment."""

    def __init__(self):
        """Initialize detector."""
        self._color_support = None
        self._is_docker = None
        self._is_ci = None

    def supports_color(self) -> bool:
        """Check if terminal supports color output."""
        if self._color_support is not None:
            return self._color_support

        # Check FORCE_COLOR env var
        force_color = os.environ.get("FORCE_COLOR", "").lower()
        if force_color == "1" or force_color == "true":
            self._color_support = True
            return True
        elif force_color == "0" or force_color == "false":
            self._color_support = False
            return False

        # No colors in CI or Docker by default
        if self.is_ci() or self.is_docker():
            self._color_support = False
            return False

        # Check if stdout is a TTY
        if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
            self._color_support = False
            return False

        # Check TERM environment variable
        term = os.environ.get("TERM", "").lower()
        if term == "dumb":
            self._color_support = False
            return False

        # Assume color support for TTY
        self._color_support = True
        return True

    def is_docker(self) -> bool:
        """Check if running in Docker container."""
        if self._is_docker is not None:
            return self._is_docker

        # Check for /.dockerenv file
        self._is_docker = os.path.exists("/.dockerenv")
        return self._is_docker

    def is_ci(self) -> bool:
        """Check if running in CI environment."""
        if self._is_ci is not None:
            return self._is_ci

        # Check common CI environment variables
        ci_vars = ["CI", "CONTINUOUS_INTEGRATION", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL"]
        self._is_ci = any(os.environ.get(var) for var in ci_vars)
        return self._is_ci


class ASCIIBoxFormatter:
    """Creates ASCII art boxes for highlighting content."""

    # Box drawing characters
    STYLES = {
        "single": {
            "tl": "┌",
            "tr": "┐",
            "bl": "└",
            "br": "┘",
            "h": "─",
            "v": "│",
            "t": "┬",
            "b": "┴",
            "l": "├",
            "r": "┤",
            "x": "┼",
        },
        "double": {
            "tl": "╔",
            "tr": "╗",
            "bl": "╚",
            "br": "╝",
            "h": "═",
            "v": "║",
            "t": "╦",
            "b": "╩",
            "l": "╠",
            "r": "╣",
            "x": "╬",
        },
        "simple": {
            "tl": "+",
            "tr": "+",
            "bl": "+",
            "br": "+",
            "h": "-",
            "v": "|",
            "t": "+",
            "b": "+",
            "l": "+",
            "r": "+",
            "x": "+",
        },
    }

    def create_box(
        self,
        content: str,
        title: Optional[str] = None,
        width: Optional[int] = None,
        style: str = "single",
    ) -> str:
        """
        Create a box around content.

        Args:
            content: Content to put in box
            title: Optional title for box
            width: Box width (auto-calculated if None)
            style: Box style (single, double, simple)

        Returns:
            Formatted box string
        """
        chars = self.STYLES.get(style, self.STYLES["single"])

        # Split content into lines
        lines = content.split("\n")

        # Calculate width
        if width is None:
            content_width = max(len(line) for line in lines) if lines else 0
            if title:
                content_width = max(content_width, len(title) + 4)
            width = content_width + 4  # Add padding
            # Ensure minimum width
            width = max(width, 20)

        # Build top line
        if title:
            title_part = f" {title} "
            padding = width - len(title_part) - 2
            left_pad = padding // 2
            right_pad = padding - left_pad
            top_line = (
                chars["tl"]
                + chars["h"] * left_pad
                + title_part
                + chars["h"] * right_pad
                + chars["tr"]
            )
        else:
            top_line = chars["tl"] + chars["h"] * (width - 2) + chars["tr"]

        # Build content lines
        box_lines = [top_line]
        for line in lines:
            padded_line = f" {line:<{width-4}} "
            box_lines.append(chars["v"] + padded_line + chars["v"])

        # Build bottom line
        bottom_line = chars["bl"] + chars["h"] * (width - 2) + chars["br"]
        box_lines.append(bottom_line)

        return "\n".join(box_lines)

    def create_highlight_box(self, content: str, width: Optional[int] = None) -> str:
        """Create a highlighted box for important content."""
        # Add emphasis markers
        emphasized = f"► {content} ◄"
        box = self.create_box(emphasized, width=width, style="double")

        # Add extra emphasis lines
        width = len(box.split("\n")[0])
        emphasis_line = "!" * width

        return f"{emphasis_line}\n{box}\n{emphasis_line}"


class LinkHighlighter:
    """Extracts and highlights links in email content."""

    # ANSI color codes
    COLORS = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "underline": "\033[4m",
        "blue": "\033[34m",
        "cyan": "\033[36m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "red": "\033[31m",
    }

    def extract_links(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Extract links from HTML content.

        Returns list of dicts with:
        - url: The full URL
        - text: Link text (if available)
        - type: Link type (verification, password_reset, other)
        - token: Extracted token (if available)
        """
        if not html_content:
            return []

        links = []

        # Find all anchor tags
        anchor_pattern = r'<a[^>]*href="([^"]+)"[^>]*>([^<]*)</a>'
        matches = re.finditer(anchor_pattern, html_content, re.IGNORECASE)

        for match in matches:
            url = match.group(1)
            text = match.group(2).strip() or "Link"

            # Determine link type
            link_type = self._determine_link_type(url, text)

            # Extract token if present
            token = self._extract_token(url)

            links.append({"url": url, "text": text, "type": link_type, "token": token})

        return links

    def _determine_link_type(self, url: str, text: str) -> str:
        """Determine the type of link."""
        url_lower = url.lower()
        text_lower = text.lower()

        if "verify" in url_lower or "verify" in text_lower or "confirm" in url_lower:
            return "verification"
        elif "reset" in url_lower or "password" in text_lower:
            return "password_reset"
        elif "unsubscribe" in url_lower:
            return "unsubscribe"
        else:
            return "other"

    def _extract_token(self, url: str) -> Optional[str]:
        """Extract token from URL."""
        # Look for token parameter
        token_match = re.search(r"token=([a-zA-Z0-9_\-]+)", url)
        if token_match:
            return token_match.group(1)

        # Look for token in path
        path_token_match = re.search(r"/(?:verify|reset|confirm)/([a-zA-Z0-9_\-]+)", url)
        if path_token_match:
            return path_token_match.group(1)

        return None

    def format_link(self, link: Dict[str, Any], use_color: bool = False) -> str:
        """Format a link for display."""
        url = link["url"]
        text = link.get("text", "Link")
        link_type = link.get("type", "other")

        if use_color:
            # Color based on type
            if link_type == "verification":
                color = self.COLORS["green"]
            elif link_type == "password_reset":
                color = self.COLORS["yellow"]
            else:
                color = self.COLORS["blue"]

            return f"{self.COLORS['bold']}{text}:{self.COLORS['reset']} {color}{self.COLORS['underline']}{url}{self.COLORS['reset']}"
        else:
            return f"{text}: {url}"

    def create_copy_block(self, link: Dict[str, Any]) -> str:
        """Create a copy-friendly block for a link."""
        url = link["url"]
        token = link.get("token")

        # Calculate width
        max_width = max(len(url) + 4, 30)
        title = " COPY THIS LINK "
        title_padding = max_width - len(title) - 2
        left_pad = title_padding // 2
        right_pad = title_padding - left_pad

        lines = [
            "╔" + "═" * left_pad + title + "═" * right_pad + "╗",
            "║" + " " * (max_width - 2) + "║",
            f"║ {url:^{max_width-4}} ║",
            "║" + " " * (max_width - 2) + "║",
            "╚" + "═" * (max_width - 2) + "╝",
        ]

        block = "\n".join(lines)

        if token:
            block += f"\n\nToken: {token}"

        return block


class ConsoleFormatter:
    """Main formatter for console email output."""

    def __init__(self):
        """Initialize formatter."""
        self.color_detector = TerminalColorDetector()
        self.box_formatter = ASCIIBoxFormatter()
        self.link_highlighter = LinkHighlighter()
        self._terminal_width = None

    def get_terminal_width(self) -> int:
        """Get terminal width."""
        if self._terminal_width is None:
            size = shutil.get_terminal_size((80, 24))
            self._terminal_width = size.columns
        return self._terminal_width

    def format_email(self, message: EmailMessage) -> str:
        """
        Format email message for console output.

        Args:
            message: Email message to format

        Returns:
            Formatted string for console output
        """
        use_color = self.color_detector.supports_color()
        width = min(self.get_terminal_width(), 100)  # Cap at 100 for readability

        # Start building output
        lines = []

        # Add environment notice if needed
        if self.color_detector.is_docker():
            lines.append("🐳 Running in Docker container (colors disabled)")
        elif self.color_detector.is_ci():
            lines.append("🤖 Running in CI environment")

        # Main header
        header = self._format_header(message, width)
        lines.append(header)

        # Email metadata
        metadata = self._format_metadata(message, width)
        lines.append(metadata)

        # Determine email type and format accordingly
        email_type = self._determine_email_type(message)

        if email_type == "verification":
            content = self._format_verification_email(message, use_color, width)
        elif email_type == "password_reset":
            content = self._format_password_reset_email(message, use_color, width)
        elif email_type == "security_alert":
            content = self._format_security_alert(message, use_color, width)
        else:
            content = self._format_general_email(message, use_color, width)

        lines.append(content)

        # Footer
        footer = self._format_footer(width)
        lines.append(footer)

        return "\n".join(lines)

    def _format_header(self, message: EmailMessage, width: int) -> str:
        """Format email header."""
        email_type = self._determine_email_type(message)

        # Choose emoji based on type
        if email_type == "verification":
            emoji = "🔐"
            title = "EMAIL VERIFICATION"
        elif email_type == "password_reset":
            emoji = "🔑"
            title = "PASSWORD RESET"
        elif email_type == "security_alert":
            emoji = "⚠️"
            title = "SECURITY ALERT"
        elif "welcome" in message.subject.lower():
            emoji = "🎉"
            title = "WELCOME EMAIL"
        else:
            emoji = "📧"
            title = "EMAIL NOTIFICATION"

        header_text = f"{emoji} {title}"

        # Create decorative header
        return self.box_formatter.create_box(header_text, width=width, style="double")

    def _format_metadata(self, message: EmailMessage, width: int) -> str:
        """Format email metadata."""
        lines = []

        # Basic metadata
        lines.append(f"To: {', '.join(message.to)}")
        lines.append(f"Subject: {message.subject}")

        if message.from_email:
            from_line = f"From: {message.from_email}"
            if message.from_name:
                from_line = f"From: {message.from_name} <{message.from_email}>"
            lines.append(from_line)

        if message.cc:
            lines.append(f"CC: {', '.join(message.cc)}")

        return "\n".join(lines)

    def _determine_email_type(self, message: EmailMessage) -> str:
        """Determine the type of email."""
        subject_lower = message.subject.lower()
        content = (message.html_body or "") + (message.text_body or "")
        content_lower = content.lower()

        if "verify" in subject_lower or "verify" in content_lower:
            return "verification"
        elif "reset" in subject_lower and "password" in subject_lower:
            return "password_reset"
        elif "security" in subject_lower or "alert" in subject_lower:
            return "security_alert"
        elif "welcome" in subject_lower:
            return "welcome"
        else:
            return "general"

    def _format_verification_email(self, message: EmailMessage, use_color: bool, width: int) -> str:
        """Format verification email content."""
        lines = []

        # Extract links
        links = self.link_highlighter.extract_links(message.html_body)
        verification_links = [l for l in links if l["type"] == "verification"]

        if verification_links:
            link = verification_links[0]
            token = link.get("token", "No token found")

            # Token display
            token_box = self.box_formatter.create_box(
                f"Verification Token: {token}", title="TOKEN", width=width
            )
            lines.append(token_box)
            lines.append("")

            # Link display
            lines.append("🔗 Verification Link:")
            lines.append(self.link_highlighter.create_copy_block(link))
            lines.append("")

            # Quick actions
            actions = self._create_quick_actions_verification(link, message.to[0])
            lines.append(actions)
        else:
            lines.append("⚠️  No verification link found in email")

        return "\n".join(lines)

    def _format_password_reset_email(
        self, message: EmailMessage, use_color: bool, width: int
    ) -> str:
        """Format password reset email content."""
        lines = []

        # Extract links
        links = self.link_highlighter.extract_links(message.html_body)
        reset_links = [l for l in links if l["type"] == "password_reset"]

        if reset_links:
            link = reset_links[0]
            token = link.get("token", "No token found")

            # Token display
            token_box = self.box_formatter.create_box(
                f"Reset Token: {token}", title="TOKEN", width=width
            )
            lines.append(token_box)
            lines.append("")

            # Link display
            lines.append("🔗 Password Reset Link:")
            lines.append(self.link_highlighter.create_copy_block(link))
            lines.append("")

            # Instructions
            lines.append("📝 Instructions:")
            lines.append("1. Click the link above or copy it to your browser")
            lines.append("2. Enter your new password")
            lines.append("3. Confirm the password change")
        else:
            lines.append("⚠️  No reset link found in email")

        return "\n".join(lines)

    def _format_security_alert(self, message: EmailMessage, use_color: bool, width: int) -> str:
        """Format security alert email."""
        lines = []

        # Extract important info
        content = message.html_body or message.text_body or ""

        # Look for IP addresses
        ip_matches = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", content)

        # Warning box
        warning = self.box_formatter.create_highlight_box(
            "SECURITY ALERT - Please review this activity", width=width
        )
        lines.append(warning)
        lines.append("")

        # Show detected IPs
        if ip_matches:
            lines.append("🌐 Detected IP Addresses:")
            for ip in ip_matches:
                lines.append(f"   • {ip}")
            lines.append("")

        # Show preview
        if message.text_body:
            lines.append("📄 Alert Details:")
            preview = message.text_body[:200]
            if len(message.text_body) > 200:
                preview += "..."
            lines.append(preview)

        return "\n".join(lines)

    def _format_general_email(self, message: EmailMessage, use_color: bool, width: int) -> str:
        """Format general email content."""
        lines = []

        # Extract all links
        links = self.link_highlighter.extract_links(message.html_body)

        # Show content preview
        if message.text_body:
            lines.append("📄 Content Preview:")
            preview = message.text_body[:300]
            if len(message.text_body) > 300:
                preview += "..."
            lines.append(preview)
            lines.append("")

        # Show links if any
        if links:
            lines.append("🔗 Links Found:")
            for link in links:
                formatted = self.link_highlighter.format_link(link, use_color)
                lines.append(f"   • {formatted}")

        return "\n".join(lines)

    def _create_quick_actions_verification(self, link: Dict[str, Any], email: str) -> str:
        """Create quick actions section for verification emails."""
        token = link.get("token", "")

        actions = [
            "✨ Quick Actions:",
            "",
            "1️⃣  Click the link above in your browser",
            "",
            "2️⃣  Use the API endpoint:",
            f"    curl -X GET http://localhost:8081/api/auth/verify-email/{token}",
            "",
            "3️⃣  Manual database update (development only):",
            "    docker compose exec server sqlite3 /data/prism.db",
            f'    UPDATE users SET email_verified = 1 WHERE email = "{email}";',
        ]

        return "\n".join(actions)

    def _format_footer(self, width: int) -> str:
        """Format email footer."""
        separator = "═" * width
        timestamp = "📅 Email sent via Console Provider (Development Mode)"

        return f"\n{separator}\n{timestamp}\n"
