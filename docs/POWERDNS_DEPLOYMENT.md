# PowerDNS Deployment Guide

This guide explains how to deploy PowerDNS alongside the Prism DNS application using the CI/CD pipeline.

## Overview

PowerDNS provides actual DNS resolution capabilities for the Prism DNS system. The CI/CD pipeline has been enhanced to optionally deploy PowerDNS with its PostgreSQL backend.

## Deployment Methods

### 1. Manual Deployment via GitHub Actions

1. Go to the [Actions tab](https://github.com/juniorpayne/prism/actions) in your repository
2. Select "Direct Deploy to EC2" workflow
3. Click "Run workflow"
4. Check the "Deploy PowerDNS stack" option
5. Click "Run workflow" to start deployment

### 2. Automatic Deployment

You can configure automatic PowerDNS deployment by modifying the workflow trigger in `.github/workflows/deploy-direct.yml`.

## Port Configuration

PowerDNS uses the following ports:

| Service | Port | Protocol | Description |
|---------|------|----------|-------------|
| DNS | 53 | UDP/TCP | DNS queries |
| API | 8053 | TCP | PowerDNS REST API |

**Note**: PowerDNS API uses port 8053 instead of the default 8081 to avoid conflicts with the Prism API.

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

## Environment Configuration

### Production Settings

Create `.env.powerdns` on the EC2 instance:

```bash
PDNS_API_KEY=your-secure-api-key-here
PDNS_DB_PASSWORD=your-secure-database-password
PDNS_DB_NAME=powerdns
PDNS_DB_USER=powerdns
PDNS_DEFAULT_ZONE=your-domain.com
PDNS_API_ALLOW_FROM=10.0.0.0/8,172.16.0.0/12,YOUR_OFFICE_IP/32
```

### Setting Environment Variables

SSH to your EC2 instance and update the environment file:

```bash
ssh -i citadel.pem ubuntu@35.170.180.10
cd ~/prism-deployment
nano .env.powerdns
```

## Deployment Process

The CI/CD pipeline performs the following steps:

1. **Build**: Creates PowerDNS Docker image
2. **Package**: Saves images as compressed tarballs
3. **Transfer**: Copies images and configuration to EC2
4. **Deploy**: Loads images and starts containers
5. **Verify**: Checks health of deployed services

## Post-Deployment Steps

### 1. Verify Deployment

```bash
# Check container status
ssh -i citadel.pem ubuntu@35.170.180.10
cd ~/prism-deployment
docker compose -f docker-compose.powerdns.yml ps

# Check logs
docker compose -f docker-compose.powerdns.yml logs
```

### 2. Create Initial DNS Zone

```bash
# Create your primary zone
curl -X POST -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "managed.your-domain.com.",
    "kind": "Native",
    "nameservers": ["ns1.your-domain.com.", "ns2.your-domain.com."]
  }' \
  http://35.170.180.10:8053/api/v1/servers/localhost/zones
```

### 3. Test DNS Resolution

```bash
# Add a test record
curl -X PATCH -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "rrsets": [{
      "name": "test.managed.your-domain.com.",
      "type": "A",
      "changetype": "REPLACE",
      "records": [{
        "content": "192.168.1.100",
        "disabled": false
      }]
    }]
  }' \
  http://35.170.180.10:8053/api/v1/servers/localhost/zones/managed.your-domain.com.

# Test resolution
dig @35.170.180.10 test.managed.your-domain.com
```

## Health Monitoring

### Manual Health Check

Use the provided health check script:

```bash
# On the EC2 instance
cd ~/prism-deployment
./scripts/check-powerdns-health.sh
```

### Monitoring Endpoints

- PowerDNS API: `http://YOUR_EC2_IP:8053/api/v1/servers/localhost`
- Container status: `docker compose -f docker-compose.powerdns.yml ps`

## Troubleshooting

### Common Issues

1. **Port 53 Permission Denied**
   - Ensure Docker has NET_BIND_SERVICE capability
   - Check if systemd-resolved is using port 53

2. **API Not Accessible**
   - Verify API key is set correctly
   - Check security group allows port 8053
   - Ensure PDNS_API_ALLOW_FROM includes your IP

3. **DNS Queries Not Working**
   - Check if port 53 is open in security group
   - Verify PowerDNS container is running
   - Check zone configuration

### Debug Commands

```bash
# Check PowerDNS logs
docker logs powerdns-server

# Check database connectivity
docker exec powerdns-server pdns_control ping

# List all zones
curl -H "X-API-Key: YOUR_API_KEY" \
  http://localhost:8053/api/v1/servers/localhost/zones

# Check PowerDNS statistics
curl -H "X-API-Key: YOUR_API_KEY" \
  http://localhost:8053/api/v1/servers/localhost/statistics
```

## Rollback Procedure

If deployment fails:

```bash
# Stop PowerDNS containers
docker compose -f docker-compose.powerdns.yml down

# Remove containers and volumes
docker compose -f docker-compose.powerdns.yml down -v

# Clean up images
docker image prune -f
```

## Integration with Prism

Once PowerDNS is deployed, the Prism server can be configured to automatically create DNS records for registered hosts. This integration is implemented in a separate task (SCRUM-49).

## Security Considerations

1. **API Security**: Always use strong API keys
2. **Network Security**: Restrict API access by IP
3. **DNS Security**: Consider enabling DNSSEC
4. **Monitoring**: Set up alerts for unusual query patterns

## Next Steps

1. Configure production environment variables
2. Create DNS zones for your domains
3. Update Prism server configuration to use PowerDNS API
4. Set up monitoring and alerts
5. Configure backup procedures