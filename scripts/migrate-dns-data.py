#!/usr/bin/env python3
"""
DNS Data Migration Script (SCRUM-125)
Migrates existing DNS data from mock service storage to PowerDNS.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add server directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "server"))

from server.dns_manager import PowerDNSClient, PowerDNSError


class DNSMigrator:
    """Handles migration of DNS data from mock service to PowerDNS."""

    def __init__(self, powerdns_url: str, api_key: str, dry_run: bool = False):
        self.powerdns_url = powerdns_url
        self.api_key = api_key
        self.dry_run = dry_run
        self.logger = logging.getLogger(__name__)

        # Migration statistics
        self.stats = {
            "zones_processed": 0,
            "zones_created": 0,
            "zones_updated": 0,
            "zones_skipped": 0,
            "records_processed": 0,
            "records_created": 0,
            "records_updated": 0,
            "errors": [],
        }

    def load_mock_data(self, data_source: str) -> Dict[str, Any]:
        """Load DNS data from various sources."""
        try:
            if data_source.startswith("file:"):
                # Load from JSON file
                file_path = data_source[5:]  # Remove 'file:' prefix
                with open(file_path, "r") as f:
                    return json.load(f)

            elif data_source.startswith("localStorage:"):
                # Extract from localStorage dump
                storage_data = data_source[13:]  # Remove 'localStorage:' prefix
                return json.loads(storage_data)

            elif data_source == "default":
                # Load default mock data
                return self._load_default_mock_data()

            else:
                raise ValueError(f"Unsupported data source: {data_source}")

        except Exception as e:
            self.logger.error(f"Failed to load mock data from {data_source}: {e}")
            raise

    def _load_default_mock_data(self) -> Dict[str, Any]:
        """Load default mock DNS data structure."""
        return {
            "zones": [
                {
                    "id": "example.com.",
                    "name": "example.com.",
                    "kind": "Native",
                    "account": "",
                    "dnssec": False,
                    "api_rectify": False,
                    "serial": 2024122001,
                    "notified_serial": 2024122001,
                    "edited_serial": 2024122001,
                    "masters": [],
                    "nameservers": ["ns1.managed.prism.local.", "ns2.managed.prism.local."],
                    "rrsets": [
                        {
                            "name": "example.com.",
                            "type": "SOA",
                            "ttl": 3600,
                            "records": [
                                {
                                    "content": "ns1.managed.prism.local. admin.example.com. 2024122001 3600 600 86400 3600",
                                    "disabled": False,
                                }
                            ],
                        },
                        {
                            "name": "example.com.",
                            "type": "NS",
                            "ttl": 86400,
                            "records": [
                                {"content": "ns1.managed.prism.local.", "disabled": False},
                                {"content": "ns2.managed.prism.local.", "disabled": False},
                            ],
                        },
                    ],
                }
            ]
        }

    async def migrate_zones(self, mock_data: Dict[str, Any], mode: str = "merge") -> Dict[str, Any]:
        """
        Migrate zones from mock data to PowerDNS.

        Args:
            mock_data: Mock DNS data structure
            mode: Migration mode ('merge', 'replace', 'skip')

        Returns:
            Migration result summary
        """
        zones = mock_data.get("zones", [])

        async with PowerDNSClient(self.powerdns_url, self.api_key) as client:
            for zone_data in zones:
                await self._migrate_zone(client, zone_data, mode)

        return self._get_migration_summary()

    async def _migrate_zone(self, client: PowerDNSClient, zone_data: Dict[str, Any], mode: str):
        """Migrate a single zone."""
        zone_name = zone_data.get("name", "")
        if not zone_name:
            self.logger.warning("Zone missing name, skipping")
            self.stats["zones_skipped"] += 1
            return

        self.stats["zones_processed"] += 1
        self.logger.info(f"Processing zone: {zone_name}")

        try:
            # Check if zone exists
            existing_zone = None
            try:
                existing_zone = await client.get_zone_details(zone_name)
            except PowerDNSError:
                pass  # Zone doesn't exist

            if existing_zone:
                if mode == "skip":
                    self.logger.info(f"Zone {zone_name} exists, skipping (mode: skip)")
                    self.stats["zones_skipped"] += 1
                    return
                elif mode == "replace":
                    self.logger.info(f"Zone {zone_name} exists, deleting for replacement")
                    if not self.dry_run:
                        await client.delete_zone(zone_name)
                    existing_zone = None

            # Create or update zone
            if not existing_zone:
                # Create new zone
                self.logger.info(f"Creating zone: {zone_name}")
                if not self.dry_run:
                    zone_config = {
                        "name": zone_name,
                        "kind": zone_data.get("kind", "Native"),
                        "nameservers": zone_data.get("nameservers", []),
                    }
                    await client.create_zone(zone_config)
                self.stats["zones_created"] += 1
            else:
                self.logger.info(f"Updating zone: {zone_name}")
                self.stats["zones_updated"] += 1

            # Migrate records
            rrsets = zone_data.get("rrsets", [])
            for rrset in rrsets:
                await self._migrate_record_set(client, zone_name, rrset)

        except Exception as e:
            error_msg = f"Failed to migrate zone {zone_name}: {e}"
            self.logger.error(error_msg)
            self.stats["errors"].append(error_msg)

    async def _migrate_record_set(
        self, client: PowerDNSClient, zone_name: str, rrset: Dict[str, Any]
    ):
        """Migrate a single record set."""
        name = rrset.get("name", "")
        record_type = rrset.get("type", "")
        records = rrset.get("records", [])
        ttl = rrset.get("ttl", 300)

        if not name or not record_type or not records:
            self.logger.warning(f"Invalid record set in {zone_name}, skipping: {rrset}")
            return

        self.stats["records_processed"] += 1

        try:
            # Skip SOA and NS records for zone apex - they're handled by zone creation
            if name == zone_name and record_type in ["SOA", "NS"]:
                self.logger.debug(f"Skipping {record_type} record for zone apex")
                return

            # Convert records to PowerDNS format
            powerdns_records = []
            for record in records:
                if isinstance(record, dict):
                    content = record.get("content", "")
                    disabled = record.get("disabled", False)
                else:
                    content = str(record)
                    disabled = False

                if content:
                    powerdns_records.append({"content": content, "disabled": disabled})

            if powerdns_records:
                self.logger.info(f"Creating/updating record: {name} {record_type}")
                if not self.dry_run:
                    await client.create_or_update_record(
                        zone_name=zone_name,
                        name=name,
                        record_type=record_type,
                        records=powerdns_records,
                        ttl=ttl,
                    )
                self.stats["records_created"] += 1

        except Exception as e:
            error_msg = f"Failed to migrate record {name}/{record_type} in {zone_name}: {e}"
            self.logger.error(error_msg)
            self.stats["errors"].append(error_msg)

    def _get_migration_summary(self) -> Dict[str, Any]:
        """Generate migration summary report."""
        return {
            "status": "completed" if not self.stats["errors"] else "completed_with_errors",
            "dry_run": self.dry_run,
            "statistics": self.stats,
            "summary": {
                "zones": {
                    "processed": self.stats["zones_processed"],
                    "created": self.stats["zones_created"],
                    "updated": self.stats["zones_updated"],
                    "skipped": self.stats["zones_skipped"],
                },
                "records": {
                    "processed": self.stats["records_processed"],
                    "created": self.stats["records_created"],
                    "updated": self.stats["records_updated"],
                },
                "errors": len(self.stats["errors"]),
            },
        }


def setup_logging(level: str = "INFO"):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("/tmp/dns-migration.log")],
    )


async def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description="Migrate DNS data from mock service to PowerDNS")
    parser.add_argument("--powerdns-url", required=True, help="PowerDNS API URL")
    parser.add_argument("--api-key", required=True, help="PowerDNS API key")
    parser.add_argument(
        "--data-source",
        default="default",
        help="Data source (file:/path/to/file.json, localStorage:data, or 'default')",
    )
    parser.add_argument(
        "--mode", choices=["merge", "replace", "skip"], default="merge", help="Migration mode"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    try:
        # Initialize migrator
        migrator = DNSMigrator(args.powerdns_url, args.api_key, args.dry_run)

        # Load mock data
        logger.info(f"Loading DNS data from: {args.data_source}")
        mock_data = migrator.load_mock_data(args.data_source)

        # Perform migration
        logger.info(f"Starting migration (mode: {args.mode}, dry_run: {args.dry_run})")
        result = await migrator.migrate_zones(mock_data, args.mode)

        # Print results
        print("\n" + "=" * 60)
        print("DNS MIGRATION COMPLETED")
        print("=" * 60)
        print(f"Status: {result['status']}")
        print(f"Dry Run: {result['dry_run']}")
        print("\nSummary:")
        print(
            f"  Zones - Processed: {result['summary']['zones']['processed']}, "
            f"Created: {result['summary']['zones']['created']}, "
            f"Updated: {result['summary']['zones']['updated']}, "
            f"Skipped: {result['summary']['zones']['skipped']}"
        )
        print(
            f"  Records - Processed: {result['summary']['records']['processed']}, "
            f"Created: {result['summary']['records']['created']}"
        )
        print(f"  Errors: {result['summary']['errors']}")

        if result["statistics"]["errors"]:
            print("\nErrors:")
            for error in result["statistics"]["errors"]:
                print(f"  - {error}")

        # Exit with appropriate code
        sys.exit(0 if result["status"] == "completed" else 1)

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
