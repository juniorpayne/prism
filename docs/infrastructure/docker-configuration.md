# Docker Configuration Guide

## Overview

This guide covers Docker and Docker Compose configuration for Prism DNS, including container optimization, networking, volume management, and best practices.

## Docker Architecture

```mermaid
graph TB
    subgraph "Docker Host"
        subgraph "Network: prism-network"
            A[Prism Server<br/>Container]
            B[Nginx<br/>Container]
            C[PostgreSQL<br/>Container]
            D[PowerDNS<br/>Container]
            E[Prometheus<br/>Container]
        end
        
        subgraph "Volumes"
            F[(postgres_data)]
            G[(prism_data)]
            H[(powerdns_data)]
            I[(prometheus_data)]
        end
        
        A --> F
        C --> F
        A --> G
        D --> H
        E --> I
    end
    
    subgraph "Ports"
        J[8080:8080<br/>TCP Server]
        K[8081:8081<br/>API Server]
        L[443:443<br/>HTTPS]
        M[53:53<br/>DNS]
    end
    
    A --> J
    A --> K
    B --> L
    D --> M
```

## Docker Installation

### Ubuntu 22.04

```bash
#!/bin/bash
# install-docker.sh

# Remove old versions
sudo apt-get remove docker docker-engine docker.io containerd runc

# Install prerequisites
sudo apt-get update
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
sudo mkdir -m 0755 -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Verify installation
docker --version
docker compose version
```

## Docker Daemon Configuration

### daemon.json

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "5",
    "compress": "true"
  },
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.override_kernel_check=true"
  ],
  "metrics-addr": "127.0.0.1:9323",
  "experimental": true,
  "features": {
    "buildkit": true
  },
  "default-ulimits": {
    "nofile": {
      "Hard": 64000,
      "Name": "nofile",
      "Soft": 64000
    }
  },
  "live-restore": true,
  "userland-proxy": false,
  "default-shm-size": "128M",
  "shutdown-timeout": 30,
  "debug": false,
  "hosts": ["unix:///var/run/docker.sock"],
  "iptables": true,
  "ip-forward": true,
  "ip-masq": true,
  "bridge": "docker0",
  "fixed-cidr": "172.17.0.0/16",
  "default-address-pools": [
    {
      "base": "172.20.0.0/16",
      "size": 24
    }
  ]
}
```

## Docker Compose Configuration

### Production docker-compose.yml

```yaml
version: '3.8'

x-logging: &default-logging
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "5"
    compress: "true"

x-restart-policy: &restart-policy
  restart: unless-stopped

x-healthcheck-defaults: &healthcheck-defaults
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s

services:
  postgres:
    image: postgres:15-alpine
    <<: *restart-policy
    container_name: prism-postgres
    environment:
      POSTGRES_DB: prism
      POSTGRES_USER: prism
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=C"
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db:/docker-entrypoint-initdb.d:ro
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD-SHELL", "pg_isready -U prism -d prism"]
    logging: *default-logging
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M

  prism-server:
    image: ghcr.io/yourorg/prism-server:${VERSION:-latest}
    <<: *restart-policy
    container_name: prism-server
    depends_on:
      postgres:
        condition: service_healthy
      powerdns:
        condition: service_healthy
    environment:
      NODE_ENV: production
      DATABASE_URL: postgresql://prism:${POSTGRES_PASSWORD}@postgres:5432/prism
      POWERDNS_ENABLED: "true"
      POWERDNS_API_URL: "http://powerdns:8053/api/v1"
      POWERDNS_API_KEY: ${PDNS_API_KEY}
      PRISM_SECRET_KEY: ${PRISM_SECRET_KEY}
      LOG_LEVEL: ${LOG_LEVEL:-info}
    volumes:
      - prism_data:/data
      - ./config:/config:ro
    ports:
      - "8080:8080"
      - "127.0.0.1:8081:8081"
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "curl", "-f", "http://localhost:8081/api/health"]
    logging: *default-logging
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    networks:
      - prism-network

  nginx:
    image: nginx:alpine
    <<: *restart-policy
    container_name: prism-nginx
    depends_on:
      prism-server:
        condition: service_healthy
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./web/static:/usr/share/nginx/html:ro
      - ./ssl:/etc/nginx/ssl:ro
      - nginx_logs:/var/log/nginx
    ports:
      - "80:80"
      - "443:443"
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/health"]
    logging: *default-logging
    deploy:
      resources:
        limits:
          cpus: '0.25'
          memory: 256M
    networks:
      - prism-network

  powerdns:
    image: powerdns/pdns-auth-48:latest
    <<: *restart-policy
    container_name: prism-powerdns
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
      PDNS_DEFAULT_TTL: 300
    volumes:
      - powerdns_data:/var/lib/powerdns
    ports:
      - "53:53/udp"
      - "53:53/tcp"
      - "127.0.0.1:8053:8053"
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "pdns_control", "ping"]
    logging: *default-logging
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
    networks:
      - prism-network

volumes:
  postgres_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/postgres
  prism_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/prism
  powerdns_data:
    driver: local
  nginx_logs:
    driver: local

networks:
  prism-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
```

## Container Optimization

### 1. Multi-Stage Builds

```dockerfile
# Dockerfile - Optimized multi-stage build
# Stage 1: Build dependencies
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Build wheels
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /wheels /wheels

# Install Python packages
RUN pip install --no-cache /wheels/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash prism

WORKDIR /app

# Copy application
COPY --chown=prism:prism . .

# Switch to non-root user
USER prism

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

# Run application
CMD ["python", "-m", "server.main"]
```

### 2. Image Size Optimization

```bash
# Analyze image layers
docker history prism-server:latest

# Use dive for detailed analysis
dive prism-server:latest

# Remove unnecessary files in Dockerfile
RUN apt-get update && apt-get install -y package \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /tmp/* /var/tmp/*

# Use .dockerignore
cat > .dockerignore << EOF
.git
.gitignore
.github
*.pyc
__pycache__
.pytest_cache
.coverage
*.log
.env
.env.*
docker-compose*.yml
Dockerfile*
docs/
tests/
scripts/
*.md
EOF
```

## Volume Management

### 1. Volume Types

```yaml
# Named volumes (preferred for data)
volumes:
  postgres_data:
    driver: local
    labels:
      com.prism.volume: "database"
      com.prism.backup: "daily"

# Bind mounts (for config)
volumes:
  - ./config:/config:ro
  - ./logs:/logs:rw

# tmpfs (for temporary data)
tmpfs:
  - /tmp
  - /run
```

### 2. Backup Strategy

```bash
#!/bin/bash
# backup-volumes.sh

# Backup all volumes
for volume in $(docker volume ls -q | grep prism); do
    echo "Backing up volume: $volume"
    
    # Create backup container
    docker run --rm \
        -v $volume:/data \
        -v /backup:/backup \
        alpine \
        tar czf /backup/${volume}_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .
done

# Backup to S3
aws s3 sync /backup s3://prism-backups/volumes/
```

### 3. Volume Maintenance

```bash
# Check volume usage
docker system df -v

# Clean unused volumes
docker volume prune -f

# Inspect volume
docker volume inspect prism_postgres_data

# Volume migration
docker run --rm \
    -v old_volume:/source \
    -v new_volume:/dest \
    alpine \
    sh -c "cd /source && cp -av . /dest"
```

## Network Configuration

### 1. Custom Networks

```yaml
networks:
  frontend:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
  backend:
    driver: bridge
    internal: true
    ipam:
      config:
        - subnet: 172.21.0.0/24
  monitoring:
    driver: bridge
    ipam:
      config:
        - subnet: 172.22.0.0/24
```

### 2. Network Security

```bash
# Isolate containers
docker network create --internal backend-network

# Custom iptables rules
iptables -I DOCKER-USER -i docker0 -j DROP
iptables -I DOCKER-USER -s 172.20.0.0/24 -d 172.20.0.0/24 -j ACCEPT
iptables -I DOCKER-USER -s 172.20.0.0/24 -d 172.21.0.0/24 -j ACCEPT
iptables -I DOCKER-USER -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
```

## Security Hardening

### 1. Security Options

```yaml
services:
  app:
    security_opt:
      - no-new-privileges:true
      - seccomp:unconfined
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
      - SYS_TIME
    read_only: true
    tmpfs:
      - /tmp
      - /run
```

### 2. User Namespace Remapping

```bash
# /etc/docker/daemon.json
{
  "userns-remap": "default"
}

# Create subuid/subgid mappings
echo "dockremap:231072:65536" >> /etc/subuid
echo "dockremap:231072:65536" >> /etc/subgid

# Restart Docker
systemctl restart docker
```

## Resource Management

### 1. CPU and Memory Limits

```yaml
deploy:
  resources:
    limits:
      cpus: '0.50'
      memory: 512M
    reservations:
      cpus: '0.25'
      memory: 256M
```

### 2. Resource Monitoring

```bash
# Real-time stats
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Export metrics
curl http://localhost:9323/metrics | grep container_

# Resource usage over time
docker run -d \
  --name=cadvisor \
  --volume=/:/rootfs:ro \
  --volume=/var/run:/var/run:ro \
  --volume=/sys:/sys:ro \
  --volume=/var/lib/docker/:/var/lib/docker:ro \
  --publish=8080:8080 \
  google/cadvisor:latest
```

## Logging Configuration

### 1. Centralized Logging

```yaml
logging:
  driver: "fluentd"
  options:
    fluentd-address: "localhost:24224"
    tag: "docker.{{.Name}}"
    fluentd-async: "true"
    fluentd-buffer-limit: "1MB"
```

### 2. Log Rotation

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "5"
    compress: "true"
    labels: "service,environment"
    env: "NODE_ENV,VERSION"
```

## Health Checks

### 1. Container Health Checks

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1
```

### 2. Compose Health Checks

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U prism -d prism"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

## Troubleshooting

### Common Issues

1. **Container Won't Start**
   ```bash
   # Check logs
   docker logs container_name --tail 50
   
   # Inspect container
   docker inspect container_name
   
   # Debug interactively
   docker run -it --entrypoint /bin/bash image_name
   ```

2. **Network Issues**
   ```bash
   # List networks
   docker network ls
   
   # Inspect network
   docker network inspect prism-network
   
   # Test connectivity
   docker exec container1 ping container2
   ```

3. **Volume Permissions**
   ```bash
   # Fix permissions
   docker exec container chown -R user:group /data
   
   # Or in Dockerfile
   RUN mkdir -p /data && chown -R prism:prism /data
   ```

## Best Practices

### 1. Image Management
- Use specific tags, not `latest`
- Scan images for vulnerabilities
- Minimize layer count
- Use official base images
- Regular updates

### 2. Container Runtime
- One process per container
- Handle signals properly
- Log to stdout/stderr
- Use health checks
- Graceful shutdown

### 3. Development vs Production
- Separate compose files
- Environment-specific configs
- Different resource limits
- Security hardening in prod
- Debug tools in dev only

---

*Always test Docker changes in development first!*