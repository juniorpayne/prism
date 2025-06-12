# PowerDNS Monitoring and Security Guide

## Overview

This guide covers the monitoring and security implementation for PowerDNS in the Prism DNS infrastructure.

## Table of Contents

1. [Monitoring Stack](#monitoring-stack)
2. [Security Configuration](#security-configuration)
3. [Metrics and Dashboards](#metrics-and-dashboards)
4. [Alerting Rules](#alerting-rules)
5. [Log Management](#log-management)
6. [Security Best Practices](#security-best-practices)
7. [Incident Response](#incident-response)

## Monitoring Stack

### Components

1. **PowerDNS Exporter**: Collects metrics from PowerDNS API
2. **DNS Monitor**: Custom health checker for DNS queries
3. **Prometheus**: Metrics storage and alerting
4. **Grafana**: Visualization dashboards
5. **Fluent Bit**: Log collection and processing

### Deployment

```bash
# Deploy monitoring stack with PowerDNS components
docker compose -f docker-compose.monitoring-powerdns.yml up -d

# Verify all components are running
docker compose -f docker-compose.monitoring-powerdns.yml ps
```

### Available Metrics

#### DNS Query Metrics
- `dns_monitor_queries_total`: Total DNS queries by status
- `dns_monitor_query_duration_seconds`: Query response time histogram
- `dns_monitor_query_success`: Success status per domain/record type
- `dns_monitor_records_found`: Number of records found

#### PowerDNS API Metrics
- `prism_powerdns_api_requests_total`: API request counts
- `prism_powerdns_api_request_duration_seconds`: API latency
- `prism_powerdns_record_operations_total`: DNS record operations

#### System Metrics
- CPU and memory usage
- Network I/O
- Disk usage for DNS data

## Security Configuration

### PowerDNS Hardening

The secure configuration (`pdns-secure.conf`) includes:

1. **API Security**
   - Strong API key requirement
   - IP-based access control
   - Optional webserver password

2. **Query Security**
   - Rate limiting
   - UDP packet size limits
   - Query source restrictions

3. **Network Security**
   - Disabled AXFR by default
   - Restricted allow lists
   - EDNS configuration

### Security Script

Run the hardening script on PowerDNS servers:

```bash
sudo ./scripts/security/harden-powerdns.sh
```

This script:
- Creates dedicated user
- Sets secure file permissions
- Configures firewall rules
- Sets up fail2ban
- Applies kernel hardening
- Creates security audit tools

### Security Audit

Regular security checks:

```bash
# Run security audit
/usr/local/bin/powerdns-security-check.sh

# Monitor for security events
/usr/local/bin/powerdns-monitor-security.sh
```

## Metrics and Dashboards

### Grafana Dashboards

1. **PowerDNS Overview Dashboard**
   - Query rate by status
   - Domain health status
   - Query latency percentiles
   - Record operations
   - API performance

Access: http://grafana.yourdomain.com/d/powerdns-overview

### Key Metrics to Monitor

1. **Performance**
   - Query latency (95th percentile < 100ms)
   - Query rate (baseline vs current)
   - Cache hit rate (> 70%)

2. **Availability**
   - DNS service uptime
   - Failed queries percentage (< 1%)
   - API availability

3. **Security**
   - Suspicious query patterns
   - Rate limit violations
   - Unauthorized access attempts

## Alerting Rules

### Critical Alerts

1. **PowerDNS Down**
   - Triggers: Service unavailable for 2 minutes
   - Action: Immediate investigation required

2. **High Query Failure Rate**
   - Triggers: > 25% queries failing
   - Action: Check PowerDNS logs and database

3. **DNS Amplification Attack**
   - Triggers: High rate of ANY/TXT queries
   - Action: Enable rate limiting, block source IPs

### Warning Alerts

1. **High Query Latency**
   - Triggers: 95th percentile > 100ms for 5 minutes
   - Action: Check system resources and query load

2. **Low Cache Hit Rate**
   - Triggers: Cache hit rate < 70%
   - Action: Review cache configuration

3. **API Errors**
   - Triggers: > 10% API requests failing
   - Action: Check API connectivity and authentication

## Log Management

### Log Collection

Fluent Bit configuration collects:
- PowerDNS service logs
- Query logs (when enabled)
- API access logs
- Security events

### Log Analysis

1. **Security Events**
   ```bash
   # View recent security events
   docker logs fluent-bit | grep security
   ```

2. **Query Patterns**
   ```bash
   # Analyze top queried domains
   tail -n 10000 /var/log/powerdns/query.log | \
     awk '{print $4}' | sort | uniq -c | sort -rn | head -20
   ```

3. **Error Analysis**
   ```bash
   # Check for errors
   grep -i error /var/log/powerdns/*.log | tail -50
   ```

### Log Retention

- Service logs: 7 days local, 30 days in CloudWatch
- Query logs: 24 hours (privacy compliance)
- Security logs: 90 days

## Security Best Practices

### 1. Access Control

- Use strong API keys (min 32 characters)
- Implement IP allowlisting
- Regular key rotation (quarterly)
- Separate read-only accounts for monitoring

### 2. Network Security

- Run PowerDNS in isolated network segment
- Use firewall rules to restrict access
- Enable rate limiting at network level
- Monitor for amplification attacks

### 3. Configuration Security

```yaml
# Secure defaults
disable-axfr: yes
allow-dnsupdate-from: ""
query-logging: no  # Enable only for debugging
version-string: "anonymous"
```

### 4. Regular Updates

- Monitor PowerDNS security advisories
- Apply patches within 30 days
- Test updates in staging first
- Document all changes

### 5. Monitoring

- Real-time alerting for security events
- Daily security report reviews
- Weekly trend analysis
- Monthly security audits

## Incident Response

### DNS Amplification Attack

1. **Detection**
   - Alert: "Possible DNS Amplification Attack"
   - High rate of ANY/TXT queries

2. **Response**
   ```bash
   # Block source IPs
   iptables -A INPUT -s <attacker-ip> -j DROP
   
   # Enable stricter rate limiting
   pdns_control set max-udp-queries-per-round 1000
   
   # Notify upstream provider
   ```

3. **Recovery**
   - Monitor query rates
   - Remove IP blocks after 24 hours
   - Document attack patterns

### Cache Poisoning Attempt

1. **Detection**
   - Unusual response patterns
   - Mismatched query IDs

2. **Response**
   ```bash
   # Flush cache
   pdns_control purge-cache
   
   # Review recent queries
   tail -n 1000 /var/log/powerdns/query.log | grep <suspicious-domain>
   ```

3. **Prevention**
   - Enable DNSSEC when ready
   - Use source port randomization
   - Monitor cache contents

### Service Degradation

1. **Detection**
   - High latency alerts
   - Increased error rates

2. **Response**
   ```bash
   # Check system resources
   top -p $(pgrep pdns)
   
   # Review configuration
   pdns_control show-config
   
   # Restart if necessary
   systemctl restart pdns
   ```

3. **Root Cause Analysis**
   - Review metrics history
   - Check for configuration changes
   - Analyze query patterns

## Maintenance Procedures

### Daily Tasks

- Review security alerts
- Check service health
- Monitor query patterns

### Weekly Tasks

- Analyze performance trends
- Review security logs
- Update threat intelligence

### Monthly Tasks

- Run security audit
- Review and update firewall rules
- Test incident response procedures
- Update documentation

### Quarterly Tasks

- Rotate API keys
- Review access controls
- Update security policies
- Conduct security training

## Integration with Prism

### Metrics Collection

Prism server exports DNS operation metrics:
- Record creation success/failure
- API latency
- Sync status

### Health Checks

DNS monitor validates:
- Prism-created records resolve correctly
- Response times are acceptable
- Zone integrity

### Alerting Integration

- Prism alerts on DNS sync failures
- PowerDNS alerts on service issues
- Consolidated view in Grafana

## Troubleshooting

### High Memory Usage

```bash
# Check cache sizes
pdns_control get cache-entries
pdns_control get packet-cache-entries

# Reduce if necessary
pdns_control set max-cache-entries 500000
```

### Slow Queries

```bash
# Check backend latency
pdns_control show-config | grep backend

# Analyze slow queries
tail -f /var/log/powerdns/slow-queries.log
```

### API Connection Issues

```bash
# Test API connectivity
curl -H "X-API-Key: $PDNS_API_KEY" http://localhost:8053/api/v1/servers

# Check API configuration
grep -E "api|webserver" /etc/powerdns/pdns.conf
```

## Conclusion

This monitoring and security implementation provides:
- Real-time visibility into DNS operations
- Proactive alerting for issues
- Security against common attacks
- Compliance with best practices

Regular reviews and updates ensure the system remains secure and performant.