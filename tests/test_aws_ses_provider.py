#!/usr/bin/env python3
"""
Unit tests for AWS SES email provider.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from botocore.exceptions import ClientError

from server.auth.email_providers import EmailMessage
from server.auth.email_providers.aws_ses import AWSSESEmailProvider
from server.auth.email_providers.config import AWSSESConfig, EmailProviderType


class TestAWSSESEmailProvider:
    """Test AWS SES email provider functionality."""

    @pytest.fixture
    def ses_config(self):
        """Create test SES configuration."""
        return AWSSESConfig(
            provider=EmailProviderType.AWS_SES,
            from_email="noreply@example.com",
            from_name="Test App",
            region="us-east-1",
            access_key_id="test_access_key",
            secret_access_key="test_secret_key",
            use_iam_role=False,
            configuration_set="test-config-set",
        )

    @pytest.fixture
    def ses_config_iam(self):
        """Create test SES configuration with IAM role."""
        return AWSSESConfig(
            provider=EmailProviderType.AWS_SES,
            from_email="noreply@example.com",
            from_name="Test App",
            region="us-east-1",
            use_iam_role=True,
        )

    @pytest.fixture
    def email_message(self):
        """Create test email message."""
        return EmailMessage(
            to=["recipient@example.com"],
            subject="Test Email",
            text_body="This is a test email.",
            html_body="<p>This is a test email.</p>",
            from_email="sender@example.com",
            from_name="Sender Name",
        )

    @pytest.mark.asyncio
    async def test_send_email_success(self, ses_config, email_message):
        """Test successful email sending."""
        provider = AWSSESEmailProvider(ses_config)

        # Mock SES client
        mock_ses_client = MagicMock()
        mock_ses_client.send_email.return_value = {
            "MessageId": "test-message-id-123",
            "ResponseMetadata": {"RequestId": "test-request-id"},
        }

        provider._client = mock_ses_client

        # Send email
        result = await provider.send_email(email_message)

        # Verify result
        assert result.success is True
        assert result.message_id == "test-message-id-123"
        assert result.provider == "aws_ses"
        assert result.metadata["ses_message_id"] == "test-message-id-123"
        assert result.metadata["request_id"] == "test-request-id"

        # Verify SES client was called correctly
        mock_ses_client.send_email.assert_called_once()
        call_args = mock_ses_client.send_email.call_args[1]

        assert call_args["Source"] == "Sender Name <sender@example.com>"
        assert call_args["Destination"]["ToAddresses"] == ["recipient@example.com"]
        assert call_args["Message"]["Subject"]["Data"] == "Test Email"
        assert call_args["Message"]["Body"]["Text"]["Data"] == "This is a test email."
        assert call_args["Message"]["Body"]["Html"]["Data"] == "<p>This is a test email.</p>"
        assert call_args["ConfigurationSetName"] == "test-config-set"

    @pytest.mark.asyncio
    async def test_send_email_client_error(self, ses_config, email_message):
        """Test handling of AWS client errors."""
        provider = AWSSESEmailProvider(ses_config)

        # Mock SES client with error
        mock_ses_client = MagicMock()
        error_response = {
            "Error": {
                "Code": "MessageRejected",
                "Message": "Email address is not verified.",
            }
        }
        mock_ses_client.send_email.side_effect = ClientError(error_response, "SendEmail")

        provider._client = mock_ses_client

        # Send email
        result = await provider.send_email(email_message)

        # Verify error handling
        assert result.success is False
        assert "Email was rejected" in result.error
        assert result.metadata["error_code"] == "MessageRejected"

    @pytest.mark.asyncio
    async def test_send_email_with_cc_and_reply_to(self, ses_config):
        """Test sending email with CC and Reply-To."""
        provider = AWSSESEmailProvider(ses_config)

        message = EmailMessage(
            to=["recipient@example.com"],
            cc=["cc@example.com"],
            subject="Test",
            text_body="Test",
            html_body="<p>Test</p>",
            reply_to="reply@example.com",
        )

        # Mock SES client
        mock_ses_client = MagicMock()
        mock_ses_client.send_email.return_value = {
            "MessageId": "test-123",
            "ResponseMetadata": {"RequestId": "req-123"},
        }

        provider._client = mock_ses_client

        # Send email
        await provider.send_email(message)

        # Verify CC and Reply-To were set
        call_args = mock_ses_client.send_email.call_args[1]
        assert call_args["Destination"]["CcAddresses"] == ["cc@example.com"]
        assert call_args["ReplyToAddresses"] == ["reply@example.com"]

    @pytest.mark.asyncio
    async def test_send_email_with_custom_headers(self, ses_config):
        """Test sending email with custom headers."""
        provider = AWSSESEmailProvider(ses_config)

        message = EmailMessage(
            to=["recipient@example.com"],
            subject="Test",
            text_body="Test",
            html_body="<p>Test</p>",
            headers={"X-Custom-Header": "value", "X-Priority": "high"},
        )

        # Mock SES client
        mock_ses_client = MagicMock()
        mock_ses_client.send_email.return_value = {
            "MessageId": "test-123",
            "ResponseMetadata": {"RequestId": "req-123"},
        }

        provider._client = mock_ses_client

        # Send email
        await provider.send_email(message)

        # Verify tags were set for headers
        call_args = mock_ses_client.send_email.call_args[1]
        tags = call_args.get("Tags", [])
        assert len(tags) == 2
        tag_dict = {tag["Name"]: tag["Value"] for tag in tags}
        assert tag_dict["X-Custom-Header"] == "value"
        assert tag_dict["X-Priority"] == "high"

    def test_create_client_with_credentials(self, ses_config):
        """Test SES client creation with explicit credentials."""
        provider = AWSSESEmailProvider(ses_config)

        with patch("boto3.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            # Access client property to trigger creation
            _ = provider.client

            # Verify session was created with credentials
            mock_session_class.assert_called_once_with(
                region_name="us-east-1",
                aws_access_key_id="test_access_key",
                aws_secret_access_key="test_secret_key",
            )
            mock_session.client.assert_called_once_with("ses")

    def test_create_client_with_iam_role(self, ses_config_iam):
        """Test SES client creation with IAM role."""
        provider = AWSSESEmailProvider(ses_config_iam)

        with patch("boto3.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            # Access client property to trigger creation
            _ = provider.client

            # Verify session was created without explicit credentials
            mock_session_class.assert_called_once_with(region_name="us-east-1")
            mock_session.client.assert_called_once_with("ses")

    @pytest.mark.asyncio
    async def test_verify_configuration_success(self, ses_config):
        """Test successful configuration verification."""
        provider = AWSSESEmailProvider(ses_config)

        # Mock SES client
        mock_ses_client = MagicMock()
        mock_ses_client.describe_configuration_set.return_value = {
            "ConfigurationSet": {"Name": "test-config-set"}
        }

        provider._client = mock_ses_client

        # Verify configuration
        result = await provider.verify_configuration()

        assert result is True
        mock_ses_client.describe_configuration_set.assert_called_once_with(
            ConfigurationSetName="test-config-set"
        )

    @pytest.mark.asyncio
    async def test_verify_configuration_no_config_set(self, ses_config_iam):
        """Test configuration verification without config set."""
        provider = AWSSESEmailProvider(ses_config_iam)

        # Mock SES client
        mock_ses_client = MagicMock()
        mock_ses_client.get_send_quota.return_value = {
            "Max24HourSend": 200.0,
            "MaxSendRate": 1.0,
            "SentLast24Hours": 10.0,
        }

        provider._client = mock_ses_client

        # Verify configuration
        result = await provider.verify_configuration()

        assert result is True
        mock_ses_client.get_send_quota.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_configuration_failure(self, ses_config):
        """Test configuration verification failure."""
        provider = AWSSESEmailProvider(ses_config)

        # Mock SES client with error
        mock_ses_client = MagicMock()
        error_response = {
            "Error": {
                "Code": "ConfigurationSetDoesNotExist",
                "Message": "Configuration set not found.",
            }
        }
        mock_ses_client.describe_configuration_set.side_effect = ClientError(
            error_response, "DescribeConfigurationSet"
        )

        provider._client = mock_ses_client

        # Verify configuration
        result = await provider.verify_configuration()

        assert result is False

    @pytest.mark.asyncio
    async def test_send_email_async_execution(self, ses_config, email_message):
        """Test that SES operations run in executor."""
        provider = AWSSESEmailProvider(ses_config)

        # Mock SES client
        mock_ses_client = MagicMock()
        mock_ses_client.send_email.return_value = {
            "MessageId": "test-123",
            "ResponseMetadata": {"RequestId": "req-123"},
        }

        provider._client = mock_ses_client

        # Mock event loop
        mock_loop = AsyncMock()
        mock_loop.run_in_executor = AsyncMock(
            return_value={
                "MessageId": "test-123",
                "ResponseMetadata": {"RequestId": "req-123"},
            }
        )

        with patch("asyncio.get_event_loop", return_value=mock_loop):
            result = await provider.send_email(email_message)

            assert result.success is True
            # Verify run_in_executor was called
            mock_loop.run_in_executor.assert_called_once()
            assert mock_loop.run_in_executor.call_args[0][0] is None  # executor

    def test_get_user_friendly_error_messages(self, ses_config):
        """Test error message mapping."""
        provider = AWSSESEmailProvider(ses_config)

        # Test known error codes
        assert "rejected" in provider._get_user_friendly_error("MessageRejected", "").lower()
        assert (
            "domain is not verified"
            in provider._get_user_friendly_error("MailFromDomainNotVerified", "").lower()
        )
        assert (
            "configuration set not found"
            in provider._get_user_friendly_error("ConfigurationSetDoesNotExist", "").lower()
        )
        assert (
            "sending is paused"
            in provider._get_user_friendly_error("AccountSendingPausedException", "").lower()
        )
        assert (
            "sending limit reached"
            in provider._get_user_friendly_error("SendingQuotaExceeded", "").lower()
        )
        assert (
            "too quickly" in provider._get_user_friendly_error("MaxSendingRateExceeded", "").lower()
        )

        # Test unknown error code
        error_msg = provider._get_user_friendly_error("UnknownError", "Something went wrong")
        assert "SES Error: Something went wrong" == error_msg

    @pytest.mark.asyncio
    async def test_send_email_without_html_body(self, ses_config):
        """Test sending plain text only email."""
        provider = AWSSESEmailProvider(ses_config)

        message = EmailMessage(
            to=["recipient@example.com"],
            subject="Test",
            text_body="Plain text only",
            html_body=None,
        )

        # Mock SES client
        mock_ses_client = MagicMock()
        mock_ses_client.send_email.return_value = {
            "MessageId": "test-123",
            "ResponseMetadata": {"RequestId": "req-123"},
        }

        provider._client = mock_ses_client

        # Send email
        await provider.send_email(message)

        # Verify only text part was sent
        call_args = mock_ses_client.send_email.call_args[1]
        assert "Text" in call_args["Message"]["Body"]
        assert "Html" not in call_args["Message"]["Body"]

    @pytest.mark.asyncio
    async def test_send_email_without_text_body(self, ses_config):
        """Test sending HTML only email."""
        provider = AWSSESEmailProvider(ses_config)

        message = EmailMessage(
            to=["recipient@example.com"],
            subject="Test",
            text_body=None,
            html_body="<p>HTML only</p>",
        )

        # Mock SES client
        mock_ses_client = MagicMock()
        mock_ses_client.send_email.return_value = {
            "MessageId": "test-123",
            "ResponseMetadata": {"RequestId": "req-123"},
        }

        provider._client = mock_ses_client

        # Send email
        await provider.send_email(message)

        # Verify only HTML part was sent
        call_args = mock_ses_client.send_email.call_args[1]
        assert "Html" in call_args["Message"]["Body"]
        assert "Text" not in call_args["Message"]["Body"]

    def test_provider_name(self, ses_config):
        """Test provider name property."""
        provider = AWSSESEmailProvider(ses_config)
        assert provider.provider_name == "aws_ses"

    def test_repr(self, ses_config):
        """Test string representation."""
        provider = AWSSESEmailProvider(ses_config)
        repr_str = repr(provider)
        assert "AWSSESEmailProvider" in repr_str
        assert "us-east-1" in repr_str

    @pytest.mark.asyncio
    async def test_send_email_with_suppression(self, ses_config, email_message):
        """Test email sending with suppressed recipient."""
        provider = AWSSESEmailProvider(ses_config)

        # Mock suppression check to return suppressed email
        with patch.object(
            provider, "_check_suppressions", return_value=["recipient@example.com"]
        ) as mock_check:
            # Send email
            result = await provider.send_email(email_message)

            # Verify suppression was checked
            mock_check.assert_called_once_with(["recipient@example.com"])

            # Verify result
            assert result.success is False
            assert "suppressed" in result.error.lower()
            assert result.metadata["suppressed_emails"] == ["recipient@example.com"]

    @pytest.mark.asyncio
    async def test_check_suppressions_empty(self, ses_config):
        """Test suppression check with no suppressions."""
        provider = AWSSESEmailProvider(ses_config)

        # Mock database query
        with patch("server.database.connection.get_async_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_result = AsyncMock()
            mock_result.fetchall.return_value = []
            mock_db.execute.return_value = mock_result
            mock_get_db.return_value.__aiter__.return_value = [mock_db]

            suppressions = await provider._check_suppressions(["test@example.com"])
            assert suppressions == []

    @pytest.mark.asyncio
    async def test_check_suppressions_with_results(self, ses_config):
        """Test suppression check with suppressed emails."""
        provider = AWSSESEmailProvider(ses_config)

        # Mock database query
        with patch("server.database.connection.get_async_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_result = AsyncMock()
            mock_result.fetchall.return_value = [("suppressed@example.com",)]
            mock_db.execute.return_value = mock_result
            mock_get_db.return_value.__aiter__.return_value = [mock_db]

            suppressions = await provider._check_suppressions(
                ["test@example.com", "suppressed@example.com"]
            )
            assert suppressions == ["suppressed@example.com"]

    @pytest.mark.asyncio
    async def test_check_suppressions_error_handling(self, ses_config):
        """Test suppression check handles errors gracefully."""
        provider = AWSSESEmailProvider(ses_config)

        # Mock database error
        with patch("server.database.connection.get_async_db") as mock_get_db:
            mock_get_db.side_effect = Exception("Database error")

            # Should return empty list on error
            suppressions = await provider._check_suppressions(["test@example.com"])
            assert suppressions == []
