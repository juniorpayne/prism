#!/usr/bin/env python3
"""
Pydantic Models for API Responses (SCRUM-17)
Data models for REST API endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class HostResponse(BaseModel):
    """Response model for individual host data."""

    model_config = ConfigDict(
        from_attributes=True, json_encoders={datetime: lambda v: v.isoformat() + "Z" if v else None}
    )

    id: int = Field(..., description="Host ID")
    hostname: str = Field(..., description="Host identifier")
    current_ip: str = Field(..., description="Current IP address")
    status: str = Field(..., description="Host status (online/offline)")
    first_seen: datetime = Field(..., description="First registration timestamp")
    last_seen: datetime = Field(..., description="Last seen timestamp")


class HostListResponse(BaseModel):
    """Response model for paginated host list."""

    hosts: List[HostResponse] = Field(..., description="List of hosts")
    total: int = Field(..., description="Total number of hosts")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = Field(..., description="Server status")
    uptime: float = Field(..., description="Server uptime in seconds")
    total_hosts: int = Field(..., description="Total number of registered hosts")
    online_hosts: int = Field(..., description="Number of online hosts")
    offline_hosts: int = Field(..., description="Number of offline hosts")
    database_status: str = Field(..., description="Database connection status")
    version: str = Field(default="1.0", description="API version")


class StatisticsResponse(BaseModel):
    """Response model for server statistics."""

    host_statistics: Dict[str, Any] = Field(..., description="Host-related statistics")
    server_statistics: Dict[str, Any] = Field(..., description="Server performance statistics")
    database_statistics: Dict[str, Any] = Field(..., description="Database statistics")
    uptime_info: Dict[str, Any] = Field(..., description="Server uptime information")


class ErrorResponse(BaseModel):
    """Response model for API errors."""

    detail: str = Field(..., description="Error description")
    error_type: Optional[str] = Field(None, description="Type of error")
    error_code: Optional[str] = Field(None, description="Internal error code")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class PaginationParams(BaseModel):
    """Model for pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    per_page: int = Field(default=50, ge=1, le=1000, description="Items per page")


class HostFilterParams(BaseModel):
    """Model for host filtering parameters."""

    status: Optional[str] = Field(None, description="Filter by host status")
    search: Optional[str] = Field(None, description="Search in hostname")
    ip: Optional[str] = Field(None, description="Filter by IP address")


def create_error_response(
    detail: str, error_type: Optional[str] = None, error_code: Optional[str] = None
) -> ErrorResponse:
    """
    Create standardized error response.

    Args:
        detail: Error description
        error_type: Type of error
        error_code: Internal error code

    Returns:
        ErrorResponse instance
    """
    return ErrorResponse(detail=detail, error_type=error_type, error_code=error_code)
