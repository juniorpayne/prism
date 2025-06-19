#!/usr/bin/env python3
"""
SMTP configuration validator for testing and troubleshooting.

This module provides tools to validate SMTP server configurations
including DNS resolution, port connectivity, and authentication.
"""

import asyncio
import logging
import socket
from typing import List, Optional, Tuple

import aiosmtplib

from .config import SMTPEmailConfig


class SMTPConfigValidator:
    """
    Validates SMTP configuration by testing various connection aspects.

    Performs the following checks:
    1. DNS resolution of SMTP host
    2. Port connectivity
    3. SMTP connection establishment
    4. TLS/SSL negotiation
    5. Authentication (if configured)
    """

    def __init__(self, config: SMTPEmailConfig):
        """
        Initialize validator with SMTP configuration.

        Args:
            config: SMTP configuration to validate
        """
        self.config = config
        self.results: List[str] = []
        self.logger = logging.getLogger(__name__)

    async def validate(self) -> Tuple[bool, List[str]]:
        """
        Run full validation of SMTP configuration.

        Returns:
            Tuple of (success, results) where results is a list of test outcomes
        """
        self.results = []

        # Test DNS resolution
        if not self._test_dns():
            return False, self.results

        # Test port connectivity
        if not await self._test_port():
            return False, self.results

        # Test SMTP connection
        if not await self._test_smtp_connection():
            return False, self.results

        # Test authentication if configured
        if self.config.username:
            if not await self._test_authentication():
                return False, self.results

        self.results.append("✅ All SMTP configuration tests passed!")
        return True, self.results

    async def quick_check(self) -> Tuple[bool, List[str]]:
        """
        Perform quick validation (DNS and port only).

        Returns:
            Tuple of (success, results)
        """
        self.results = []

        # Test DNS resolution
        if not self._test_dns():
            return False, self.results

        # Test port connectivity
        if not await self._test_port():
            return False, self.results

        self.results.append("✅ Quick check passed (DNS and port reachable)")
        return True, self.results

    def _test_dns(self) -> bool:
        """
        Test DNS resolution of SMTP host.

        Returns:
            True if DNS resolution succeeds
        """
        try:
            ip = socket.gethostbyname(self.config.host)
            self.results.append(f"✅ DNS resolution successful for {self.config.host} ({ip})")
            return True
        except socket.gaierror as e:
            self.results.append(f"❌ Failed to resolve {self.config.host}: {e}")
            return False

    async def _test_port(self) -> bool:
        """
        Test if SMTP port is reachable.

        Returns:
            True if port is reachable
        """
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.config.host, self.config.port),
                timeout=5.0,
            )
            writer.close()
            try:
                await writer.wait_closed()
            except AttributeError:
                # Handle mocks that don't have wait_closed
                pass
            self.results.append(f"✅ Port {self.config.port} is reachable")
            return True
        except asyncio.TimeoutError:
            self.results.append(
                f"❌ Cannot connect to {self.config.host}:{self.config.port} - Connection timeout"
            )
            return False
        except Exception as e:
            self.results.append(
                f"❌ Cannot connect to {self.config.host}:{self.config.port} - {type(e).__name__}: {e}"
            )
            return False

    async def _test_smtp_connection(self) -> bool:
        """
        Test SMTP connection and protocol negotiation.

        Returns:
            True if SMTP connection succeeds
        """
        smtp = None
        try:
            # Create SMTP client
            smtp = aiosmtplib.SMTP(
                hostname=self.config.host,
                port=self.config.port,
                timeout=10,
                use_tls=self.config.use_ssl,  # SSL from start
            )

            # Connect to server
            await smtp.connect()
            self.results.append("✅ SMTP connection established")

            # Test TLS if configured (and not using SSL)
            if self.config.use_tls and not self.config.use_ssl:
                try:
                    await smtp.starttls()
                    self.results.append("✅ TLS/SSL negotiation successful")
                except Exception as e:
                    self.results.append(f"❌ TLS/SSL configuration failed: {e}")
                    return False

            return True

        except aiosmtplib.SMTPException as e:
            self.results.append(f"❌ SMTP connection failed: {e}")
            return False
        except Exception as e:
            self.results.append(
                f"❌ Unexpected error during SMTP connection: {type(e).__name__}: {e}"
            )
            return False
        finally:
            if smtp:
                try:
                    await smtp.quit()
                except Exception:
                    pass

    async def _test_authentication(self) -> bool:
        """
        Test SMTP authentication.

        Returns:
            True if authentication succeeds
        """
        smtp = None
        try:
            # Create and connect SMTP client
            smtp = aiosmtplib.SMTP(
                hostname=self.config.host,
                port=self.config.port,
                timeout=10,
                use_tls=self.config.use_ssl,
            )

            await smtp.connect()

            # Handle TLS if needed
            if self.config.use_tls and not self.config.use_ssl:
                await smtp.starttls()

            # Test authentication
            await smtp.login(self.config.username, self.config.password)
            self.results.append("✅ Authentication successful")
            return True

        except aiosmtplib.SMTPAuthenticationError as e:
            self.results.append(f"❌ Authentication failed: {e}")
            return False
        except Exception as e:
            self.results.append(f"❌ Error during authentication test: {type(e).__name__}: {e}")
            return False
        finally:
            if smtp:
                try:
                    await smtp.quit()
                except Exception:
                    pass

    async def test_send_capability(self, test_email: str) -> Tuple[bool, str]:
        """
        Test ability to send an email (without actually sending).

        Args:
            test_email: Email address to test sending to

        Returns:
            Tuple of (success, message)
        """
        smtp = None
        try:
            # Create and connect SMTP client
            smtp = aiosmtplib.SMTP(
                hostname=self.config.host,
                port=self.config.port,
                timeout=10,
                use_tls=self.config.use_ssl,
            )

            await smtp.connect()

            # Handle TLS if needed
            if self.config.use_tls and not self.config.use_ssl:
                await smtp.starttls()

            # Authenticate if needed
            if self.config.username:
                await smtp.login(self.config.username, self.config.password)

            # Test recipient validation (VRFY command)
            # Note: Many servers disable VRFY for security
            try:
                response = await smtp.vrfy(test_email)
                if response.code == 250:
                    return True, f"Email address {test_email} verified by server"
            except Exception:
                # VRFY often disabled, not a failure
                pass

            # If we got here, connection is good
            return True, "SMTP server is ready to accept emails"

        except Exception as e:
            return False, f"Cannot send emails: {type(e).__name__}: {e}"
        finally:
            if smtp:
                try:
                    await smtp.quit()
                except Exception:
                    pass


async def validate_smtp_config(config: SMTPEmailConfig) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate SMTP configuration.

    Args:
        config: SMTP configuration to validate

    Returns:
        Tuple of (success, results)
    """
    validator = SMTPConfigValidator(config)
    return await validator.validate()
