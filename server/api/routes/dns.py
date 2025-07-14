#!/usr/bin/env python3
"""
DNS API Routes (SCRUM-116)
PowerDNS API integration endpoints for DNS zone and record management.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

from server.api.dependencies import get_app_config
from server.auth.dependencies import get_current_verified_user
from server.auth.models import User
from server.dns_manager import (
    PowerDNSAPIError,
    PowerDNSClient,
    PowerDNSConnectionError,
    PowerDNSError,
)
from server.monitoring import get_metrics_collector

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

# Create router
router = APIRouter(prefix="/dns", tags=["DNS Management"])


def get_powerdns_client() -> PowerDNSClient:
    """
    Get PowerDNS client instance.

    Returns:
        PowerDNSClient instance
    """
    config = get_app_config()
    return PowerDNSClient(config)


@router.get("/zones", response_model=Dict[str, Any])
@limiter.limit("100/minute")
async def list_zones(
    request: Request,
    current_user: User = Depends(get_current_verified_user),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=500, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for zone names"),
    sort: str = Query("name", description="Sort field (name, type, serial)"),
    order: str = Query("asc", description="Sort order (asc, desc)"),
):
    """
    List DNS zones with pagination and search.

    This endpoint provides a simple proxy to PowerDNS API for listing zones.
    Following KISS principles - minimal transformation, direct proxy.
    """
    metrics = get_metrics_collector()

    try:
        async with get_powerdns_client() as dns_client:
            # Get all zones from PowerDNS
            zones_response = await dns_client.list_zones()

            # Simple filtering and pagination
            zones = zones_response if isinstance(zones_response, list) else []

            # Search filter
            if search:
                search_lower = search.lower()
                zones = [z for z in zones if search_lower in z.get("name", "").lower()]

            # Sort zones
            reverse = order.lower() == "desc"
            if sort == "name":
                zones.sort(key=lambda x: x.get("name", ""), reverse=reverse)
            elif sort == "type":
                zones.sort(key=lambda x: x.get("kind", ""), reverse=reverse)
            elif sort == "serial":
                zones.sort(key=lambda x: x.get("serial", 0), reverse=reverse)

            # Pagination
            total = len(zones)
            start = (page - 1) * limit
            end = start + limit
            paginated_zones = zones[start:end]

            # Add zone statistics
            for zone in paginated_zones:
                zone["record_count"] = len(zone.get("rrsets", []))
                zone["status"] = "Active"  # PowerDNS doesn't have status

            metrics.record_dns_operation("list_zones", "success")

            return {
                "zones": paginated_zones,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": (total + limit - 1) // limit,
                },
            }

    except PowerDNSConnectionError as e:
        logger.error(f"PowerDNS connection error: {e}")
        metrics.record_dns_operation("list_zones", "error")
        raise HTTPException(status_code=503, detail="DNS service unavailable")

    except PowerDNSAPIError as e:
        logger.error(f"PowerDNS API error: {e}")
        metrics.record_dns_operation("list_zones", "error")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))

    except Exception as e:
        logger.error(f"Unexpected error listing zones: {e}")
        metrics.record_dns_operation("list_zones", "error")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/zones/{zone_id}", response_model=Dict[str, Any])
@limiter.limit("200/minute")
async def get_zone(
    request: Request,
    zone_id: str,
    current_user: User = Depends(get_current_verified_user),
):
    """
    Get specific DNS zone details.

    Direct proxy to PowerDNS API - minimal transformation.
    """
    metrics = get_metrics_collector()

    try:
        async with get_powerdns_client() as dns_client:
            # Get zone from PowerDNS
            zone_response = await dns_client.get_zone_details(zone_id)

            if not zone_response:
                raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")

            # Add computed fields (to match list_zones behavior)
            zone_response["record_count"] = len(zone_response.get("rrsets", []))
            zone_response["status"] = "Active"  # PowerDNS doesn't have status

            metrics.record_dns_operation("get_zone", "success")
            return zone_response

    except HTTPException:
        raise
    except PowerDNSConnectionError as e:
        logger.error(f"PowerDNS connection error: {e}")
        metrics.record_dns_operation("get_zone", "error")
        raise HTTPException(status_code=503, detail="DNS service unavailable")

    except PowerDNSAPIError as e:
        logger.error(f"PowerDNS API error: {e}")
        metrics.record_dns_operation("get_zone", "error")
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))

    except Exception as e:
        logger.error(f"Unexpected error getting zone {zone_id}: {e}")
        metrics.record_dns_operation("get_zone", "error")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health", response_model=Dict[str, Any])
async def dns_health():
    """
    Check DNS service health.

    Simple health check for PowerDNS connectivity.
    """
    try:
        async with get_powerdns_client() as dns_client:
            # Simple ping to PowerDNS
            await dns_client._make_request("GET", "servers/localhost")
            return {"status": "healthy", "powerdns": "connected"}

    except Exception as e:
        logger.error(f"DNS health check failed: {e}")
        return {"status": "unhealthy", "powerdns": "disconnected", "error": str(e)}


@router.post("/zones", response_model=Dict[str, Any])
@limiter.limit("50/minute")
async def create_zone(
    request: Request,
    zone_data: Dict[str, Any],
    current_user: User = Depends(get_current_verified_user),
):
    """
    Create a new DNS zone.

    Required fields:
    - name: Zone name (must end with dot)
    - kind: Zone type (Native, Master, Slave)
    - nameservers: List of nameservers
    """
    metrics = get_metrics_collector()

    try:
        async with get_powerdns_client() as dns_client:
            # Validate zone name
            zone_name = zone_data.get("name", "")
            is_valid, error_msg = dns_client.validate_zone_name(zone_name)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_msg)

            # Check if zone already exists
            existing_zone = await dns_client.get_zone_details(zone_name)
            if existing_zone:
                raise HTTPException(status_code=409, detail=f"Zone '{zone_name}' already exists")

            # Create the zone
            result = await dns_client.create_zone(
                zone=zone_name,
                kind=zone_data.get("kind", "Native"),
                nameservers=zone_data.get("nameservers", []),
                masters=zone_data.get("masters", []),
                soa_edit=zone_data.get("soa_edit"),
                soa_edit_api=zone_data.get("soa_edit_api", "DEFAULT"),
                api_rectify=zone_data.get("api_rectify", True),
                account=zone_data.get("account", ""),
                dnssec=zone_data.get("dnssec", False),
            )

            metrics.record_dns_operation("create_zone", "success")
            return result

    except HTTPException:
        raise
    except PowerDNSConnectionError as e:
        logger.error(f"PowerDNS connection error: {e}")
        metrics.record_dns_operation("create_zone", "error")
        raise HTTPException(status_code=503, detail="DNS service unavailable")
    except PowerDNSAPIError as e:
        logger.error(f"PowerDNS API error: {e}")
        metrics.record_dns_operation("create_zone", "error")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating zone: {e}")
        metrics.record_dns_operation("create_zone", "error")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/zones/{zone_id}", response_model=Dict[str, Any])
@limiter.limit("50/minute")
async def update_zone(
    request: Request,
    zone_id: str,
    zone_data: Dict[str, Any],
    current_user: User = Depends(get_current_verified_user),
):
    """
    Update an existing DNS zone.

    Updates zone configuration like kind, masters, SOA settings, etc.
    To update records, use the record endpoints.
    """
    metrics = get_metrics_collector()

    try:
        async with get_powerdns_client() as dns_client:
            # Check if zone exists
            existing_zone = await dns_client.get_zone_details(zone_id)
            if not existing_zone:
                raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")

            # Update the zone
            result = await dns_client.update_zone(zone_id, zone_data)

            metrics.record_dns_operation("update_zone", "success")
            return result

    except HTTPException:
        raise
    except PowerDNSConnectionError as e:
        logger.error(f"PowerDNS connection error: {e}")
        metrics.record_dns_operation("update_zone", "error")
        raise HTTPException(status_code=503, detail="DNS service unavailable")
    except PowerDNSAPIError as e:
        logger.error(f"PowerDNS API error: {e}")
        metrics.record_dns_operation("update_zone", "error")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error updating zone {zone_id}: {e}")
        metrics.record_dns_operation("update_zone", "error")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/zones/{zone_id}", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def delete_zone(
    request: Request,
    zone_id: str,
    current_user: User = Depends(get_current_verified_user),
):
    """
    Delete a DNS zone.

    This will permanently delete the zone and all its records.
    This operation cannot be undone.
    """
    metrics = get_metrics_collector()

    try:
        async with get_powerdns_client() as dns_client:
            # Check if zone exists
            existing_zone = await dns_client.get_zone_details(zone_id)
            if not existing_zone:
                raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")

            # Delete the zone
            result = await dns_client.delete_zone(zone_id)

            metrics.record_dns_operation("delete_zone", "success")
            return result

    except HTTPException:
        raise
    except PowerDNSConnectionError as e:
        logger.error(f"PowerDNS connection error: {e}")
        metrics.record_dns_operation("delete_zone", "error")
        raise HTTPException(status_code=503, detail="DNS service unavailable")
    except PowerDNSAPIError as e:
        logger.error(f"PowerDNS API error: {e}")
        metrics.record_dns_operation("delete_zone", "error")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error deleting zone {zone_id}: {e}")
        metrics.record_dns_operation("delete_zone", "error")
        raise HTTPException(status_code=500, detail="Internal server error")
