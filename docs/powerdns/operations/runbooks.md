# PowerDNS Operational Runbooks

Standard operating procedures for PowerDNS management and incident response.

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Incident Response](#incident-response)
3. [Maintenance Procedures](#maintenance-procedures)
4. [Emergency Procedures](#emergency-procedures)
5. [Recovery Procedures](#recovery-procedures)

---

## Daily Operations

### Morning Health Check

**Frequency**: Daily at start of shift  
**Time Required**: 10 minutes  
**Severity**: Routine

```bash
#!/bin/bash
# morning-check.sh

echo "☀️ PowerDNS Morning Health Check - $(date)"
echo "========================================"

# 1. Check all services are running
echo "1. Service Status:"
docker-compose ps | grep -E "powerdns|postgres|prism"

# 2. Check API responsiveness
echo -e "\n2. API Health:"
curl -s -w "Response time: %{time_total}s\n" \
  -H "X-API-Key: ${PDNS_API_KEY}" \
  http://localhost:8053/api/v1/servers/localhost | jq -r .version

# 3. Check DNS resolution
echo -e "\n3. DNS Resolution Test:"
dig @localhost -p 5353 health-check.${DNS_ZONE} +short || echo "No health check record"

# 4. Check recent errors
echo -e "\n4. Recent Errors (last 24h):"
docker logs powerdns --since 24h 2>&1 | grep -i error | tail -5

# 5. Check metrics
echo -e "\n5. Key Metrics:"
curl -s http://localhost:8081/metrics | grep -E "powerdns_queries_total|dns_record_"

echo -e "\n✅ Morning check complete"
```

### Zone Verification

**Frequency**: Weekly  
**Time Required**: 30 minutes  
**Severity**: Routine

```bash
#!/bin/bash
# verify-zones.sh

echo "🔍 Weekly Zone Verification"
echo "=========================="

# Get all zones
ZONES=$(curl -s -H "X-API-Key: ${PDNS_API_KEY}" \
  http://localhost:8053/api/v1/servers/localhost/zones | jq -r '.[].name')

for zone in $ZONES; do
    echo -e "\nChecking zone: $zone"
    
    # 1. Verify SOA record
    SOA=$(dig @localhost -p 5353 SOA $zone +short)
    if [ -z "$SOA" ]; then
        echo "  ❌ Missing SOA record!"
    else
        echo "  ✅ SOA: $SOA"
    fi
    
    # 2. Verify NS records
    NS=$(dig @localhost -p 5353 NS $zone +short)
    if [ -z "$NS" ]; then
        echo "  ❌ Missing NS records!"
    else
        echo "  ✅ NS records found"
    fi
    
    # 3. Check DNSSEC status
    DNSSEC=$(curl -s -H "X-API-Key: ${PDNS_API_KEY}" \
      http://localhost:8053/api/v1/servers/localhost/zones/$zone | jq .dnssec)
    echo "  📎 DNSSEC: $DNSSEC"
    
    # 4. Record count
    RECORDS=$(curl -s -H "X-API-Key: ${PDNS_API_KEY}" \
      http://localhost:8053/api/v1/servers/localhost/zones/$zone | jq '.rrsets | length')
    echo "  📊 Total records: $RECORDS"
done
```

---

## Incident Response

### IR-001: High Query Latency

**Symptoms**: DNS queries taking >100ms consistently  
**Impact**: Degraded user experience  
**Priority**: P2

#### Detection
```bash
# Alert triggered by Prometheus rule:
# dns_query_latency_seconds{quantile="0.95"} > 0.1
```

#### Response Steps

1. **Verify the issue**
   ```bash
   # Test query latency
   for i in {1..10}; do
     time dig @localhost -p 5353 test.${DNS_ZONE} +short
   done
   ```

2. **Check cache effectiveness**
   ```bash
   # View cache statistics
   docker exec powerdns pdns_control show variable cache-hit-rate
   docker exec powerdns pdns_control show variable cache-size
   ```

3. **Identify slow queries**
   ```sql
   -- Connect to PostgreSQL
   docker exec -it postgres psql -U powerdns -d powerdns
   
   -- Find slow queries
   SELECT query, calls, mean_time
   FROM pg_stat_statements
   WHERE mean_time > 100
   ORDER BY mean_time DESC
   LIMIT 10;
   ```

4. **Immediate mitigation**
   ```bash
   # Increase cache size
   docker exec powerdns pdns_control set max-cache-entries 2000000
   
   # Clear specific problematic entries
   docker exec powerdns pdns_control purge "problematic.domain$"
   ```

5. **Long-term fix**
   - Add database indexes
   - Optimize slow queries
   - Scale infrastructure

### IR-002: DNS Service Unavailable

**Symptoms**: No response on port 53  
**Impact**: Complete DNS failure  
**Priority**: P1

#### Response Steps

1. **Immediate diagnosis**
   ```bash
   # Check if service is running
   docker ps | grep powerdns
   
   # Check port binding
   netstat -tlnup | grep :53
   
   # View recent logs
   docker logs powerdns --tail 100
   ```

2. **Quick restart attempt**
   ```bash
   # Restart container
   docker-compose restart powerdns
   
   # Wait for health check
   sleep 10
   
   # Verify service
   dig @localhost -p 5353 test.${DNS_ZONE}
   ```

3. **Failover if needed**
   ```bash
   # Switch to backup DNS
   ./scripts/failover-to-secondary.sh
   
   # Update load balancer
   curl -X POST http://haproxy:8080/disable/server/powerdns-primary
   ```

4. **Root cause analysis**
   - Check for OOM kills: `dmesg | grep -i "killed process"`
   - Review configuration changes
   - Check database connectivity

### IR-003: Unauthorized DNS Changes

**Symptoms**: Unexpected DNS records appearing/changing  
**Impact**: Security breach potential  
**Priority**: P1

#### Response Steps

1. **Immediate lockdown**
   ```bash
   # Disable API access
   docker exec powerdns pdns_control set api no
   
   # Rotate API key
   NEW_KEY=$(openssl rand -base64 32)
   docker exec powerdns pdns_control set api-key $NEW_KEY
   ```

2. **Audit recent changes**
   ```sql
   -- Check recent record modifications
   SELECT * FROM audit_log 
   WHERE timestamp > NOW() - INTERVAL '1 hour'
   ORDER BY timestamp DESC;
   ```

3. **Identify compromised records**
   ```bash
   # Export current records
   curl -H "X-API-Key: ${PDNS_API_KEY}" \
     http://localhost:8053/api/v1/servers/localhost/zones/${DNS_ZONE} \
     > current_records.json
   
   # Compare with known good backup
   diff known_good_records.json current_records.json
   ```

4. **Remediation**
   ```bash
   # Restore from backup
   ./scripts/restore-zone.sh ${DNS_ZONE} backup_file.json
   
   # Re-enable API with new key
   docker exec powerdns pdns_control set api yes
   ```

---

## Maintenance Procedures

### MP-001: PowerDNS Version Upgrade

**Frequency**: Quarterly  
**Duration**: 2 hours  
**Risk**: Medium

#### Pre-requisites
- [ ] Maintenance window scheduled
- [ ] Backups completed
- [ ] Rollback plan prepared
- [ ] Team notified

#### Procedure

1. **Pre-upgrade backup**
   ```bash
   # Backup database
   docker exec postgres pg_dump -U powerdns powerdns > \
     backups/powerdns_$(date +%Y%m%d_%H%M%S).sql
   
   # Backup configuration
   cp -r config/ backups/config_$(date +%Y%m%d_%H%M%S)/
   
   # Export all zones
   for zone in $(curl -s -H "X-API-Key: ${PDNS_API_KEY}" \
     http://localhost:8053/api/v1/servers/localhost/zones | jq -r '.[].name'); do
     curl -H "X-API-Key: ${PDNS_API_KEY}" \
       http://localhost:8053/api/v1/servers/localhost/zones/$zone \
       > backups/zones/${zone}.json
   done
   ```

2. **Test in staging**
   ```bash
   # Update staging environment first
   cd staging/
   docker-compose pull powerdns
   docker-compose up -d powerdns
   
   # Run test suite
   pytest tests/test_dns_*.py
   ```

3. **Production upgrade**
   ```bash
   # Pull new image
   docker pull powerdns/pdns-auth-49:latest
   
   # Update compose file
   sed -i 's/pdns-auth-48/pdns-auth-49/g' docker-compose.yml
   
   # Rolling upgrade
   docker-compose up -d --no-deps --scale powerdns=2 powerdns
   sleep 30
   docker-compose up -d --no-deps powerdns
   ```

4. **Post-upgrade verification**
   ```bash
   # Check version
   docker exec powerdns pdns_control version
   
   # Run health checks
   ./scripts/health-check.sh
   
   # Monitor for 30 minutes
   watch -n 10 './scripts/quick-stats.sh'
   ```

### MP-002: Database Maintenance

**Frequency**: Monthly  
**Duration**: 1 hour  
**Risk**: Low

#### Procedure

1. **Analyze and vacuum**
   ```sql
   -- Connect to database
   docker exec -it postgres psql -U powerdns -d powerdns
   
   -- Analyze tables
   ANALYZE domains;
   ANALYZE records;
   ANALYZE domainmetadata;
   
   -- Vacuum to reclaim space
   VACUUM (VERBOSE, ANALYZE) records;
   ```

2. **Reindex if needed**
   ```sql
   -- Check index bloat
   SELECT schemaname, tablename, indexname, 
          pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
          idx_scan as index_scans
   FROM pg_stat_user_indexes
   JOIN pg_indexes ON schemaname = schemaname 
                   AND tablename = tablename 
                   AND indexname = indexname
   WHERE idx_scan < 100
   ORDER BY pg_relation_size(indexrelid) DESC;
   
   -- Reindex if necessary
   REINDEX INDEX CONCURRENTLY idx_records_name_type;
   ```

3. **Archive old data**
   ```sql
   -- Archive deleted records older than 90 days
   INSERT INTO records_archive 
   SELECT * FROM records 
   WHERE disabled = true 
     AND modified < NOW() - INTERVAL '90 days';
   
   DELETE FROM records 
   WHERE disabled = true 
     AND modified < NOW() - INTERVAL '90 days';
   ```

---

## Emergency Procedures

### EP-001: Complete DNS Failure Recovery

**Scenario**: Total PowerDNS failure, no DNS resolution  
**Time to Recovery**: 15 minutes

1. **Immediate mitigation - Static DNS**
   ```bash
   # Deploy emergency static DNS
   docker run -d --name emergency-dns \
     -p 53:53/udp -p 53:53/tcp \
     -v $(pwd)/emergency-hosts:/etc/hosts \
     tutum/dnsmasq
   
   # Update critical records
   echo "192.168.1.100 critical-app.${DNS_ZONE}" >> emergency-hosts
   ```

2. **Restore from backup**
   ```bash
   # Find latest backup
   LATEST_BACKUP=$(ls -t backups/powerdns_*.sql | head -1)
   
   # Restore database
   docker exec -i postgres psql -U powerdns -d powerdns < $LATEST_BACKUP
   
   # Restart PowerDNS
   docker-compose restart powerdns
   ```

### EP-002: API Key Compromise

**Scenario**: API key leaked/compromised  
**Time to Recovery**: 5 minutes

```bash
#!/bin/bash
# emergency-key-rotation.sh

# 1. Generate new key
NEW_KEY=$(openssl rand -base64 32)

# 2. Update PowerDNS
docker-compose down powerdns
echo "PDNS_API_KEY=${NEW_KEY}" > .env.emergency
docker-compose --env-file .env.emergency up -d powerdns

# 3. Update all clients
for client in prism-server monitoring webhook-service; do
    docker exec $client sed -i "s/old-key/${NEW_KEY}/g" /config/config.yaml
    docker restart $client
done

# 4. Audit recent API usage
docker logs powerdns --since 24h | grep "API request" > api_audit.log
```

---

## Recovery Procedures

### RP-001: Point-in-Time Recovery

**Use Case**: Restore DNS to specific timestamp

1. **Identify recovery point**
   ```bash
   # List available backups
   ls -la backups/powerdns_*.sql
   
   # Choose backup before incident
   RESTORE_POINT="backups/powerdns_20240115_140000.sql"
   ```

2. **Create recovery database**
   ```sql
   -- Create new database
   docker exec postgres createdb -U powerdns powerdns_recovery
   
   -- Restore to recovery DB
   docker exec -i postgres psql -U powerdns powerdns_recovery < $RESTORE_POINT
   ```

3. **Validate recovery data**
   ```sql
   -- Compare record counts
   docker exec postgres psql -U powerdns -c "
   SELECT 
     (SELECT COUNT(*) FROM powerdns.records) as current,
     (SELECT COUNT(*) FROM powerdns_recovery.records) as recovery;"
   ```

4. **Perform recovery**
   ```bash
   # Stop services
   docker-compose stop prism-server powerdns
   
   # Swap databases
   docker exec postgres psql -U postgres -c "
   ALTER DATABASE powerdns RENAME TO powerdns_old;
   ALTER DATABASE powerdns_recovery RENAME TO powerdns;"
   
   # Restart services
   docker-compose start powerdns prism-server
   ```

### RP-002: Disaster Recovery

**Use Case**: Complete infrastructure failure

1. **Deploy to DR site**
   ```bash
   # On DR infrastructure
   git clone https://github.com/org/prism-dns.git
   cd prism-dns
   
   # Restore configuration
   aws s3 cp s3://backup-bucket/prism-dns/latest/config.tar.gz .
   tar -xzf config.tar.gz
   
   # Restore data
   aws s3 cp s3://backup-bucket/prism-dns/latest/powerdns.sql.gz .
   gunzip powerdns.sql.gz
   ```

2. **Initialize DR environment**
   ```bash
   # Start services
   docker-compose -f docker-compose.dr.yml up -d
   
   # Restore database
   docker exec -i postgres psql -U powerdns < powerdns.sql
   
   # Update DNS delegation
   ./scripts/update-dns-delegation.sh dr-site
   ```

---

## Runbook Management

### Updates and Reviews
- Review runbooks quarterly
- Update after each major incident
- Test procedures in staging monthly
- Maintain version control

### Training Requirements
- All operators must complete runbook training
- Annual disaster recovery drills
- Incident response simulations quarterly

### Contact Information
- On-Call: +1-555-DNS-HELP
- Escalation: dns-escalation@company.com
- Vendor Support: support@powerdns.com