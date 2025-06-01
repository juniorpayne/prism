# Docker Development Environment (SCRUM-12)

This document describes the Docker-based development environment for the Prism DNS Server.

## Overview

The Docker environment provides:
- **Consistent development environment** across different platforms
- **Isolated services** with proper networking
- **Hot reloading** for development
- **Integrated testing** with coverage reports
- **Production-ready containerization**

## Quick Start

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+

### Start Development Environment

```bash
# Using the helper script (recommended)
./scripts/docker-dev.sh start

# Or using docker-compose directly
docker-compose up -d
```

### Access Services

- **TCP Server**: `localhost:8080`
- **REST API**: `http://localhost:8081`
- **API Documentation**: `http://localhost:8081/docs`

## Docker Services

### Server Service

Main application service running the Prism DNS server.

```yaml
server:
  ports:
    - "8080:8080"  # TCP server
    - "8081:8081"  # REST API
  volumes:
    - .:/app       # Source code mounting for hot reload
```

### Database Service

SQLite database with persistent volume.

```yaml
database:
  volumes:
    - database_data:/data  # Persistent storage
```

### Test Service

Dedicated service for running tests with coverage.

```yaml
tests:
  command: pytest tests/ -v --cov=server --cov-report=html
  profiles: [testing]  # Activated with --profile testing
```

## Development Helper Script

The `scripts/docker-dev.sh` script provides convenient commands:

```bash
# Build images
./scripts/docker-dev.sh build

# Start development environment
./scripts/docker-dev.sh start

# View logs
./scripts/docker-dev.sh logs
./scripts/docker-dev.sh logs server

# Run tests
./scripts/docker-dev.sh test

# Open shell in container
./scripts/docker-dev.sh shell

# Stop services
./scripts/docker-dev.sh stop

# Clean up everything
./scripts/docker-dev.sh clean
```

## Docker Compose Commands

### Basic Operations

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f
docker-compose logs -f server

# Check service status
docker-compose ps
```

### Development Workflow

```bash
# Start with hot reloading
docker-compose up -d server

# Run tests
docker-compose --profile testing run --rm tests

# Access development tools
docker-compose --profile tools run --rm dev-tools bash

# Restart specific service
docker-compose restart server
```

## Multi-Stage Dockerfile

The Dockerfile uses multi-stage builds for different environments:

### Development Stage
- Full development dependencies
- Source code mounting
- Hot reloading support

### Production Stage
- Minimal runtime dependencies
- Optimized for deployment
- Health checks included

### Test Stage
- Additional testing tools
- Coverage reporting
- Test-specific configuration

## Volume Management

### Persistent Volumes

- `database_data`: SQLite database files
- `server_data`: Application data
- `test_coverage`: Test coverage reports

### Development Volumes

- Source code mounting for hot reloading
- Configuration file mounting
- Log file access

## Environment Variables

Key environment variables for configuration:

```bash
# Application environment
PRISM_ENV=development|production|test

# Configuration file path
PRISM_CONFIG_PATH=/app/config/server.yaml

# Python settings
PYTHONPATH=/app
PYTHONUNBUFFERED=1

# Development settings
DEBUG=1
LOG_LEVEL=DEBUG
```

## Networking

Services communicate through the `prism-network` bridge network:

- Server can access database service by hostname `database`
- All services are isolated from host network except mapped ports
- Service discovery works automatically

## Testing in Docker

### Unit Tests

```bash
# Run all tests
docker-compose --profile testing run --rm tests

# Run specific test file
docker-compose --profile testing run --rm tests pytest tests/test_specific.py

# Run with coverage
docker-compose --profile testing run --rm tests pytest --cov=server --cov-report=html
```

### Integration Tests

```bash
# Run integration tests that require database
docker-compose --profile testing run --rm tests pytest tests/test_integration/
```

## Troubleshooting

### Common Issues

**Container won't start:**
```bash
# Check logs
docker-compose logs server

# Rebuild image
docker-compose build --no-cache server
```

**Permission issues:**
```bash
# Fix file permissions
sudo chown -R $USER:$USER .
```

**Port conflicts:**
```bash
# Check what's using the port
sudo lsof -i :8080
sudo lsof -i :8081

# Use different ports in docker-compose.yml
```

**Database issues:**
```bash
# Reset database volume
docker-compose down -v
docker-compose up -d
```

### Performance Optimization

**Faster builds:**
- Use `.dockerignore` to exclude unnecessary files
- Order Dockerfile commands to maximize layer caching
- Use multi-stage builds

**Development speed:**
- Mount only necessary directories
- Use override files for development-specific config
- Enable BuildKit for faster builds

## Production Deployment

For production deployment:

```bash
# Build production image
docker build --target production -t prism-server:latest .

# Run with production compose file
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Security Considerations

- Non-root user in containers
- Minimal base images
- No secrets in images
- Health checks for reliability
- Resource limits in production