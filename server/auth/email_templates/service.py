#!/usr/bin/env python3
"""
Email template service for rendering HTML and text email templates.
"""

import os
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from html2text import html2text
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape
from premailer import transform

from server.auth.email_providers.exceptions import EmailTemplateError
from server.auth.email_providers.utils import sanitize_email_content


class EmailTemplateService:
    """Service for rendering email templates using Jinja2."""

    def __init__(self, app_name: Optional[str] = None, app_url: Optional[str] = None):
        """
        Initialize the email template service.

        Args:
            app_name: Application name for branding
            app_url: Application URL for links
        """
        # Set up template directory
        self.template_dir = os.path.dirname(os.path.abspath(__file__))

        # Configure Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Set default context values
        self.app_name = app_name or os.getenv("APP_NAME", "Prism DNS")
        self.app_url = app_url or os.getenv("APP_URL", "https://prism.thepaynes.ca")
        self.support_email = os.getenv("SUPPORT_EMAIL", "support@prism.thepaynes.ca")

    def _get_base_context(self) -> Dict[str, Any]:
        """Get base context variables for all templates."""
        return {
            "app_name": self.app_name,
            "app_url": self.app_url,
            "support_email": self.support_email,
            "current_year": datetime.now().year,
            "logo_url": f"{self.app_url}/assets/logo.png",
        }

    def _inline_css(self, html: str) -> str:
        """
        Inline CSS styles for better email client compatibility.

        Args:
            html: HTML content with style tags

        Returns:
            HTML with inlined CSS
        """
        try:
            # Use premailer to inline CSS
            return transform(
                html,
                base_url=self.app_url,
                preserve_internal_links=True,
                exclude_pseudoclasses=True,
                keep_style_tags=False,
                include_star_selectors=False,
            )
        except Exception as e:
            # If inlining fails, return original HTML
            # This ensures email can still be sent
            return html

    def _generate_text_from_html(self, html: str) -> str:
        """
        Generate plain text version from HTML.

        Args:
            html: HTML content

        Returns:
            Plain text version
        """
        try:
            # Configure html2text
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = True
            h.ignore_emphasis = False
            h.body_width = 78
            h.unicode_snob = True

            return h.handle(html).strip()
        except Exception:
            # Fallback to basic text extraction
            import re

            text = re.sub(r"<[^>]+>", "", html)
            return text.strip()

    async def render_email(
        self,
        template_name: str,
        context: Optional[Dict[str, Any]] = None,
        auto_generate_text: bool = True,
    ) -> Tuple[str, str]:
        """
        Render both HTML and text versions of an email template.

        Args:
            template_name: Name of the template (without extension)
            context: Template context variables
            auto_generate_text: Whether to auto-generate text from HTML if text template not found

        Returns:
            Tuple of (html_content, text_content)

        Raises:
            EmailTemplateError: If template not found or rendering fails
        """
        # Merge contexts
        template_context = self._get_base_context()
        if context:
            template_context.update(context)

        try:
            # Render HTML version
            html_template = self.env.get_template(f"{template_name}.html")
            html_content = html_template.render(template_context)

            # Inline CSS for email compatibility
            html_content = self._inline_css(html_content)

            # Try to render text version
            try:
                text_template = self.env.get_template(f"{template_name}.txt")
                text_content = text_template.render(template_context)
            except TemplateNotFound:
                if auto_generate_text:
                    # Auto-generate text from HTML
                    text_content = self._generate_text_from_html(html_content)
                else:
                    raise EmailTemplateError(
                        f"Text template not found: {template_name}.txt",
                        template_name=f"{template_name}.txt",
                    )

            # Sanitize content to prevent header injection
            html_content = sanitize_email_content(html_content)
            text_content = sanitize_email_content(text_content)

            return html_content, text_content

        except TemplateNotFound as e:
            raise EmailTemplateError(
                f"Email template not found: {template_name}",
                template_name=template_name,
            )
        except Exception as e:
            raise EmailTemplateError(
                f"Failed to render email template: {e}",
                template_name=template_name,
            )

    def get_available_templates(self) -> list[str]:
        """Get list of available email templates."""
        templates = set()

        for root, dirs, files in os.walk(self.template_dir):
            # Skip __pycache__ and other hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

            for file in files:
                if file.endswith((".html", ".txt")) and not file.startswith("."):
                    # Get relative path from template directory
                    rel_path = os.path.relpath(os.path.join(root, file), self.template_dir)
                    # Normalize path
                    template_name = rel_path.replace(os.sep, "/")
                    templates.add(template_name)

        return sorted(templates)

    def validate_template(self, template_name: str) -> bool:
        """
        Check if a template exists.

        Args:
            template_name: Name of the template to check

        Returns:
            True if template exists (either HTML or text version)
        """
        try:
            # Get all available templates
            available = self.get_available_templates()
            # Check if either HTML or text version exists
            html_exists = f"{template_name}.html" in available
            text_exists = f"{template_name}.txt" in available
            return html_exists or text_exists
        except Exception:
            return False


# Singleton instance
_template_service: Optional[EmailTemplateService] = None


def get_template_service() -> EmailTemplateService:
    """Get or create the email template service singleton."""
    global _template_service
    if _template_service is None:
        _template_service = EmailTemplateService()
    return _template_service
