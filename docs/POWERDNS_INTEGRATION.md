# PowerDNS Integration Guide (SCRUM-49)

This document describes how Prism DNS Server integrates with PowerDNS to automatically manage DNS records for registered hosts.

## Overview

When a host registers with the Prism DNS server, it can automatically create and manage DNS records in PowerDNS. This integration enables:

- Automatic A/AAAA record creation for registered hosts
- DNS record updates when host IPs change
- Cleanup of DNS records for removed hosts
- Monitoring and metrics for DNS operations

## Configuration

### Enable PowerDNS Integration

Add the following configuration to your `server.yaml`:

```yaml
powerdns:
  enabled: true
  api_url: "http://powerdns:8053/api/v1"
  api_key: "your-powerdns-api-key"
  default_zone: "managed.prism.local."
  default_ttl: 300
  timeout: 5
  retry_attempts: 3
  retry_delay: 1
  record_types:
    - A
    - AAAA
  auto_ptr: false
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `enabled` | Enable/disable PowerDNS integration | `false` |
| `api_url` | PowerDNS API endpoint URL | `"http://powerdns:8053/api/v1"` |
| `api_key` | API key for PowerDNS authentication | `""` |
| `default_zone` | Default DNS zone for records | `"managed.prism.local."` |
| `default_ttl` | Default TTL for DNS records (seconds) | `300` |
| `timeout` | API request timeout (seconds) | `5` |
| `retry_attempts` | Number of retry attempts for failed requests | `3` |
| `retry_delay` | Delay between retries (seconds) | `1` |
| `record_types` | Supported DNS record types | `["A", "AAAA"]` |
| `auto_ptr` | Automatically create PTR records | `false` |

### Environment Variables

You can override configuration using environment variables:

- `PRISM_POWERDNS_ENABLED` - Enable/disable integration
- `PRISM_POWERDNS_API_URL` - PowerDNS API URL
- `PRISM_POWERDNS_API_KEY` - API authentication key
- `PRISM_POWERDNS_DEFAULT_ZONE` - Default DNS zone
- `PRISM_POWERDNS_DEFAULT_TTL` - Default record TTL

## How It Works

### Registration Flow

1. **Host Registration**: When a client registers with Prism:
   ```
   Client → TCP (8080) → Prism Server → Database
                                      ↓
                                   PowerDNS API
   ```

2. **DNS Record Creation**: If PowerDNS is enabled:
   - Prism creates an A record (IPv4) or AAAA record (IPv6)
   - The FQDN is `{hostname}.{default_zone}`
   - Records are created with the configured TTL

3. **Database Tracking**: DNS sync status is tracked in the database:
   - `dns_zone`: The DNS zone used
   - `dns_record_id`: The FQDN of the record
   - `dns_ttl`: Custom TTL if specified
   - `dns_sync_status`: `pending`, `synced`, or `failed`
   - `dns_last_sync`: Timestamp of last successful sync

### IP Address Changes

When a host's IP address changes:
1. The registration processor detects the change
2. PowerDNS record is updated automatically
3. Database sync status is updated

### Error Handling

If DNS operations fail:
- The host registration still succeeds
- DNS sync status is marked as `failed`
- Errors are logged and metrics are recorded
- Manual sync can be triggered later

## Database Schema

The following columns are added to the `hosts` table:

```sql
ALTER TABLE hosts ADD COLUMN dns_zone VARCHAR(255);
ALTER TABLE hosts ADD COLUMN dns_record_id VARCHAR(255);
ALTER TABLE hosts ADD COLUMN dns_ttl INTEGER;
ALTER TABLE hosts ADD COLUMN dns_sync_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE hosts ADD COLUMN dns_last_sync TIMESTAMP;
```

## API Integration

### PowerDNS Client

The `PowerDNSClient` class provides methods for DNS operations:

```python
from server.dns_manager import PowerDNSClient

# Create client
client = PowerDNSClient(config)

# Create A record
await client.create_a_record("host1", "192.168.1.100")

# Create AAAA record
await client.create_aaaa_record("host1", "2001:db8::1")

# Delete record
await client.delete_record("host1", "A")

# Check if zone exists
exists = await client.zone_exists("example.com.")
```

### Connection Handler Integration

The connection handler automatically manages DNS records:

```python
# In connection_handler.py
if self.dns_client and result.result_type in ["new_registration", "ip_change"]:
    await self._handle_dns_registration(hostname, ip_address, result)
```

## Monitoring

### Prometheus Metrics

The following metrics are available for monitoring:

#### API Request Metrics
- `prism_powerdns_api_requests_total` - Total API requests by method, endpoint, and status
- `prism_powerdns_api_request_duration_seconds` - API request duration histogram

#### Record Operation Metrics
- `prism_powerdns_record_operations_total` - Record operations by type and status
- `prism_powerdns_zone_operations_total` - Zone operations by type and status

#### Sync Status Metrics
- `prism_dns_sync_status` - Hosts by sync status (pending, synced, failed)

### Example Queries

```promql
# DNS operation success rate
rate(prism_powerdns_record_operations_total{status="success"}[5m]) /
rate(prism_powerdns_record_operations_total[5m])

# Average API request duration
rate(prism_powerdns_api_request_duration_seconds_sum[5m]) /
rate(prism_powerdns_api_request_duration_seconds_count[5m])

# Hosts pending DNS sync
prism_dns_sync_status{status="pending"}
```

## Deployment

### Docker Compose

Example configuration with PowerDNS:

```yaml
services:
  prism-server:
    image: prism-dns:latest
    environment:
      - PRISM_POWERDNS_ENABLED=true
      - PRISM_POWERDNS_API_KEY=${PDNS_API_KEY}
    depends_on:
      - powerdns

  powerdns:
    image: powerdns/pdns-auth:latest
    environment:
      - PDNS_API_KEY=${PDNS_API_KEY}
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "8053:8053"
```

### Production Considerations

1. **API Security**:
   - Use strong API keys
   - Restrict PowerDNS API access to Prism server only
   - Use HTTPS for API communication if possible

2. **Zone Configuration**:
   - Pre-create DNS zones in PowerDNS
   - Configure appropriate SOA and NS records
   - Set up DNSSEC if required

3. **Performance**:
   - DNS operations are asynchronous
   - Failed operations don't block registrations
   - Retry logic handles temporary failures

4. **Monitoring**:
   - Monitor DNS sync failure rates
   - Alert on high failure counts
   - Track API response times

## Troubleshooting

### Common Issues

1. **DNS records not created**:
   - Check PowerDNS is enabled in config
   - Verify API key is correct
   - Ensure zone exists in PowerDNS
   - Check network connectivity

2. **Authentication failures**:
   - Verify API key matches PowerDNS config
   - Check X-API-Key header is sent

3. **Zone not found**:
   - Pre-create zones in PowerDNS
   - Ensure zone name ends with dot (.)

### Debug Commands

```bash
# Check DNS sync status
sqlite3 /data/prism.db "SELECT hostname, dns_sync_status FROM hosts;"

# Test PowerDNS API
curl -H "X-API-Key: your-api-key" http://powerdns:8053/api/v1/servers/localhost/zones

# Query DNS record
dig @powerdns-host hostname.managed.prism.local
```

### Logs

Check logs for DNS operations:
```bash
docker compose logs prism-server | grep -i dns
docker compose logs prism-server | grep -i powerdns
```

## Migration

### Enable for Existing Hosts

To enable DNS for existing hosts:

1. Run database migration to add DNS columns
2. Use bulk sync tool (if available)
3. Or wait for next heartbeat to trigger sync

### Disable Integration

To disable PowerDNS integration:

1. Set `powerdns.enabled: false` in config
2. Existing DNS records remain in PowerDNS
3. No new records will be created/updated

## Future Enhancements

- PTR record support
- DNSSEC integration
- Multi-zone support per host
- Bulk DNS operations
- DNS record templates
- Custom record types (CNAME, MX, etc.)