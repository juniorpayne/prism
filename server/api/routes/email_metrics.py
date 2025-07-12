#!/usr/bin/env python3
"""
Email metrics endpoints for monitoring email performance and issues.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth.email_events import (
    BounceType,
    EmailBounce,
    EmailComplaint,
    EmailSuppression,
)
from server.database.connection import get_async_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metrics/email", tags=["metrics"])


@router.get("/bounces")
async def get_bounce_metrics(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_async_db),
):
    """Get email bounce metrics."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Get bounce counts by type
    result = await db.execute(
        select(EmailBounce.bounce_type, func.count(EmailBounce.id).label("count"))
        .where(EmailBounce.created_at >= since)
        .group_by(EmailBounce.bounce_type)
    )

    bounce_counts = {row[0].value: row[1] for row in result}

    # Get top bouncing domains
    result = await db.execute(
        select(
            func.substring(EmailBounce.email, func.position("@" in EmailBounce.email) + 1).label(
                "domain"
            ),
            func.count(EmailBounce.id).label("count"),
        )
        .where(EmailBounce.created_at >= since)
        .group_by("domain")
        .order_by(desc("count"))
        .limit(10)
    )

    top_domains = [{"domain": row[0], "count": row[1]} for row in result]

    # Get recent bounces
    result = await db.execute(
        select(EmailBounce)
        .where(EmailBounce.created_at >= since)
        .order_by(desc(EmailBounce.created_at))
        .limit(20)
    )

    recent_bounces = [
        {
            "email": bounce.email,
            "type": bounce.bounce_type.value,
            "subtype": bounce.bounce_subtype,
            "timestamp": bounce.timestamp.isoformat(),
            "diagnostic": bounce.diagnostic_code,
        }
        for bounce in result.scalars()
    ]

    # Get total suppression count
    total_suppressions = await db.scalar(select(func.count(EmailSuppression.email)))

    return {
        "period_days": days,
        "bounce_counts": bounce_counts,
        "top_bouncing_domains": top_domains,
        "recent_bounces": recent_bounces,
        "total_suppressions": total_suppressions,
    }


@router.get("/complaints")
async def get_complaint_metrics(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_async_db),
):
    """Get email complaint metrics."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Get complaint counts by type
    result = await db.execute(
        select(EmailComplaint.complaint_type, func.count(EmailComplaint.id).label("count"))
        .where(EmailComplaint.created_at >= since)
        .group_by(EmailComplaint.complaint_type)
    )

    complaint_types = {row[0] or "unspecified": row[1] for row in result}

    # Get top complaining domains
    result = await db.execute(
        select(
            func.substring(
                EmailComplaint.email, func.position("@" in EmailComplaint.email) + 1
            ).label("domain"),
            func.count(EmailComplaint.id).label("count"),
        )
        .where(EmailComplaint.created_at >= since)
        .group_by("domain")
        .order_by(desc("count"))
        .limit(10)
    )

    top_domains = [{"domain": row[0], "count": row[1]} for row in result]

    # Get recent complaints
    result = await db.execute(
        select(EmailComplaint)
        .where(EmailComplaint.created_at >= since)
        .order_by(desc(EmailComplaint.created_at))
        .limit(20)
    )

    recent_complaints = [
        {
            "email": complaint.email,
            "type": complaint.complaint_type or "unspecified",
            "timestamp": complaint.timestamp.isoformat(),
            "user_agent": complaint.user_agent,
        }
        for complaint in result.scalars()
    ]

    return {
        "period_days": days,
        "complaint_types": complaint_types,
        "top_complaining_domains": top_domains,
        "recent_complaints": recent_complaints,
    }


@router.get("/suppressions")
async def get_suppression_list(
    reason: Optional[str] = Query(None, description="Filter by reason: bounce, complaint, manual"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_async_db),
):
    """Get email suppression list."""
    query = select(EmailSuppression)

    # Apply reason filter if provided
    if reason:
        query = query.where(EmailSuppression.reason == reason)

    # Only show active suppressions
    now = datetime.now(timezone.utc)
    query = query.where(EmailSuppression.expires_at.is_(None) | (EmailSuppression.expires_at > now))

    # Order by creation date
    query = query.order_by(desc(EmailSuppression.created_at))

    # Get total count
    count_query = select(func.count()).select_from(query.alias())
    total_count = await db.scalar(count_query)

    # Apply pagination
    query = query.limit(limit).offset(offset)

    # Execute query
    result = await db.execute(query)

    suppressions = [
        {
            "email": supp.email,
            "reason": supp.reason,
            "created_at": supp.created_at.isoformat(),
            "expires_at": supp.expires_at.isoformat() if supp.expires_at else None,
            "is_permanent": supp.expires_at is None,
        }
        for supp in result.scalars()
    ]

    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "suppressions": suppressions,
    }


@router.delete("/suppressions/{email}")
async def remove_suppression(
    email: str,
    db: AsyncSession = Depends(get_async_db),
):
    """Remove an email from the suppression list."""
    email = email.lower()

    result = await db.execute(select(EmailSuppression).where(EmailSuppression.email == email))
    suppression = result.scalar_one_or_none()

    if not suppression:
        return {"message": "Email not found in suppression list"}

    await db.delete(suppression)
    await db.commit()

    logger.info(f"Removed {email} from suppression list")
    return {"message": f"Successfully removed {email} from suppression list"}


@router.get("/summary")
async def get_email_metrics_summary(
    db: AsyncSession = Depends(get_async_db),
):
    """Get overall email metrics summary."""
    # Last 24 hours
    last_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    # Last 7 days
    last_7d = datetime.now(timezone.utc) - timedelta(days=7)

    # Get 24h bounce rate
    bounces_24h = await db.scalar(
        select(func.count(EmailBounce.id)).where(EmailBounce.created_at >= last_24h)
    )

    # Get 24h complaint rate
    complaints_24h = await db.scalar(
        select(func.count(EmailComplaint.id)).where(EmailComplaint.created_at >= last_24h)
    )

    # Get 7d bounce breakdown
    result = await db.execute(
        select(EmailBounce.bounce_type, func.count(EmailBounce.id).label("count"))
        .where(EmailBounce.created_at >= last_7d)
        .group_by(EmailBounce.bounce_type)
    )
    bounce_breakdown_7d = {row[0].value: row[1] for row in result}

    # Get total suppressions by reason
    result = await db.execute(
        select(EmailSuppression.reason, func.count(EmailSuppression.email).label("count")).group_by(
            EmailSuppression.reason
        )
    )
    suppression_breakdown = {row[0]: row[1] for row in result}

    return {
        "last_24_hours": {
            "bounces": bounces_24h,
            "complaints": complaints_24h,
        },
        "last_7_days": {
            "bounce_breakdown": bounce_breakdown_7d,
        },
        "suppressions": {
            "total": sum(suppression_breakdown.values()),
            "by_reason": suppression_breakdown,
        },
    }
