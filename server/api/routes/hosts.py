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
from pydantic import BaseModel


class HostStatsResponse(BaseModel):
    """Response model for host statistics."""
    total_hosts: int
    online_hosts: int
    offline_hosts: int
from server.auth.dependencies import get_admin_override, get_current_verified_user
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
    admin_override: bool = Depends(get_admin_override),
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

        # Get filtered hosts - filter by current user unless admin override
        if admin_override:
            logger.info(f"Admin {current_user.username} viewing all hosts")
            # Admin sees all hosts
            if status:
                hosts = host_ops.get_hosts_by_status(status, user_id=None)
            else:
                hosts = host_ops.get_all_hosts(user_id=None)
        else:
            # Normal user - filter by user_id
            user_id = str(current_user.id)
            if status:
                hosts = host_ops.get_hosts_by_status(status, user_id=user_id)
            else:
                hosts = host_ops.get_all_hosts(user_id=user_id)

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
        # Get host only if owned by current user
        user_id = str(current_user.id)
        host = host_ops.get_host_by_hostname(hostname, user_id=user_id)

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

        # Get hosts by status - filter by current user
        user_id = str(current_user.id)
        hosts = host_ops.get_hosts_by_status(host_status, user_id=user_id)
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


@router.get(
    "/hosts/stats",
    response_model=HostStatsResponse,
    summary="Get host statistics",
    description="Get statistics for user's hosts",
)
async def get_host_stats(
    current_user: User = Depends(get_current_verified_user),
    admin_override: bool = Depends(get_admin_override),
    host_ops: HostOperations = Depends(get_host_operations),
) -> HostStatsResponse:
    """
    Get statistics for user's hosts only.
    
    Returns:
        HostStatsResponse with counts for total, online, and offline hosts
    """
    try:
        if admin_override:
            logger.info(f"Admin {current_user.username} viewing all host stats")
            # Admin sees all host stats
            total_hosts = host_ops.get_host_count(user_id=None)
            online_hosts = host_ops.get_host_count_by_status("online", user_id=None)
            offline_hosts = host_ops.get_host_count_by_status("offline", user_id=None)
        else:
            # Normal user - filter by user_id
            user_id = str(current_user.id)
            total_hosts = host_ops.get_host_count(user_id=user_id)
            online_hosts = host_ops.get_host_count_by_status("online", user_id=user_id)
            offline_hosts = host_ops.get_host_count_by_status("offline", user_id=user_id)
        
        logger.info(f"Retrieved host stats for {current_user.username}: total={total_hosts}, online={online_hosts}, offline={offline_hosts}")
        
        return HostStatsResponse(
            total_hosts=total_hosts,
            online_hosts=online_hosts,
            offline_hosts=offline_hosts
        )
        
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving host stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error retrieving host statistics",
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving host stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )
