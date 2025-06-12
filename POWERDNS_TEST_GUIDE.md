# PowerDNS Integration Testing Guide

This guide will help you test the PowerDNS integration in your development environment.

## Prerequisites

1. Docker and Docker Compose installed
2. Python environment with dependencies installed
3. Access to modify `/etc/hosts` or DNS resolution

## Step 1: Start the Development Environment

### 1.1 Create a combined docker-compose file for testing

Create `docker-compose.dev-powerdns.yml`:

```bash
cat > docker-compose.dev-powerdns.yml << 'EOF'
version: '3.8'

services:
  # PowerDNS Database
  powerdns-db:
    image: postgres:15-alpine
    container_name: powerdns-database
    restart: unless-stopped
    environment:
      POSTGRES_DB: powerdns
      POSTGRES_USER: powerdns
      POSTGRES_PASSWORD: test-db-password
    volumes:
      - powerdns-db-data:/var/lib/postgresql/data
      - ./powerdns/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql:ro
    networks:
      - prism-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U powerdns"]
      interval: 10s
      timeout: 5s
      retries: 5

  # PowerDNS Server
  powerdns:
    build:
      context: ./powerdns
      dockerfile: Dockerfile
    container_name: powerdns-server
    restart: unless-stopped
    ports:
      - "5353:53/tcp"
      - "5353:53/udp"
      - "8053:8053"
    cap_add:
      - NET_BIND_SERVICE
    environment:
      PDNS_API_KEY: test-api-key
      PDNS_DB_HOST: powerdns-db
      PDNS_DB_PORT: 5432
      PDNS_DB_NAME: powerdns
      PDNS_DB_USER: powerdns
      PDNS_DB_PASSWORD: test-db-password
      PDNS_API_ALLOW_FROM: 0.0.0.0/0,::/0
      PDNS_DEFAULT_ZONE: managed.prism.local
    depends_on:
      powerdns-db:
        condition: service_healthy
    networks:
      - prism-network
    healthcheck:
      test: ["CMD", "pdns_control", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Prism Server with PowerDNS integration
  prism-server:
    build:
      context: .
      target: development
    container_name: prism-server
    ports:
      - "8080:8080"
      - "8081:8081"
    volumes:
      - .:/app
      - server_data:/app/data
    environment:
      - PRISM_ENV=development
      - PRISM_CONFIG_PATH=/app/config/server.yaml
      - PYTHONPATH=/app
      - PYTHONUNBUFFERED=1
      - PRISM_POWERDNS_ENABLED=true
      - PRISM_POWERDNS_API_URL=http://powerdns:8053/api/v1
      - PRISM_POWERDNS_API_KEY=test-api-key
      - PRISM_POWERDNS_DEFAULT_ZONE=managed.prism.local.
    command: >
      sh -c "python -m server.main --config /app/config/server.yaml"
    depends_on:
      - powerdns
    networks:
      - prism-network
    restart: unless-stopped

volumes:
  powerdns-db-data:
  server_data:

networks:
  prism-network:
    driver: bridge
EOF
```

### 1.2 Start the services

```bash
# Stop any existing services
docker compose down

# Start the integrated environment
docker compose -f docker-compose.dev-powerdns.yml up -d

# Check services are running
docker compose -f docker-compose.dev-powerdns.yml ps

# View logs
docker compose -f docker-compose.dev-powerdns.yml logs -f
```

## Step 2: Verify PowerDNS is Working

### 2.1 Check PowerDNS API

```bash
# Test PowerDNS API is accessible
curl -H "X-API-Key: test-api-key" http://localhost:8053/api/v1/servers/localhost

# Check zones
curl -H "X-API-Key: test-api-key" http://localhost:8053/api/v1/servers/localhost/zones
```

### 2.2 Create the test zone

```bash
# Create managed.prism.local zone
curl -X POST -H "X-API-Key: test-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "managed.prism.local.",
    "kind": "Native",
    "rrsets": [
      {
        "name": "managed.prism.local.",
        "type": "SOA",
        "ttl": 3600,
        "records": [{
          "content": "ns1.managed.prism.local. admin.managed.prism.local. 1 10800 3600 604800 3600",
          "disabled": false
        }]
      },
      {
        "name": "managed.prism.local.",
        "type": "NS",
        "ttl": 3600,
        "records": [{
          "content": "ns1.managed.prism.local.",
          "disabled": false
        }]
      }
    ]
  }' \
  http://localhost:8053/api/v1/servers/localhost/zones
```

## Step 3: Test Client Registration with DNS

### 3.1 Register a test client

```bash
# Create a test client configuration
cat > test-client.yaml << EOF
server:
  host: localhost
  port: 8080

client:
  hostname: testhost1
  heartbeat_interval: 30

logging:
  level: DEBUG
EOF

# Run the client
python prism_client.py -c test-client.yaml
```

### 3.2 Verify DNS record was created

```bash
# Query PowerDNS for the record
dig @localhost -p 5353 testhost1.managed.prism.local

# Check via API
curl -H "X-API-Key: test-api-key" \
  http://localhost:8053/api/v1/servers/localhost/zones/managed.prism.local. | \
  jq '.rrsets[] | select(.name=="testhost1.managed.prism.local.")'
```

### 3.3 Check database for DNS sync status

```bash
# Check the host record in the database
docker compose -f docker-compose.dev-powerdns.yml exec prism-server \
  sqlite3 /app/data/prism.db \
  "SELECT hostname, current_ip, dns_sync_status, dns_zone, dns_record_id FROM hosts;"
```

## Step 4: Test IP Address Changes

### 4.1 Simulate IP change

```bash
# Stop the first client
# Modify the client to connect from a different interface or use a different test

# Or manually test via the API
curl -X POST http://localhost:8081/api/hosts \
  -H "Content-Type: application/json" \
  -d '{"hostname": "testhost2", "ip_address": "192.168.1.100"}'

# Check the DNS record
dig @localhost -p 5353 testhost2.managed.prism.local
```

## Step 5: Monitor DNS Operations

### 5.1 Check Prometheus metrics

```bash
# View DNS-related metrics
curl -s http://localhost:8081/metrics | grep -E "powerdns|dns_sync"
```

### 5.2 Check logs for DNS operations

```bash
# View Prism server logs
docker compose -f docker-compose.dev-powerdns.yml logs prism-server | grep -i dns

# View PowerDNS logs
docker compose -f docker-compose.dev-powerdns.yml logs powerdns
```

## Step 6: Test Error Scenarios

### 6.1 Test with PowerDNS down

```bash
# Stop PowerDNS
docker compose -f docker-compose.dev-powerdns.yml stop powerdns

# Register a new host
python prism_client.py -c test-client.yaml

# Check that registration still works but DNS sync fails
docker compose -f docker-compose.dev-powerdns.yml exec prism-server \
  sqlite3 /app/data/prism.db \
  "SELECT hostname, dns_sync_status FROM hosts WHERE hostname='testhost1';"

# Restart PowerDNS
docker compose -f docker-compose.dev-powerdns.yml start powerdns
```

### 6.2 Test invalid zone

```bash
# Try to create a record in non-existent zone
curl -X POST http://localhost:8081/api/hosts \
  -H "Content-Type: application/json" \
  -d '{"hostname": "testhost3", "ip_address": "192.168.1.101", "dns_zone": "nonexistent.zone."}'
```

## Step 7: Bulk Testing

### 7.1 Register multiple hosts

```python
# Create test_bulk_registration.py
import asyncio
import aiohttp

async def register_host(session, hostname, ip):
    url = "http://localhost:8081/api/hosts"
    data = {"hostname": hostname, "ip_address": f"192.168.1.{ip}"}
    async with session.post(url, json=data) as resp:
        return await resp.json()

async def main():
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(10):
            hostname = f"bulkhost{i}"
            ip = 100 + i
            tasks.append(register_host(session, hostname, ip))
        
        results = await asyncio.gather(*tasks)
        print(f"Registered {len(results)} hosts")

asyncio.run(main())
```

### 7.2 Verify all DNS records

```bash
# Check all records in the zone
curl -H "X-API-Key: test-api-key" \
  http://localhost:8053/api/v1/servers/localhost/zones/managed.prism.local. | \
  jq '.rrsets[] | select(.type=="A") | .name'
```

## Step 8: Performance Testing

### 8.1 Check metrics

```bash
# DNS operation metrics
curl -s http://localhost:8081/metrics | grep -E "powerdns_api_request|powerdns_record_operations"

# Check timing
curl -s http://localhost:8081/metrics | grep "powerdns_api_request_duration_seconds"
```

## Cleanup

```bash
# Stop all services
docker compose -f docker-compose.dev-powerdns.yml down

# Remove volumes if needed
docker compose -f docker-compose.dev-powerdns.yml down -v
```

## Troubleshooting

### PowerDNS not starting
- Check port 5353 is not in use: `sudo lsof -i :5353`
- Check logs: `docker compose -f docker-compose.dev-powerdns.yml logs powerdns`

### DNS records not created
- Verify PowerDNS is enabled in config
- Check API key matches
- Ensure zone exists
- Check Prism server logs for errors

### Cannot query DNS records
- Use correct port: `-p 5353`
- Ensure PowerDNS is running
- Check firewall rules

## Expected Results

When everything is working correctly:
1. Clients registering with Prism get automatic DNS records
2. DNS queries return the correct IP addresses
3. IP changes are reflected in DNS
4. Metrics show successful DNS operations
5. Database shows `dns_sync_status = 'synced'` for hosts