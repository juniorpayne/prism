#!/usr/bin/env python3
"""
DNS API Routes (SCRUM-116)
PowerDNS API integration endpoints for DNS zone and record management.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

from server.api.dependencies import get_app_config
from server.auth.dependencies import get_admin_override, get_current_verified_user
from server.auth.models import User
from server.database.connection import DatabaseManager
from server.database.dns_operations import DNSZoneOwnershipOperations
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


def get_dns_zone_ops() -> DNSZoneOwnershipOperations:
    """
    Get DNS zone operations instance.
    
    Returns:
        DNSZoneOwnershipOperations instance
    """
    config = get_app_config()
    db_manager = DatabaseManager(config)
    return DNSZoneOwnershipOperations(db_manager)


def filter_zones_by_user(zones: List[Dict[str, Any]], user_zones: List[str]) -> List[Dict[str, Any]]:
    """
    Filter zones to only those owned by user.
    
    Args:
        zones: All zones from PowerDNS
        user_zones: Zone names owned by user
        
    Returns:
        Filtered list of zones
    """
    # Convert user_zones to a set for O(1) lookup
    user_zones_set = set(user_zones)
    
    # Filter zones
    filtered = []
    for zone in zones:
        zone_name = zone.get("name", "")
        if zone_name in user_zones_set:
            filtered.append(zone)
    
    return filtered


@router.get("/zones", response_model=Dict[str, Any])
@limiter.limit("100/minute")
async def list_zones(
    request: Request,
    current_user: User = Depends(get_current_verified_user),
    admin_override: bool = Depends(get_admin_override),
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
            
            # Filter zones by user ownership unless admin override
            if admin_override:
                logger.info(f"Admin {current_user.username} viewing all {len(zones)} zones")
                # Admin sees all zones - no filtering
            else:
                # Normal user - filter by ownership
                dns_zone_ops = get_dns_zone_ops()
                user_zones = dns_zone_ops.get_user_zones(str(current_user.id))
                zones = filter_zones_by_user(zones, user_zones)

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


@router.get("/zones/search", response_model=Dict[str, Any])
@limiter.limit("100/minute")
async def search_zones(
    request: Request,
    current_user: User = Depends(get_current_verified_user),
    q: str = Query(..., description="Search query", min_length=1),
    zone_type: Optional[str] = Query(
        None, description="Filter by zone type (Native, Master, Slave)"
    ),
    hierarchy_level: Optional[int] = Query(None, ge=0, description="Filter by hierarchy level"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
):
    """
    Search for DNS zones by name pattern.

    Supports:
    - Substring matching in zone names
    - Wildcard patterns (e.g., *.example.com.)
    - Filtering by zone type and hierarchy level
    """
    metrics = get_metrics_collector()

    try:
        async with get_powerdns_client() as dns_client:
            results = await dns_client.search_zones(
                query=q, zone_type=zone_type, hierarchy_level=hierarchy_level, limit=limit
            )
            
            # Filter search results by user ownership
            dns_zone_ops = get_dns_zone_ops()
            user_zones = dns_zone_ops.get_user_zones(str(current_user.id))
            results = filter_zones_by_user(results, user_zones)

            metrics.record_dns_operation("search_zones", "success")

            return {
                "query": q,
                "total": len(results),
                "zones": results,
                "filters": {"zone_type": zone_type, "hierarchy_level": hierarchy_level},
            }

    except PowerDNSError as e:
        logger.error(f"PowerDNS error searching zones: {e}")
        metrics.record_dns_operation("search_zones", "error")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error searching zones: {e}")
        metrics.record_dns_operation("search_zones", "error")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/zones/filter", response_model=Dict[str, Any])
@limiter.limit("50/minute")
async def filter_zones(
    request: Request,
    current_user: User = Depends(get_current_verified_user),
    filters: Dict[str, Any] = {},
    sort_by: str = Query("name", description="Sort field (name, records, serial)"),
    sort_order: str = Query("asc", description="Sort order (asc, desc)"),
):
    """
    Filter zones based on multiple criteria.

    Filter options in request body:
    - min_records: Minimum number of records
    - max_records: Maximum number of records
    - has_dnssec: Filter by DNSSEC status (true/false)
    - parent_zone: Filter by parent zone name
    - serial_after: Filter by serial number (zones modified after)

    Example:
    {
        "min_records": 5,
        "max_records": 100,
        "has_dnssec": true,
        "parent_zone": "example.com."
    }
    """
    metrics = get_metrics_collector()

    try:
        async with get_powerdns_client() as dns_client:
            results = await dns_client.filter_zones(
                filters=filters, sort_by=sort_by, sort_order=sort_order
            )
            
            # Filter results by user ownership
            dns_zone_ops = get_dns_zone_ops()
            user_zones = dns_zone_ops.get_user_zones(str(current_user.id))
            results = filter_zones_by_user(results, user_zones)

            metrics.record_dns_operation("filter_zones", "success")

            return {
                "total": len(results),
                "zones": results,
                "filters": filters,
                "sort": {"by": sort_by, "order": sort_order},
            }

    except PowerDNSError as e:
        logger.error(f"PowerDNS error filtering zones: {e}")
        metrics.record_dns_operation("filter_zones", "error")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error filtering zones: {e}")
        metrics.record_dns_operation("filter_zones", "error")
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
        # Check if user owns this zone
        dns_zone_ops = get_dns_zone_ops()
        if not dns_zone_ops.check_zone_ownership(zone_id, str(current_user.id)):
            raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")
        
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
            
            # Create ownership record for the new zone
            dns_zone_ops = get_dns_zone_ops()
            dns_zone_ops.create_zone_ownership(zone_name, str(current_user.id))

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
        # Check if user owns this zone
        dns_zone_ops = get_dns_zone_ops()
        if not dns_zone_ops.check_zone_ownership(zone_id, str(current_user.id)):
            raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")
            
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
        # Check if user owns this zone
        dns_zone_ops = get_dns_zone_ops()
        if not dns_zone_ops.check_zone_ownership(zone_id, str(current_user.id)):
            raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")
            
        async with get_powerdns_client() as dns_client:
            # Check if zone exists
            existing_zone = await dns_client.get_zone_details(zone_id)
            if not existing_zone:
                raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")

            # Delete the zone
            result = await dns_client.delete_zone(zone_id)
            
            # Delete the ownership record
            dns_zone_ops.delete_zone_ownership(zone_id)

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


@router.get("/zones/{zone_id}/records", response_model=Dict[str, Any])
@limiter.limit("100/minute")
async def list_zone_records(
    request: Request,
    zone_id: str,
    current_user: User = Depends(get_current_verified_user),
    record_type: Optional[str] = Query(
        None, description="Filter by record type (A, AAAA, CNAME, etc.)"
    ),
    name: Optional[str] = Query(None, description="Filter by record name"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=500, description="Items per page"),
):
    """
    List all records in a DNS zone.

    Returns all RRSets in the zone with optional filtering.
    """
    metrics = get_metrics_collector()

    try:
        # Check if user owns this zone
        dns_zone_ops = get_dns_zone_ops()
        if not dns_zone_ops.check_zone_ownership(zone_id, str(current_user.id)):
            raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")
            
        async with get_powerdns_client() as dns_client:
            # Get all records from zone
            records = await dns_client.list_records(zone_id)

            # Filter by type if specified
            if record_type:
                records = [r for r in records if r.get("type") == record_type.upper()]

            # Filter by name if specified
            if name:
                # Ensure name is FQDN for comparison
                search_name = name if name.endswith(".") else f"{name}."
                records = [r for r in records if r.get("name", "").lower() == search_name.lower()]

            # Pagination
            total = len(records)
            start = (page - 1) * limit
            end = start + limit
            paginated_records = records[start:end]

            metrics.record_dns_operation("list_records", "success")

            return {
                "records": paginated_records,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": (total + limit - 1) // limit,
                },
            }

    except PowerDNSError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")
        logger.error(f"PowerDNS error listing records: {e}")
        metrics.record_dns_operation("list_records", "error")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error listing records for zone {zone_id}: {e}")
        metrics.record_dns_operation("list_records", "error")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/zones/{zone_id}/records/{name}/{record_type}", response_model=Dict[str, Any])
@limiter.limit("200/minute")
async def get_record_set(
    request: Request,
    zone_id: str,
    name: str,
    record_type: str,
    current_user: User = Depends(get_current_verified_user),
):
    """
    Get a specific record set.

    Returns the RRSet for the specified name and type.
    """
    metrics = get_metrics_collector()

    try:
        async with get_powerdns_client() as dns_client:
            # Get the record set
            record_set = await dns_client.get_record_set(zone_id, name, record_type.upper())

            if not record_set:
                raise HTTPException(
                    status_code=404,
                    detail=f"Record {name}/{record_type} not found in zone '{zone_id}'",
                )

            metrics.record_dns_operation("get_record", "success")
            return record_set

    except HTTPException:
        raise
    except PowerDNSError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")
        logger.error(f"PowerDNS error getting record: {e}")
        metrics.record_dns_operation("get_record", "error")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting record {name}/{record_type} in zone {zone_id}: {e}")
        metrics.record_dns_operation("get_record", "error")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/zones/{zone_id}/records", response_model=Dict[str, Any])
@limiter.limit("50/minute")
async def create_record(
    request: Request,
    zone_id: str,
    record_data: Dict[str, Any],
    current_user: User = Depends(get_current_verified_user),
):
    """
    Create a new record in a DNS zone.

    Required fields:
    - name: Record name (can be relative to zone or FQDN)
    - type: Record type (A, AAAA, CNAME, MX, TXT, etc.)
    - records: List of record data objects with 'content' field
    - ttl: Time to live (optional, defaults to 300)

    Example:
    {
        "name": "www",
        "type": "A",
        "ttl": 3600,
        "records": [
            {"content": "192.168.1.1"},
            {"content": "192.168.1.2"}
        ]
    }
    """
    metrics = get_metrics_collector()

    try:
        # Check if user owns this zone
        dns_zone_ops = get_dns_zone_ops()
        if not dns_zone_ops.check_zone_ownership(zone_id, str(current_user.id)):
            raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")
            
        async with get_powerdns_client() as dns_client:
            # Extract fields
            name = record_data.get("name", "")
            record_type = record_data.get("type", "").upper()
            records = record_data.get("records", [])
            ttl = record_data.get("ttl", 300)

            # Validate required fields
            if not name:
                raise HTTPException(status_code=400, detail="Record name is required")
            if not record_type:
                raise HTTPException(status_code=400, detail="Record type is required")
            if not records:
                raise HTTPException(status_code=400, detail="At least one record is required")

            # Convert relative name to FQDN if needed
            if not name.endswith("."):
                name = f"{name}.{zone_id}"

            # Create the record
            result = await dns_client.create_or_update_record(
                zone_name=zone_id, name=name, record_type=record_type, records=records, ttl=ttl
            )

            metrics.record_dns_operation("create_record", "success")
            return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PowerDNSError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")
        logger.error(f"PowerDNS error creating record: {e}")
        metrics.record_dns_operation("create_record", "error")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating record in zone {zone_id}: {e}")
        metrics.record_dns_operation("create_record", "error")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/zones/{zone_id}/records/{name}/{record_type}", response_model=Dict[str, Any])
@limiter.limit("50/minute")
async def update_record(
    request: Request,
    zone_id: str,
    name: str,
    record_type: str,
    record_data: Dict[str, Any],
    current_user: User = Depends(get_current_verified_user),
):
    """
    Update an existing record set.

    This replaces all records for the specified name/type combination.

    Required fields:
    - records: List of record data objects with 'content' field
    - ttl: Time to live (optional, defaults to 300)
    """
    metrics = get_metrics_collector()

    try:
        # Check if user owns this zone
        dns_zone_ops = get_dns_zone_ops()
        if not dns_zone_ops.check_zone_ownership(zone_id, str(current_user.id)):
            raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")
            
        async with get_powerdns_client() as dns_client:
            # Extract fields
            records = record_data.get("records", [])
            ttl = record_data.get("ttl", 300)

            # Validate required fields
            if not records:
                raise HTTPException(status_code=400, detail="At least one record is required")

            # Ensure name is FQDN
            if not name.endswith("."):
                name = f"{name}.{zone_id}"

            # Update the record
            result = await dns_client.create_or_update_record(
                zone_name=zone_id,
                name=name,
                record_type=record_type.upper(),
                records=records,
                ttl=ttl,
            )

            metrics.record_dns_operation("update_record", "success")
            return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PowerDNSError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")
        logger.error(f"PowerDNS error updating record: {e}")
        metrics.record_dns_operation("update_record", "error")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(
            f"Unexpected error updating record {name}/{record_type} in zone {zone_id}: {e}"
        )
        metrics.record_dns_operation("update_record", "error")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/zones/{zone_id}/records/{name}/{record_type}", response_model=Dict[str, Any])
@limiter.limit("50/minute")
async def delete_record(
    request: Request,
    zone_id: str,
    name: str,
    record_type: str,
    current_user: User = Depends(get_current_verified_user),
):
    """
    Delete a record set.

    This removes all records for the specified name/type combination.
    """
    metrics = get_metrics_collector()

    try:
        # Check if user owns this zone
        dns_zone_ops = get_dns_zone_ops()
        if not dns_zone_ops.check_zone_ownership(zone_id, str(current_user.id)):
            raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")
            
        async with get_powerdns_client() as dns_client:
            # Ensure name is FQDN
            if not name.endswith("."):
                name = f"{name}.{zone_id}"

            # Delete the record
            result = await dns_client.delete_record_set(
                zone_name=zone_id, name=name, record_type=record_type.upper()
            )

            metrics.record_dns_operation("delete_record", "success")
            return result

    except PowerDNSError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")
        logger.error(f"PowerDNS error deleting record: {e}")
        metrics.record_dns_operation("delete_record", "error")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(
            f"Unexpected error deleting record {name}/{record_type} in zone {zone_id}: {e}"
        )
        metrics.record_dns_operation("delete_record", "error")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/records/search", response_model=Dict[str, Any])
@limiter.limit("100/minute")
async def search_records(
    request: Request,
    current_user: User = Depends(get_current_verified_user),
    q: str = Query(..., description="Search query", min_length=1),
    record_type: Optional[str] = Query(
        None, description="Filter by record type (A, AAAA, CNAME, etc.)"
    ),
    zone: Optional[str] = Query(None, description="Limit search to specific zone"),
    content: bool = Query(False, description="Search in record content instead of names"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
):
    """
    Search for DNS records across user's zones only.

    Supports:
    - Search in record names or content
    - Filter by record type
    - Limit to specific zone
    - Returns records with zone information
    - Only searches within zones owned by the current user
    """
    metrics = get_metrics_collector()

    try:
        # Get user's zones first
        dns_zone_ops = get_dns_zone_ops()
        user_zones = dns_zone_ops.get_user_zones(str(current_user.id))
        
        # If searching in a specific zone, verify ownership
        if zone:
            if zone not in user_zones and not zone.endswith("."):
                # Try with trailing dot
                zone_fqdn = f"{zone}."
                if zone_fqdn not in user_zones:
                    raise HTTPException(status_code=404, detail=f"Zone '{zone}' not found")
        
        async with get_powerdns_client() as dns_client:
            # Get all zones to search
            all_zones = await dns_client.list_zones()
            filtered_zones = filter_zones_by_user(all_zones, user_zones)
            
            # Search records only in user's zones
            all_records = []
            zones_searched = 0
            
            for zone_info in filtered_zones:
                zone_name = zone_info["name"]
                
                # Skip if searching specific zone and this isn't it
                if zone and zone_name != zone and zone_name != f"{zone}.":
                    continue
                    
                try:
                    # Get records from this zone
                    zone_records = await dns_client.list_records(zone_name)
                    
                    # Filter by search query
                    for record in zone_records:
                        if content:
                            # Search in content
                            if q.lower() in record.get("content", "").lower():
                                if not record_type or record.get("type") == record_type.upper():
                                    all_records.append({
                                        **record,
                                        "zone": zone_name
                                    })
                        else:
                            # Search in name
                            if q.lower() in record.get("name", "").lower():
                                if not record_type or record.get("type") == record_type.upper():
                                    all_records.append({
                                        **record,
                                        "zone": zone_name
                                    })
                    
                    zones_searched += 1
                    
                    # Stop if we've hit the limit
                    if len(all_records) >= limit:
                        break
                        
                except Exception as e:
                    logger.warning(f"Error searching zone {zone_name}: {e}")

            # Limit results
            all_records = all_records[:limit]
            
            metrics.record_dns_operation("search_records", "success")

            return {
                "query": q,
                "total": len(all_records),
                "records": all_records,
                "zones_searched": zones_searched,
                "filters": {"record_type": record_type, "zone": zone, "content_search": content},
            }

    except PowerDNSError as e:
        logger.error(f"PowerDNS error searching records: {e}")
        metrics.record_dns_operation("search_records", "error")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error searching records: {e}")
        metrics.record_dns_operation("search_records", "error")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/records/export", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def export_records(
    request: Request,
    current_user: User = Depends(get_current_verified_user),
    format: str = Query("json", regex="^(json|csv|bind)$", description="Export format"),
):
    """
    Export records from user's zones only.
    
    Supports export formats:
    - json: Structured JSON format
    - csv: Comma-separated values
    - bind: BIND zone file format
    """
    metrics = get_metrics_collector()
    
    try:
        # Get user's zones
        dns_zone_ops = get_dns_zone_ops()
        user_zones = dns_zone_ops.get_user_zones(str(current_user.id))
        
        async with get_powerdns_client() as dns_client:
            # Get all zones and filter by user
            all_zones = await dns_client.list_zones()
            filtered_zones = filter_zones_by_user(all_zones, user_zones)
            
            # Collect all records from user's zones
            export_data = {
                "zones": [],
                "exported_at": datetime.utcnow().isoformat(),
                "user": current_user.username
            }
            
            for zone_info in filtered_zones:
                zone_name = zone_info["name"]
                try:
                    records = await dns_client.list_records(zone_name)
                    export_data["zones"].append({
                        "name": zone_name,
                        "records": records
                    })
                except Exception as e:
                    logger.warning(f"Error exporting zone {zone_name}: {e}")
            
            metrics.record_dns_operation("export_records", "success")
            
            # Format output based on requested format
            if format == "json":
                return export_data
            elif format == "csv":
                # Convert to CSV format
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["Zone", "Name", "Type", "TTL", "Content", "Priority"])
                
                for zone_data in export_data["zones"]:
                    zone_name = zone_data["name"]
                    for record in zone_data["records"]:
                        writer.writerow([
                            zone_name,
                            record.get("name", ""),
                            record.get("type", ""),
                            record.get("ttl", ""),
                            record.get("content", ""),
                            record.get("priority", "")
                        ])
                
                from fastapi.responses import Response
                return Response(
                    content=output.getvalue(),
                    media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=dns-records.csv"}
                )
            elif format == "bind":
                # Convert to BIND zone file format
                output_lines = []
                output_lines.append(f"; DNS Records Export - {export_data['exported_at']}")
                output_lines.append(f"; User: {export_data['user']}")
                output_lines.append("")
                
                for zone_data in export_data["zones"]:
                    zone_name = zone_data["name"]
                    output_lines.append(f"; Zone: {zone_name}")
                    
                    for record in zone_data["records"]:
                        name = record.get("name", "@")
                        ttl = record.get("ttl", 3600)
                        rtype = record.get("type", "A")
                        content = record.get("content", "")
                        
                        # Format BIND record line
                        if rtype == "MX":
                            priority = record.get("priority", 10)
                            output_lines.append(f"{name} {ttl} IN {rtype} {priority} {content}")
                        else:
                            output_lines.append(f"{name} {ttl} IN {rtype} {content}")
                    
                    output_lines.append("")
                
                from fastapi.responses import Response
                return Response(
                    content="\n".join(output_lines),
                    media_type="text/plain",
                    headers={"Content-Disposition": "attachment; filename=dns-records.zone"}
                )
                
    except Exception as e:
        logger.error(f"Error exporting records: {e}")
        metrics.record_dns_operation("export_records", "error")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/export/zones", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def export_zones(
    request: Request,
    current_user: User = Depends(get_current_verified_user),
    export_format: str = Query(
        "json", description="Export format (json, bind, csv)", alias="format"
    ),
    zones: Optional[str] = Query(None, description="Comma-separated list of zone names"),
    include_dnssec: bool = Query(True, description="Include DNSSEC data"),
):
    """
    Export DNS zones in specified format.

    Supports multiple export formats:
    - JSON: PowerDNS API compatible format
    - BIND: Standard zone file format
    - CSV: Simplified tabular format

    Optionally specify zone names to export specific zones only.
    """
    metrics = get_metrics_collector()

    try:
        async with get_powerdns_client() as dns_client:
            # Parse zone names if provided
            zone_names = None
            if zones:
                zone_names = [z.strip() for z in zones.split(",") if z.strip()]

            # Export zones
            export_result = await dns_client.export_zones(
                zone_names=zone_names, format=export_format.lower(), include_dnssec=include_dnssec
            )

            metrics.record_dns_operation("export_zones", "success")

            # Return appropriate response based on format
            if export_format.lower() == "json":
                return export_result
            else:
                # For BIND and CSV, return as downloadable content
                from fastapi.responses import Response

                content_type = "text/plain" if export_format.lower() == "bind" else "text/csv"
                filename = f"dns-export.{export_format.lower()}"

                return Response(
                    content=export_result["data"],
                    media_type=content_type,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
                )

    except HTTPException:
        # Re-raise HTTPException without wrapping
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PowerDNSError as e:
        logger.error(f"PowerDNS error exporting zones: {e}")
        metrics.record_dns_operation("export_zones", "error")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error exporting zones: {e}")
        metrics.record_dns_operation("export_zones", "error")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/import/zones", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def import_zones(
    request: Request,
    import_data: Dict[str, Any],
    current_user: User = Depends(get_current_verified_user),
):
    """
    Import DNS zones from uploaded data.

    Request body should contain:
    - data: The zone data to import (string)
    - format: Import format (json, bind)
    - mode: Import mode (merge, replace, skip)
    - dry_run: Preview changes without applying (optional, default false)

    Import modes:
    - merge: Add new records, update existing ones
    - replace: Delete existing zone and recreate
    - skip: Skip zones that already exist

    Returns import statistics and any errors encountered.
    """
    metrics = get_metrics_collector()

    try:
        # Extract parameters
        data = import_data.get("data", "")
        import_format = import_data.get("format", "json")
        mode = import_data.get("mode", "merge")
        dry_run = import_data.get("dry_run", False)

        # Validate parameters
        if not data:
            raise HTTPException(status_code=400, detail="Import data is required")

        if import_format not in ["json", "bind"]:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {import_format}")

        if mode not in ["merge", "replace", "skip"]:
            raise HTTPException(status_code=400, detail=f"Invalid import mode: {mode}")

        async with get_powerdns_client() as dns_client:
            # Import zones
            import_result = await dns_client.import_zones(
                data=data, format=import_format, mode=mode, dry_run=dry_run
            )

            # Record metrics
            if import_result["status"] == "success":
                metrics.record_dns_operation("import_zones", "success")
            else:
                metrics.record_dns_operation("import_zones", "error")

            return import_result

    except HTTPException:
        # Re-raise HTTPException without wrapping
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PowerDNSError as e:
        logger.error(f"PowerDNS error importing zones: {e}")
        metrics.record_dns_operation("import_zones", "error")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error importing zones: {e}")
        metrics.record_dns_operation("import_zones", "error")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/import/preview", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def preview_import(
    request: Request,
    import_data: Dict[str, Any],
    current_user: User = Depends(get_current_verified_user),
):
    """
    Preview DNS zone import without applying changes.

    Same parameters as /import/zones but always runs in dry-run mode.
    Returns what would be imported without making any changes.
    """
    # Force dry_run mode for preview
    import_data["dry_run"] = True

    # Reuse import_zones logic
    return await import_zones(request, import_data, current_user)


@router.get("/config", response_model=Dict[str, Any])
@limiter.limit("100/minute")
async def get_dns_config(
    request: Request,
):
    """
    Get DNS service configuration for frontend adapter.

    Returns feature flags and settings from server configuration
    to control PowerDNS integration rollout.
    
    Note: This endpoint is public as it only returns configuration
    needed by the frontend to determine service availability.
    """
    try:
        # Get configuration from server's config object (single source of truth)
        app_config = get_app_config()
        powerdns_config = app_config.get("powerdns", {})
        
        # Get feature flags from environment (these are deployment-specific)
        feature_flag_percentage = int(os.getenv("POWERDNS_FEATURE_FLAG_PERCENTAGE", "0"))
        fallback_to_mock = os.getenv("POWERDNS_FALLBACK_TO_MOCK", "true").lower() == "true"
        
        config = {
            "powerdns_enabled": powerdns_config.get("enabled", False),
            "feature_flag_percentage": feature_flag_percentage,
            "fallback_to_mock": fallback_to_mock,
            "api_url": powerdns_config.get("api_url", "http://localhost:8053/api/v1"),
            "default_zone": powerdns_config.get("default_zone", "managed.prism.local."),
        }

        return config

    except ValueError as e:
        logger.error(f"Invalid configuration value: {e}")
        # Return safe defaults if config is invalid
        return {
            "powerdns_enabled": False,
            "feature_flag_percentage": 0,
            "fallback_to_mock": True,
            "api_url": "http://localhost:8053/api/v1",
            "default_zone": "managed.prism.local.",
        }
    except Exception as e:
        logger.error(f"Unexpected error getting DNS config: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
