# Docker Usage Guide for Prism DNS

## ⚠️ IMPORTANT: Correct Docker Commands

### Development Environment

**Starting Services:**
```bash
# ALWAYS use this command for development with PowerDNS
docker compose --profile with-powerdns up -d

# Without PowerDNS (basic development)
docker compose up -d
```

**Stopping Services:**
```bash
docker compose --profile with-powerdns down
```

### Production Environment

```bash
docker compose -f docker-compose.production.yml up -d
```

## ❌ DO NOT USE

Never use these commands or files:
- `docker-compose -f docker-compose.powerdns-test.yml up`
- `docker-compose -f docker-compose.test.yml up`
- Any docker-compose files from the archive directory

## Why This Matters

Using the wrong docker-compose file will cause:
1. **Network Isolation** - Services on different networks cannot communicate
2. **Authentication Failures** - Different passwords in different files
3. **Configuration Mismatches** - Inconsistent environment variables
4. **DNS Zone Creation Failures** - PowerDNS API unreachable

## Troubleshooting

If DNS zones are not being created:
1. Check all services are on the same network:
   ```bash
   docker ps --format "table {{.Names}}\t{{.Networks}}"
   ```
2. Verify DNS health:
   ```bash
   curl http://localhost:8081/api/dns/health
   ```
3. If services are on different networks, restart everything:
   ```bash
   docker compose --profile with-powerdns down
   docker compose --profile with-powerdns up -d
   ```

## Files Structure

- `docker-compose.yml` - Main development configuration (USE THIS)
- `docker-compose.production.yml` - Production configuration
- `archive/docker-compose-files/` - Old/conflicting files (DO NOT USE)