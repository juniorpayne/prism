# Archived Docker Compose Files

These Docker Compose files have been archived to prevent configuration conflicts and network isolation issues.

## Why These Files Were Archived

### Network Isolation Issues
- **docker-compose.powerdns-test.yml** - Created separate `powerdns-net` network
- **docker-compose.powerdns.yml** - Standalone PowerDNS configuration
- **docker-compose.test.yml** - Used different `test-network` and passwords

These files caused services to run on different networks, preventing communication between Prism and PowerDNS.

### Password/Configuration Conflicts
- Different files used different passwords (e.g., "changeme" vs "development-db-password")
- Inconsistent environment variables
- Different service names and configurations

## Correct Usage

**For Development:**
```bash
# Always use the main docker-compose.yml with profiles
docker compose --profile with-powerdns up -d
```

**For Production:**
```bash
# Use the production-specific file
docker compose -f docker-compose.production.yml up -d
```

## DO NOT USE These Files
These archived files should NOT be used as they will cause:
- Services unable to communicate (different networks)
- Authentication failures (wrong passwords)
- Inconsistent configurations
- Hard-to-debug issues

Last updated: 2025-07-23