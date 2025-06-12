# PowerDNS Deployment Guide

Production deployment guide for PowerDNS with Prism DNS.

## Deployment Overview

This guide covers deploying PowerDNS in production environments with high availability, security, and monitoring.

## Prerequisites

- Linux server (Ubuntu 20.04+ or RHEL 8+)
- Docker and Docker Compose
- PostgreSQL or MySQL database
- SSL certificates for HTTPS
- Monitoring infrastructure (Prometheus/Grafana)

## Deployment Architectures

### Single Server Deployment

Suitable for small to medium deployments.

```yaml
# docker-compose.production.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: powerdns
      POSTGRES_USER: powerdns
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U powerdns"]
      interval: 10s
      timeout: 5s
      retries: 5

  powerdns:
    image: powerdns/pdns-auth-48:latest
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      PDNS_BACKEND: gpgsql
      PDNS_GPGSQL_HOST: postgres
      PDNS_GPGSQL_PORT: 5432
      PDNS_GPGSQL_DBNAME: powerdns
      PDNS_GPGSQL_USER: powerdns
      PDNS_GPGSQL_PASSWORD: ${POSTGRES_PASSWORD}
      PDNS_API: yes
      PDNS_API_KEY: ${PDNS_API_KEY}
      PDNS_WEBSERVER: yes
      PDNS_WEBSERVER_ADDRESS: 0.0.0.0
      PDNS_WEBSERVER_PORT: 8053
    ports:
      - "5353:53/udp"
      - "5353:53/tcp"
      - "8053:8053"
    volumes:
      - ./config/pdns.conf:/etc/powerdns/pdns.conf:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "pdns_control", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  prism-server:
    image: prism-dns:latest
    depends_on:
      powerdns:
        condition: service_healthy
    environment:
      POWERDNS_ENABLED: "true"
      POWERDNS_API_URL: "http://powerdns:8053/api/v1"
      POWERDNS_API_KEY: ${PDNS_API_KEY}
      POWERDNS_DEFAULT_ZONE: ${DNS_ZONE}
    ports:
      - "8080:8080"
      - "8081:8081"
    volumes:
      - prism_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  prism_data:
```

### High Availability Deployment

For production environments requiring high availability.

```yaml
# docker-compose.ha.yml
version: '3.8'

services:
  # PostgreSQL Primary
  postgres-primary:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: powerdns
      POSTGRES_USER: powerdns
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_REPLICATION_MODE: master
      POSTGRES_REPLICATION_USER: replicator
      POSTGRES_REPLICATION_PASSWORD: ${REPLICATION_PASSWORD}
    volumes:
      - postgres_primary_data:/var/lib/postgresql/data
    restart: unless-stopped

  # PostgreSQL Replica
  postgres-replica:
    image: postgres:15-alpine
    environment:
      POSTGRES_REPLICATION_MODE: slave
      POSTGRES_MASTER_HOST: postgres-primary
      POSTGRES_REPLICATION_USER: replicator
      POSTGRES_REPLICATION_PASSWORD: ${REPLICATION_PASSWORD}
    volumes:
      - postgres_replica_data:/var/lib/postgresql/data
    restart: unless-stopped

  # PowerDNS Primary
  powerdns-primary:
    image: powerdns/pdns-auth-48:latest
    environment:
      PDNS_BACKEND: gpgsql
      PDNS_GPGSQL_HOST: postgres-primary
      PDNS_GPGSQL_PORT: 5432
      PDNS_GPGSQL_DBNAME: powerdns
      PDNS_GPGSQL_USER: powerdns
      PDNS_GPGSQL_PASSWORD: ${POSTGRES_PASSWORD}
      PDNS_API: yes
      PDNS_API_KEY: ${PDNS_API_KEY}
      PDNS_MASTER: yes
      PDNS_SLAVE: no
      PDNS_WEBSERVER: yes
      PDNS_WEBSERVER_ADDRESS: 0.0.0.0
      PDNS_WEBSERVER_PORT: 8053
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: any
        delay: 5s
        max_attempts: 3

  # PowerDNS Secondary
  powerdns-secondary:
    image: powerdns/pdns-auth-48:latest
    environment:
      PDNS_BACKEND: gpgsql
      PDNS_GPGSQL_HOST: postgres-replica
      PDNS_GPGSQL_PORT: 5432
      PDNS_GPGSQL_DBNAME: powerdns
      PDNS_GPGSQL_USER: powerdns
      PDNS_GPGSQL_PASSWORD: ${POSTGRES_PASSWORD}
      PDNS_API: yes
      PDNS_API_KEY: ${PDNS_API_KEY}
      PDNS_MASTER: no
      PDNS_SLAVE: yes
      PDNS_WEBSERVER: yes
      PDNS_WEBSERVER_ADDRESS: 0.0.0.0
      PDNS_WEBSERVER_PORT: 8053
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 10s

  # HAProxy Load Balancer
  haproxy:
    image: haproxy:2.8-alpine
    volumes:
      - ./config/haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
    ports:
      - "53:53/udp"
      - "53:53/tcp"
      - "8053:8053"
      - "8404:8404"  # Stats page
    restart: unless-stopped

volumes:
  postgres_primary_data:
  postgres_replica_data:
```

## Installation Steps

### 1. System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y \
  docker.io \
  docker-compose \
  git \
  openssl \
  certbot \
  python3-certbot-nginx

# Configure firewall
sudo ufw allow 22/tcp
sudo ufw allow 53/udp
sudo ufw allow 53/tcp
sudo ufw allow 8053/tcp
sudo ufw allow 8080/tcp
sudo ufw allow 8081/tcp
sudo ufw enable
```

### 2. SSL Certificate Setup

```bash
# For Let's Encrypt
sudo certbot certonly --standalone \
  -d dns.yourdomain.com \
  --agree-tos \
  --email admin@yourdomain.com

# For self-signed (development only)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/powerdns.key \
  -out /etc/ssl/certs/powerdns.crt
```

### 3. Database Setup

```bash
# Create database initialization script
cat > init-db.sql << 'EOF'
CREATE SCHEMA IF NOT EXISTS powerdns;

CREATE TABLE powerdns.domains (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  master VARCHAR(128) DEFAULT NULL,
  last_check INT DEFAULT NULL,
  type VARCHAR(6) NOT NULL,
  notified_serial INT DEFAULT NULL,
  account VARCHAR(40) DEFAULT NULL,
  CONSTRAINT c_lowercase_name CHECK (name = LOWER(name))
);

CREATE UNIQUE INDEX name_index ON powerdns.domains(name);

CREATE TABLE powerdns.records (
  id BIGSERIAL PRIMARY KEY,
  domain_id INT DEFAULT NULL,
  name VARCHAR(255) DEFAULT NULL,
  type VARCHAR(10) DEFAULT NULL,
  content VARCHAR(65535) DEFAULT NULL,
  ttl INT DEFAULT NULL,
  prio INT DEFAULT NULL,
  disabled BOOL DEFAULT 'f',
  ordername VARCHAR(255),
  auth BOOL DEFAULT 't',
  CONSTRAINT domain_exists FOREIGN KEY(domain_id) REFERENCES powerdns.domains(id) ON DELETE CASCADE,
  CONSTRAINT c_lowercase_name CHECK (name = LOWER(name))
);

CREATE INDEX rec_name_index ON powerdns.records(name);
CREATE INDEX nametype_index ON powerdns.records(name,type);
CREATE INDEX domain_id ON powerdns.records(domain_id);
CREATE INDEX recordorder ON powerdns.records (domain_id, ordername text_pattern_ops);

-- Additional tables for DNSSEC, metadata, etc.
EOF

# Initialize database
docker run --rm \
  -v $(pwd)/init-db.sql:/init-db.sql \
  -e POSTGRES_PASSWORD=${POSTGRES_PASSWORD} \
  postgres:15-alpine \
  psql -h postgres -U powerdns -f /init-db.sql
```

### 4. Configuration Files

#### PowerDNS Configuration

```conf
# /opt/prism-dns/config/pdns.conf
# General settings
daemon=no
guardian=no
write-pid=no
setuid=pdns
setgid=pdns

# Backend
launch=gpgsql
gpgsql-host=postgres
gpgsql-port=5432
gpgsql-dbname=powerdns
gpgsql-user=powerdns
gpgsql-password=${POSTGRES_PASSWORD}

# DNS settings
local-address=0.0.0.0:53
local-ipv6=::
allow-axfr-ips=127.0.0.1,::1
disable-axfr=no
max-tcp-connections=1000

# API/Webserver
api=yes
api-key=${PDNS_API_KEY}
webserver=yes
webserver-address=0.0.0.0
webserver-port=8053
webserver-allow-from=0.0.0.0/0
webserver-loglevel=normal

# Performance
receiver-threads=4
distributor-threads=4
queue-limit=5000
max-cache-entries=1000000
cache-ttl=60
negquery-cache-ttl=60

# Security
security-poll-suffix=

# Logging
log-dns-queries=no
log-dns-details=no
loglevel=4
```

#### HAProxy Configuration

```conf
# /opt/prism-dns/config/haproxy.cfg
global
    log stdout local0
    maxconn 4096
    user haproxy
    group haproxy

defaults
    log global
    mode tcp
    timeout connect 5s
    timeout client 30s
    timeout server 30s
    option tcplog

# DNS UDP Load Balancing
listen dns_udp
    bind *:53
    mode udp
    balance roundrobin
    server powerdns1 powerdns-primary-1:53 check
    server powerdns2 powerdns-primary-2:53 check
    server powerdns3 powerdns-secondary-1:53 check backup
    server powerdns4 powerdns-secondary-2:53 check backup

# DNS TCP Load Balancing
listen dns_tcp
    bind *:53
    balance roundrobin
    server powerdns1 powerdns-primary-1:53 check
    server powerdns2 powerdns-primary-2:53 check
    server powerdns3 powerdns-secondary-1:53 check backup
    server powerdns4 powerdns-secondary-2:53 check backup

# API Load Balancing
listen api
    bind *:8053
    balance roundrobin
    option httpchk GET /api/v1/servers/localhost
    http-check expect status 200
    server powerdns1 powerdns-primary-1:8053 check
    server powerdns2 powerdns-primary-2:8053 check

# Stats page
listen stats
    bind *:8404
    stats enable
    stats uri /stats
    stats refresh 30s
```

### 5. Deployment Process

```bash
# Clone repository
git clone https://github.com/yourorg/prism-dns.git /opt/prism-dns
cd /opt/prism-dns

# Create environment file
cat > .env << EOF
POSTGRES_PASSWORD=$(openssl rand -base64 32)
REPLICATION_PASSWORD=$(openssl rand -base64 32)
PDNS_API_KEY=$(openssl rand -base64 32)
DNS_ZONE=managed.yourdomain.com.
EOF

# Set permissions
chmod 600 .env

# Build images
docker-compose -f docker-compose.production.yml build

# Start services
docker-compose -f docker-compose.production.yml up -d

# Verify deployment
docker-compose ps
docker-compose logs -f
```

## Post-Deployment Tasks

### 1. Create Default Zone

```bash
# Create zone via API
curl -X POST http://localhost:8053/api/v1/servers/localhost/zones \
  -H "X-API-Key: ${PDNS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "managed.yourdomain.com.",
    "kind": "Native",
    "soa_edit": "INCEPTION-INCREMENT",
    "nameservers": [
      "ns1.yourdomain.com.",
      "ns2.yourdomain.com."
    ]
  }'
```

### 2. Configure Monitoring

```bash
# Deploy monitoring stack
docker-compose -f docker-compose.monitoring-powerdns.yml up -d

# Import Grafana dashboards
./scripts/import-dashboards.sh
```

### 3. Setup Backups

```bash
# Create backup script
cat > /opt/prism-dns/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/powerdns"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup database
docker exec postgres pg_dump -U powerdns powerdns | \
  gzip > "${BACKUP_DIR}/powerdns_${DATE}.sql.gz"

# Backup configuration
tar -czf "${BACKUP_DIR}/config_${DATE}.tar.gz" /opt/prism-dns/config

# Keep only last 7 days
find "${BACKUP_DIR}" -name "*.gz" -mtime +7 -delete
EOF

chmod +x /opt/prism-dns/backup.sh

# Add to crontab
echo "0 2 * * * /opt/prism-dns/backup.sh" | crontab -
```

## Security Hardening

### 1. Network Security

```bash
# Configure iptables rules
sudo iptables -A INPUT -p udp --dport 53 -m recent --set --name DNS
sudo iptables -A INPUT -p udp --dport 53 -m recent --update --seconds 1 --hitcount 10 --name DNS -j DROP

# Save rules
sudo iptables-save > /etc/iptables/rules.v4
```

### 2. API Security

```nginx
# /etc/nginx/sites-available/powerdns-api
server {
    listen 443 ssl http2;
    server_name api.dns.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/dns.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dns.yourdomain.com/privkey.pem;

    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";

    # API proxy
    location /api/ {
        proxy_pass http://localhost:8053/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # Rate limiting
        limit_req zone=api burst=10 nodelay;
        
        # IP allowlist
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        deny all;
    }
}
```

### 3. Audit Logging

```bash
# Enable audit logging
echo "PDNS_LOG_DNS_QUERIES=yes" >> .env
echo "PDNS_LOG_DNS_DETAILS=yes" >> .env

# Configure log rotation
cat > /etc/logrotate.d/powerdns << EOF
/var/log/powerdns/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 640 pdns pdns
    sharedscripts
    postrotate
        docker exec powerdns pdns_control reload
    endscript
}
EOF
```

## Maintenance

### Rolling Updates

```bash
# Update PowerDNS
docker-compose pull powerdns
docker-compose up -d --no-deps --scale powerdns=2 powerdns
# Wait for health check
docker-compose up -d --no-deps powerdns

# Update Prism
docker-compose pull prism-server
docker-compose up -d --no-deps prism-server
```

### Health Checks

```bash
# Check PowerDNS health
curl http://localhost:8053/api/v1/servers/localhost

# Check DNS resolution
dig @localhost -p 5353 test.managed.yourdomain.com

# Check replication status
docker exec postgres psql -U powerdns -c "SELECT * FROM pg_stat_replication;"
```

## Troubleshooting Deployment

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check PostgreSQL logs
   docker logs postgres
   
   # Test connection
   docker exec powerdns pdns_control ping
   ```

2. **API Not Accessible**
   ```bash
   # Check API key
   curl -H "X-API-Key: wrong-key" http://localhost:8053/api/v1
   
   # Check webserver config
   docker exec powerdns grep webserver /etc/powerdns/pdns.conf
   ```

3. **DNS Queries Failing**
   ```bash
   # Check listeners
   docker exec powerdns netstat -tlnup | grep 53
   
   # Test query directly
   docker exec powerdns dig @127.0.0.1 test.local
   ```

## Production Checklist

- [ ] SSL certificates configured
- [ ] Firewall rules applied
- [ ] Database backups scheduled
- [ ] Monitoring deployed
- [ ] Alerts configured
- [ ] Security hardening applied
- [ ] Log rotation configured
- [ ] Documentation updated
- [ ] Runbooks created
- [ ] Team trained