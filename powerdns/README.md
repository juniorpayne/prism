# PowerDNS Setup for Prism DNS

This directory contains the PowerDNS authoritative DNS server configuration for Prism DNS.

## Overview

PowerDNS provides the actual DNS resolution capabilities for the Prism DNS system. It integrates with the existing Prism server to automatically create DNS records for registered hosts.

## Port Configuration

- **Port 53 (UDP/TCP)**: DNS service port
- **Port 8053 (TCP)**: PowerDNS API (changed from default 8081 to avoid conflict with Prism API)

## Quick Start

### 1. Set Environment Variables

Create a `.env` file or export these variables:

```bash
export PDNS_API_KEY=your-secure-api-key
export PDNS_DB_PASSWORD=your-secure-db-password
export PDNS_DEFAULT_ZONE=managed.example.com
```

### 2. Start PowerDNS Stack

```bash
# Create external networks if they don't exist
docker network create prism-backend 2>/dev/null || true
docker network create prism-frontend 2>/dev/null || true

# Start PowerDNS
docker compose -f docker-compose.powerdns.yml up -d
```

### 3. Verify Installation

```bash
# Check if PowerDNS is running
docker compose -f docker-compose.powerdns.yml ps

# Test DNS resolution (after creating a zone)
dig @localhost -p 53 test.managed.example.com

# Test API access
curl -H "X-API-Key: ${PDNS_API_KEY}" http://localhost:8053/api/v1/servers/localhost
```

## API Usage Examples

### Create a Zone

```bash
curl -X POST -H "X-API-Key: ${PDNS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "managed.example.com.",
    "kind": "Native",
    "nameservers": ["ns1.managed.example.com.", "ns2.managed.example.com."]
  }' \
  http://localhost:8053/api/v1/servers/localhost/zones
```

### Add an A Record

```bash
curl -X PATCH -H "X-API-Key: ${PDNS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "rrsets": [{
      "name": "test.managed.example.com.",
      "type": "A",
      "changetype": "REPLACE",
      "records": [{
        "content": "192.168.1.100",
        "disabled": false
      }]
    }]
  }' \
  http://localhost:8053/api/v1/servers/localhost/zones/managed.example.com.
```

## Configuration

### Environment Variables

- `PDNS_API_KEY`: API authentication key (required)
- `PDNS_DB_PASSWORD`: PostgreSQL password (required)
- `PDNS_DB_NAME`: Database name (default: powerdns)
- `PDNS_DB_USER`: Database user (default: powerdns)
- `PDNS_API_ALLOW_FROM`: IP ranges allowed to access API (default: local networks)
- `PDNS_DEFAULT_ZONE`: Default DNS zone (default: managed.prism.local)

### Performance Tuning

The configuration includes optimized settings for:
- 4 receiver threads
- 4 distributor threads
- 1M packet cache entries
- 2M general cache entries

Adjust these in `pdns.conf` based on your load requirements.

## Security Considerations

1. **API Security**:
   - Always use a strong API key
   - Restrict API access by IP (configured via PDNS_API_ALLOW_FROM)
   - Use HTTPS proxy in production

2. **DNS Security**:
   - AXFR (zone transfers) disabled by default
   - DNS updates restricted to localhost
   - DNSSEC can be enabled by modifying configuration

3. **Database Security**:
   - Use strong passwords
   - Database not exposed externally
   - Regular backups recommended

## Troubleshooting

### Check Logs

```bash
# PowerDNS logs
docker compose -f docker-compose.powerdns.yml logs powerdns

# Database logs
docker compose -f docker-compose.powerdns.yml logs powerdns-db
```

### Common Issues

1. **Port 53 Permission Denied**:
   - Requires NET_BIND_SERVICE capability (already configured)
   - May need to stop systemd-resolved: `sudo systemctl stop systemd-resolved`

2. **Database Connection Failed**:
   - Check database is healthy: `docker compose -f docker-compose.powerdns.yml ps`
   - Verify credentials match between services

3. **API Not Accessible**:
   - Verify API key is set
   - Check allowed IP ranges
   - Ensure port 8053 is not blocked

## Integration with Prism

The Prism server will be updated to automatically:
- Create A records when hosts register
- Update records when IPs change
- Remove records when hosts are deleted

This integration is implemented in SCRUM-49.