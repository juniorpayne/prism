#!/usr/bin/env python3
"""
AWS SES webhook endpoints for handling bounce and complaint notifications.
"""

import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.models.email_events import (
    BounceType,
    EmailBounce,
    EmailComplaint,
    EmailSuppression,
)
from server.database.connection import get_async_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks/ses", tags=["webhooks"])


async def verify_sns_signature(headers: dict, body: bytes) -> bool:
    """
    Verify SNS message signature for security.

    Args:
        headers: Request headers
        body: Raw request body

    Returns:
        True if signature is valid
    """
    # In development, skip verification
    # TODO: Implement proper SNS signature verification in production
    if headers.get("x-amz-sns-message-type"):
        return True
    return False


async def confirm_subscription(subscribe_url: str) -> None:
    """
    Confirm SNS subscription by visiting the subscribe URL.

    Args:
        subscribe_url: URL to confirm subscription
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(subscribe_url) as response:
                if response.status != 200:
                    logger.error(f"Failed to confirm subscription: {response.status}")
                else:
                    logger.info("SNS subscription confirmed successfully")
    except Exception as e:
        logger.error(f"Error confirming subscription: {e}")


@router.post("/notifications")
async def ses_notification_webhook(request: Request, db: AsyncSession = Depends(get_async_db)):
    """Handle SES bounce and complaint notifications from SNS."""
    try:
        # Get raw body
        body = await request.body()

        # Verify SNS signature (important for security)
        if not await verify_sns_signature(dict(request.headers), body):
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse notification
        data = json.loads(body)

        # Handle subscription confirmation
        if data.get("Type") == "SubscriptionConfirmation":
            await confirm_subscription(data["SubscribeURL"])
            return {"status": "subscription confirmed"}

        # Handle notification
        if data.get("Type") == "Notification":
            message = json.loads(data["Message"])

            if message["notificationType"] == "Bounce":
                await handle_bounce(db, message["bounce"])
            elif message["notificationType"] == "Complaint":
                await handle_complaint(db, message["complaint"])
            elif message["notificationType"] == "Delivery":
                # Optionally track successful deliveries
                logger.info(f"Delivery notification: {message.get('mail', {}).get('messageId')}")

        return {"status": "processed"}

    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook request")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Error processing SES webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def handle_bounce(db: AsyncSession, bounce_data: Dict[str, Any]) -> None:
    """Process bounce notification."""
    try:
        bounce_type = BounceType(bounce_data["bounceType"])

        for recipient in bounce_data["bouncedRecipients"]:
            email = recipient["emailAddress"].lower()

            # Check if bounce already exists (avoid duplicates)
            existing = await db.execute(
                select(EmailBounce).where(EmailBounce.feedback_id == bounce_data["feedbackId"])
            )
            if existing.scalar_one_or_none():
                logger.info(f"Bounce already recorded for feedback ID: {bounce_data['feedbackId']}")
                continue

            # Record bounce
            bounce = EmailBounce(
                email=email,
                bounce_type=bounce_type,
                bounce_subtype=bounce_data.get("bounceSubType"),
                message_id=bounce_data.get("mail", {}).get("messageId"),
                feedback_id=bounce_data["feedbackId"],
                timestamp=datetime.fromisoformat(bounce_data["timestamp"].replace("Z", "+00:00")),
                diagnostic_code=recipient.get("diagnosticCode"),
                reporting_mta=bounce_data.get("reportingMTA"),
            )
            db.add(bounce)

            # Add to suppression list for permanent bounces
            if bounce_type == BounceType.PERMANENT:
                # Check if already suppressed
                existing_suppression = await db.execute(
                    select(EmailSuppression).where(EmailSuppression.email == email)
                )
                if not existing_suppression.scalar_one_or_none():
                    suppression = EmailSuppression(email=email, reason="bounce")
                    db.add(suppression)
                    logger.info(f"Added {email} to suppression list due to permanent bounce")

            # For transient bounces, add temporary suppression (24 hours)
            elif bounce_type == BounceType.TRANSIENT:
                existing_suppression = await db.execute(
                    select(EmailSuppression).where(EmailSuppression.email == email)
                )
                if not existing_suppression.scalar_one_or_none():
                    suppression = EmailSuppression(
                        email=email,
                        reason="bounce",
                        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
                    )
                    db.add(suppression)
                    logger.info(f"Added {email} to temporary suppression list (24h)")

        await db.commit()
        logger.info(f"Processed bounce for {len(bounce_data['bouncedRecipients'])} recipients")

    except Exception as e:
        logger.error(f"Error handling bounce: {e}")
        await db.rollback()
        raise


async def handle_complaint(db: AsyncSession, complaint_data: Dict[str, Any]) -> None:
    """Process complaint notification."""
    try:
        for recipient in complaint_data["complainedRecipients"]:
            email = recipient["emailAddress"].lower()

            # Check if complaint already exists
            existing = await db.execute(
                select(EmailComplaint).where(
                    EmailComplaint.feedback_id == complaint_data["feedbackId"]
                )
            )
            if existing.scalar_one_or_none():
                logger.info(
                    f"Complaint already recorded for feedback ID: {complaint_data['feedbackId']}"
                )
                continue

            # Record complaint
            complaint = EmailComplaint(
                email=email,
                complaint_type=complaint_data.get("complaintFeedbackType"),
                message_id=complaint_data.get("mail", {}).get("messageId"),
                feedback_id=complaint_data["feedbackId"],
                timestamp=datetime.fromisoformat(
                    complaint_data["timestamp"].replace("Z", "+00:00")
                ),
                user_agent=complaint_data.get("userAgent"),
            )
            db.add(complaint)

            # Always suppress complaints
            existing_suppression = await db.execute(
                select(EmailSuppression).where(EmailSuppression.email == email)
            )
            if not existing_suppression.scalar_one_or_none():
                suppression = EmailSuppression(email=email, reason="complaint")
                db.add(suppression)
                logger.info(f"Added {email} to suppression list due to complaint")

        await db.commit()
        logger.info(
            f"Processed complaint for {len(complaint_data['complainedRecipients'])} recipients"
        )

    except Exception as e:
        logger.error(f"Error handling complaint: {e}")
        await db.rollback()
        raise


@router.get("/health")
async def webhook_health():
    """Health check endpoint for webhook service."""
    return {"status": "healthy", "service": "ses-webhooks"}
