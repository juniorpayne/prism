# Deployment Documentation

This document describes the automated deployment process for the Prism DNS project using GitHub Actions and EC2.

> **PowerDNS Deployment**: For instructions on deploying the PowerDNS DNS server component, see [POWERDNS_DEPLOYMENT.md](./POWERDNS_DEPLOYMENT.md)

## Quick Start - Production Deployment

### Prerequisites
- SSH access to production server
- `.env.production` file configured (see `.env.production.example`)
- Docker and Docker Compose installed on server

### Deployment Steps
```bash
# Connect to production server
ssh -i citadel.pem ubuntu@35.170.180.10

# Navigate to deployment directory
cd /home/ubuntu/prism-deployment

# Deploy using the unified compose file
docker compose -f docker-compose.production.yml up -d

# Verify deployment
docker compose -f docker-compose.production.yml ps
curl http://localhost:8081/api/health
curl http://localhost:8081/api/dns/health
```

## Docker Compose Structure

### Simplified Structure (As of July 2025)
- **docker-compose.yml** - Development environment (use with `--profile with-powerdns`)
- **docker-compose.production.yml** - Production environment (includes all services)
- **ARCHIVED: docker-compose.test.yml** - DO NOT USE (moved to archive/)

### Service Configuration
All services run on a single `prism-network` bridge network to ensure proper communication:
- prism-server (main application)
- prism-nginx (web interface)
- powerdns-server (DNS server)
- powerdns-database (PostgreSQL for PowerDNS)

## Overview

The deployment system provides automated, reliable deployments to multiple environments with health checks, rollback capabilities, and comprehensive monitoring.

## Deployment Environments

### Development Environment
- **Trigger**: Automatic on push to `develop` branch
- **Target**: EC2 instance (35.170.180.10)
- **Approval**: None required
- **Database**: Test data, migrations allowed
- **Monitoring**: Basic health checks

### Staging Environment
- **Trigger**: Automatic on push to `main` branch
- **Target**: EC2 instance (35.170.180.10)
- **Approval**: None required
- **Database**: Production-like data, migration testing
- **Monitoring**: Full monitoring suite

### Production Environment
- **Trigger**: Manual trigger with approval required
- **Target**: EC2 instance (35.170.180.10)
- **Approval**: Required from authorized team members
- **Database**: Live data, careful migration handling
- **Monitoring**: Full monitoring with alerting

## Deployment Workflow

### Automatic Deployment
Deployments are automatically triggered when:
1. CI Pipeline completes successfully on `main` or `develop` branches
2. Container images are built and pushed to registry
3. All tests pass and quality gates are met

### Manual Deployment
Deployments can be manually triggered via GitHub Actions:
1. Go to Actions → Deploy to EC2
2. Click "Run workflow"
3. Select environment and image tag
4. For production, approval is required

## Deployment Process

### 1. Pre-deployment Checks
- ✅ Verify container images exist in registry
- ✅ Test SSH connection to EC2 instance  
- ✅ Check current deployment health
- ✅ Create backup of current deployment

### 2. Deployment Execution
- 📦 Create deployment package
- 📤 Upload to EC2 instance
- 💾 Backup current configuration
- 🔄 Perform rolling deployment
- 🏥 Run health checks
- 💨 Execute smoke tests

### 3. Post-deployment
- ✅ Comprehensive health verification
- 📊 Generate deployment summary
- 🧹 Cleanup deployment artifacts
- 📧 Send notifications (if configured)

### 4. Rollback (if needed)
- 🔄 Automatic rollback on failure
- 💾 Restore from backup
- 🏥 Verify service restoration

## Container Images

All deployments use container images from GitHub Container Registry (ghcr.io):

- **Server**: `ghcr.io/[owner]/prism-server:latest`
- **Web**: `ghcr.io/[owner]/prism-web:latest`
- **Database**: `postgres:15-alpine`

## Health Checks

### Container Health
- All containers (prism-server, prism-nginx, prism-database) must be running
- Container logs checked for recent errors
- Resource usage monitoring

### Service Health
- **Web Interface**: HTTP GET to `http://localhost/`
- **API Health**: HTTP GET to `http://localhost/api/health`
- **TCP Server**: TCP connection to `localhost:8080`
- **Database**: PostgreSQL connectivity check

### System Health
- Disk space utilization
- Memory usage monitoring
- Network connectivity verification

## Smoke Tests

Automated tests run after deployment:

1. **Web Interface Content**: Verify expected content is served
2. **API Structure**: Verify health endpoint returns proper JSON
3. **TCP Connectivity**: Test DNS server accepts connections
4. **Database Connection**: Verify database is accessible
5. **File Permissions**: Check container file system access

## Rollback Procedures

### Automatic Rollback
- Triggered automatically if deployment health checks fail
- Restores previous docker-compose configuration
- Restarts services with previous images
- Verifies service restoration

### Manual Rollback
```bash
# Connect to EC2 instance
ssh -i citadel.pem ubuntu@35.170.180.10

# List available backups
ls -la ~/deployment-backups/

# Choose backup to restore from
BACKUP_NAME="20240106-143022-1234567"
cd ~/managedDns

# Stop current services
docker-compose down

# Restore configuration
cp ~/deployment-backups/$BACKUP_NAME/docker-compose.* .

# Restart services
docker-compose -f docker-compose.production.yml up -d

# Verify restoration
curl http://localhost/api/health
```

## Environment Configuration

### Environment Variables
- `PRISM_ENV`: Environment identifier (development/staging/production)
- `PRISM_LOG_LEVEL`: Logging level (DEBUG/INFO/WARNING/ERROR)
- `PRISM_DATABASE_PATH`: Database file path
- `DB_PASSWORD`: Database password (from secrets)

### Secrets Management
- `EC2_SSH_KEY`: SSH private key for EC2 access
- `DB_PASSWORD`: Database password
- `GITHUB_TOKEN`: Container registry access

## Deployment Scripts

### Main Scripts
- `.github/workflows/deploy.yml`: GitHub Actions deployment workflow
- `scripts/deploy-registry.sh`: Registry-based deployment script
- `scripts/deploy-utils.sh`: Deployment utility functions

### Utility Functions
- Health check automation
- Service monitoring
- Backup management
- Rolling update procedures

## Monitoring and Alerting

### Deployment Monitoring
- Deployment success/failure tracking
- Performance metrics during deployment
- Resource utilization monitoring
- Error tracking and logging

### Health Monitoring
- Continuous service health checks
- Automated alerting on failures
- Performance degradation detection
- Resource exhaustion warnings

### Deployment Metrics
- Deployment frequency and duration
- Success/failure rates
- Rollback frequency
- Time to recovery

## Security

### SSH Security
- SSH keys managed in GitHub secrets
- Host key verification enabled
- Non-interactive deployment execution
- Secure key file handling

### Container Security
- Images scanned for vulnerabilities
- Security patches applied automatically
- Principle of least privilege
- Network isolation where possible

### Data Security
- Database passwords encrypted
- No sensitive data in logs
- Audit trail for all deployments
- Secure backup storage

## Troubleshooting

### Common Issues

#### Deployment Fails with SSH Connection Error
```bash
# Check SSH key is correctly set in GitHub secrets
# Verify EC2 instance is running and accessible
# Check security groups allow SSH access
ssh -i citadel.pem ubuntu@35.170.180.10 echo "Connection test"
```

#### Health Checks Fail After Deployment
```bash
# Check container status
docker ps --filter "name=prism-"

# Check container logs
docker logs prism-server
docker logs prism-nginx

# Check service endpoints manually
curl -v http://localhost/
curl -v http://localhost/api/health
nc -v localhost 8080
```

#### Images Not Found in Registry
```bash
# Verify CI pipeline completed successfully
# Check container registry for images
# Verify image tag exists
docker manifest inspect ghcr.io/[owner]/prism-server:latest
```

#### Rollback Fails
```bash
# Check backup directory exists
ls -la ~/deployment-backups/

# Manually restore configuration
cp ~/deployment-backups/latest/docker-compose.production.yml ~/managedDns/

# Restart services manually
cd ~/managedDns
docker-compose down
docker-compose -f docker-compose.production.yml up -d
```

### Log Locations
- **Deployment Logs**: GitHub Actions workflow logs
- **Application Logs**: Docker container logs
- **System Logs**: EC2 system logs (/var/log/)
- **Deployment History**: ~/deployment-backups/

### Support Contacts
- **DevOps Team**: Contact for deployment issues
- **Development Team**: Contact for application issues
- **Infrastructure Team**: Contact for EC2/networking issues

## Best Practices

### Deployment
- Always test in development/staging first
- Use feature flags for risky deployments
- Monitor metrics during and after deployment
- Keep deployment windows short
- Have rollback plan ready

### Monitoring
- Set up comprehensive alerting
- Monitor key metrics continuously
- Regular health check validation
- Performance baseline maintenance

### Security
- Regular security updates
- Audit deployment access
- Secure secret management
- Network security reviews

### Backup and Recovery
- Regular backup verification
- Test restore procedures
- Document recovery processes
- Maintain multiple backup copies

## Future Enhancements

### Planned Improvements
- Blue-green deployment strategy
- Canary deployment support
- Multi-region deployment
- Enhanced monitoring dashboards
- Automated performance testing
- Infrastructure as Code (Terraform)

### Integration Opportunities
- Slack/Teams notifications
- Monitoring tool integration
- Automated security scanning
- Performance testing automation
- Database migration automation

## Migration Guide

### From Local Builds to Registry
1. Update docker-compose files to use registry images
2. Configure authentication for registry access
3. Update deployment scripts to pull from registry
4. Test image pulling and deployment
5. Monitor for performance differences

### Environment Promotion
1. Test in development environment
2. Promote to staging for integration testing
3. Run full test suite in staging
4. Get approval for production deployment
5. Deploy to production with monitoring