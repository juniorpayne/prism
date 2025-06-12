# PowerDNS Troubleshooting Guide

Comprehensive troubleshooting guide for common PowerDNS integration issues.

## Quick Diagnostics

### Health Check Script

```bash
#!/bin/bash
# save as check-powerdns.sh

echo "🔍 PowerDNS Health Check"
echo "======================="

# Check PowerDNS API
echo -n "PowerDNS API: "
if curl -s -f -H "X-API-Key: ${PDNS_API_KEY}" http://localhost:8053/api/v1/servers/localhost > /dev/null; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

# Check DNS port
echo -n "DNS Port (53): "
if nc -zv localhost 5353 2>&1 | grep -q succeeded; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

# Check database connection
echo -n "Database: "
if docker exec powerdns pdns_control ping 2>&1 | grep -q PONG; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

# Check zone
echo -n "Default Zone: "
ZONE_CHECK=$(curl -s -H "X-API-Key: ${PDNS_API_KEY}" http://localhost:8053/api/v1/servers/localhost/zones/${POWERDNS_DEFAULT_ZONE})
if echo "$ZONE_CHECK" | grep -q "\"name\""; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

# Test DNS resolution
echo -n "DNS Resolution: "
if dig @localhost -p 5353 test.${POWERDNS_DEFAULT_ZONE} +short > /dev/null 2>&1; then
    echo "✅ OK"
else
    echo "⚠️  No test record"
fi
```

## Common Issues and Solutions

### 1. PowerDNS Not Starting

#### Symptoms
- Container exits immediately
- No response on port 53 or 8053
- Error logs show startup failures

#### Diagnostics
```bash
# Check container status
docker ps -a | grep powerdns

# View logs
docker logs powerdns --tail 100

# Check configuration
docker exec powerdns pdns_control show-config
```

#### Common Causes and Solutions

**Database Connection Failed**
```bash
# Error: "Unable to connect to database"
# Solution: Check database credentials
docker exec powerdns printenv | grep PDNS_GPGSQL

# Test database connection
docker exec postgres psql -U powerdns -d powerdns -c "SELECT 1;"

# Fix: Update environment variables
docker-compose down
# Edit .env file with correct credentials
docker-compose up -d
```

**Port Already in Use**
```bash
# Error: "Address already in use"
# Find process using port
sudo lsof -i :53
sudo lsof -i :8053

# Solution 1: Stop conflicting service
sudo systemctl stop systemd-resolved  # Common on Ubuntu

# Solution 2: Use different ports
# Update docker-compose.yml:
ports:
  - "5353:53/udp"
  - "5353:53/tcp"
  - "8053:8053"
```

**Invalid Configuration**
```bash
# Error: "Unknown setting 'invalid-option'"
# Validate configuration
docker run --rm \
  -v $(pwd)/pdns.conf:/etc/powerdns/pdns.conf \
  powerdns/pdns-auth-48:latest \
  pdns_server --config-check

# Common fixes:
# - Remove deprecated options
# - Check syntax errors
# - Verify backend settings
```

### 2. DNS Records Not Created

#### Symptoms
- Host registration succeeds but no DNS record
- API returns success but record missing
- Dig queries return NXDOMAIN

#### Diagnostics
```bash
# Check Prism logs
docker logs prism-server --tail 50 | grep -i dns

# Verify PowerDNS integration enabled
curl http://localhost:8081/api/dns/status

# Check specific record
curl -H "X-API-Key: ${PDNS_API_KEY}" \
  "http://localhost:8053/api/v1/servers/localhost/zones/${POWERDNS_DEFAULT_ZONE}" \
  | jq '.rrsets[] | select(.name=="test-host.managed.prism.local.")'
```

#### Solutions

**Zone Not Created**
```bash
# Create zone
curl -X POST http://localhost:8053/api/v1/servers/localhost/zones \
  -H "X-API-Key: ${PDNS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "managed.prism.local.",
    "kind": "Native",
    "nameservers": ["ns1.prism.local.", "ns2.prism.local."]
  }'

# Verify zone
curl -H "X-API-Key: ${PDNS_API_KEY}" \
  http://localhost:8053/api/v1/servers/localhost/zones
```

**API Key Mismatch**
```bash
# Test API key
curl -H "X-API-Key: wrong-key" http://localhost:8053/api/v1

# Fix: Ensure keys match
# In Prism container:
docker exec prism-server printenv | grep POWERDNS_API_KEY

# In PowerDNS container:
docker exec powerdns printenv | grep PDNS_API_KEY

# Update and restart if needed
docker-compose down
# Update .env
docker-compose up -d
```

**Async Processing Delays**
```python
# Check database for pending sync
docker exec prism-server python -c "
from server.database.connection import DatabaseManager
import asyncio

async def check():
    db = DatabaseManager({'database': {'path': '/data/prism.db'}})
    await db.initialize()
    async with db.get_session() as session:
        result = await session.execute(
            'SELECT hostname, dns_sync_status FROM hosts WHERE dns_sync_status != \"synced\"'
        )
        for row in result:
            print(f'{row.hostname}: {row.dns_sync_status}')
    await db.close()

asyncio.run(check())
"
```

### 3. DNS Queries Failing

#### Symptoms
- Dig returns SERVFAIL or timeout
- Intermittent resolution failures
- High query latency

#### Diagnostics
```bash
# Test direct query to PowerDNS
dig @localhost -p 5353 test.managed.prism.local +trace

# Check query logs
docker exec powerdns tail -f /var/log/pdns.log

# Monitor query performance
while true; do
  time dig @localhost -p 5353 test.managed.prism.local +short
  sleep 1
done
```

#### Solutions

**Database Performance Issues**
```sql
-- Check slow queries
docker exec postgres psql -U powerdns -c "
SELECT query, calls, mean_time 
FROM pg_stat_statements 
WHERE mean_time > 1000 
ORDER BY mean_time DESC;"

-- Add missing indexes
docker exec postgres psql -U powerdns -d powerdns -c "
CREATE INDEX IF NOT EXISTS idx_records_name_type ON records(name, type);
CREATE INDEX IF NOT EXISTS idx_records_domain_id ON records(domain_id);
ANALYZE records;"
```

**Cache Configuration**
```bash
# Increase cache sizes
docker exec powerdns pdns_control set cache-ttl 120
docker exec powerdns pdns_control set negquery-cache-ttl 60
docker exec powerdns pdns_control set max-cache-entries 2000000

# Monitor cache hit rate
watch -n 1 'docker exec powerdns pdns_control show cache-hit-rate'
```

**Network Issues**
```bash
# Check MTU issues
ping -M do -s 1472 dns-server-ip

# Test TCP fallback
dig @localhost -p 5353 +tcp test.managed.prism.local

# Check firewall rules
iptables -L -n -v | grep -E "53|8053"
```

### 4. API Performance Problems

#### Symptoms
- Slow API responses
- Timeouts on bulk operations
- High CPU/memory usage

#### Diagnostics
```bash
# Monitor API response times
for i in {1..10}; do
  time curl -s -H "X-API-Key: ${PDNS_API_KEY}" \
    http://localhost:8053/api/v1/servers/localhost/zones > /dev/null
done

# Check connection pool
netstat -an | grep 8053 | wc -l

# Monitor resource usage
docker stats powerdns
```

#### Solutions

**Connection Pool Exhaustion**
```python
# Increase Prism connection pool
# config.yaml:
powerdns:
  connection_pool:
    size: 20
    max_overflow: 30
    timeout: 60

# Monitor pool usage
curl http://localhost:8081/api/dns/stats | jq .connection_pool
```

**Batch Operation Optimization**
```python
# Use batch operations instead of individual requests
# Bad:
for hostname in hostnames:
    await dns_client.create_a_record(hostname, ip)

# Good:
tasks = [dns_client.create_a_record(h, ip) for h in hostnames]
await asyncio.gather(*tasks)
```

### 5. Replication Issues

#### Symptoms
- Secondary servers out of sync
- AXFR/IXFR failures
- Inconsistent query results

#### Diagnostics
```bash
# Check zone serial numbers
for server in primary secondary; do
  echo "Server: $server"
  dig @$server -p 5353 SOA managed.prism.local +short
done

# Check AXFR permissions
dig @primary -p 5353 AXFR managed.prism.local

# Monitor replication logs
docker logs powerdns-secondary | grep -i "transfer"
```

#### Solutions

**AXFR Permission Denied**
```bash
# Update PowerDNS config
docker exec powerdns-primary pdns_control set allow-axfr-ips "10.0.0.0/8,172.16.0.0/12"

# Or in pdns.conf:
allow-axfr-ips=127.0.0.1,::1,10.0.0.0/8
also-notify=secondary1-ip,secondary2-ip
```

**Serial Number Issues**
```sql
-- Force serial update
UPDATE domains 
SET notified_serial = notified_serial + 1 
WHERE name = 'managed.prism.local.';

-- Trigger NOTIFY
docker exec powerdns-primary pdns_control notify managed.prism.local
```

### 6. Memory Leaks

#### Symptoms
- Increasing memory usage over time
- Container OOM kills
- Performance degradation

#### Diagnostics
```bash
# Monitor memory usage
docker stats powerdns --no-stream

# Check for connection leaks
lsof -p $(pgrep pdns_server) | grep -c TCP

# Analyze memory usage
docker exec powerdns cat /proc/$(pgrep pdns_server)/status | grep -E "Vm|Rss"
```

#### Solutions

**Restart Schedule**
```yaml
# docker-compose.yml
services:
  powerdns:
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 512M
```

**Cache Limits**
```conf
# pdns.conf
max-cache-entries=1000000
max-packet-cache-entries=500000

# Periodic cache purge
0 * * * * docker exec powerdns pdns_control purge "*.old.local$"
```

## Advanced Debugging

### Enable Debug Logging

```bash
# Temporary debug mode
docker exec powerdns pdns_control set loglevel 9

# Permanent in pdns.conf
loglevel=7
log-dns-queries=yes
log-dns-details=yes

# Watch logs
docker logs -f powerdns 2>&1 | grep -v "Question"
```

### Packet Capture

```bash
# Capture DNS traffic
tcpdump -i any -w dns.pcap 'port 53'

# Analyze with tshark
tshark -r dns.pcap -Y "dns.qry.name contains managed.prism.local"

# Live monitoring
tcpdump -i any -n 'port 53' -l | grep -E "A\?|AAAA\?"
```

### Performance Profiling

```bash
# Query performance test
dnsperf -s localhost -p 5353 -d queries.txt -t 30

# API performance test
ab -n 1000 -c 10 -H "X-API-Key: ${PDNS_API_KEY}" \
  http://localhost:8053/api/v1/servers/localhost/zones

# Database query analysis
docker exec postgres pg_stat_statements_reset
# Run workload
docker exec postgres psql -U powerdns -c "
SELECT query, calls, mean_time, total_time 
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;"
```

## Emergency Procedures

### Complete Reset

```bash
#!/bin/bash
# emergency-reset.sh

echo "⚠️  Emergency PowerDNS Reset"
read -p "This will delete all DNS data. Continue? (y/N) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Stop services
    docker-compose down
    
    # Backup current data
    mkdir -p backups/emergency
    docker exec postgres pg_dump -U powerdns powerdns > backups/emergency/powerdns_$(date +%s).sql
    
    # Clear data
    docker volume rm prism-dns_postgres_data
    
    # Restart fresh
    docker-compose up -d
    
    # Recreate default zone
    sleep 10
    ./scripts/create-default-zone.sh
    
    echo "✅ Reset complete"
fi
```

### Failover Procedure

```bash
# Manual failover to secondary
# 1. Update DNS to point to secondary
dig @ns1.provider.com update <<EOF
update delete dns.yourdomain.com A
update add dns.yourdomain.com 60 A secondary-ip
send
EOF

# 2. Promote secondary
docker exec powerdns-secondary pdns_control set master yes

# 3. Update Prism configuration
docker exec prism-server sed -i 's/primary-ip/secondary-ip/g' /config/config.yaml
docker restart prism-server
```

## Monitoring Queries

### Useful Prometheus Queries

```promql
# DNS query rate
rate(powerdns_queries_total[5m])

# Cache hit ratio
rate(powerdns_cache_hits_total[5m]) / rate(powerdns_cache_lookups_total[5m])

# API error rate
rate(prism_powerdns_api_errors_total[5m])

# Record operation latency
histogram_quantile(0.95, rate(prism_dns_operation_duration_seconds_bucket[5m]))
```

## Support Resources

- PowerDNS IRC: #powerdns on irc.oftc.net
- PowerDNS Mailing List: https://mailman.powerdns.com/
- GitHub Issues: https://github.com/PowerDNS/pdns/issues
- Commercial Support: https://www.powerdns.com/support.html

## Quick Reference Card

| Issue | Check | Fix |
|-------|-------|-----|
| Container won't start | `docker logs powerdns` | Check database connection |
| API not responding | `curl -I localhost:8053` | Verify API key and webserver config |
| DNS queries fail | `dig @localhost -p 5353` | Check zone exists, cache settings |
| Records not created | API logs, zone config | Create zone, check permissions |
| High latency | Cache stats, DB queries | Increase cache, optimize queries |
| Memory issues | `docker stats` | Set limits, schedule restarts |