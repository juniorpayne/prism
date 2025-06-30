#!/usr/bin/env python3
"""
Tests for AWS SES webhook endpoints.
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from server.auth.models.email_events import (
    BounceType,
    EmailBounce,
    EmailComplaint,
    EmailSuppression,
)


@pytest.mark.asyncio
class TestSESWebhooks:
    """Test SES webhook endpoints."""

    async def test_subscription_confirmation(self, async_client: AsyncClient):
        """Test SNS subscription confirmation."""
        subscription_data = {
            "Type": "SubscriptionConfirmation",
            "SubscribeURL": "https://sns.amazonaws.com/confirm/abc123",
            "Token": "abc123",
            "TopicArn": "arn:aws:sns:us-east-1:123456789012:ses-notifications",
        }

        with patch("server.api.routes.ses_webhooks.confirm_subscription") as mock_confirm:
            mock_confirm.return_value = None

            response = await async_client.post(
                "/api/webhooks/ses/notifications",
                json=subscription_data,
                headers={"x-amz-sns-message-type": "SubscriptionConfirmation"},
            )

            assert response.status_code == 200
            assert response.json() == {"status": "subscription confirmed"}
            mock_confirm.assert_called_once_with(subscription_data["SubscribeURL"])

    async def test_bounce_notification_permanent(self, async_client: AsyncClient, test_db_session):
        """Test permanent bounce notification handling."""
        bounce_notification = {
            "Type": "Notification",
            "Message": json.dumps(
                {
                    "notificationType": "Bounce",
                    "bounce": {
                        "bounceType": "permanent",
                        "bounceSubType": "General",
                        "feedbackId": "test-feedback-id-123",
                        "timestamp": "2025-06-30T00:00:00.000Z",
                        "reportingMTA": "dns; mail.example.com",
                        "bouncedRecipients": [
                            {
                                "emailAddress": "bounced@example.com",
                                "diagnosticCode": "550 5.1.1 User unknown",
                            }
                        ],
                        "mail": {"messageId": "test-message-id"},
                    },
                }
            ),
        }

        response = await async_client.post(
            "/api/webhooks/ses/notifications",
            json=bounce_notification,
            headers={"x-amz-sns-message-type": "Notification"},
        )

        assert response.status_code == 200
        assert response.json() == {"status": "processed"}

        # Check bounce was recorded
        bounce = await test_db_session.get(EmailBounce, {"feedback_id": "test-feedback-id-123"})
        assert bounce is not None
        assert bounce.email == "bounced@example.com"
        assert bounce.bounce_type == BounceType.PERMANENT
        assert bounce.diagnostic_code == "550 5.1.1 User unknown"

        # Check suppression was added
        suppression = await test_db_session.get(EmailSuppression, "bounced@example.com")
        assert suppression is not None
        assert suppression.reason == "bounce"
        assert suppression.expires_at is None  # Permanent

    async def test_bounce_notification_transient(self, async_client: AsyncClient, test_db_session):
        """Test transient bounce notification handling."""
        bounce_notification = {
            "Type": "Notification",
            "Message": json.dumps(
                {
                    "notificationType": "Bounce",
                    "bounce": {
                        "bounceType": "transient",
                        "bounceSubType": "MailboxFull",
                        "feedbackId": "test-feedback-id-456",
                        "timestamp": "2025-06-30T00:00:00.000Z",
                        "bouncedRecipients": [
                            {
                                "emailAddress": "full@example.com",
                                "diagnosticCode": "452 4.2.2 Mailbox full",
                            }
                        ],
                        "mail": {"messageId": "test-message-id"},
                    },
                }
            ),
        }

        response = await async_client.post(
            "/api/webhooks/ses/notifications",
            json=bounce_notification,
            headers={"x-amz-sns-message-type": "Notification"},
        )

        assert response.status_code == 200

        # Check bounce was recorded
        bounce = await test_db_session.get(EmailBounce, {"feedback_id": "test-feedback-id-456"})
        assert bounce is not None
        assert bounce.bounce_type == BounceType.TRANSIENT

        # Check temporary suppression was added
        suppression = await test_db_session.get(EmailSuppression, "full@example.com")
        assert suppression is not None
        assert suppression.expires_at is not None  # Temporary
        assert suppression.expires_at > datetime.now(timezone.utc)

    async def test_complaint_notification(self, async_client: AsyncClient, test_db_session):
        """Test complaint notification handling."""
        complaint_notification = {
            "Type": "Notification",
            "Message": json.dumps(
                {
                    "notificationType": "Complaint",
                    "complaint": {
                        "complaintFeedbackType": "abuse",
                        "feedbackId": "test-complaint-id-789",
                        "timestamp": "2025-06-30T00:00:00.000Z",
                        "userAgent": "Mozilla/5.0",
                        "complainedRecipients": [{"emailAddress": "complainer@example.com"}],
                        "mail": {"messageId": "test-message-id"},
                    },
                }
            ),
        }

        response = await async_client.post(
            "/api/webhooks/ses/notifications",
            json=complaint_notification,
            headers={"x-amz-sns-message-type": "Notification"},
        )

        assert response.status_code == 200

        # Check complaint was recorded
        complaint = await test_db_session.get(
            EmailComplaint, {"feedback_id": "test-complaint-id-789"}
        )
        assert complaint is not None
        assert complaint.email == "complainer@example.com"
        assert complaint.complaint_type == "abuse"

        # Check suppression was added
        suppression = await test_db_session.get(EmailSuppression, "complainer@example.com")
        assert suppression is not None
        assert suppression.reason == "complaint"

    async def test_duplicate_notification_ignored(self, async_client: AsyncClient, test_db_session):
        """Test that duplicate notifications are ignored."""
        bounce_notification = {
            "Type": "Notification",
            "Message": json.dumps(
                {
                    "notificationType": "Bounce",
                    "bounce": {
                        "bounceType": "permanent",
                        "feedbackId": "duplicate-id",
                        "timestamp": "2025-06-30T00:00:00.000Z",
                        "bouncedRecipients": [{"emailAddress": "dup@example.com"}],
                    },
                }
            ),
        }

        # Send first notification
        response1 = await async_client.post(
            "/api/webhooks/ses/notifications",
            json=bounce_notification,
            headers={"x-amz-sns-message-type": "Notification"},
        )
        assert response1.status_code == 200

        # Send duplicate
        response2 = await async_client.post(
            "/api/webhooks/ses/notifications",
            json=bounce_notification,
            headers={"x-amz-sns-message-type": "Notification"},
        )
        assert response2.status_code == 200

        # Check only one bounce exists
        bounces = (
            await test_db_session.query(EmailBounce).filter_by(feedback_id="duplicate-id").all()
        )
        assert len(bounces) == 1

    async def test_webhook_health_check(self, async_client: AsyncClient):
        """Test webhook health check endpoint."""
        response = await async_client.get("/api/webhooks/ses/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "ses-webhooks"}


@pytest.mark.asyncio
class TestEmailMetrics:
    """Test email metrics endpoints."""

    async def setup_test_data(self, db_session):
        """Setup test data for metrics."""
        # Add some bounces
        now = datetime.now(timezone.utc)
        bounces = [
            EmailBounce(
                email="bounce1@gmail.com",
                bounce_type=BounceType.PERMANENT,
                feedback_id="fb1",
                timestamp=now - timedelta(days=1),
                created_at=now - timedelta(days=1),
            ),
            EmailBounce(
                email="bounce2@yahoo.com",
                bounce_type=BounceType.PERMANENT,
                feedback_id="fb2",
                timestamp=now - timedelta(days=2),
                created_at=now - timedelta(days=2),
            ),
            EmailBounce(
                email="bounce3@gmail.com",
                bounce_type=BounceType.TRANSIENT,
                feedback_id="fb3",
                timestamp=now - timedelta(hours=12),
                created_at=now - timedelta(hours=12),
            ),
        ]
        for bounce in bounces:
            db_session.add(bounce)

        # Add some complaints
        complaints = [
            EmailComplaint(
                email="complaint1@hotmail.com",
                complaint_type="abuse",
                feedback_id="fc1",
                timestamp=now - timedelta(days=1),
                created_at=now - timedelta(days=1),
            ),
            EmailComplaint(
                email="complaint2@gmail.com",
                complaint_type="fraud",
                feedback_id="fc2",
                timestamp=now - timedelta(days=3),
                created_at=now - timedelta(days=3),
            ),
        ]
        for complaint in complaints:
            db_session.add(complaint)

        # Add suppressions
        suppressions = [
            EmailSuppression(email="bounce1@gmail.com", reason="bounce"),
            EmailSuppression(email="bounce2@yahoo.com", reason="bounce"),
            EmailSuppression(email="complaint1@hotmail.com", reason="complaint"),
        ]
        for suppression in suppressions:
            db_session.add(suppression)

        await db_session.commit()

    async def test_bounce_metrics(self, async_client: AsyncClient, test_db_session):
        """Test bounce metrics endpoint."""
        await self.setup_test_data(test_db_session)

        response = await async_client.get("/api/metrics/email/bounces?days=7")
        assert response.status_code == 200

        data = response.json()
        assert data["period_days"] == 7
        assert "permanent" in data["bounce_counts"]
        assert "transient" in data["bounce_counts"]
        assert data["bounce_counts"]["permanent"] == 2
        assert data["bounce_counts"]["transient"] == 1
        assert len(data["top_bouncing_domains"]) > 0
        assert data["total_suppressions"] == 3

    async def test_complaint_metrics(self, async_client: AsyncClient, test_db_session):
        """Test complaint metrics endpoint."""
        await self.setup_test_data(test_db_session)

        response = await async_client.get("/api/metrics/email/complaints?days=7")
        assert response.status_code == 200

        data = response.json()
        assert data["period_days"] == 7
        assert "abuse" in data["complaint_types"]
        assert "fraud" in data["complaint_types"]
        assert len(data["top_complaining_domains"]) > 0

    async def test_suppression_list(self, async_client: AsyncClient, test_db_session):
        """Test suppression list endpoint."""
        await self.setup_test_data(test_db_session)

        response = await async_client.get("/api/metrics/email/suppressions")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 3
        assert len(data["suppressions"]) == 3

        # Test filtering by reason
        response = await async_client.get("/api/metrics/email/suppressions?reason=bounce")
        data = response.json()
        assert data["total"] == 2

    async def test_remove_suppression(self, async_client: AsyncClient, test_db_session):
        """Test removing email from suppression list."""
        await self.setup_test_data(test_db_session)

        response = await async_client.delete("/api/metrics/email/suppressions/bounce1@gmail.com")
        assert response.status_code == 200

        # Check it's removed
        suppression = await test_db_session.get(EmailSuppression, "bounce1@gmail.com")
        assert suppression is None

    async def test_metrics_summary(self, async_client: AsyncClient, test_db_session):
        """Test metrics summary endpoint."""
        await self.setup_test_data(test_db_session)

        response = await async_client.get("/api/metrics/email/summary")
        assert response.status_code == 200

        data = response.json()
        assert "last_24_hours" in data
        assert "last_7_days" in data
        assert "suppressions" in data
        assert data["suppressions"]["total"] == 3
