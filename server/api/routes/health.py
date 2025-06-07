#!/usr/bin/env python3
"""
Health and Statistics API Routes (SCRUM-17)
REST endpoints for server health and statistics.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from server.api.dependencies import get_database_manager, get_host_operations
from server.api.models import HealthResponse, StatisticsResponse
from server.database.connection import DatabaseManager
from server.database.operations import HostOperations

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["health"])

# Store server start time for uptime calculation
_server_start_time = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Server health check",
    description="Get server health status and basic statistics",
)
async def get_health(host_ops: HostOperations = Depends(get_host_operations)) -> HealthResponse:
    """
    Get server health status and basic host statistics.

    Args:
        host_ops: Host operations dependency

    Returns:
        HealthResponse with server health information
    """
    try:
        # Calculate uptime
        uptime = time.time() - _server_start_time

        # Get host statistics
        stats = host_ops.get_host_statistics()

        # Test database connectivity
        database_status = "healthy"
        try:
            # Simple database health check
            total_hosts = stats.get("total_hosts", 0)
            if total_hosts >= 0:  # If we can get a count, DB is working
                database_status = "healthy"
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            database_status = "unhealthy"

        logger.debug(
            f"Health check completed - uptime: {uptime:.1f}s, hosts: {stats.get('total_hosts', 0)}"
        )

        return HealthResponse(
            status="healthy",
            uptime=uptime,
            total_hosts=stats.get("total_hosts", 0),
            online_hosts=stats.get("online_hosts", 0),
            offline_hosts=stats.get("offline_hosts", 0),
            database_status=database_status,
            version="1.0",
        )

    except SQLAlchemyError as e:
        logger.error(f"Database error in health check: {e}")
        # Return partial health info even if database is down
        uptime = time.time() - _server_start_time
        return HealthResponse(
            status="degraded",
            uptime=uptime,
            total_hosts=0,
            online_hosts=0,
            offline_hosts=0,
            database_status="unhealthy",
            version="1.0",
        )
    except Exception as e:
        logger.error(f"Unexpected error in health check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Health check failed"
        )


@router.get(
    "/stats",
    response_model=StatisticsResponse,
    summary="Server statistics",
    description="Get detailed server and host statistics",
)
async def get_statistics(
    host_ops: HostOperations = Depends(get_host_operations),
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> StatisticsResponse:
    """
    Get detailed server and host statistics.

    Args:
        host_ops: Host operations dependency
        db_manager: Database manager dependency

    Returns:
        StatisticsResponse with detailed statistics
    """
    try:
        # Get host statistics
        host_statistics = host_ops.get_host_statistics()

        # Calculate uptime info
        uptime_seconds = time.time() - _server_start_time
        uptime_info = {
            "uptime_seconds": uptime_seconds,
            "uptime_minutes": uptime_seconds / 60,
            "uptime_hours": uptime_seconds / 3600,
            "uptime_days": uptime_seconds / 86400,
            "server_start_time": datetime.fromtimestamp(
                _server_start_time, tz=timezone.utc
            ).isoformat(),
            "current_time": datetime.now(timezone.utc).isoformat(),
        }

        # Server performance statistics
        server_statistics = {
            "uptime_seconds": uptime_seconds,
            "api_version": "1.0",
            "python_version": f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}.{__import__('sys').version_info.micro}",
            "fastapi_version": __import__("fastapi").__version__,
            "memory_usage": _get_memory_usage(),
        }

        # Database statistics
        database_statistics = {
            "database_type": "SQLite",
            "connection_pool_size": (
                db_manager.pool_size if hasattr(db_manager, "pool_size") else "N/A"
            ),
            "database_file_size": _get_database_file_size(db_manager),
            "schema_version": "1.0",
        }

        logger.info("Statistics retrieved successfully")

        return StatisticsResponse(
            host_statistics=host_statistics,
            server_statistics=server_statistics,
            database_statistics=database_statistics,
            uptime_info=uptime_info,
        )

    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error retrieving statistics",
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


def _get_memory_usage() -> Dict[str, Any]:
    """
    Get memory usage information.

    Returns:
        Dictionary with memory usage stats
    """
    try:
        import psutil

        process = psutil.Process()
        memory_info = process.memory_info()

        return {
            "rss_bytes": memory_info.rss,
            "vms_bytes": memory_info.vms,
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "memory_percent": process.memory_percent(),
        }
    except ImportError:
        # psutil not available, use basic info
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        return {
            "max_rss_kb": usage.ru_maxrss,
            "user_time": usage.ru_utime,
            "system_time": usage.ru_stime,
        }
    except Exception as e:
        logger.warning(f"Could not get memory usage: {e}")
        return {"error": "Memory usage unavailable"}


def _get_database_file_size(db_manager: DatabaseManager) -> Dict[str, Any]:
    """
    Get database file size information.

    Args:
        db_manager: Database manager instance

    Returns:
        Dictionary with database file size info
    """
    try:
        import os

        # Extract database path from connection string
        db_path = None
        if hasattr(db_manager, "connection_string"):
            if "sqlite:///" in db_manager.connection_string:
                db_path = db_manager.connection_string.replace("sqlite:///", "")

        if db_path and os.path.exists(db_path):
            size_bytes = os.path.getsize(db_path)
            return {
                "size_bytes": size_bytes,
                "size_kb": size_bytes / 1024,
                "size_mb": size_bytes / 1024 / 1024,
                "file_path": db_path,
            }
        else:
            return {"error": "Database file path not found"}

    except Exception as e:
        logger.warning(f"Could not get database file size: {e}")
        return {"error": "Database file size unavailable"}


def reset_server_start_time() -> None:
    """Reset server start time (for testing purposes)."""
    global _server_start_time
    _server_start_time = time.time()


def get_server_start_time() -> float:
    """Get server start time timestamp."""
    return _server_start_time
