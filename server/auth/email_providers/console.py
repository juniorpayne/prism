#!/usr/bin/env python3
"""
Console email provider for development environments.
"""

import re
from typing import Dict, List, Optional, Tuple

from server.auth.email_providers.base import EmailMessage, EmailProvider, EmailResult
from server.auth.email_providers.console_formatter import ConsoleFormatter


class ConsoleEmailProvider(EmailProvider):
    """
    Console email provider that prints emails to console/logs.

    Perfect for development environments where you need to see
    verification links and email content without sending actual emails.
    """

    def __init__(self, config: Optional[Dict[str, str]] = None):
        """
        Initialize console email provider.

        Args:
            config: Optional configuration (format, colors, etc.)
        """
        super().__init__(config)
        self.format = self.config.get("format", "pretty")
        self.use_colors = self.config.get("use_colors", False)
        self.highlight_links = self.config.get("highlight_links", True)
        self.enhanced_formatting = self.config.get("enhanced_formatting", True)

        # Initialize formatter if enhanced formatting is enabled
        if self.enhanced_formatting:
            self.formatter = ConsoleFormatter()
        else:
            self.formatter = None

    async def send_email(self, message: EmailMessage) -> EmailResult:
        """Print email to console."""
        try:
            self._print_email(message)
            return EmailResult(
                success=True,
                message_id=f"console-{id(message)}",
                provider=self.provider_name,
                metadata={"format": self.format},
            )
        except Exception as e:
            self._logger.error(f"Failed to print email to console: {e}")
            return EmailResult(
                success=False,
                error=str(e),
                provider=self.provider_name,
            )

    async def verify_configuration(self) -> bool:
        """Console provider is always configured correctly."""
        self._logger.info("Console email provider is ready")
        return True

    def _print_email(self, message: EmailMessage) -> None:
        """Print formatted email to console."""
        # Use enhanced formatter if available
        if self.formatter and self.enhanced_formatting:
            output = self.formatter.format_email(message)
            print(output)
            return

        # Fall back to simple formatting
        self._print_simple_email(message)

    def _print_simple_email(self, message: EmailMessage) -> None:
        """Print email with simple formatting (fallback)."""
        # Extract important information
        links = self._extract_links(message.html_body)
        tokens = self._extract_tokens(message.html_body)

        # Build output
        output_lines = [
            "\n" + "=" * 80,
            "📧 EMAIL CONSOLE OUTPUT (Development Mode)",
            "=" * 80,
            f"To: {', '.join(message.to)}",
            f"Subject: {message.subject}",
        ]

        if message.cc:
            output_lines.append(f"CC: {', '.join(message.cc)}")
        if message.from_email:
            from_line = f"From: {message.from_email}"
            if message.from_name:
                from_line = f"From: {message.from_name} <{message.from_email}>"
            output_lines.append(from_line)

        output_lines.append("-" * 80)

        # Determine email type and show relevant info
        if self._is_verification_email(message):
            self._add_verification_info(output_lines, links, tokens, message.to[0])
        elif self._is_password_reset_email(message):
            self._add_password_reset_info(output_lines, links, tokens)
        elif self._is_password_changed_email(message):
            self._add_password_changed_info(output_lines)
        else:
            self._add_general_email_info(output_lines, message, links)

        output_lines.append("=" * 80 + "\n")

        # Print to console
        print("\n".join(output_lines))

    def _extract_links(self, html_content: str) -> List[Tuple[str, str]]:
        """Extract links from HTML content."""
        if not html_content:
            return []

        # Find all links with href
        link_pattern = r'href="([^"]+)"'
        links = re.findall(link_pattern, html_content)

        # Filter for important links
        important_links = []
        for link in links:
            if any(
                keyword in link.lower()
                for keyword in ["verify", "reset", "confirm", "token", "activate"]
            ):
                # Try to get link text (simplified)
                link_text = "Link"
                if "verify" in link.lower():
                    link_text = "Verification Link"
                elif "reset" in link.lower():
                    link_text = "Reset Link"
                important_links.append((link_text, link))

        return important_links

    def _extract_tokens(self, html_content: str) -> List[str]:
        """Extract tokens from content."""
        if not html_content:
            return []

        # Look for token patterns in URLs
        token_pattern = r"token=([a-zA-Z0-9_-]+)"
        tokens = re.findall(token_pattern, html_content)

        return list(set(tokens))  # Remove duplicates

    def _is_verification_email(self, message: EmailMessage) -> bool:
        """Check if this is a verification email."""
        subject_lower = message.subject.lower()
        content = (message.html_body or "") + (message.text_body or "")
        return "verify" in subject_lower or "verify" in content.lower()

    def _is_password_reset_email(self, message: EmailMessage) -> bool:
        """Check if this is a password reset email."""
        subject_lower = message.subject.lower()
        return "password" in subject_lower and "reset" in subject_lower

    def _is_password_changed_email(self, message: EmailMessage) -> bool:
        """Check if this is a password changed notification."""
        subject_lower = message.subject.lower()
        return "password" in subject_lower and "changed" in subject_lower

    def _add_verification_info(
        self, lines: List[str], links: List[Tuple[str, str]], tokens: List[str], email: str
    ) -> None:
        """Add verification email specific information."""
        lines.extend(
            [
                "🔐 EMAIL VERIFICATION",
                f"Verification Token: {tokens[0] if tokens else 'No token found'}",
            ]
        )

        if links:
            lines.append(f"Verification Link: {links[0][1]}")

        lines.extend(
            [
                "\nTo verify this email, use one of these methods:",
                "1. Click the link above in your browser",
                "2. Use the API endpoint:",
                f"   GET /api/auth/verify-email/{tokens[0] if tokens else '<token>'}",
            ]
        )

        if tokens:
            lines.extend(
                [
                    "\n3. Or manually update the database:",
                    "   docker compose exec server sqlite3 /app/data/prism.db",
                    f'   UPDATE users SET email_verified = 1, email_verified_at = datetime("now") WHERE email = "{email}";',
                ]
            )

    def _add_password_reset_info(
        self, lines: List[str], links: List[Tuple[str, str]], tokens: List[str]
    ) -> None:
        """Add password reset email specific information."""
        lines.extend(
            [
                "🔑 PASSWORD RESET",
                f"Reset Token: {tokens[0] if tokens else 'No token found'}",
            ]
        )

        if links:
            lines.append(f"Reset Link: {links[0][1]}")

        lines.append("\nTo reset password, visit the link above in your browser")

    def _add_password_changed_info(self, lines: List[str]) -> None:
        """Add password changed notification information."""
        lines.extend(
            [
                "✅ PASSWORD CHANGED NOTIFICATION",
                "This is a security notification that the password was changed.",
            ]
        )

    def _add_general_email_info(
        self, lines: List[str], message: EmailMessage, links: List[Tuple[str, str]]
    ) -> None:
        """Add general email information."""
        lines.append("📨 GENERAL EMAIL")

        # Show text preview
        if message.text_body:
            preview = message.text_body[:200]
            if len(message.text_body) > 200:
                preview += "..."
            lines.append(f"Preview: {preview}")
        elif message.html_body:
            # Strip HTML tags for preview
            text_preview = re.sub(r"<[^>]+>", "", message.html_body)[:200]
            lines.append(f"Preview: {text_preview}...")

        # Show any important links
        if links:
            lines.append("\nLinks found:")
            for link_text, link_url in links:
                lines.append(f"- {link_text}: {link_url}")

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "Console"
