# Container Registry and Image Management

This document describes the container registry setup and image management strategy for the Prism DNS project.

## Overview

We use GitHub Container Registry (ghcr.io) to store and manage Docker images for all Prism DNS components.

## Registry Configuration

- **Registry**: `ghcr.io`
- **Namespace**: `$GITHUB_REPOSITORY_OWNER` (automatically set by GitHub Actions)
- **Authentication**: GitHub token (automatically provided in workflows)

## Images

### Server Image: `ghcr.io/[owner]/prism-server`
- **Description**: Main Prism DNS server with heartbeat monitoring
- **Build Context**: Root directory
- **Dockerfile**: `Dockerfile.production`
- **Platforms**: linux/amd64, linux/arm64

### Web Interface Image: `ghcr.io/[owner]/prism-web`
- **Description**: Web interface for Prism DNS management
- **Build Context**: `./web` directory
- **Dockerfile**: `web/Dockerfile`
- **Platforms**: linux/amd64, linux/arm64

### Client Image: `ghcr.io/[owner]/prism-client`
- **Description**: DNS client for Prism managed DNS
- **Build Context**: Root directory
- **Dockerfile**: `Dockerfile.client` (generated automatically)
- **Platforms**: linux/amd64, linux/arm64

## Tagging Strategy

### Automatic Tags

| Trigger | Tag Pattern | Example | Description |
|---------|-------------|---------|-------------|
| Push to main | `latest` | `ghcr.io/owner/prism-server:latest` | Latest stable version |
| Push to branch | `{branch}` | `ghcr.io/owner/prism-server:develop` | Branch-specific builds |
| Pull request | `pr-{number}` | `ghcr.io/owner/prism-server:pr-123` | PR testing builds |
| Release | `v{version}` | `ghcr.io/owner/prism-server:v1.2.3` | Semantic versioning |
| Any commit | `{branch}-{sha}` | `ghcr.io/owner/prism-server:main-abc1234` | Commit-specific builds |

### Manual Tags
- `stable` - Manually tagged stable releases
- `production` - Currently deployed in production
- `staging` - Currently deployed in staging

## Security

### Vulnerability Scanning
- All images are automatically scanned with Trivy
- Scan results are uploaded to GitHub Security tab
- High/Critical vulnerabilities block deployments

### Access Control
- Registry access requires GitHub authentication
- Push access limited to repository collaborators
- Pull access follows repository visibility settings

### Image Signing
- Images include standard OCI labels with metadata
- Provenance information tracked via GitHub Actions

## Workflows

### Build and Publish Workflow
**File**: `.github/workflows/build-and-publish.yml`

**Triggers**:
- Push to main/develop branches
- Pull requests to main
- Release publication

**Features**:
- Change detection (only build what changed)
- Multi-platform builds (amd64, arm64)
- Automatic tagging
- Security scanning
- Build caching

### Cleanup Workflow
**File**: `.github/workflows/cleanup-images.yml`

**Schedule**: Weekly (Sundays at 02:00 UTC)

**Features**:
- Keeps last 10 versions per package
- Protects `latest`, `main`, `develop` tags
- Manual trigger with dry-run option

## Usage

### Pulling Images

```bash
# Latest version
docker pull ghcr.io/[owner]/prism-server:latest

# Specific version
docker pull ghcr.io/[owner]/prism-server:v1.2.3

# Specific commit
docker pull ghcr.io/[owner]/prism-server:main-abc1234
```

### Running with Docker Compose

```yaml
services:
  prism-server:
    image: ghcr.io/[owner]/prism-server:latest
    # ... other configuration
```

### Local Development

For local development, continue using the existing build process:

```bash
# Build locally
docker build -f Dockerfile.production -t prism-server:local .

# Or use docker-compose
docker-compose up --build
```

## Deployment Integration

### Production Deployment

The registry images are used in production deployments via the generated `docker-compose.registry.yml` file:

```bash
# Pull latest images
docker-compose -f docker-compose.registry.yml pull

# Deploy with registry images
docker-compose -f docker-compose.registry.yml up -d
```

### Environment-Specific Images

- **Development**: Uses local builds or `develop` branch images
- **Staging**: Uses `main` branch images
- **Production**: Uses tagged release images (`v1.2.3`) or `latest`

## Monitoring and Maintenance

### Image Metrics
- Build success/failure rates
- Image sizes and layer counts
- Pull/download statistics
- Security scan results

### Cleanup Policy
- **Retention**: 10 most recent versions per package
- **Protected**: `latest`, `main`, `develop` tags never deleted
- **Schedule**: Weekly automated cleanup
- **Manual**: Can be triggered on-demand

### Storage Optimization
- Multi-stage builds minimize image sizes
- Layer caching reduces build times
- Multi-platform manifests avoid duplication

## Troubleshooting

### Common Issues

**Build failures:**
```bash
# Check workflow logs in GitHub Actions
# Verify Dockerfile syntax
# Check for missing dependencies
```

**Image pull failures:**
```bash
# Verify authentication
docker login ghcr.io -u $GITHUB_ACTOR -p $GITHUB_TOKEN

# Check image exists
docker pull ghcr.io/[owner]/prism-server:latest
```

**Large image sizes:**
```bash
# Analyze image layers
docker history ghcr.io/[owner]/prism-server:latest

# Use dive for detailed analysis
dive ghcr.io/[owner]/prism-server:latest
```

### Support

For issues with the container registry:
1. Check GitHub Actions workflow logs
2. Verify GitHub token permissions
3. Review security scan results
4. Contact repository maintainers

## Migration from Local Images

When moving from local builds to registry images:

1. Update docker-compose files to use registry references
2. Ensure authentication is configured
3. Update deployment scripts
4. Test image pulling and running
5. Monitor for any performance differences

## Future Enhancements

Planned improvements:
- Image signing with Cosign
- Software Bill of Materials (SBOM)
- Additional security scanning tools
- Registry mirroring for high availability
- Custom retention policies per environment