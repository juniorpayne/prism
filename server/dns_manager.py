#!/usr/bin/env python3
"""
PowerDNS API Client for Prism DNS Server (SCRUM-49)
Manages DNS records through PowerDNS API integration.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional
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
            endpoint = f"/servers/localhost/zones/{zone}"
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
            endpoint = f"/servers/localhost/zones/{zone}"
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
        self, zone: Optional[str] = None, nameservers: Optional[List[str]] = None
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
            "kind": "Native",
            "rrsets": [
                {
                    "name": zone,
                    "type": "SOA",
                    "ttl": 3600,
                    "records": [
                        {
                            "content": f"{nameservers[0]} admin.{zone} 1 10800 3600 604800 3600",
                            "disabled": False,
                        }
                    ],
                },
                {
                    "name": zone,
                    "type": "NS",
                    "ttl": 3600,
                    "records": [{"content": ns, "disabled": False} for ns in nameservers],
                },
            ],
        }

        metrics = get_metrics_collector()
        try:
            endpoint = "/servers/localhost/zones"
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

            # Add computed fields
            for zone in zones:
                zone["record_count"] = len(zone.get("rrsets", []))
                zone["status"] = "Active"  # PowerDNS doesn't have status

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

            return zone
        except Exception as e:
            logger.error(f"Failed to get zone details for {zone_name}: {e}")
            return None

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
