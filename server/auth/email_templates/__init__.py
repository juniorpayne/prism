#!/usr/bin/env python3
"""
Email templates package for Prism DNS authentication system.
"""

from server.auth.email_templates.service import EmailTemplateService, get_template_service

__all__ = [
    "EmailTemplateService",
    "get_template_service",
]
