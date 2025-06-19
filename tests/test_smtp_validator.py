#!/usr/bin/env python3
"""
Unit tests for SMTP configuration validator.
"""

import asyncio
import socket
from unittest.mock import AsyncMock, MagicMock, patch

import aiosmtplib
import pytest

from server.auth.email_providers.config import EmailProviderType, SMTPEmailConfig
from server.auth.email_providers.smtp_validator import SMTPConfigValidator


class TestSMTPConfigValidator:
    """Test SMTP configuration validator."""

    @pytest.fixture
    def smtp_config(self):
        """Create test SMTP configuration."""
        return SMTPEmailConfig(
            provider=EmailProviderType.SMTP,
            from_email="test@example.com",
            from_name="Test App",
            host="smtp.example.com",
            port=587,
            username="test_user",
            password="test_pass",
            use_tls=True,
            use_ssl=False,
            timeout=30,
        )

    @pytest.mark.asyncio
    async def test_validator_initialization(self, smtp_config):
        """Test validator initializes correctly."""
        validator = SMTPConfigValidator(smtp_config)

        assert validator.config == smtp_config
        assert validator.results == []

    @pytest.mark.asyncio
    async def test_successful_validation(self, smtp_config):
        """Test successful validation of all checks."""
        validator = SMTPConfigValidator(smtp_config)

        # Mock DNS resolution
        with patch("socket.gethostbyname", return_value="192.168.1.1"):
            # Mock port connectivity
            mock_writer = AsyncMock()
            with patch("asyncio.open_connection", return_value=(None, mock_writer)):
                # Mock SMTP connection
                mock_smtp = AsyncMock(spec=aiosmtplib.SMTP)
                with patch("aiosmtplib.SMTP", return_value=mock_smtp):
                    success, results = await validator.validate()

        assert success is True
        assert "✅ All SMTP configuration tests passed!" in results[-1]
        assert any("DNS resolution successful" in r for r in results)
        assert any("Port 587 is reachable" in r for r in results)

    @pytest.mark.asyncio
    async def test_dns_resolution_failure(self, smtp_config):
        """Test handling of DNS resolution failure."""
        validator = SMTPConfigValidator(smtp_config)

        # Mock DNS failure
        with patch("socket.gethostbyname", side_effect=socket.gaierror("DNS lookup failed")):
            success, results = await validator.validate()

        assert success is False
        assert any("Failed to resolve smtp.example.com" in r for r in results)

    @pytest.mark.asyncio
    async def test_port_connectivity_failure(self, smtp_config):
        """Test handling of port connectivity failure."""
        validator = SMTPConfigValidator(smtp_config)

        # Mock successful DNS but failed port connection
        with patch("socket.gethostbyname", return_value="192.168.1.1"):
            with patch(
                "asyncio.open_connection",
                side_effect=asyncio.TimeoutError("Connection timeout"),
            ):
                success, results = await validator.validate()

        assert success is False
        assert any("Cannot connect to smtp.example.com:587" in r for r in results)

    @pytest.mark.asyncio
    async def test_smtp_connection_failure(self, smtp_config):
        """Test handling of SMTP connection failure."""
        validator = SMTPConfigValidator(smtp_config)

        with patch("socket.gethostbyname", return_value="192.168.1.1"):
            mock_writer = AsyncMock()
            with patch("asyncio.open_connection", return_value=(None, mock_writer)):
                # Mock SMTP connection failure
                mock_smtp = AsyncMock(spec=aiosmtplib.SMTP)
                mock_smtp.connect.side_effect = aiosmtplib.SMTPException("Connection failed")
                with patch("aiosmtplib.SMTP", return_value=mock_smtp):
                    success, results = await validator.validate()

        assert success is False
        assert any("SMTP connection failed" in r for r in results)

    @pytest.mark.asyncio
    async def test_authentication_failure(self, smtp_config):
        """Test handling of authentication failure."""
        validator = SMTPConfigValidator(smtp_config)

        with patch("socket.gethostbyname", return_value="192.168.1.1"):
            mock_writer = AsyncMock()
            with patch("asyncio.open_connection", return_value=(None, mock_writer)):
                # Mock SMTP with auth failure
                mock_smtp = AsyncMock(spec=aiosmtplib.SMTP)
                mock_smtp.login.side_effect = aiosmtplib.SMTPAuthenticationError(
                    535, "Authentication failed"
                )
                with patch("aiosmtplib.SMTP", return_value=mock_smtp):
                    success, results = await validator.validate()

        assert success is False
        assert any("Authentication failed" in r for r in results)

    @pytest.mark.asyncio
    async def test_tls_failure(self, smtp_config):
        """Test handling of TLS negotiation failure."""
        validator = SMTPConfigValidator(smtp_config)

        with patch("socket.gethostbyname", return_value="192.168.1.1"):
            mock_writer = AsyncMock()
            with patch("asyncio.open_connection", return_value=(None, mock_writer)):
                # Mock SMTP with TLS failure
                mock_smtp = AsyncMock(spec=aiosmtplib.SMTP)
                mock_smtp.starttls.side_effect = aiosmtplib.SMTPException("TLS negotiation failed")
                with patch("aiosmtplib.SMTP", return_value=mock_smtp):
                    success, results = await validator.validate()

        assert success is False
        assert any("TLS/SSL configuration failed" in r for r in results)

    @pytest.mark.asyncio
    async def test_validation_without_auth(self):
        """Test validation when no authentication is configured."""
        # Create config without auth
        config = SMTPEmailConfig(
            provider=EmailProviderType.SMTP,
            from_email="test@example.com",
            from_name="Test App",
            host="smtp.example.com",
            port=587,
            use_tls=True,
            use_ssl=False,
            timeout=30,
            # No username/password
        )

        validator = SMTPConfigValidator(config)

        with patch("socket.gethostbyname", return_value="192.168.1.1"):
            mock_writer = AsyncMock()
            with patch("asyncio.open_connection", return_value=(None, mock_writer)):
                mock_smtp = AsyncMock(spec=aiosmtplib.SMTP)
                with patch("aiosmtplib.SMTP", return_value=mock_smtp):
                    success, results = await validator.validate()

        assert success is True
        # Should not attempt login
        mock_smtp.login.assert_not_called()

    @pytest.mark.asyncio
    async def test_ssl_configuration(self):
        """Test validation with SSL instead of TLS."""
        config = SMTPEmailConfig(
            provider=EmailProviderType.SMTP,
            from_email="test@example.com",
            host="smtp.example.com",
            port=465,
            use_ssl=True,
            use_tls=False,
        )

        validator = SMTPConfigValidator(config)

        with patch("socket.gethostbyname", return_value="192.168.1.1"):
            mock_writer = AsyncMock()
            with patch("asyncio.open_connection", return_value=(None, mock_writer)):
                mock_smtp = AsyncMock(spec=aiosmtplib.SMTP)
                with patch("aiosmtplib.SMTP", return_value=mock_smtp):
                    success, results = await validator.validate()

        assert success is True
        # Should not call starttls for SSL connections
        mock_smtp.starttls.assert_not_called()

    @pytest.mark.asyncio
    async def test_quick_check_mode(self, smtp_config):
        """Test quick validation mode (DNS and port only)."""
        validator = SMTPConfigValidator(smtp_config)

        with patch("socket.gethostbyname", return_value="192.168.1.1"):
            mock_writer = AsyncMock()
            with patch("asyncio.open_connection", return_value=(None, mock_writer)):
                success, results = await validator.quick_check()

        assert success is True
        assert any("DNS resolution successful" in r for r in results)
        assert any("Port 587 is reachable" in r for r in results)
        # Should not include SMTP connection results
        assert not any("SMTP connection" in r for r in results)
