#!/usr/bin/env python3
"""
PowerDNS API Client for Prism DNS Server (SCRUM-49)
Manages DNS records through PowerDNS API integration.
"""

import asyncio
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import aiohttp
from aiohttp import ClientError, ClientTimeout

from .monitoring import get_metrics_collector

logger = logging.getLogger(__name__)


class PowerDNSError(Exception):
    """Base exception for PowerDNS operations."""

    pass


class PowerDNSAPIError(PowerDNSError):
    """Exception raised for API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class PowerDNSConnectionError(PowerDNSError):
    """Exception raised for connection errors."""

    pass


class PowerDNSClient:
    """
    Client for PowerDNS API integration.

    Provides methods for managing DNS records through the PowerDNS API.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize PowerDNS client.

        Args:
            config: Configuration dictionary with PowerDNS settings
        """
        powerdns_config = config.get("powerdns", {})

        # API configuration
        self.enabled = powerdns_config.get("enabled", False)
        self.base_url = powerdns_config.get("api_url", "http://powerdns:8053/api/v1")
        # Ensure base URL ends with slash for proper urljoin behavior
        if not self.base_url.endswith("/"):
            self.base_url += "/"
        self.api_key = powerdns_config.get("api_key", "")
        self.default_zone = powerdns_config.get("default_zone", "managed.prism.local.")
        self.default_ttl = powerdns_config.get("default_ttl", 300)

        # Connection settings
        self.timeout = powerdns_config.get("timeout", 5)
        self.retry_attempts = powerdns_config.get("retry_attempts", 3)
        self.retry_delay = powerdns_config.get("retry_delay", 1)

        # Record type settings
        self.record_types = powerdns_config.get("record_types", ["A", "AAAA"])
        self.auto_ptr = powerdns_config.get("auto_ptr", False)

        # Ensure zone ends with a dot
        if not self.default_zone.endswith("."):
            self.default_zone += "."

        # Session management
        self._session: Optional[aiohttp.ClientSession] = None

        logger.info(
            f"PowerDNS client initialized: enabled={self.enabled}, "
            f"url={self.base_url}, zone={self.default_zone}"
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = ClientTimeout(total=self.timeout)
            headers = {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
            )
        return self._session

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to PowerDNS API with retry logic.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint path
            json_data: JSON data for request body
            params: Query parameters

        Returns:
            Response data as dictionary

        Raises:
            PowerDNSAPIError: For API errors
            PowerDNSConnectionError: For connection errors
        """
        url = urljoin(self.base_url, endpoint)
        session = await self._get_session()
        metrics = get_metrics_collector()
        start_time = time.time()

        for attempt in range(self.retry_attempts):
            try:
                async with session.request(
                    method=method,
                    url=url,
                    json=json_data,
                    params=params,
                ) as response:
                    response_text = await response.text()
                    duration = time.time() - start_time

                    # Handle successful responses
                    if response.status in (200, 201, 204):
                        metrics.record_powerdns_api_request(method, endpoint, "success", duration)
                        if response_text:
                            return json.loads(response_text)
                        return {}

                    # Handle API errors
                    try:
                        error_data = json.loads(response_text) if response_text else {}
                    except json.JSONDecodeError:
                        error_data = {"error": response_text}

                    metrics.record_powerdns_api_request(method, endpoint, "error", duration)

                    raise PowerDNSAPIError(
                        f"API error: {response.status} - {response_text}",
                        status_code=response.status,
                        response_data=error_data,
                    )

            except ClientError as e:
                logger.warning(
                    f"Connection error on attempt {attempt + 1}/{self.retry_attempts}: {e}"
                )

                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue

                duration = time.time() - start_time
                metrics.record_powerdns_api_request(method, endpoint, "error", duration)
                raise PowerDNSConnectionError(f"Failed to connect to PowerDNS API: {e}")

            except Exception as e:
                logger.error(f"Unexpected error making request to {url}: {e}")
                duration = time.time() - start_time
                metrics.record_powerdns_api_request(method, endpoint, "error", duration)
                raise PowerDNSError(f"Unexpected error: {e}")

    async def _patch_zone(self, zone: str, rrsets_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Patch zone with RRset changes.

        Args:
            zone: Zone name
            rrsets_data: RRset data containing changes

        Returns:
            Response data
        """
        endpoint = f"servers/localhost/zones/{zone}"
        return await self._make_request("PATCH", endpoint, json_data=rrsets_data)

    async def create_a_record(
        self,
        hostname: str,
        ip_address: str,
        zone: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create A record for hostname.

        Args:
            hostname: Hostname (without zone)
            ip_address: IPv4 address
            zone: DNS zone (defaults to configured zone)
            ttl: Time to live (defaults to configured TTL)

        Returns:
            API response data

        Raises:
            PowerDNSError: On any error
        """
        if not self.enabled:
            logger.debug("PowerDNS integration disabled, skipping A record creation")
            return {"status": "disabled"}

        zone = zone or self.default_zone
        ttl = ttl or self.default_ttl

        # Ensure zone ends with dot
        if not zone.endswith("."):
            zone += "."

        # Build FQDN
        if hostname.endswith("."):
            fqdn = hostname
        else:
            fqdn = f"{hostname}.{zone}"

        rrsets = {
            "rrsets": [
                {
                    "name": fqdn,
                    "type": "A",
                    "ttl": ttl,
                    "changetype": "REPLACE",
                    "records": [
                        {
                            "content": ip_address,
                            "disabled": False,
                        }
                    ],
                }
            ]
        }

        logger.info(f"Creating A record: {fqdn} -> {ip_address}")

        metrics = get_metrics_collector()
        try:
            result = await self._patch_zone(zone, rrsets)
            logger.info(f"Successfully created A record for {hostname}")
            metrics.record_powerdns_record_operation("create", "A", "success")
            return {"status": "success", "fqdn": fqdn, "zone": zone}
        except Exception as e:
            logger.error(f"Failed to create A record for {hostname}: {e}")
            metrics.record_powerdns_record_operation("create", "A", "failed")
            raise

    async def create_aaaa_record(
        self,
        hostname: str,
        ipv6_address: str,
        zone: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create AAAA record for hostname.

        Args:
            hostname: Hostname (without zone)
            ipv6_address: IPv6 address
            zone: DNS zone (defaults to configured zone)
            ttl: Time to live (defaults to configured TTL)

        Returns:
            API response data
        """
        if not self.enabled:
            logger.debug("PowerDNS integration disabled, skipping AAAA record creation")
            return {"status": "disabled"}

        zone = zone or self.default_zone
        ttl = ttl or self.default_ttl

        # Ensure zone ends with dot
        if not zone.endswith("."):
            zone += "."

        # Build FQDN
        if hostname.endswith("."):
            fqdn = hostname
        else:
            fqdn = f"{hostname}.{zone}"

        rrsets = {
            "rrsets": [
                {
                    "name": fqdn,
                    "type": "AAAA",
                    "ttl": ttl,
                    "changetype": "REPLACE",
                    "records": [
                        {
                            "content": ipv6_address,
                            "disabled": False,
                        }
                    ],
                }
            ]
        }

        logger.info(f"Creating AAAA record: {fqdn} -> {ipv6_address}")

        metrics = get_metrics_collector()
        try:
            result = await self._patch_zone(zone, rrsets)
            logger.info(f"Successfully created AAAA record for {hostname}")
            metrics.record_powerdns_record_operation("create", "AAAA", "success")
            return {"status": "success", "fqdn": fqdn, "zone": zone}
        except Exception as e:
            logger.error(f"Failed to create AAAA record for {hostname}: {e}")
            metrics.record_powerdns_record_operation("create", "AAAA", "failed")
            raise

    async def update_record(
        self,
        hostname: str,
        ip_address: str,
        record_type: str = "A",
        zone: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Update DNS record for hostname.

        Args:
            hostname: Hostname (without zone)
            ip_address: IP address
            record_type: Record type (A or AAAA)
            zone: DNS zone (defaults to configured zone)
            ttl: Time to live (defaults to configured TTL)

        Returns:
            API response data
        """
        if record_type == "A":
            return await self.create_a_record(hostname, ip_address, zone, ttl)
        elif record_type == "AAAA":
            return await self.create_aaaa_record(hostname, ip_address, zone, ttl)
        else:
            raise ValueError(f"Unsupported record type: {record_type}")

    async def delete_record(
        self,
        hostname: str,
        record_type: str = "A",
        zone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Delete DNS record for hostname.

        Args:
            hostname: Hostname (without zone)
            record_type: Record type to delete
            zone: DNS zone (defaults to configured zone)

        Returns:
            API response data
        """
        if not self.enabled:
            logger.debug("PowerDNS integration disabled, skipping record deletion")
            return {"status": "disabled"}

        zone = zone or self.default_zone

        # Ensure zone ends with dot
        if not zone.endswith("."):
            zone += "."

        # Build FQDN
        if hostname.endswith("."):
            fqdn = hostname
        else:
            fqdn = f"{hostname}.{zone}"

        rrsets = {
            "rrsets": [
                {
                    "name": fqdn,
                    "type": record_type,
                    "changetype": "DELETE",
                }
            ]
        }

        logger.info(f"Deleting {record_type} record: {fqdn}")

        metrics = get_metrics_collector()
        try:
            result = await self._patch_zone(zone, rrsets)
            logger.info(f"Successfully deleted {record_type} record for {hostname}")
            metrics.record_powerdns_record_operation("delete", record_type, "success")
            return {"status": "success", "fqdn": fqdn, "zone": zone}
        except Exception as e:
            logger.error(f"Failed to delete {record_type} record for {hostname}: {e}")
            metrics.record_powerdns_record_operation("delete", record_type, "failed")
            raise

    async def get_record(
        self,
        hostname: str,
        record_type: str = "A",
        zone: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get DNS record for hostname.

        Args:
            hostname: Hostname (without zone)
            record_type: Record type to retrieve
            zone: DNS zone (defaults to configured zone)

        Returns:
            Record data or None if not found
        """
        if not self.enabled:
            logger.debug("PowerDNS integration disabled")
            return None

        zone = zone or self.default_zone

        # Ensure zone ends with dot
        if not zone.endswith("."):
            zone += "."

        # Build FQDN
        if hostname.endswith("."):
            fqdn = hostname
        else:
            fqdn = f"{hostname}.{zone}"

        try:
            # Get zone data
            endpoint = f"servers/localhost/zones/{zone}"
            zone_data = await self._make_request("GET", endpoint)

            # Find the record
            for rrset in zone_data.get("rrsets", []):
                if rrset["name"].lower() == fqdn.lower() and rrset["type"] == record_type:
                    return {
                        "name": rrset["name"],
                        "type": rrset["type"],
                        "ttl": rrset.get("ttl"),
                        "records": rrset.get("records", []),
                    }

            return None

        except Exception as e:
            logger.error(f"Failed to get {record_type} record for {hostname}: {e}")
            return None

    async def zone_exists(self, zone: Optional[str] = None) -> bool:
        """
        Check if zone exists.

        Args:
            zone: Zone name (defaults to configured zone)

        Returns:
            True if zone exists, False otherwise
        """
        if not self.enabled:
            return False

        zone = zone or self.default_zone

        # Ensure zone ends with dot
        if not zone.endswith("."):
            zone += "."

        metrics = get_metrics_collector()
        try:
            endpoint = f"servers/localhost/zones/{zone}"
            await self._make_request("GET", endpoint)
            metrics.record_powerdns_zone_operation("check", "success")
            return True
        except PowerDNSAPIError as e:
            if e.status_code == 404:
                metrics.record_powerdns_zone_operation("check", "success")
                return False
            metrics.record_powerdns_zone_operation("check", "failed")
            raise
        except Exception:
            metrics.record_powerdns_zone_operation("check", "failed")
            return False

    async def create_zone(
        self,
        zone: Optional[str] = None,
        nameservers: Optional[List[str]] = None,
        kind: str = "Native",
        masters: Optional[List[str]] = None,
        soa_edit: Optional[str] = None,
        soa_edit_api: str = "DEFAULT",
        api_rectify: bool = True,
        account: str = "",
        dnssec: bool = False,
    ) -> Dict[str, Any]:
        """
        Create DNS zone if it doesn't exist.

        Args:
            zone: Zone name (defaults to configured zone)
            nameservers: List of nameservers for the zone

        Returns:
            API response data
        """
        if not self.enabled:
            logger.debug("PowerDNS integration disabled")
            return {"status": "disabled"}

        zone = zone or self.default_zone

        # Ensure zone ends with dot
        if not zone.endswith("."):
            zone += "."

        # Check if zone already exists
        if await self.zone_exists(zone):
            logger.info(f"Zone {zone} already exists")
            return {"status": "exists", "zone": zone}

        # Default nameservers
        if not nameservers:
            nameservers = ["ns1.example.com.", "ns2.example.com."]

        zone_data = {
            "name": zone,
            "kind": kind,
            "masters": masters or [],
            "soa_edit": soa_edit,
            "soa_edit_api": soa_edit_api,
            "api_rectify": api_rectify,
            "account": account,
            "dnssec": dnssec,
            "nameservers": nameservers,
        }

        metrics = get_metrics_collector()
        try:
            endpoint = "servers/localhost/zones"
            result = await self._make_request("POST", endpoint, json_data=zone_data)
            logger.info(f"Successfully created zone {zone}")
            metrics.record_powerdns_zone_operation("create", "success")
            return {"status": "created", "zone": zone}
        except Exception as e:
            logger.error(f"Failed to create zone {zone}: {e}")
            metrics.record_powerdns_zone_operation("create", "failed")
            raise

    async def list_zones(self) -> List[Dict[str, Any]]:
        """
        List all DNS zones.

        Returns:
            List of zone dictionaries
        """
        if not self.enabled:
            logger.debug("PowerDNS integration disabled")
            return []

        try:
            endpoint = "servers/localhost/zones"
            zones = await self._make_request("GET", endpoint)

            # Add computed fields and fetch zone details for nameservers
            for zone in zones:
                zone["record_count"] = 0  # Will be updated from zone details
                zone["status"] = "Active"  # PowerDNS doesn't have status
                
                # Fetch zone details to get nameservers
                try:
                    zone_details = await self.get_zone_details(zone["name"])
                    if zone_details:
                        zone["nameservers"] = zone_details.get("nameservers", [])
                        zone["record_count"] = zone_details.get("record_count", 0)
                    else:
                        zone["nameservers"] = []
                except Exception as e:
                    logger.debug(f"Could not fetch details for zone {zone.get('name')}: {e}")
                    zone["nameservers"] = []

            return zones
        except Exception as e:
            logger.error(f"Failed to list zones: {e}")
            return []

    async def get_zone_details(self, zone_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed zone information.

        Args:
            zone_name: Name of the zone to retrieve

        Returns:
            Zone details or None if not found
        """
        if not self.enabled:
            logger.debug("PowerDNS integration disabled")
            return None

        try:
            endpoint = f"servers/localhost/zones/{zone_name}"
            zone = await self._make_request("GET", endpoint)

            # Add computed fields
            zone["record_count"] = len(zone.get("rrsets", []))
            zone["status"] = "Active"  # PowerDNS doesn't have status
            
            # Extract nameservers from NS records
            nameservers = []
            for rrset in zone.get("rrsets", []):
                if rrset.get("type") == "NS" and rrset.get("name") == zone_name:
                    for record in rrset.get("records", []):
                        if not record.get("disabled", False):
                            nameservers.append(record.get("content", ""))
            zone["nameservers"] = nameservers

            return zone
        except Exception as e:
            logger.error(f"Failed to get zone details for {zone_name}: {e}")
            return None

    def validate_zone_name(self, zone_name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a DNS zone name.

        Args:
            zone_name: Zone name to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not zone_name:
            return False, "Zone name cannot be empty"

        # Zone names must end with a dot
        if not zone_name.endswith("."):
            return False, "Zone name must end with a dot (.)"

        # Remove trailing dot for validation
        name = zone_name[:-1]

        # Check for valid characters and format
        if not re.match(
            r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$",
            name,
        ):
            return False, "Zone name contains invalid characters or format"

        # Check label length
        labels = name.split(".")
        for label in labels:
            if len(label) > 63:
                return False, f"Label '{label}' exceeds 63 characters"
            if len(label) == 0:
                return False, "Zone name contains empty labels"

        # Total length check (including dots)
        if len(zone_name) > 255:
            return False, "Zone name exceeds 255 characters"

        return True, None

    def validate_soa_record(self, soa_content: str) -> Tuple[bool, Optional[str]]:
        """
        Validate SOA record format.

        Args:
            soa_content: SOA record content

        Returns:
            Tuple of (is_valid, error_message)
        """
        # SOA format: primary-ns admin-email serial refresh retry expire minimum
        parts = soa_content.split()
        if len(parts) != 7:
            return (
                False,
                "SOA record must have 7 parts: primary-ns admin-email serial refresh retry expire minimum",
            )

        # Validate primary nameserver
        if not parts[0].endswith("."):
            return False, "Primary nameserver must end with a dot"

        # Validate admin email (in DNS format)
        if not parts[1].endswith("."):
            return False, "Admin email must end with a dot"

        # Validate numeric fields
        numeric_fields = ["serial", "refresh", "retry", "expire", "minimum"]
        for i, field in enumerate(numeric_fields, 2):
            try:
                value = int(parts[i])
                if value < 0:
                    return False, f"{field} must be non-negative"
            except ValueError:
                return False, f"{field} must be a number"

        return True, None

    def detect_zone_hierarchy(self, zone_name: str, existing_zones: List[str]) -> Dict[str, Any]:
        """
        Detect zone hierarchy relationships.

        Args:
            zone_name: Zone to check
            existing_zones: List of existing zone names

        Returns:
            Dictionary with parent and children zones
        """
        hierarchy = {"zone": zone_name, "parent": None, "children": [], "level": 0}

        # Remove trailing dot for comparison
        zone_labels = zone_name[:-1].split(".") if zone_name.endswith(".") else zone_name.split(".")

        for existing in existing_zones:
            if existing == zone_name:
                continue

            existing_labels = (
                existing[:-1].split(".") if existing.endswith(".") else existing.split(".")
            )

            # Check if existing is a parent of zone
            if len(existing_labels) < len(zone_labels):
                if zone_labels[-len(existing_labels) :] == existing_labels:
                    if not hierarchy["parent"] or len(existing_labels) > len(
                        hierarchy["parent"][:-1].split(".")
                    ):
                        hierarchy["parent"] = existing

            # Check if existing is a child of zone
            elif len(existing_labels) > len(zone_labels):
                if existing_labels[-len(zone_labels) :] == zone_labels:
                    hierarchy["children"].append(existing)

        # Calculate hierarchy level
        if hierarchy["parent"]:
            parent_labels = hierarchy["parent"][:-1].split(".")
            hierarchy["level"] = len(zone_labels) - len(parent_labels)

        return hierarchy

    async def update_zone(self, zone_name: str, zone_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing DNS zone.

        Args:
            zone_name: Name of the zone to update
            zone_data: Zone configuration data

        Returns:
            Update result
        """
        if not self.enabled:
            raise PowerDNSError("PowerDNS integration is disabled")

        metrics = get_metrics_collector()
        try:
            endpoint = f"servers/localhost/zones/{zone_name}"

            # PowerDNS expects specific fields for zone updates
            # Define how each field should be handled when updating a zone
            # Format: field_name -> (should_include_field_function, default_value_if_missing)
            
            def always_include(value):
                """Include field regardless of value"""
                return True
                
            def include_if_not_empty(value):
                """Include field only if it has a non-empty value"""
                return value and value != ""
                
            def include_if_true(value):
                """Include field only if explicitly set to True"""
                return value is True
            
            zone_update_field_handlers = {
                # Standard zone configuration fields - always include if present
                "kind": (always_include, None),
                "masters": (always_include, None),
                "soa_edit": (always_include, None),
                "soa_edit_api": (always_include, None),
                "api_rectify": (always_include, None),
                "dnssec": (always_include, None),
                "account": (always_include, None),
                "nameservers": (always_include, None),
                
                # NSEC3/DNSSEC fields - only include if they have meaningful values
                # Empty nsec3param causes PowerDNS to try removing NSEC3 parameters
                "nsec3param": (include_if_not_empty, None),
                "nsec3narrow": (include_if_true, None),
                "presigned": (include_if_true, None),
            }
            
            # Build the update payload based on the field handlers
            update_data = {}
            for field_name, (should_include, default_value) in zone_update_field_handlers.items():
                if field_name in zone_data:
                    field_value = zone_data[field_name]
                    if should_include(field_value):
                        update_data[field_name] = field_value
                elif default_value is not None:
                    update_data[field_name] = default_value

            result = await self._make_request("PUT", endpoint, json_data=update_data)
            logger.info(f"Successfully updated zone {zone_name}")
            metrics.record_powerdns_zone_operation("update", "success")
            return {"status": "updated", "zone": zone_name}
        except Exception as e:
            logger.error(f"Failed to update zone {zone_name}: {e}")
            metrics.record_powerdns_zone_operation("update", "failed")
            raise

    async def list_records(self, zone_name: str) -> List[Dict[str, Any]]:
        """
        List all records in a zone.

        Args:
            zone_name: Name of the zone

        Returns:
            List of records (RRSets)
        """
        if not self.enabled:
            raise PowerDNSError("PowerDNS integration is disabled")

        try:
            zone = await self.get_zone_details(zone_name)
            if not zone:
                raise PowerDNSError(f"Zone '{zone_name}' not found")

            return zone.get("rrsets", [])
        except Exception as e:
            logger.error(f"Failed to list records for zone {zone_name}: {e}")
            raise

    async def get_record_set(
        self, zone_name: str, name: str, record_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific record set.

        Args:
            zone_name: Name of the zone
            name: Record name (FQDN)
            record_type: Record type (A, AAAA, CNAME, etc.)

        Returns:
            Record set or None if not found
        """
        if not self.enabled:
            raise PowerDNSError("PowerDNS integration is disabled")

        try:
            records = await self.list_records(zone_name)
            for rrset in records:
                if rrset["name"].lower() == name.lower() and rrset["type"] == record_type:
                    return rrset
            return None
        except Exception as e:
            logger.error(f"Failed to get record {name}/{record_type} in zone {zone_name}: {e}")
            raise

    async def create_or_update_record(
        self,
        zone_name: str,
        name: str,
        record_type: str,
        records: List[Dict[str, Any]],
        ttl: int = 300,
    ) -> Dict[str, Any]:
        """
        Create or update a record set.

        Args:
            zone_name: Name of the zone
            name: Record name (FQDN)
            record_type: Record type
            records: List of record data dicts with 'content' and optional 'disabled'
            ttl: Time to live

        Returns:
            Operation result
        """
        if not self.enabled:
            raise PowerDNSError("PowerDNS integration is disabled")

        # Validate record type
        valid_types = ["A", "AAAA", "CNAME", "MX", "TXT", "NS", "SOA", "SRV", "PTR", "CAA"]
        if record_type not in valid_types:
            raise ValueError(f"Invalid record type: {record_type}")

        # Ensure name is FQDN
        if not name.endswith("."):
            name += "."

        # Validate records
        for record in records:
            if "content" not in record:
                raise ValueError("Each record must have 'content' field")

            # Type-specific validation
            self._validate_record_content(record_type, record["content"])

        rrset_data = {
            "rrsets": [
                {
                    "name": name,
                    "type": record_type,
                    "ttl": ttl,
                    "changetype": "REPLACE",
                    "records": records,
                }
            ]
        }

        metrics = get_metrics_collector()
        try:
            result = await self._patch_zone(zone_name, rrset_data)
            logger.info(
                f"Successfully created/updated {record_type} record {name} in zone {zone_name}"
            )
            metrics.record_powerdns_record_operation("create_or_update", record_type, "success")
            return {"status": "success", "name": name, "type": record_type}
        except Exception as e:
            logger.error(
                f"Failed to create/update record {name}/{record_type} in zone {zone_name}: {e}"
            )
            metrics.record_powerdns_record_operation("create_or_update", record_type, "failed")
            raise

    async def delete_record_set(
        self, zone_name: str, name: str, record_type: str
    ) -> Dict[str, Any]:
        """
        Delete a record set.

        Args:
            zone_name: Name of the zone
            name: Record name (FQDN)
            record_type: Record type

        Returns:
            Deletion result
        """
        if not self.enabled:
            raise PowerDNSError("PowerDNS integration is disabled")

        # Ensure name is FQDN
        if not name.endswith("."):
            name += "."

        rrset_data = {"rrsets": [{"name": name, "type": record_type, "changetype": "DELETE"}]}

        metrics = get_metrics_collector()
        try:
            result = await self._patch_zone(zone_name, rrset_data)
            logger.info(f"Successfully deleted {record_type} record {name} in zone {zone_name}")
            metrics.record_powerdns_record_operation("delete", record_type, "success")
            return {"status": "deleted", "name": name, "type": record_type}
        except Exception as e:
            logger.error(f"Failed to delete record {name}/{record_type} in zone {zone_name}: {e}")
            metrics.record_powerdns_record_operation("delete", record_type, "failed")
            raise

    def _validate_record_content(self, record_type: str, content: str):
        """
        Validate record content based on type.

        Args:
            record_type: Record type
            content: Record content

        Raises:
            ValueError: If content is invalid
        """
        import ipaddress

        if record_type == "A":
            try:
                ipaddress.IPv4Address(content)
            except ValueError:
                raise ValueError(f"Invalid IPv4 address: {content}")

        elif record_type == "AAAA":
            try:
                ipaddress.IPv6Address(content)
            except ValueError:
                raise ValueError(f"Invalid IPv6 address: {content}")

        elif record_type in ["CNAME", "NS", "PTR"]:
            if not content.endswith("."):
                raise ValueError(f"{record_type} record content must end with dot: {content}")

        elif record_type == "MX":
            parts = content.split()
            if len(parts) != 2:
                raise ValueError(f"MX record must have priority and domain: {content}")
            try:
                int(parts[0])  # Priority must be integer
            except ValueError:
                raise ValueError(f"MX priority must be integer: {parts[0]}")
            if not parts[1].endswith("."):
                raise ValueError(f"MX domain must end with dot: {parts[1]}")

        elif record_type == "TXT":
            # TXT records should be quoted
            if not (content.startswith('"') and content.endswith('"')):
                raise ValueError(f"TXT record should be quoted: {content}")

        elif record_type == "SRV":
            parts = content.split()
            if len(parts) != 4:
                raise ValueError(f"SRV record must have priority weight port target: {content}")
            try:
                int(parts[0])  # Priority
                int(parts[1])  # Weight
                int(parts[2])  # Port
            except ValueError:
                raise ValueError(f"SRV priority/weight/port must be integers: {content}")
            if not parts[3].endswith("."):
                raise ValueError(f"SRV target must end with dot: {parts[3]}")

        elif record_type == "CAA":
            parts = content.split(None, 2)
            if len(parts) != 3:
                raise ValueError(f"CAA record must have flag tag value: {content}")
            try:
                int(parts[0])  # Flag must be integer
            except ValueError:
                raise ValueError(f"CAA flag must be integer: {parts[0]}")

    async def delete_zone(self, zone_name: str) -> Dict[str, Any]:
        """
        Delete a DNS zone.

        Args:
            zone_name: Name of the zone to delete

        Returns:
            Deletion result
        """
        if not self.enabled:
            raise PowerDNSError("PowerDNS integration is disabled")

        metrics = get_metrics_collector()
        try:
            endpoint = f"servers/localhost/zones/{zone_name}"
            await self._make_request("DELETE", endpoint)
            logger.info(f"Successfully deleted zone {zone_name}")
            metrics.record_powerdns_zone_operation("delete", "success")
            return {"status": "deleted", "zone": zone_name}
        except Exception as e:
            logger.error(f"Failed to delete zone {zone_name}: {e}")
            metrics.record_powerdns_zone_operation("delete", "failed")
            raise

    async def search_zones(
        self,
        query: str,
        zone_type: Optional[str] = None,
        hierarchy_level: Optional[int] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search for zones matching query.

        Args:
            query: Search query (searches in zone names)
            zone_type: Filter by zone type (Native, Master, Slave)
            hierarchy_level: Filter by hierarchy level (0=root, 1=subdomain, etc.)
            limit: Maximum results to return

        Returns:
            List of matching zones
        """
        if not self.enabled:
            raise PowerDNSError("PowerDNS integration is disabled")

        try:
            # Get all zones
            zones = await self.list_zones()

            # Filter by search query
            if query:
                query_lower = query.lower()
                # Support wildcard search
                if "*" in query:
                    import fnmatch

                    pattern = query_lower.replace(".", r"\.")
                    zones = [
                        z for z in zones if fnmatch.fnmatch(z.get("name", "").lower(), pattern)
                    ]
                else:
                    zones = [z for z in zones if query_lower in z.get("name", "").lower()]

            # Filter by zone type
            if zone_type:
                zones = [z for z in zones if z.get("kind", "").lower() == zone_type.lower()]

            # Filter by hierarchy level
            if hierarchy_level is not None:
                filtered_zones = []
                all_zone_names = [z.get("name", "") for z in zones]

                for zone in zones:
                    zone_name = zone.get("name", "")
                    hierarchy = self.detect_zone_hierarchy(zone_name, all_zone_names)
                    if hierarchy["level"] == hierarchy_level:
                        filtered_zones.append(zone)
                zones = filtered_zones

            # Limit results
            return zones[:limit]

        except Exception as e:
            logger.error(f"Failed to search zones with query '{query}': {e}")
            raise

    async def search_records(
        self,
        query: str,
        record_type: Optional[str] = None,
        zone_name: Optional[str] = None,
        content_search: bool = False,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search for records matching query across zones.

        Args:
            query: Search query
            record_type: Filter by record type (A, AAAA, CNAME, etc.)
            zone_name: Limit search to specific zone
            content_search: Search in record content instead of names
            limit: Maximum results to return

        Returns:
            List of matching records with zone information
        """
        if not self.enabled:
            raise PowerDNSError("PowerDNS integration is disabled")

        try:
            results = []

            # Get zones to search
            if zone_name:
                zones = [await self.get_zone_details(zone_name)]
                if not zones[0]:
                    return []
            else:
                zones = await self.list_zones()

            query_lower = query.lower() if query else ""

            # Search through each zone
            for zone in zones:
                zone_id = zone.get("id", zone.get("name", ""))
                try:
                    records = await self.list_records(zone_id)

                    for record in records:
                        # Filter by record type
                        if record_type and record.get("type") != record_type.upper():
                            continue

                        # Search in record name or content
                        if query:
                            if content_search:
                                # Search in record content
                                match = any(
                                    query_lower in r.get("content", "").lower()
                                    for r in record.get("records", [])
                                )
                            else:
                                # Search in record name
                                match = query_lower in record.get("name", "").lower()

                            if not match:
                                continue

                        # Add zone information to record
                        record_with_zone = record.copy()
                        record_with_zone["zone"] = zone_id
                        results.append(record_with_zone)

                        if len(results) >= limit:
                            return results

                except Exception as e:
                    logger.warning(f"Failed to search records in zone {zone_id}: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Failed to search records with query '{query}': {e}")
            raise

    async def filter_zones(
        self,
        filters: Dict[str, Any],
        sort_by: str = "name",
        sort_order: str = "asc",
    ) -> List[Dict[str, Any]]:
        """
        Filter zones based on multiple criteria.

        Args:
            filters: Dictionary of filter criteria
                - min_records: Minimum number of records
                - max_records: Maximum number of records
                - has_dnssec: Filter by DNSSEC status
                - parent_zone: Filter by parent zone
                - created_after: Filter by creation date
                - modified_after: Filter by modification date
            sort_by: Field to sort by (name, records, serial)
            sort_order: Sort order (asc, desc)

        Returns:
            Filtered and sorted list of zones
        """
        if not self.enabled:
            raise PowerDNSError("PowerDNS integration is disabled")

        try:
            zones = await self.list_zones()
            all_zone_names = [z.get("name", "") for z in zones]

            # Apply filters
            filtered_zones = []
            for zone in zones:
                # Filter by record count
                record_count = zone.get("record_count", len(zone.get("rrsets", [])))
                if filters.get("min_records") and record_count < filters["min_records"]:
                    continue
                if filters.get("max_records") and record_count > filters["max_records"]:
                    continue

                # Filter by DNSSEC
                if filters.get("has_dnssec") is not None:
                    if zone.get("dnssec", False) != filters["has_dnssec"]:
                        continue

                # Filter by parent zone
                if filters.get("parent_zone"):
                    hierarchy = self.detect_zone_hierarchy(zone.get("name", ""), all_zone_names)
                    if hierarchy["parent"] != filters["parent_zone"]:
                        continue

                # Filter by serial (as proxy for modification date)
                if filters.get("serial_after"):
                    if zone.get("serial", 0) < filters["serial_after"]:
                        continue

                filtered_zones.append(zone)

            # Sort results
            reverse = sort_order.lower() == "desc"
            if sort_by == "name":
                filtered_zones.sort(key=lambda x: x.get("name", ""), reverse=reverse)
            elif sort_by == "records":
                filtered_zones.sort(
                    key=lambda x: x.get("record_count", len(x.get("rrsets", []))), reverse=reverse
                )
            elif sort_by == "serial":
                filtered_zones.sort(key=lambda x: x.get("serial", 0), reverse=reverse)

            return filtered_zones

        except Exception as e:
            logger.error(f"Failed to filter zones: {e}")
            raise

    async def export_zones(
        self,
        zone_names: Optional[List[str]] = None,
        format: str = "json",
        include_dnssec: bool = True,
    ) -> Dict[str, Any]:
        """
        Export DNS zones in specified format.

        Args:
            zone_names: List of zone names to export (None = all zones)
            format: Export format (json, bind, csv)
            include_dnssec: Include DNSSEC data

        Returns:
            Exported data in requested format
        """
        if not self.enabled:
            raise PowerDNSError("PowerDNS integration is disabled")

        try:
            # Get zones to export
            if zone_names:
                zones = []
                for zone_name in zone_names:
                    zone = await self.get_zone_details(zone_name)
                    if zone:
                        zones.append(zone)
            else:
                zones = await self.list_zones()

            # Export based on format
            if format == "json":
                return {"format": "json", "version": "1.0", "zones": zones}
            elif format == "bind":
                return {"format": "bind", "data": self._export_zones_bind(zones)}
            elif format == "csv":
                return {"format": "csv", "data": self._export_zones_csv(zones)}
            else:
                raise ValueError(f"Unsupported export format: {format}")

        except Exception as e:
            logger.error(f"Failed to export zones: {e}")
            raise

    def _export_zones_bind(self, zones: List[Dict[str, Any]]) -> str:
        """
        Export zones in BIND format.

        Args:
            zones: List of zones to export

        Returns:
            BIND formatted zone data
        """
        bind_data = []

        for zone in zones:
            zone_name = zone.get("name", "")
            bind_data.append(f"; Zone: {zone_name}")
            bind_data.append(f"; Exported from PowerDNS")
            bind_data.append("")

            # Process RRsets
            for rrset in zone.get("rrsets", []):
                name = rrset.get("name", "")
                ttl = rrset.get("ttl", 300)
                record_type = rrset.get("type", "")

                for record in rrset.get("records", []):
                    content = record.get("content", "")
                    if not record.get("disabled", False):
                        bind_data.append(f"{name}\t{ttl}\tIN\t{record_type}\t{content}")

            bind_data.append("")  # Empty line between zones

        return "\n".join(bind_data)

    def _export_zones_csv(self, zones: List[Dict[str, Any]]) -> str:
        """
        Export zones in CSV format.

        Args:
            zones: List of zones to export

        Returns:
            CSV formatted zone data
        """
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["zone", "name", "type", "ttl", "content", "disabled"])

        for zone in zones:
            zone_name = zone.get("name", "")

            for rrset in zone.get("rrsets", []):
                name = rrset.get("name", "")
                ttl = rrset.get("ttl", 300)
                record_type = rrset.get("type", "")

                for record in rrset.get("records", []):
                    content = record.get("content", "")
                    disabled = record.get("disabled", False)
                    writer.writerow([zone_name, name, record_type, ttl, content, disabled])

        return output.getvalue()

    async def import_zones(
        self,
        data: str,
        format: str = "json",
        mode: str = "merge",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Import DNS zones from specified format.

        Args:
            data: Import data in specified format
            format: Import format (json, bind)
            mode: Import mode (merge, replace, skip)
            dry_run: Preview changes without applying

        Returns:
            Import result with statistics
        """
        if not self.enabled:
            raise PowerDNSError("PowerDNS integration is disabled")

        try:
            # Parse data based on format
            if format == "json":
                import_zones = self._parse_json_import(data)
            elif format == "bind":
                import_zones = self._parse_bind_import(data)
            else:
                raise ValueError(f"Unsupported import format: {format}")

            # Validate import data
            validation_errors = self._validate_import(import_zones)
            if validation_errors:
                return {
                    "status": "error",
                    "errors": validation_errors,
                    "zones_parsed": len(import_zones),
                }

            # Process import
            results = {
                "status": "success" if not dry_run else "preview",
                "mode": mode,
                "zones_processed": 0,
                "zones_created": 0,
                "zones_updated": 0,
                "zones_skipped": 0,
                "records_added": 0,
                "records_updated": 0,
                "errors": [],
            }

            for zone_data in import_zones:
                zone_name = zone_data.get("name", "")

                try:
                    # Check if zone exists
                    existing_zone = await self.get_zone_details(zone_name)

                    if existing_zone:
                        if mode == "skip":
                            results["zones_skipped"] += 1
                            continue
                        elif mode == "replace":
                            if not dry_run:
                                await self.delete_zone(zone_name)
                                await self._create_zone_from_import(zone_data)
                            results["zones_updated"] += 1
                        else:  # merge
                            if not dry_run:
                                await self._merge_zone_data(existing_zone, zone_data)
                            results["zones_updated"] += 1
                    else:
                        if not dry_run:
                            await self._create_zone_from_import(zone_data)
                        results["zones_created"] += 1

                    results["zones_processed"] += 1

                    # Count records
                    for rrset in zone_data.get("rrsets", []):
                        results["records_added"] += len(rrset.get("records", []))

                except Exception as e:
                    logger.error(f"Failed to import zone {zone_name}: {e}")
                    results["errors"].append(f"Zone {zone_name}: {str(e)}")

            return results

        except Exception as e:
            logger.error(f"Failed to import zones: {e}")
            raise

    def _parse_json_import(self, data: str) -> List[Dict[str, Any]]:
        """Parse JSON import data."""
        import json

        try:
            import_data = json.loads(data)
            if isinstance(import_data, dict) and "zones" in import_data:
                return import_data["zones"]
            elif isinstance(import_data, list):
                return import_data
            else:
                raise ValueError("Invalid JSON format: expected zones array or object with zones")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

    def _parse_bind_import(self, data: str) -> List[Dict[str, Any]]:
        """Parse BIND zone file format."""
        zones = {}
        current_zone = None
        current_origin = None

        lines = data.strip().split("\n")
        for line in lines:
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith(";"):
                continue

            # Parse $ORIGIN directive
            if line.startswith("$ORIGIN"):
                parts = line.split()
                if len(parts) >= 2:
                    current_origin = parts[1]
                    if not current_origin.endswith("."):
                        current_origin += "."
                continue

            # Parse $TTL directive
            if line.startswith("$TTL"):
                continue  # Handle TTL in record parsing

            # Parse resource records
            parts = line.split(None, 4)
            if len(parts) >= 4:
                name = parts[0]

                # Handle relative names
                if name == "@" and current_origin:
                    name = current_origin
                elif not name.endswith(".") and current_origin:
                    name = f"{name}.{current_origin}"

                # Determine zone from name
                zone_name = self._determine_zone_from_name(name)
                if zone_name not in zones:
                    zones[zone_name] = {
                        "name": zone_name,
                        "kind": "Native",
                        "rrsets": {},
                    }

                # Parse record fields
                if parts[1].isdigit():
                    ttl = int(parts[1])
                    record_class = parts[2]  # Usually "IN"
                    record_type = parts[3]
                    content = parts[4] if len(parts) > 4 else ""
                else:
                    ttl = 300  # Default TTL
                    record_class = parts[1]
                    record_type = parts[2]
                    content = parts[3] if len(parts) > 3 else ""

                # Create RRset key
                rrset_key = f"{name}:{record_type}"
                if rrset_key not in zones[zone_name]["rrsets"]:
                    zones[zone_name]["rrsets"][rrset_key] = {
                        "name": name,
                        "type": record_type,
                        "ttl": ttl,
                        "records": [],
                    }

                # Add record
                zones[zone_name]["rrsets"][rrset_key]["records"].append(
                    {"content": content, "disabled": False}
                )

        # Convert rrsets dict to list
        result = []
        for zone_name, zone_data in zones.items():
            zone_data["rrsets"] = list(zone_data["rrsets"].values())
            result.append(zone_data)

        return result

    def _determine_zone_from_name(self, name: str) -> str:
        """Determine zone name from record name."""
        # Simple heuristic: use second-level domain
        labels = name.strip(".").split(".")
        if len(labels) >= 2:
            return f"{labels[-2]}.{labels[-1]}."
        return name

    def _validate_import(self, zones: List[Dict[str, Any]]) -> List[str]:
        """Validate import data."""
        errors = []

        for i, zone in enumerate(zones):
            zone_name = zone.get("name", f"zone_{i}")

            # Validate zone name
            if not zone.get("name"):
                errors.append(f"Zone {i}: Missing zone name")
                continue

            is_valid, error_msg = self.validate_zone_name(zone["name"])
            if not is_valid:
                errors.append(f"Zone {zone_name}: {error_msg}")

            # Validate records
            for j, rrset in enumerate(zone.get("rrsets", [])):
                if not rrset.get("name"):
                    errors.append(f"Zone {zone_name}, RRset {j}: Missing record name")

                if not rrset.get("type"):
                    errors.append(f"Zone {zone_name}, RRset {j}: Missing record type")

                for k, record in enumerate(rrset.get("records", [])):
                    if not record.get("content"):
                        errors.append(f"Zone {zone_name}, RRset {j}, Record {k}: Missing content")

        return errors

    async def _create_zone_from_import(self, zone_data: Dict[str, Any]) -> None:
        """Create zone from import data."""
        # Create the zone
        zone_name = zone_data["name"]
        await self.create_zone(
            zone=zone_name,
            kind=zone_data.get("kind", "Native"),
            nameservers=zone_data.get("nameservers", []),
            masters=zone_data.get("masters", []),
            dnssec=zone_data.get("dnssec", False),
        )

        # Add records
        for rrset in zone_data.get("rrsets", []):
            await self.create_or_update_record(
                zone_name=zone_name,
                name=rrset["name"],
                record_type=rrset["type"],
                records=rrset.get("records", []),
                ttl=rrset.get("ttl", 300),
            )

    async def _merge_zone_data(
        self, existing_zone: Dict[str, Any], import_zone: Dict[str, Any]
    ) -> None:
        """Merge imported zone data with existing zone."""
        zone_name = existing_zone["name"]

        # Update zone configuration if different
        if import_zone.get("kind") != existing_zone.get("kind"):
            await self.update_zone(zone_name, import_zone)

        # Merge records
        for rrset in import_zone.get("rrsets", []):
            await self.create_or_update_record(
                zone_name=zone_name,
                name=rrset["name"],
                record_type=rrset["type"],
                records=rrset.get("records", []),
                ttl=rrset.get("ttl", 300),
            )

    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


def create_dns_client(config: Dict[str, Any]) -> PowerDNSClient:
    """
    Create PowerDNS client instance.

    Args:
        config: Configuration dictionary

    Returns:
        PowerDNSClient instance
    """
    return PowerDNSClient(config)
