# PowerDNS Quick Start Guide

Get up and running with PowerDNS integration in minutes.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.8+ (for local development)
- Basic understanding of DNS concepts

## Quick Setup

### 1. Start PowerDNS with Docker Compose

```bash
# Start all services including PowerDNS
docker compose -f docker-compose.powerdns.yml up -d

# Verify services are running
docker compose ps
```

### 2. Configure Prism Server

Set the following environment variables:

```bash
export POWERDNS_ENABLED=true
export POWERDNS_API_URL=http://localhost:8053/api/v1
export POWERDNS_API_KEY=your-secure-api-key
export POWERDNS_DEFAULT_ZONE=managed.prism.local.
```

Or add to your `.env` file:

```env
POWERDNS_ENABLED=true
POWERDNS_API_URL=http://localhost:8053/api/v1
POWERDNS_API_KEY=your-secure-api-key
POWERDNS_DEFAULT_ZONE=managed.prism.local.
```

### 3. Start Prism Server

```bash
# Using Docker
docker compose up -d

# Or locally
python -m server.main
```

### 4. Test the Integration

#### Register a Host
```bash
# Using the Prism client
python prism_client.py -c prism-client.yaml

# Or via API
curl -X POST http://localhost:8081/api/hosts \
  -H "Content-Type: application/json" \
  -d '{"hostname": "test-host", "ip": "192.168.1.100"}'
```

#### Verify DNS Record
```bash
# Query PowerDNS directly
dig @localhost -p 5353 test-host.managed.prism.local

# Or check via API
curl http://localhost:8081/api/hosts/test-host
```

## Common Operations

### Create a New Zone

```python
from server.dns_manager import create_dns_client

# Create client
config = {"powerdns": {...}}
dns_client = create_dns_client(config)

# Create zone
async with dns_client:
    await dns_client.create_zone("example.com.")
```

### Manual Record Management

```python
# Create A record
await dns_client.create_a_record("host1", "192.168.1.10")

# Create AAAA record
await dns_client.create_aaaa_record("host1", "2001:db8::1")

# Update record
await dns_client.update_record("host1", "192.168.1.20", "A")

# Delete record
await dns_client.delete_record("host1", "A")
```

### Check DNS Status

```bash
# Via REST API
curl http://localhost:8081/api/dns/status

# Check specific host DNS status
curl http://localhost:8081/api/hosts/test-host/dns
```

## Monitoring

### View Metrics

```bash
# Prometheus metrics
curl http://localhost:8081/metrics | grep powerdns

# Grafana dashboards (if monitoring stack deployed)
open http://localhost:3000
```

### Check Logs

```bash
# PowerDNS logs
docker compose logs powerdns

# Prism server logs (DNS operations)
docker compose logs server | grep -i dns
```

## Troubleshooting Quick Fixes

### DNS Records Not Created

1. Check PowerDNS is running:
   ```bash
   curl http://localhost:8053/api/v1/servers/localhost
   ```

2. Verify API key:
   ```bash
   curl -H "X-API-Key: your-api-key" \
     http://localhost:8053/api/v1/servers/localhost/zones
   ```

3. Check zone exists:
   ```bash
   curl -H "X-API-Key: your-api-key" \
     http://localhost:8053/api/v1/servers/localhost/zones/managed.prism.local.
   ```

### Connection Issues

```bash
# Test connectivity
nc -zv localhost 8053
nc -zv localhost 5353

# Check firewall rules
sudo iptables -L -n | grep -E "8053|5353"
```

### Performance Issues

```bash
# Run quick benchmark
python tests/test_dns_performance.py --quick

# Check connection pool
curl http://localhost:8081/api/dns/stats
```

## Next Steps

- Read the [Installation Guide](installation.md) for production setup
- Review [Configuration Reference](configuration.md) for all options
- Set up [Monitoring](../operations/monitoring.md) for production
- Implement [Security Best Practices](../operations/security.md)

## Quick Reference

| Service | Default Port | Purpose |
|---------|-------------|---------|
| PowerDNS API | 8053 | REST API for management |
| PowerDNS DNS | 5353 | DNS query port |
| Prism API | 8081 | Host registration API |
| Prism TCP | 8080 | Client connections |

| Common Commands | Description |
|-----------------|-------------|
| `docker compose logs powerdns` | View PowerDNS logs |
| `dig @localhost -p 5353 <hostname>` | Query DNS record |
| `curl http://localhost:8081/metrics` | View metrics |
| `pytest tests/test_dns_*.py` | Run DNS tests |