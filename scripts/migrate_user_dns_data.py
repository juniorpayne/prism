#!/usr/bin/env python3
"""
Migrate existing DNS data to user ownership (SCRUM-134).

Simple migration script following KISS principles:
- Creates ownership records in OUR database only (does NOT modify PowerDNS)
- Maps zones to users based on patterns
- Handles hosts with missing created_by
- Generates JSON report
- Supports dry-run mode
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
import requests
import os

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from server.database.connection import DatabaseManager
from server.database.dns_operations import DNSZoneOwnershipOperations
from sqlalchemy import text

# System user ID for orphaned data
SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"


def get_powerdns_zones():
    """Get list of zones from PowerDNS API (read-only)."""
    powerdns_api_url = os.getenv('POWERDNS_API_URL', 'http://powerdns-server:8053/api/v1')
    powerdns_api_key = os.getenv('POWERDNS_API_KEY', 'changeme')
    
    try:
        response = requests.get(
            f"{powerdns_api_url}/servers/localhost/zones",
            headers={"X-API-Key": powerdns_api_key},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Warning: Could not fetch zones from PowerDNS: {e}")
        print("Continuing with empty zone list...")
        return []


def analyze_zone_ownership(zone_name, users):
    """
    Determine which user should own a zone based on simple patterns.
    
    Rules:
    1. If zone contains username -> assign to that user
    2. If zone contains email domain -> assign to that user
    3. Otherwise -> orphaned (system user)
    """
    zone_lower = zone_name.lower().rstrip('.')
    
    for user in users:
        # Check username in zone
        if user['username'].lower() in zone_lower:
            return user['id'], f"username '{user['username']}' in zone name"
        
        # Check email domain
        email_domain = user['email'].split('@')[1].lower()
        if email_domain in zone_lower:
            return user['id'], f"email domain '{email_domain}' in zone name"
    
    return None, "no pattern match"


def migrate_zones(db_manager, dry_run=True):
    """
    Create ownership records for DNS zones in our database.
    This does NOT modify PowerDNS - only creates records in our dns_zone_ownership table.
    """
    print("\n=== Creating Zone Ownership Records ===")
    print("(This only modifies our application database, not PowerDNS)")
    
    stats = {
        "total_zones": 0,
        "assigned_zones": 0,
        "orphaned_zones": 0,
        "already_assigned": 0,
        "errors": 0,
        "assignments": []
    }
    
    try:
        # Get all active users from our database
        with db_manager.get_session() as session:
            result = session.execute(text("""
                SELECT id, username, email 
                FROM users 
                WHERE is_active = 1
            """))
            users = [{"id": str(row[0]), "username": row[1], "email": row[2]} 
                    for row in result.fetchall()]
        
        print(f"Found {len(users)} active users")
        
        # Get DNS zone operations helper
        dns_zone_ops = DNSZoneOwnershipOperations(db_manager)
        
        # Get all zones from PowerDNS (read-only)
        zones = get_powerdns_zones()
        stats["total_zones"] = len(zones)
        print(f"Found {len(zones)} DNS zones in PowerDNS")
        
        # Check which zones already have ownership records in our database
        existing_zones = set()
        with db_manager.get_session() as session:
            result = session.execute(text("SELECT zone_name FROM dns_zone_ownership"))
            existing_zones = {row[0] for row in result.fetchall()}
        
        print(f"Found {len(existing_zones)} zones already with ownership records")
        
        # Process each zone
        for zone in zones:
            zone_name = zone.get("name", "")
            
            # Skip if already has ownership record
            if zone_name in existing_zones:
                stats["already_assigned"] += 1
                continue
            
            # Determine owner based on patterns
            owner_id, reason = analyze_zone_ownership(zone_name, users)
            
            if not owner_id:
                owner_id = SYSTEM_USER_ID
                stats["orphaned_zones"] += 1
                assignment_type = "orphaned"
            else:
                stats["assigned_zones"] += 1
                assignment_type = "assigned"
            
            # Record assignment
            assignment = {
                "zone": zone_name,
                "assigned_to": owner_id,
                "type": assignment_type,
                "reason": reason
            }
            stats["assignments"].append(assignment)
            
            # Create ownership record if not dry run
            if not dry_run:
                try:
                    dns_zone_ops.create_zone_ownership(zone_name, owner_id)
                    print(f"  ✓ {zone_name} -> {assignment_type} ({reason})")
                except Exception as e:
                    print(f"  ✗ {zone_name} -> ERROR: {e}")
                    stats["errors"] += 1
            else:
                print(f"  [DRY RUN] {zone_name} -> {assignment_type} ({reason})")
    
    except Exception as e:
        print(f"Error during zone migration: {e}")
        stats["errors"] += 1
    
    return stats


def migrate_hosts(db_manager, dry_run=True):
    """
    Update hosts table to ensure created_by is set.
    This only modifies our application database.
    """
    print("\n=== Updating Host Records ===")
    print("(Setting created_by for hosts without an owner)")
    
    stats = {
        "total_hosts": 0,
        "null_created_by": 0,
        "updated_hosts": 0,
        "already_assigned": 0
    }
    
    try:
        with db_manager.get_session() as session:
            # Count total hosts
            result = session.execute(text("SELECT COUNT(*) FROM hosts"))
            stats["total_hosts"] = result.scalar() or 0
            
            # Count hosts with created_by set
            result = session.execute(text("SELECT COUNT(*) FROM hosts WHERE created_by IS NOT NULL"))
            stats["already_assigned"] = result.scalar() or 0
            
            # Count hosts without created_by
            result = session.execute(text("SELECT COUNT(*) FROM hosts WHERE created_by IS NULL"))
            stats["null_created_by"] = result.scalar() or 0
            
            print(f"Total hosts: {stats['total_hosts']}")
            print(f"Already assigned: {stats['already_assigned']}")
            print(f"Need assignment: {stats['null_created_by']}")
            
            if stats["null_created_by"] > 0 and not dry_run:
                # Update all NULL created_by to system user
                session.execute(text("""
                    UPDATE hosts 
                    SET created_by = :system_user_id 
                    WHERE created_by IS NULL
                """), {"system_user_id": SYSTEM_USER_ID})
                
                stats["updated_hosts"] = stats["null_created_by"]
                print(f"  ✓ Updated {stats['updated_hosts']} hosts to system user")
            elif stats["null_created_by"] > 0:
                print(f"  [DRY RUN] Would update {stats['null_created_by']} hosts to system user")
    
    except Exception as e:
        print(f"Error during host migration: {e}")
    
    return stats


def generate_report(zone_stats, host_stats, dry_run):
    """Generate migration report."""
    report = {
        "migration_date": datetime.utcnow().isoformat(),
        "mode": "dry_run" if dry_run else "applied",
        "database_changes_only": True,
        "powerdns_modified": False,
        "summary": {
            "total_changes": zone_stats["assigned_zones"] + zone_stats["orphaned_zones"] + host_stats.get("updated_hosts", 0),
            "zones": {
                "total": zone_stats["total_zones"],
                "assigned": zone_stats["assigned_zones"],
                "orphaned": zone_stats["orphaned_zones"],
                "already_assigned": zone_stats["already_assigned"],
                "errors": zone_stats["errors"]
            },
            "hosts": {
                "total": host_stats["total_hosts"],
                "updated": host_stats.get("updated_hosts", 0),
                "already_assigned": host_stats["already_assigned"]
            }
        },
        "zone_assignments": zone_stats["assignments"]
    }
    
    # Save to file in data directory (where we have write permissions)
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    filename = f"migration_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = data_dir / filename
    
    with open(filepath, 'w') as f:
        json.dump(report, f, indent=2)
    
    return str(filepath)


def main():
    parser = argparse.ArgumentParser(
        description="Create user ownership records for existing DNS data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script creates ownership records in the application database.
It does NOT modify PowerDNS zones or records.

Examples:
  # Preview changes without applying
  python migrate_user_dns_data.py --dry-run
  
  # Apply changes
  python migrate_user_dns_data.py --confirm
  
  # Use custom database
  python migrate_user_dns_data.py --db-path /custom/path/prism.db --dry-run
"""
    )
    
    parser.add_argument("--dry-run", action="store_true", 
                      help="Preview changes without applying")
    parser.add_argument("--confirm", action="store_true", 
                      help="Confirm and apply changes")
    parser.add_argument("--db-path", default="data/prism.db",
                      help="Path to database file (default: data/prism.db)")
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.confirm:
        print("ERROR: Use --dry-run to preview or --confirm to apply changes")
        return 1
    
    # Initialize database
    config = {
        'database': {
            'path': args.db_path,
            'pool_size': 5,
            'echo': False
        }
    }
    
    try:
        db_manager = DatabaseManager(config)
        db_manager.initialize_schema()
        
        print(f"=== DNS Data User Assignment Migration ===")
        print(f"Mode: {'DRY RUN' if args.dry_run else 'APPLYING CHANGES'}")
        print(f"Database: {args.db_path}")
        print("\nNOTE: This script only modifies the application database.")
        print("      PowerDNS zones and records are NOT modified.")
        
        # Run migrations
        zone_stats = migrate_zones(db_manager, dry_run=args.dry_run)
        host_stats = migrate_hosts(db_manager, dry_run=args.dry_run)
        
        # Generate report
        report_file = generate_report(zone_stats, host_stats, args.dry_run)
        
        # Print summary
        print("\n=== Migration Summary ===")
        print(f"DNS Zone Ownership Records:")
        print(f"  - Total zones found: {zone_stats['total_zones']}")
        print(f"  - Assigned to users: {zone_stats['assigned_zones']}")
        print(f"  - Orphaned (system): {zone_stats['orphaned_zones']}")
        print(f"  - Already assigned: {zone_stats['already_assigned']}")
        print(f"  - Errors: {zone_stats['errors']}")
        
        print(f"\nHost Records:")
        print(f"  - Total hosts: {host_stats['total_hosts']}")
        print(f"  - Updated: {host_stats.get('updated_hosts', 0)}")
        print(f"  - Already assigned: {host_stats['already_assigned']}")
        
        print(f"\nReport saved to: {report_file}")
        
        if args.dry_run:
            print("\n⚠️  This was a DRY RUN. No changes were made.")
            print("    Use --confirm to apply changes.")
        else:
            print("\n✅ Migration completed successfully!")
            print("    Only application database was modified.")
            print("    PowerDNS remains unchanged.")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())