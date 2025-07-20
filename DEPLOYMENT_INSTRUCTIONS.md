# PowerDNS Production Deployment Instructions

## Overview
We've aligned the production PowerDNS deployment with the local development setup to ensure consistency between environments.

## Key Changes Made

1. **Networking Configuration**
   - Changed from host network mode to bridge network (same as local)
   - PowerDNS now runs on the same `prism-backend` network as Prism server
   - This allows containers to communicate using container names

2. **New Files Created**
   - `docker-compose.powerdns-production.yml` - Production PowerDNS config matching local setup
   - `scripts/deploy-powerdns-production.sh` - Automated deployment script
   - Updated `.env.production.template` to use `powerdns-server` hostname

## Deployment Steps

### On Production Server:

1. **SSH to production**
   ```bash
   ssh -i citadel.pem ubuntu@35.170.180.10
   ```

2. **Pull latest changes**
   ```bash
   cd ~/prism-deployment
   git pull origin main
   ```

3. **Create PowerDNS environment file** (if not exists)
   ```bash
   cp .env.powerdns.template .env.powerdns
   # Edit .env.powerdns and set:
   # - PDNS_API_KEY to a secure value
   # - PDNS_DB_PASSWORD to a secure value
   ```

4. **Run deployment script**
   ```bash
   ./scripts/deploy-powerdns-production.sh
   ```

5. **Verify deployment**
   ```bash
   # Check PowerDNS is running
   docker compose -f docker-compose.powerdns-production.yml ps
   
   # Test DNS config endpoint
   curl https://prism.thepaynes.ca/api/dns/config
   
   # Check logs if needed
   docker compose -f docker-compose.powerdns-production.yml logs -f
   ```

## What the Deployment Script Does

1. Stops any existing PowerDNS containers
2. Ensures the `prism-backend` network exists
3. Deploys PowerDNS using the production configuration
4. Updates Prism's `.env.production` with correct PowerDNS settings
5. Restarts Prism server to apply changes
6. Verifies connectivity between services

## Expected Result

After deployment:
- PowerDNS API accessible at `http://powerdns-server:8053/api/v1` from Prism container
- DNS service available on port 53 (TCP/UDP)
- PowerDNS API management on port 8053
- Prism can communicate with PowerDNS using container networking

## Troubleshooting

If issues occur:
1. Check container logs: `docker compose -f docker-compose.powerdns-production.yml logs`
2. Verify network connectivity: `docker network inspect prism-backend`
3. Test API from Prism container: 
   ```bash
   docker compose -f docker-compose.production.yml exec prism-server \
     curl -H "X-API-Key: YOUR_KEY" http://powerdns-server:8053/api/v1/servers/localhost
   ```

## Rollback

If needed, disable PowerDNS:
```bash
# Quick disable
sed -i 's/POWERDNS_ENABLED=true/POWERDNS_ENABLED=false/' .env.production
docker compose -f docker-compose.production.yml restart prism-server

# Full removal
docker compose -f docker-compose.powerdns-production.yml down
```