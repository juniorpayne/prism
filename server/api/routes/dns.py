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
    Search for DNS records across zones.

    Supports:
    - Search in record names or content
    - Filter by record type
    - Limit to specific zone
    - Returns records with zone information
    """
    metrics = get_metrics_collector()

    try:
        async with get_powerdns_client() as dns_client:
            results = await dns_client.search_records(
                query=q,
                record_type=record_type,
                zone_name=zone,
                content_search=content,
                limit=limit,
            )

            metrics.record_dns_operation("search_records", "success")

            return {
                "query": q,
                "total": len(results),
                "records": results,
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
