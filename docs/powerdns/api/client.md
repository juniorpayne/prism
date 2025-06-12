# PowerDNS Client API Reference

## Overview

The PowerDNS Client provides an async Python interface for managing DNS records through the PowerDNS API.

## Installation

```python
from server.dns_manager import PowerDNSClient, create_dns_client
```

## Configuration

```python
config = {
    "powerdns": {
        "enabled": True,
        "api_url": "http://localhost:8053/api/v1",
        "api_key": "your-api-key",
        "default_zone": "example.com.",
        "default_ttl": 300,
        "timeout": 10,
        "retry_attempts": 3
    }
}

client = create_dns_client(config)
```

## Class: PowerDNSClient

### Constructor

```python
PowerDNSClient(config: Dict[str, Any])
```

Creates a new PowerDNS client instance.

**Parameters:**
- `config`: Configuration dictionary with PowerDNS settings

### Context Manager

```python
async with client:
    # Use client
    await client.create_a_record("host", "192.168.1.1")
```

## Methods

### create_a_record

```python
async def create_a_record(
    self,
    hostname: str,
    ip_address: str,
    zone: Optional[str] = None,
    ttl: Optional[int] = None
) -> Dict[str, Any]
```

Creates or updates an A record.

**Parameters:**
- `hostname`: The hostname (without domain)
- `ip_address`: IPv4 address
- `zone`: DNS zone (defaults to configured zone)
- `ttl`: Time to live in seconds

**Returns:**
```python
{
    "status": "success",
    "fqdn": "host.example.com.",
    "zone": "example.com.",
    "ttl": 300
}
```

**Example:**
```python
result = await client.create_a_record("web-server", "192.168.1.100")
```

### create_aaaa_record

```python
async def create_aaaa_record(
    self,
    hostname: str,
    ipv6_address: str,
    zone: Optional[str] = None,
    ttl: Optional[int] = None
) -> Dict[str, Any]
```

Creates or updates an AAAA record for IPv6.

**Parameters:**
- `hostname`: The hostname (without domain)
- `ipv6_address`: IPv6 address
- `zone`: DNS zone (defaults to configured zone)
- `ttl`: Time to live in seconds

**Example:**
```python
result = await client.create_aaaa_record("web-server", "2001:db8::1")
```

### update_record

```python
async def update_record(
    self,
    hostname: str,
    content: str,
    record_type: str = "A",
    zone: Optional[str] = None,
    ttl: Optional[int] = None
) -> Dict[str, Any]
```

Updates an existing DNS record.

**Parameters:**
- `hostname`: The hostname to update
- `content`: New record content (IP address)
- `record_type`: Type of record ("A" or "AAAA")
- `zone`: DNS zone
- `ttl`: Time to live

**Example:**
```python
result = await client.update_record("web-server", "192.168.1.101", "A")
```

### delete_record

```python
async def delete_record(
    self,
    hostname: str,
    record_type: str = "A",
    zone: Optional[str] = None
) -> Dict[str, Any]
```

Deletes a DNS record.

**Parameters:**
- `hostname`: The hostname to delete
- `record_type`: Type of record to delete
- `zone`: DNS zone

**Example:**
```python
result = await client.delete_record("old-server", "A")
```

### get_record

```python
async def get_record(
    self,
    hostname: str,
    record_type: str = "A",
    zone: Optional[str] = None
) -> Optional[Dict[str, Any]]
```

Retrieves a DNS record.

**Parameters:**
- `hostname`: The hostname to lookup
- `record_type`: Type of record to retrieve
- `zone`: DNS zone

**Returns:**
```python
{
    "name": "host.example.com.",
    "type": "A",
    "ttl": 300,
    "records": [
        {
            "content": "192.168.1.100",
            "disabled": False
        }
    ]
}
```

**Example:**
```python
record = await client.get_record("web-server", "A")
if record:
    print(f"IP: {record['records'][0]['content']}")
```

### zone_exists

```python
async def zone_exists(self, zone: str) -> bool
```

Checks if a DNS zone exists.

**Parameters:**
- `zone`: Zone name to check

**Example:**
```python
if await client.zone_exists("example.com."):
    print("Zone exists")
```

### create_zone

```python
async def create_zone(
    self,
    zone: str,
    nameservers: Optional[List[str]] = None,
    kind: str = "Native",
    soa_edit: str = "INCEPTION-INCREMENT"
) -> Dict[str, Any]
```

Creates a new DNS zone.

**Parameters:**
- `zone`: Zone name (must end with dot)
- `nameservers`: List of nameserver FQDNs
- `kind`: Zone type ("Native", "Master", "Slave")
- `soa_edit`: SOA serial update method

**Example:**
```python
result = await client.create_zone(
    "newzone.com.",
    nameservers=["ns1.example.com.", "ns2.example.com."]
)
```

## Error Handling

### Exception Classes

```python
# Base exception
class PowerDNSError(Exception):
    pass

# Connection errors
class PowerDNSConnectionError(PowerDNSError):
    pass

# API errors
class PowerDNSAPIError(PowerDNSError):
    def __init__(self, message: str, status_code: int, response_data: Dict):
        self.status_code = status_code
        self.response_data = response_data
```

### Error Handling Example

```python
from server.dns_manager import PowerDNSError, PowerDNSAPIError

try:
    await client.create_a_record("host", "192.168.1.1")
except PowerDNSAPIError as e:
    if e.status_code == 404:
        print("Zone not found")
    elif e.status_code == 422:
        print(f"Validation error: {e.response_data}")
except PowerDNSConnectionError as e:
    print(f"Connection failed: {e}")
except PowerDNSError as e:
    print(f"DNS operation failed: {e}")
```

## Advanced Usage

### Batch Operations

```python
# Create multiple records efficiently
hostnames = ["web1", "web2", "web3"]
tasks = []

for i, hostname in enumerate(hostnames):
    ip = f"192.168.1.{100 + i}"
    tasks.append(client.create_a_record(hostname, ip))

results = await asyncio.gather(*tasks, return_exceptions=True)

for hostname, result in zip(hostnames, results):
    if isinstance(result, Exception):
        print(f"Failed to create {hostname}: {result}")
    else:
        print(f"Created {hostname}")
```

### Custom TTL and Zones

```python
# Create record in specific zone with custom TTL
await client.create_a_record(
    "special-host",
    "10.0.0.100",
    zone="internal.company.com.",
    ttl=60  # 1 minute TTL for dynamic hosts
)
```

### Connection Pool Management

```python
# Configure connection pool
config = {
    "powerdns": {
        "connection_pool": {
            "size": 20,
            "max_overflow": 10,
            "timeout": 30
        }
    }
}

# The client manages the pool automatically
async with create_dns_client(config) as client:
    # Pool is created on first use
    await client.create_a_record("host1", "192.168.1.1")
    # Subsequent calls reuse connections
    await client.create_a_record("host2", "192.168.1.2")
# Pool is closed when context exits
```

### Retry Configuration

```python
config = {
    "powerdns": {
        "retry_attempts": 3,
        "retry_delay": 1,  # seconds
        "retry_backoff": 2  # exponential backoff factor
    }
}

# Automatic retry on transient failures
client = create_dns_client(config)
```

## Integration Examples

### With Prism Registration

```python
from server.dns_manager import create_dns_client
from server.registration_processor import RegistrationProcessor

class DNSEnabledRegistration(RegistrationProcessor):
    def __init__(self, config):
        super().__init__(config)
        self.dns_client = create_dns_client(config)
    
    async def process_registration(self, hostname: str, ip_address: str):
        # Regular registration
        result = await super().process_registration(hostname, ip_address)
        
        # Create DNS record
        if result["status"] == "success":
            try:
                await self.dns_client.create_a_record(hostname, ip_address)
                result["dns_created"] = True
            except Exception as e:
                logger.error(f"DNS creation failed: {e}")
                result["dns_created"] = False
        
        return result
```

### Health Check Implementation

```python
async def dns_health_check(client: PowerDNSClient) -> bool:
    """Check if DNS system is healthy."""
    try:
        # Check API connectivity
        zones = await client._make_request("GET", "/servers/localhost/zones")
        
        # Try to create/update a health check record
        test_hostname = "_health-check"
        test_ip = "127.0.0.1"
        
        result = await client.create_a_record(test_hostname, test_ip, ttl=60)
        
        # Verify record exists
        record = await client.get_record(test_hostname)
        
        return record is not None
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False
```

## Performance Considerations

### Connection Reuse

```python
# Bad: Creating new client for each operation
for hostname in hostnames:
    client = create_dns_client(config)
    await client.create_a_record(hostname, ip)
    await client.close()

# Good: Reuse client and connections
async with create_dns_client(config) as client:
    for hostname in hostnames:
        await client.create_a_record(hostname, ip)
```

### Bulk Operations

```python
# For large batches, limit concurrency
semaphore = asyncio.Semaphore(10)

async def create_with_limit(client, hostname, ip):
    async with semaphore:
        return await client.create_a_record(hostname, ip)

# Process 1000 records with max 10 concurrent
tasks = [
    create_with_limit(client, f"host{i}", f"10.0.{i//256}.{i%256}")
    for i in range(1000)
]
results = await asyncio.gather(*tasks)
```

## Monitoring and Metrics

The client automatically records Prometheus metrics:

```python
# Metrics exposed:
powerdns_api_requests_total{operation="create_record", status="success"}
powerdns_api_request_duration_seconds{operation="create_record"}
powerdns_api_errors_total{operation="create_record", error_type="timeout"}
```

Access metrics:
```python
from prometheus_client import generate_latest

# Get current metrics
metrics = generate_latest()
```

## Best Practices

1. **Always use context manager** for automatic cleanup
2. **Handle specific exceptions** for better error recovery
3. **Set appropriate timeouts** based on network conditions
4. **Use batch operations** for bulk updates
5. **Monitor metrics** for performance tracking
6. **Implement circuit breakers** for failure scenarios
7. **Log all DNS operations** for audit trails
8. **Validate inputs** before API calls
9. **Use connection pooling** for better performance
10. **Implement retries** with exponential backoff