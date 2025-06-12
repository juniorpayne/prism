# Deployment Guide

## Overview

This guide covers the deployment process for Prism DNS, including automated deployments via CI/CD and manual deployment procedures.

## Deployment Architecture

```mermaid
graph TB
    subgraph "GitHub"
        A[GitHub Actions] --> B[Build & Test]
        B --> C[Push Images]
    end
    
    subgraph "AWS EC2"
        C --> D[Pull Images]
        D --> E[Docker Compose]
        E --> F[Prism Server]
        E --> G[Nginx]
        E --> H[PostgreSQL]
        E --> I[PowerDNS]
    end
    
    subgraph "Monitoring"
        F --> J[Prometheus]
        G --> J
        H --> J
        I --> J
        J --> K[Grafana]
    end
```

## Automated Deployment

### Prerequisites

- GitHub repository access
- AWS EC2 instance configured
- Docker and Docker Compose installed
- SSL certificates configured
- Monitoring stack deployed

### Deployment Process

1. **Code Push**
   ```bash
   git add .
   git commit -m "feat: Add new feature"
   git push origin main
   ```

2. **GitHub Actions Triggered**
   - Build Docker images
   - Run tests
   - Security scanning
   - Push to registry

3. **Deployment Approval** (Production only)
   - Go to Actions tab
   - Find deployment workflow
   - Click "Review deployments"
   - Approve or reject

4. **Automatic Deployment**
   - SSH to EC2 instance
   - Pull latest images
   - Run docker-compose up
   - Health checks
   - Monitoring alerts

## Manual Deployment

### Step-by-Step Guide

1. **Connect to EC2**
   ```bash
   ssh -i ~/.ssh/prism-key.pem ubuntu@35.170.180.10
   ```

2. **Navigate to Deployment Directory**
   ```bash
   cd ~/prism-deployment
   ```

3. **Pull Latest Code**
   ```bash
   git pull origin main
   ```

4. **Update Environment Variables**
   ```bash
   # Edit production environment
   nano .env
   
   # Required variables:
   POSTGRES_PASSWORD=secure-password
   PDNS_API_KEY=powerdns-api-key
   PRISM_SECRET_KEY=app-secret-key
   ```

5. **Pull Docker Images**
   ```bash
   docker-compose pull
   ```

6. **Deploy Services**
   ```bash
   # Deploy with zero downtime
   docker-compose up -d --no-deps --scale prism-server=2 prism-server
   sleep 30
   docker-compose up -d --no-deps prism-server
   
   # Or full deployment
   docker-compose up -d
   ```

7. **Verify Deployment**
   ```bash
   # Check running containers
   docker-compose ps
   
   # Check logs
   docker-compose logs -f --tail=100
   
   # Test endpoints
   curl https://prism.thepaynes.ca/api/health
   ```

## Deployment Configurations

### Production Configuration

```yaml
# docker-compose.production.yml
version: '3.8'

services:
  prism-server:
    image: ghcr.io/yourorg/prism-server:latest
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://prism:${POSTGRES_PASSWORD}@postgres:5432/prism
    deploy:
      replicas: 2
      restart_policy:
        condition: any
        delay: 5s
        max_attempts: 3
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Environment-Specific Settings

| Environment | Domain | SSL | Monitoring | Backups |
|------------|--------|-----|------------|---------|
| Production | prism.thepaynes.ca | Let's Encrypt | Full | Daily |
| Staging | staging.prism.thepaynes.ca | Let's Encrypt | Basic | Weekly |
| Development | dev.prism.local | Self-signed | None | None |

## Pre-Deployment Checklist

- [ ] All tests passing
- [ ] Security scan clean
- [ ] Database migrations ready
- [ ] Environment variables updated
- [ ] SSL certificates valid
- [ ] Monitoring alerts configured
- [ ] Backup completed
- [ ] Team notified
- [ ] Maintenance window scheduled (if needed)

## Deployment Scripts

### Zero-Downtime Deployment

```bash
#!/bin/bash
# scripts/deploy-zero-downtime.sh

set -e

echo "🚀 Starting zero-downtime deployment..."

# Health check function
health_check() {
    local service=$1
    local attempts=0
    local max_attempts=30
    
    while [ $attempts -lt $max_attempts ]; do
        if docker-compose exec -T $service curl -f http://localhost:8081/health > /dev/null 2>&1; then
            echo "✅ $service is healthy"
            return 0
        fi
        attempts=$((attempts + 1))
        echo "⏳ Waiting for $service to be healthy... ($attempts/$max_attempts)"
        sleep 2
    done
    
    echo "❌ $service failed health check"
    return 1
}

# Pull latest images
docker-compose pull

# Scale up
docker-compose up -d --no-deps --scale prism-server=2 prism-server

# Wait for new instance
health_check prism-server

# Remove old instance
docker-compose up -d --no-deps prism-server

echo "✅ Deployment complete!"
```

### Rollback Script

```bash
#!/bin/bash
# scripts/rollback.sh

set -e

VERSION=${1:-"previous"}

echo "🔄 Rolling back to version: $VERSION"

if [ "$VERSION" == "previous" ]; then
    # Get previous version from tags
    VERSION=$(docker images --format "{{.Tag}}" | grep -v latest | head -n 1)
fi

# Update docker-compose to use specific version
sed -i "s/:latest/:$VERSION/g" docker-compose.yml

# Deploy previous version
docker-compose up -d

# Verify
sleep 10
docker-compose ps

echo "✅ Rollback to $VERSION complete!"
```

## Health Checks

### Application Health

```bash
# API Health
curl https://prism.thepaynes.ca/api/health

# Expected response:
{
  "status": "healthy",
  "version": "1.2.3",
  "uptime": 3600,
  "database": "connected",
  "dns": "operational"
}
```

### Infrastructure Health

```bash
# Check all services
for service in prism-server nginx postgres powerdns; do
    echo "Checking $service..."
    docker-compose exec $service echo "OK" || echo "FAILED"
done

# Check disk space
df -h

# Check memory
free -m

# Check CPU
top -bn1 | head -10
```

## Post-Deployment Tasks

### 1. Verify Functionality

```bash
# Test registration
python test_client.py --endpoint production

# Test DNS resolution
dig @35.170.180.10 test.managed.prism.local

# Check metrics
curl http://35.170.180.10:8081/metrics | grep prism_
```

### 2. Update Monitoring

```bash
# Verify dashboards
open https://grafana.prism.thepaynes.ca

# Check alerts
curl -X GET https://prometheus.prism.thepaynes.ca/api/v1/alerts
```

### 3. Clear CDN Cache (if applicable)

```bash
# CloudFlare example
curl -X POST "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/purge_cache" \
     -H "Authorization: Bearer ${CF_TOKEN}" \
     -H "Content-Type: application/json" \
     --data '{"purge_everything":true}'
```

## Troubleshooting Deployments

### Common Issues

1. **Container Won't Start**
   ```bash
   # Check logs
   docker-compose logs prism-server
   
   # Check resources
   docker system df
   docker system prune -a
   ```

2. **Database Connection Failed**
   ```bash
   # Test connection
   docker-compose exec postgres psql -U prism -c "SELECT 1"
   
   # Check network
   docker network ls
   docker network inspect prism-deployment_default
   ```

3. **Port Already in Use**
   ```bash
   # Find process using port
   sudo lsof -i :8080
   
   # Kill process
   sudo kill -9 <PID>
   ```

4. **SSL Certificate Issues**
   ```bash
   # Renew certificate
   sudo certbot renew --force-renewal
   
   # Restart nginx
   docker-compose restart nginx
   ```

## Emergency Procedures

### Service Completely Down

1. **Immediate Response**
   ```bash
   # Try restart
   docker-compose restart
   
   # If that fails, recreate
   docker-compose down
   docker-compose up -d
   ```

2. **Use Backup Instance**
   ```bash
   # Switch DNS to backup
   ./scripts/failover.sh backup-instance
   ```

3. **Restore from Backup**
   ```bash
   # Restore database
   ./scripts/restore-db.sh latest
   
   # Restore configuration
   ./scripts/restore-config.sh latest
   ```

## Deployment Metrics

### Key Metrics to Track

- Deployment frequency
- Deployment duration
- Success rate
- Rollback frequency
- Time to recovery

### Monitoring Deployment Success

```promql
# Deployment success rate
rate(deployment_success_total[7d]) / rate(deployment_total[7d])

# Average deployment time
histogram_quantile(0.95, deployment_duration_seconds)

# Failed deployments in last hour
increase(deployment_failed_total[1h])
```

## Security Considerations

### Pre-Deployment Security

1. **Scan Images**
   ```bash
   trivy image ghcr.io/yourorg/prism-server:latest
   ```

2. **Check Secrets**
   ```bash
   # Ensure no secrets in code
   git secrets --scan
   ```

3. **Verify Permissions**
   ```bash
   # Check file permissions
   find . -type f -perm 0777
   ```

### Post-Deployment Security

1. **Verify SSL**
   ```bash
   openssl s_client -connect prism.thepaynes.ca:443
   ```

2. **Check Open Ports**
   ```bash
   sudo netstat -tlnp
   ```

3. **Review Access Logs**
   ```bash
   docker-compose logs nginx | grep -E "4[0-9]{2}|5[0-9]{2}"
   ```

## Continuous Improvement

### Deployment Retrospectives

After each deployment:
1. What went well?
2. What could be improved?
3. Were there any surprises?
4. How can we automate more?

### Optimization Opportunities

- Reduce image size
- Improve build cache
- Parallelize deployments
- Enhance monitoring
- Automate more checks

---

*Remember: Always test deployments in staging before production!*