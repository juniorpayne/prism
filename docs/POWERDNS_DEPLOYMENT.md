# PowerDNS Integration Deployment Guide

This document provides comprehensive instructions for deploying the PowerDNS integration to production with feature flags and gradual rollout.

## Overview

The PowerDNS integration enables Prism DNS to use a real DNS server (PowerDNS) instead of mock data. The deployment uses feature flags for gradual rollout and includes comprehensive monitoring and rollback procedures.

## Prerequisites

1. Production environment running Prism DNS
2. PostgreSQL database for PowerDNS
3. Monitoring stack (Prometheus/Grafana) deployed
4. SSH access to production server
5. GitHub Actions deployment permissions

## Deployment Process

### Phase 1: Infrastructure Preparation

1. **Update Environment Configuration**
   ```bash
   # Copy template and update with production values
   cp .env.powerdns.template .env.powerdns
   
   # Generate strong passwords
   openssl rand -hex 32  # For PDNS_API_KEY
   openssl rand -hex 16  # For PDNS_DB_PASSWORD
   
   # Update .env.powerdns with actual values
   ```

2. **Update Production Environment**
   ```bash
   # Update .env.production
   POWERDNS_ENABLED=false                    # Start disabled
   POWERDNS_API_URL=http://localhost:8053/api/v1
   POWERDNS_API_KEY=your-secure-api-key
   POWERDNS_DEFAULT_ZONE=managed.prism.local.
   POWERDNS_FALLBACK_TO_MOCK=true           # Safe fallback
   POWERDNS_FEATURE_FLAG_PERCENTAGE=0       # Start with 0%
   ```

### Phase 2: Deploy PowerDNS Stack

1. **Deploy via GitHub Actions**
   ```bash
   # Trigger deployment with PowerDNS enabled
   gh workflow run "Direct Deploy to EC2" \
     --field deploy_powerdns=true \
     --field deploy_monitoring=true
   ```

2. **Manual Deployment (Alternative)**
   ```bash
   # On production server
   cd ~/prism-deployment
   
   # Deploy PowerDNS stack
   docker compose -f docker-compose.powerdns.yml --env-file .env.powerdns up -d
   
   # Verify deployment
   docker compose -f docker-compose.powerdns.yml ps
   ```

### Phase 3: Verify PowerDNS Installation

1. **Check PowerDNS Health**
   ```bash
   # Check API endpoint
   curl -H "X-API-Key: your-api-key" \
        http://localhost:8053/api/v1/servers/localhost
   
   # Check DNS resolution
   dig @localhost -p 53 managed.prism.local SOA
   ```

2. **Verify Database Connection**
   ```bash
   # Check PostgreSQL
   docker compose -f docker-compose.powerdns.yml exec powerdns-db \
     psql -U powerdns -c "\dt"
   ```

### Phase 4: Gradual Feature Rollout

1. **Enable PowerDNS for Testing (0% users)**
   ```bash
   # Update environment
   POWERDNS_ENABLED=true
   POWERDNS_FEATURE_FLAG_PERCENTAGE=0
   
   # Restart application
   docker compose -f docker-compose.production.yml restart
   ```

2. **Test API Endpoints**
   ```bash
   # Test DNS config endpoint
   curl http://localhost:8081/api/dns/config
   
   # Test zone operations (authenticated)
   curl -H "Authorization: Bearer $TOKEN" \
        http://localhost:8081/api/dns/zones
   ```

3. **Gradual Rollout**
   ```bash
   # 5% rollout
   POWERDNS_FEATURE_FLAG_PERCENTAGE=5
   docker compose -f docker-compose.production.yml restart
   
   # Monitor for 24 hours, then increase
   # 25% -> 50% -> 75% -> 100%
   ```

### Phase 5: Data Migration

1. **Migrate Existing DNS Data**
   ```bash
   # Run migration script
   python3 scripts/migrate-dns-data.py \
     --powerdns-url "http://localhost:8053/api/v1" \
     --api-key "your-api-key" \
     --data-source "default" \
     --mode "merge" \
     --dry-run  # Preview first
   
   # Run actual migration
   python3 scripts/migrate-dns-data.py \
     --powerdns-url "http://localhost:8053/api/v1" \
     --api-key "your-api-key" \
     --data-source "default" \
     --mode "merge"
   ```

## Monitoring and Validation

### Health Checks

1. **Application Health**
   ```bash
   curl https://prism.thepaynes.ca/api/health
   ```

2. **PowerDNS Health**
   ```bash
   curl -H "X-API-Key: your-api-key" \
        http://localhost:8053/api/v1/servers/localhost
   ```

3. **DNS Resolution**
   ```bash
   dig @35.170.180.10 managed.prism.local SOA
   ```

### Monitoring Dashboards

- **Grafana**: Check PowerDNS dashboard for metrics
- **Prometheus**: Verify PowerDNS targets are up
- **Alerts**: Configure PowerDNS alerting rules

### Key Metrics to Monitor

- PowerDNS query latency
- DNS error rates
- Feature flag usage
- Service adapter fallbacks
- Database connection health

## Rollback Procedures

### Quick Rollback (Disable Integration)

```bash
# Use rollback script
./scripts/rollback-dns-deployment.sh disable-only

# Or manual rollback
POWERDNS_ENABLED=false
POWERDNS_FEATURE_FLAG_PERCENTAGE=0
docker compose -f docker-compose.production.yml restart
```

### Full Rollback (Remove PowerDNS)

```bash
# Complete rollback with data preservation
./scripts/rollback-dns-deployment.sh full-rollback

# Complete rollback with data removal (DESTRUCTIVE)
./scripts/rollback-dns-deployment.sh full-rollback --remove-volumes
```

### Rollback Verification

```bash
# Check rollback status
./scripts/rollback-dns-deployment.sh status

# Verify DNS config
curl http://localhost:8081/api/dns/config
```

## Troubleshooting

### Common Issues

1. **PowerDNS Container Won't Start**
   ```bash
   # Check logs
   docker compose -f docker-compose.powerdns.yml logs powerdns
   
   # Common causes:
   # - Database not ready
   # - Port 53 already in use
   # - Configuration errors
   ```

2. **DNS Queries Not Working**
   ```bash
   # Check port 53 binding
   sudo lsof -i :53
   
   # Check PowerDNS logs
   docker compose -f docker-compose.powerdns.yml logs powerdns
   
   # Test database connection
   docker compose -f docker-compose.powerdns.yml exec powerdns-db \
     psql -U powerdns -c "SELECT * FROM domains;"
   ```

3. **Feature Flags Not Working**
   ```bash
   # Check DNS config endpoint
   curl http://localhost:8081/api/dns/config
   
   # Verify environment variables
   docker compose -f docker-compose.production.yml exec prism-server env | grep POWERDNS
   ```

4. **High Error Rates**
   ```bash
   # Check Prometheus metrics
   curl http://localhost:8081/metrics | grep dns
   
   # Check application logs
   docker compose -f docker-compose.production.yml logs prism-server
   ```

### Emergency Contacts

- **System Administrator**: Check on-call rotation
- **DNS Team**: DNS operations team
- **DevOps**: Infrastructure team

## AWS Security Group Requirements

Add these rules to your EC2 security group:

```bash
# DNS UDP
aws ec2 authorize-security-group-ingress \
  --group-id $SECURITY_GROUP_ID \
  --protocol udp \
  --port 53 \
  --cidr 0.0.0.0/0 \
  --group-rule-description "PowerDNS UDP"

# DNS TCP
aws ec2 authorize-security-group-ingress \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 53 \
  --cidr 0.0.0.0/0 \
  --group-rule-description "PowerDNS TCP"

# PowerDNS API (restrict to your IPs)
aws ec2 authorize-security-group-ingress \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 8053 \
  --cidr YOUR_IP_RANGE/32 \
  --group-rule-description "PowerDNS API"
```

## Security Considerations

1. **API Key Management**
   - Use strong, randomly generated API keys
   - Rotate keys regularly
   - Never commit keys to version control

2. **Network Security**
   - Ensure PowerDNS API is not exposed externally
   - Use firewall rules to restrict access
   - Monitor for unauthorized access attempts

3. **Database Security**
   - Use strong database passwords
   - Enable SSL for database connections
   - Regular security updates

## Performance Tuning

### PowerDNS Configuration

```conf
# Optimize for production load
receiver-threads=4
distributor-threads=4
signing-threads=4
max-packet-cache-entries=1000000
max-cache-entries=2000000
```

### Database Optimization

```sql
-- PostgreSQL tuning for PowerDNS
shared_buffers = 256MB
effective_cache_size = 1GB
random_page_cost = 1.1
```

### Monitoring Thresholds

- Query latency: < 50ms
- Error rate: < 1%
- Cache hit rate: > 90%
- Database connections: < 80% of max

## Maintenance

### Regular Tasks

1. **Weekly**: Check PowerDNS logs for errors
2. **Monthly**: Review performance metrics
3. **Quarterly**: Update PowerDNS version
4. **Annually**: Rotate API keys and passwords

### Backup Strategy

1. **PostgreSQL**: Daily automated backups
2. **Configuration**: Version controlled
3. **Zone Data**: Export and backup weekly

## Support and Documentation

- **Internal Wiki**: Link to internal documentation
- **PowerDNS Docs**: https://doc.powerdns.com/
- **Troubleshooting**: See docs/troubleshooting/
- **Monitoring**: See docs/monitoring/