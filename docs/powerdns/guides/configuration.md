# PowerDNS Configuration Reference

Complete configuration reference for PowerDNS integration with Prism DNS.

## Configuration Overview

PowerDNS configuration can be provided through:
1. Environment variables (highest priority)
2. Configuration files (YAML/JSON)
3. Default values

## Core Configuration

### PowerDNS Connection Settings

```yaml
powerdns:
  # Enable/disable PowerDNS integration
  enabled: true
  
  # PowerDNS API endpoint
  api_url: "http://localhost:8053/api/v1"
  
  # API authentication key
  api_key: "your-secure-api-key"
  
  # Default DNS zone for host records
  default_zone: "managed.prism.local."
  
  # Default TTL for DNS records (seconds)
  default_ttl: 300
  
  # API request timeout (seconds)
  timeout: 10
  
  # Number of retry attempts for failed requests
  retry_attempts: 3
  
  # Delay between retries (seconds)
  retry_delay: 1
  
  # Record types to manage
  record_types: ["A", "AAAA"]
  
  # Enable automatic PTR record creation
  auto_ptr: false
  
  # Connection pool settings
  connection_pool:
    size: 10
    max_overflow: 20
    timeout: 30
```

### Environment Variables

All configuration options can be set via environment variables:

```bash
# Core settings
POWERDNS_ENABLED=true
POWERDNS_API_URL=http://powerdns:8053/api/v1
POWERDNS_API_KEY=your-secure-api-key
POWERDNS_DEFAULT_ZONE=managed.prism.local.
POWERDNS_DEFAULT_TTL=300

# Connection settings
POWERDNS_TIMEOUT=10
POWERDNS_RETRY_ATTEMPTS=3
POWERDNS_RETRY_DELAY=1

# Advanced settings
POWERDNS_AUTO_PTR=false
POWERDNS_CONNECTION_POOL_SIZE=10
POWERDNS_CONNECTION_POOL_MAX_OVERFLOW=20
```

## PowerDNS Server Configuration

### Docker Deployment

```yaml
# docker-compose.powerdns.yml
services:
  powerdns:
    image: powerdns/pdns-auth-48:latest
    environment:
      # Database backend
      PDNS_BACKEND: gpgsql
      PDNS_GPGSQL_HOST: postgres
      PDNS_GPGSQL_PORT: 5432
      PDNS_GPGSQL_DBNAME: powerdns
      PDNS_GPGSQL_USER: powerdns
      PDNS_GPGSQL_PASSWORD: ${POSTGRES_PASSWORD}
      
      # API configuration
      PDNS_API: yes
      PDNS_API_KEY: ${PDNS_API_KEY}
      PDNS_WEBSERVER: yes
      PDNS_WEBSERVER_ADDRESS: 0.0.0.0
      PDNS_WEBSERVER_PORT: 8053
      PDNS_WEBSERVER_ALLOW_FROM: 0.0.0.0/0
      
      # DNS settings
      PDNS_DEFAULT_TTL: 300
      PDNS_QUERY_CACHE_TTL: 20
      PDNS_CACHE_TTL: 60
      PDNS_NEGQUERY_CACHE_TTL: 60
      
      # Performance tuning
      PDNS_RECEIVER_THREADS: 4
      PDNS_DISTRIBUTOR_THREADS: 4
      PDNS_SIGNING_THREADS: 4
      
      # Security
      PDNS_DISABLE_AXFR: no
      PDNS_ALLOW_AXFR_IPS: 127.0.0.1,::1
      PDNS_ONLY_NOTIFY: 0.0.0.0/0
```

### Native Configuration File

```conf
# /etc/powerdns/pdns.conf
# Backend configuration
launch=gpgsql
gpgsql-host=localhost
gpgsql-port=5432
gpgsql-dbname=powerdns
gpgsql-user=powerdns
gpgsql-password=secure-password

# API configuration
api=yes
api-key=your-secure-api-key
webserver=yes
webserver-address=0.0.0.0
webserver-port=8053
webserver-allow-from=127.0.0.1,::1,10.0.0.0/8

# DNS server settings
local-address=0.0.0.0:53
local-ipv6=::
default-ttl=300
query-cache-ttl=20
cache-ttl=60
negquery-cache-ttl=60

# Performance settings
receiver-threads=4
distributor-threads=4
signing-threads=4
max-cache-entries=1000000
max-packet-cache-entries=1000000

# Security settings
disable-axfr=no
allow-axfr-ips=127.0.0.1,::1
only-notify=0.0.0.0/0

# Logging
log-dns-queries=no
log-dns-details=no
loglevel=4
```

## Zone Configuration

### Default Zone Setup

```python
# In your initialization code
from server.dns_manager import create_dns_client

async def setup_default_zone():
    dns_client = create_dns_client(config)
    async with dns_client:
        # Create default zone if it doesn't exist
        zone = config["powerdns"]["default_zone"]
        if not await dns_client.zone_exists(zone):
            await dns_client.create_zone(
                zone,
                nameservers=[
                    "ns1.prism.local.",
                    "ns2.prism.local."
                ],
                soa_edit="INCEPTION-INCREMENT"
            )
```

### Zone Configuration Options

```yaml
zones:
  managed.prism.local.:
    # Zone type (Native, Master, Slave)
    kind: "Native"
    
    # Start of Authority (SOA) record
    soa:
      primary_ns: "ns1.prism.local."
      contact: "admin.prism.local."
      serial: 2024010101
      refresh: 10800
      retry: 3600
      expire: 604800
      minimum: 3600
    
    # Nameservers
    nameservers:
      - "ns1.prism.local."
      - "ns2.prism.local."
    
    # SOA-EDIT setting for automatic serial updates
    soa_edit: "INCEPTION-INCREMENT"
    
    # Zone metadata
    metadata:
      allow_axfr_from: ["127.0.0.1", "::1"]
      axfr_source: "127.0.0.1"
```

## Integration Settings

### Host Registration Behavior

```yaml
registration:
  # Automatically create DNS records on host registration
  auto_create_dns: true
  
  # Update DNS on IP changes
  auto_update_dns: true
  
  # Delete DNS records when host is removed
  auto_delete_dns: true
  
  # DNS sync retry settings
  dns_sync:
    max_retries: 3
    retry_delay: 5
    backoff_factor: 2
```

### Monitoring Configuration

```yaml
monitoring:
  # Enable Prometheus metrics for DNS operations
  metrics_enabled: true
  
  # Metric labels
  metric_labels:
    - operation
    - record_type
    - status
  
  # DNS health check settings
  health_check:
    enabled: true
    interval: 30
    timeout: 5
    test_hostname: "_health-check"
```

## Security Configuration

### API Security

```yaml
security:
  # API key rotation
  api_key_rotation:
    enabled: true
    interval_days: 90
    notify_days_before: 7
  
  # IP allowlisting for API access
  api_allowlist:
    enabled: true
    allowed_ips:
      - "127.0.0.1"
      - "10.0.0.0/8"
      - "172.16.0.0/12"
  
  # Rate limiting
  rate_limiting:
    enabled: true
    requests_per_minute: 1000
    burst_size: 100
```

### DNS Security

```yaml
dns_security:
  # DNSSEC settings
  dnssec:
    enabled: false
    algorithm: "ECDSAP256SHA256"
    ksk_bits: 256
    zsk_bits: 256
  
  # Query access control
  query_acl:
    allow_from:
      - "0.0.0.0/0"
    deny_from:
      - "192.168.100.0/24"
  
  # Response rate limiting
  response_rate_limit:
    enabled: true
    responses_per_second: 100
    window: 15
```

## Performance Tuning

### Connection Pool Optimization

```yaml
performance:
  # Connection pool settings
  connection_pool:
    # Minimum connections to maintain
    min_size: 5
    
    # Maximum connections allowed
    max_size: 20
    
    # Maximum overflow connections
    max_overflow: 10
    
    # Connection timeout (seconds)
    timeout: 30
    
    # Idle connection timeout
    idle_timeout: 300
    
    # Connection recycle time
    recycle: 3600
```

### Caching Configuration

```yaml
caching:
  # Local record cache
  record_cache:
    enabled: true
    max_entries: 10000
    ttl: 60
  
  # Zone cache
  zone_cache:
    enabled: true
    max_entries: 100
    ttl: 300
  
  # Negative cache (for non-existent records)
  negative_cache:
    enabled: true
    ttl: 30
```

## High Availability Configuration

### Multi-Master Setup

```yaml
high_availability:
  # Enable HA mode
  enabled: true
  
  # PowerDNS endpoints
  endpoints:
    - url: "http://powerdns1:8053/api/v1"
      priority: 1
      weight: 100
    - url: "http://powerdns2:8053/api/v1"
      priority: 2
      weight: 100
    - url: "http://powerdns3:8053/api/v1"
      priority: 3
      weight: 100
  
  # Health check settings
  health_check:
    interval: 10
    timeout: 5
    unhealthy_threshold: 3
    healthy_threshold: 2
  
  # Failover behavior
  failover:
    strategy: "round_robin"  # or "priority", "random"
    retry_failed: true
    retry_interval: 60
```

## Logging Configuration

```yaml
logging:
  # DNS operation logging
  dns_operations:
    enabled: true
    level: "INFO"
    include_details: true
    
  # Audit logging
  audit:
    enabled: true
    log_creates: true
    log_updates: true
    log_deletes: true
    log_reads: false
    
  # Performance logging
  performance:
    enabled: true
    slow_query_threshold: 1.0  # seconds
    log_slow_queries: true
```

## Example Complete Configuration

```yaml
# config.yaml - Complete Prism configuration with PowerDNS
server:
  host: "0.0.0.0"
  tcp_port: 8080
  api_port: 8081

database:
  path: "/data/prism.db"
  connection_pool_size: 10

powerdns:
  enabled: true
  api_url: "http://powerdns:8053/api/v1"
  api_key: "${PDNS_API_KEY}"
  default_zone: "managed.prism.local."
  default_ttl: 300
  timeout: 10
  retry_attempts: 3
  retry_delay: 1
  record_types: ["A", "AAAA"]
  auto_ptr: false
  connection_pool:
    size: 10
    max_overflow: 20
    timeout: 30

registration:
  auto_create_dns: true
  auto_update_dns: true
  auto_delete_dns: true
  dns_sync:
    max_retries: 3
    retry_delay: 5

monitoring:
  metrics_enabled: true
  health_check:
    enabled: true
    interval: 30

security:
  api_allowlist:
    enabled: true
    allowed_ips: ["127.0.0.1", "10.0.0.0/8"]
  rate_limiting:
    enabled: true
    requests_per_minute: 1000

logging:
  level: "INFO"
  dns_operations:
    enabled: true
    include_details: true
```

## Configuration Validation

Use the included validation script to check your configuration:

```bash
# Validate configuration file
python -m server.config_validator --config config.yaml

# Test PowerDNS connectivity
python -m server.dns_manager --test-connection

# Verify zone configuration
python -m server.dns_manager --verify-zones
```

## Best Practices

1. **Security**
   - Always use strong API keys
   - Enable IP allowlisting in production
   - Rotate API keys regularly
   - Use HTTPS for API connections

2. **Performance**
   - Tune connection pool based on load
   - Enable caching for read-heavy workloads
   - Monitor connection pool usage
   - Use connection recycling

3. **Reliability**
   - Configure appropriate timeouts
   - Enable retry logic with backoff
   - Set up health checks
   - Monitor error rates

4. **Maintenance**
   - Keep configuration in version control
   - Document all custom settings
   - Test configuration changes
   - Monitor for deprecated options