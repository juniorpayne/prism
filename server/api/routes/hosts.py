#!/usr/bin/env python3
"""
Host API Routes (SCRUM-17)
REST endpoints for host data retrieval.
"""

import logging
import math
from datetime import datetime
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
    last_registration: Optional[datetime] = None
    
    
class SystemStatsResponse(BaseModel):
    """Response model for system-wide statistics (admin only)."""
    total_hosts: int
    users_with_hosts: int
    anonymous_hosts: int
    
    
class HostStatsWithSystemResponse(HostStatsResponse):
    """Extended host stats response with system stats for admins."""
    system_stats: Optional[SystemStatsResponse] = None


class HostResponseWithOwner(HostResponse):
    """Extended host response with owner information for admins."""
    owner: Optional[str] = None  # Owner user ID
    owner_username: Optional[str] = None  # Owner username (admin only)
    

class HostDetailResponse(HostResponse):
    """Detailed host response with additional fields."""
    id: int
    dns_zone: Optional[str] = None
    dns_sync_status: Optional[str] = None
    owner_id: Optional[str] = None
    owner_username: Optional[str] = None
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
    all: bool = Query(False, description="Show all hosts (admin only)"),
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

        # Get filtered hosts - filter by current user unless admin requesting all
        if all and current_user.is_admin:
            logger.info(f"Admin {current_user.username} viewing all hosts")
            # Admin sees all hosts
            if status:
                hosts = host_ops.get_hosts_by_status(status, user_id=None)
            else:
                hosts = host_ops.get_all_hosts(user_id=None)
        else:
            # Normal user or admin without all=true - filter by user_id
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
        if all and current_user.is_admin:
            # Include owner information for admin view
            host_responses = []
            for host in paginated_hosts:
                response_data = {
                    "id": host.id,
                    "hostname": host.hostname,
                    "current_ip": host.current_ip,
                    "status": host.status,
                    "first_seen": host.first_seen,
                    "last_seen": host.last_seen,
                    "owner": host.created_by  # Include owner ID
                }
                host_responses.append(HostResponseWithOwner(**response_data))
        else:
            # Regular response without owner info
            host_responses = [
                HostResponse(
                    id=host.id,
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
    "/hosts/{host_id}",
    response_model=HostDetailResponse,
    summary="Get host by ID",
    description="Get detailed information for a specific host",
)
async def get_host(
    host_id: int,
    current_user: User = Depends(get_current_verified_user),
    host_ops: HostOperations = Depends(get_host_operations),
    db_manager = Depends(get_database_manager),
) -> HostDetailResponse:
    """
    Get detailed information for a specific host.

    Args:
        host_id: Host identifier
        current_user: Current authenticated user
        host_ops: Host operations dependency

    Returns:
        HostDetailResponse with host details
    """
    try:
        # Get host from database
        with db_manager.get_session() as session:
            from sqlalchemy import select
            stmt = select(Host).where(Host.id == host_id)
            result = session.execute(stmt)
            host = result.scalar_one_or_none()

        if not host:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Host not found"
            )

        # Check ownership unless admin
        if not current_user.is_admin and host.created_by != str(current_user.id):
            # Don't reveal that the host exists
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Host not found"
            )

        logger.info(f"Retrieved host details for ID: {host_id}")
        
        # Get owner username if admin
        owner_username = None
        if current_user.is_admin and host.created_by:
            # Look up username
            with db_manager.get_session() as session:
                from sqlalchemy import select
                from server.auth.models import User
                stmt = select(User).where(User.id == host.created_by)
                result = session.execute(stmt)
                owner = result.scalar_one_or_none()
                if owner:
                    owner_username = owner.username

        return HostDetailResponse(
            id=host.id,
            hostname=host.hostname,
            current_ip=host.current_ip,
            status=host.status,
            first_seen=host.first_seen,
            last_seen=host.last_seen,
            dns_zone=getattr(host, 'dns_zone', None),
            dns_sync_status=getattr(host, 'dns_sync_status', None),
            owner_id=host.created_by,
            owner_username=owner_username if current_user.is_admin else None
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
                id=host.id,
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
    "/hosts/stats/summary",
    response_model=HostStatsWithSystemResponse,
    summary="Get host statistics summary",
    description="Get statistics for user's hosts with optional system stats for admins",
)
async def get_host_stats(
    current_user: User = Depends(get_current_verified_user),
    host_ops: HostOperations = Depends(get_host_operations),
    db_manager = Depends(get_database_manager),
) -> HostStatsWithSystemResponse:
    """
    Get statistics for user's hosts.
    
    Returns:
        HostStatsWithSystemResponse with user stats and system stats for admins
    """
    try:
        # Get user's hosts
        user_id = str(current_user.id)
        user_hosts = host_ops.get_all_hosts(user_id=user_id)
        
        online_count = sum(1 for h in user_hosts if h.status == "online")
        offline_count = sum(1 for h in user_hosts if h.status == "offline")
        
        # Get last registration time
        last_registration = None
        if user_hosts:
            last_registration = max(h.last_seen for h in user_hosts)
        
        response = HostStatsWithSystemResponse(
            total_hosts=len(user_hosts),
            online_hosts=online_count,
            offline_hosts=offline_count,
            last_registration=last_registration
        )
        
        # Add system-wide stats for admins
        if current_user.is_admin:
            with db_manager.get_session() as session:
                from sqlalchemy import select, func
                
                # Total system hosts
                total_system_hosts = session.query(Host).count()
                
                # Users with hosts
                users_with_hosts = session.query(Host.created_by).distinct().count()
                
                # Anonymous hosts (assuming system user ID is a specific value)
                # For now, count hosts without created_by
                anonymous_hosts = session.query(Host).filter(
                    (Host.created_by == None) | (Host.created_by == "")
                ).count()
                
                response.system_stats = SystemStatsResponse(
                    total_hosts=total_system_hosts,
                    users_with_hosts=users_with_hosts,
                    anonymous_hosts=anonymous_hosts
                )
        
        logger.info(f"Retrieved host stats for {current_user.username}")
        
        return response
        
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
