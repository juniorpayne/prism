#!/usr/bin/env python3
"""
Host API Routes (SCRUM-17)
REST endpoints for host data retrieval.
"""

import logging
import math
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError

from server.api.dependencies import get_database_manager, get_host_operations
from server.api.models import (
    HostListResponse,
    HostResponse,
    PaginationParams,
    create_error_response,
)
from server.auth.dependencies import get_current_verified_user
from server.auth.models import User
from server.database.models import Host
from server.database.operations import HostOperations

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["hosts"])


@router.get(
    "/hosts",
    response_model=HostListResponse,
    summary="List all hosts",
    description="Get paginated list of all registered hosts",
)
async def get_hosts(
    current_user: User = Depends(get_current_verified_user),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(50, ge=1, le=1000, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by host status"),
    search: Optional[str] = Query(None, description="Search in hostname"),
    host_ops: HostOperations = Depends(get_host_operations),
) -> HostListResponse:
    """
    Get paginated list of hosts with optional filtering.

    Args:
        page: Page number (1-based)
        per_page: Number of items per page
        status: Optional status filter
        search: Optional hostname search
        host_ops: Host operations dependency

    Returns:
        HostListResponse with paginated host data
    """
    try:
        # Validate pagination parameters
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Page number must be >= 1"
            )

        if per_page < 1 or per_page > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Items per page must be between 1 and 1000",
            )

        # Validate status filter
        if status and status not in ["online", "offline"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status must be 'online' or 'offline'",
            )

        # Calculate offset
        offset = (page - 1) * per_page

        # Get filtered hosts
        if status:
            hosts = host_ops.get_hosts_by_status(status)
        else:
            hosts = host_ops.get_all_hosts()

        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            hosts = [host for host in hosts if search_lower in host.hostname.lower()]

        total_hosts = len(hosts)

        # Apply pagination
        paginated_hosts = hosts[offset : offset + per_page]

        # Convert to response models
        host_responses = [
            HostResponse(
                hostname=host.hostname,
                current_ip=host.current_ip,
                status=host.status,
                first_seen=host.first_seen,
                last_seen=host.last_seen,
            )
            for host in paginated_hosts
        ]

        # Calculate total pages
        total_pages = math.ceil(total_hosts / per_page) if total_hosts > 0 else 1

        logger.info(f"Retrieved {len(host_responses)} hosts (page {page}/{total_pages})")

        return HostListResponse(
            hosts=host_responses, total=total_hosts, page=page, per_page=per_page, pages=total_pages
        )

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving hosts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error retrieving hosts",
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving hosts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.get(
    "/hosts/{hostname}",
    response_model=HostResponse,
    summary="Get host by hostname",
    description="Get detailed information for a specific host",
)
async def get_host(
    hostname: str,
    current_user: User = Depends(get_current_verified_user),
    host_ops: HostOperations = Depends(get_host_operations),
) -> HostResponse:
    """
    Get detailed information for a specific host.

    Args:
        hostname: Host identifier
        host_ops: Host operations dependency

    Returns:
        HostResponse with host details
    """
    try:
        host = host_ops.get_host_by_hostname(hostname)

        if not host:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Host '{hostname}' not found"
            )

        logger.info(f"Retrieved host details for: {hostname}")

        return HostResponse(
            hostname=host.hostname,
            current_ip=host.current_ip,
            status=host.status,
            first_seen=host.first_seen,
            last_seen=host.last_seen,
        )

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving host {hostname}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error retrieving host",
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving host {hostname}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.get(
    "/hosts/status/{host_status}",
    response_model=HostListResponse,
    summary="Get hosts by status",
    description="Get paginated list of hosts filtered by status",
)
async def get_hosts_by_status(
    host_status: str,
    current_user: User = Depends(get_current_verified_user),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(50, ge=1, le=1000, description="Items per page"),
    host_ops: HostOperations = Depends(get_host_operations),
) -> HostListResponse:
    """
    Get hosts filtered by status with pagination.

    Args:
        host_status: Status to filter by (online/offline)
        page: Page number (1-based)
        per_page: Number of items per page
        host_ops: Host operations dependency

    Returns:
        HostListResponse with filtered host data
    """
    try:
        # Validate status
        if host_status not in ["online", "offline"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status must be 'online' or 'offline'",
            )

        # Validate pagination parameters
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Page number must be >= 1"
            )

        if per_page < 1 or per_page > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Items per page must be between 1 and 1000",
            )

        # Get hosts by status
        hosts = host_ops.get_hosts_by_status(host_status)
        total_hosts = len(hosts)

        # Apply pagination
        offset = (page - 1) * per_page
        paginated_hosts = hosts[offset : offset + per_page]

        # Convert to response models
        host_responses = [
            HostResponse(
                hostname=host.hostname,
                current_ip=host.current_ip,
                status=host.status,
                first_seen=host.first_seen,
                last_seen=host.last_seen,
            )
            for host in paginated_hosts
        ]

        # Calculate total pages
        total_pages = math.ceil(total_hosts / per_page) if total_hosts > 0 else 1

        logger.info(
            f"Retrieved {len(host_responses)} {host_status} hosts (page {page}/{total_pages})"
        )

        return HostListResponse(
            hosts=host_responses, total=total_hosts, page=page, per_page=per_page, pages=total_pages
        )

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving {host_status} hosts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error retrieving hosts",
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving {host_status} hosts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )
