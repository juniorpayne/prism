# Production Monitoring and Alerting (SCRUM-38)

This document describes the monitoring and alerting infrastructure for the Prism DNS server.

## Overview

The monitoring stack consists of:
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **AlertManager**: Alert routing and notifications
- **Node Exporter**: Host-level metrics

## Quick Start

### Local Deployment
```bash
./scripts/deploy-monitoring.sh local
```

### Production Deployment
```bash
./scripts/deploy-monitoring.sh
```

## Access Points

### Local
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- AlertManager: http://localhost:9093

### Production
- Prometheus: https://prism.thepaynes.ca/prometheus/
- Grafana: https://prism.thepaynes.ca/grafana/
- Metrics endpoint: https://prism.thepaynes.ca/metrics

## Metrics

### Application Metrics

#### HTTP Metrics
- `prism_http_requests_total`: Total HTTP requests by method, endpoint, and status
- `prism_http_request_duration_seconds`: HTTP request duration histogram

#### TCP Connection Metrics
- `prism_tcp_connections_total`: Total TCP connections by status
- `prism_tcp_active_connections`: Current active TCP connections
- `prism_tcp_connection_duration_seconds`: TCP connection duration

#### Host Metrics
- `prism_registered_hosts_total`: Total number of registered hosts
- `prism_online_hosts_total`: Number of online hosts
- `prism_offline_hosts_total`: Number of offline hosts

#### Message Processing
- `prism_messages_processed_total`: Messages processed by type and status
- `prism_message_processing_duration_seconds`: Message processing duration

#### Database Metrics
- `prism_database_queries_total`: Database queries by operation and status
- `prism_database_query_duration_seconds`: Query execution time
- `prism_database_connection_pool_size`: Connection pool size
- `prism_database_connection_pool_used`: Active connections

#### Business Metrics
- `prism_dns_queries_total`: DNS queries by type and status
- `prism_host_registrations_total`: Host registrations
- `prism_host_updates_total`: Host updates

### Infrastructure Metrics (via Node Exporter)
- CPU usage and load average
- Memory usage and availability
- Disk usage and I/O
- Network traffic and errors

## Alerts

### Critical Alerts (Immediate)
- **PrismServerDown**: Server is unreachable
- **HighErrorRate**: Error rate > 10%
- **NoActiveHosts**: No hosts are online
- **DatabaseConnectionPoolExhausted**: No available DB connections
- **DiskSpaceLow**: Less than 10% disk space

### Warning Alerts (15 minutes)
- **HighResponseTime**: p95 response time > 5s
- **ManyHostsOffline**: > 50% hosts offline
- **HighCPUUsage**: CPU > 80%
- **HighMemoryUsage**: Memory > 85%
- **HighTCPConnectionCount**: Connections > 900

### Info Alerts (1 hour)
- Deployment notifications
- Configuration changes
- Scheduled maintenance

## Dashboards

### Prism DNS Overview
The main dashboard includes:
- Server status indicator
- Request rate graph
- Response time percentiles
- Error rate tracking
- Host statistics
- Active connections

### Custom Dashboards
Additional dashboards can be created in Grafana for:
- Detailed performance analysis
- Business metrics tracking
- Infrastructure monitoring
- Alert history

## Configuration

### Adding Metrics
To add new metrics to the application:

```python
from server.monitoring import get_metrics_collector

collector = get_metrics_collector()
collector.record_custom_metric(value)
```

### Alert Configuration
Alerts are defined in `monitoring/rules/prism-alerts.yml`. To add new alerts:

```yaml
- alert: AlertName
  expr: prometheus_expression
  for: duration
  labels:
    severity: critical|warning|info
  annotations:
    summary: "Brief description"
    description: "Detailed description"
```

### Notification Channels
Configure notification channels in `monitoring/alertmanager.yml`:

```yaml
receivers:
  - name: 'critical'
    webhook_configs:
      - url: 'http://your-webhook-endpoint'
    email_configs:
      - to: 'oncall@example.com'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
```

## Troubleshooting

### Prometheus Not Scraping Metrics
1. Check if metrics endpoint is accessible: `curl http://localhost:8080/metrics`
2. Verify Prometheus configuration: `docker exec prism-prometheus promtool check config /etc/prometheus/prometheus.yml`
3. Check Prometheus targets: http://localhost:9090/targets

### Grafana Dashboard Not Loading
1. Verify datasource configuration
2. Check Prometheus connectivity
3. Review dashboard JSON for errors

### Alerts Not Firing
1. Check alert rules syntax: `docker exec prism-prometheus promtool check rules /etc/prometheus/rules/*.yml`
2. Verify AlertManager configuration
3. Check alert state in Prometheus: http://localhost:9090/alerts

## Maintenance

### Backup
- Prometheus data: `/var/lib/prometheus`
- Grafana dashboards: Export via UI or API
- AlertManager config: `monitoring/alertmanager.yml`

### Updates
```bash
docker compose -f docker-compose.monitoring.yml pull
docker compose -f docker-compose.monitoring.yml up -d
```

### Log Rotation
Monitoring logs are automatically rotated by Docker. Configure in docker-compose:
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

## Security Considerations

1. **Access Control**: Secure Grafana with strong passwords and RBAC
2. **Network Security**: Restrict access to monitoring ports
3. **Data Retention**: Configure appropriate retention policies
4. **Sensitive Data**: Avoid exposing sensitive information in metrics

## Performance Impact

The monitoring stack has minimal performance impact:
- Metrics collection: < 1% CPU overhead
- Memory usage: ~100MB for application metrics
- Network: Negligible (local scraping)
- Storage: ~1GB per week (configurable retention)