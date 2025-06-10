#!/usr/bin/env python3
"""
Prometheus Metrics API Route (SCRUM-38)
Endpoint for Prometheus metrics scraping.
"""

import logging

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST

from server.monitoring import get_metrics_collector

logger = logging.getLogger(__name__)

router = APIRouter(tags=["monitoring"])


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Get Prometheus metrics for monitoring",
    response_class=Response,
)
async def get_metrics():
    """
    Get Prometheus metrics endpoint.

    Returns:
        Response with metrics in Prometheus format
    """
    try:
        collector = get_metrics_collector()
        metrics_data = collector.get_metrics()

        return Response(
            content=metrics_data,
            media_type=CONTENT_TYPE_LATEST,
            headers={"Content-Type": CONTENT_TYPE_LATEST},
        )
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return Response(
            content=f"# Error generating metrics: {str(e)}",
            media_type="text/plain",
            status_code=500,
        )
