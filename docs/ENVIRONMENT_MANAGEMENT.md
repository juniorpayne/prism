# Environment Management and Secrets Guide

This document describes the environment management and secrets handling system for Prism DNS, implementing secure, scalable configuration management across development, staging, and production environments.

## Overview

The environment management system provides:

- **Environment-specific configurations** for development, staging, and production
- **Secure secrets management** using GitHub Secrets and environment variables
- **Automated configuration generation** from templates
- **Deployment workflows** with environment-aware configurations
- **Configuration drift detection** and validation

## Directory Structure

```
environments/
├── development/
│   ├── .env.template                    # Development environment variables
│   ├── docker-compose.override.yml     # Development Docker configuration
│   └── nginx.dev.conf                  # Development nginx config (optional)
├── staging/
│   ├── .env.template                    # Staging environment variables
│   ├── docker-compose.override.yml     # Staging Docker configuration
│   └── nginx.staging.conf              # Staging nginx config (optional)
└── production/
    ├── .env.template                    # Production environment variables
    ├── docker-compose.override.yml     # Production Docker configuration
    └── nginx.production.conf           # Production nginx config (optional)

scripts/
├── generate-config.sh                  # Configuration generation script
└── deploy-with-env.sh                  # Environment-aware deployment script

.github/workflows/
└── deploy-environments.yml             # GitHub Actions deployment workflow
```

## Environment Configurations

### Development Environment

**Purpose**: Local development and testing
- Uses SQLite database
- Relaxed security settings
- Debug mode enabled
- Hot reloading support

**Key Settings**:
```bash
ENVIRONMENT=development
LOG_LEVEL=DEBUG
DATABASE_URL=sqlite:///tmp/prism_dev.db
SSL_ENABLED=false
DEBUG_MODE=true
```

### Staging Environment

**Purpose**: Pre-production testing and validation
- Uses PostgreSQL database
- Production-like security
- Monitoring enabled
- SSL/TLS configured

**Key Settings**:
```bash
ENVIRONMENT=staging
LOG_LEVEL=INFO
DATABASE_URL=postgresql://prism:${DATABASE_PASSWORD}@database:5432/prism_staging
SSL_ENABLED=true
MONITORING_ENABLED=true
```

### Production Environment

**Purpose**: Live production deployment
- PostgreSQL with connection pooling
- Maximum security hardening
- Performance optimization
- Full monitoring and alerting

**Key Settings**:
```bash
ENVIRONMENT=production
LOG_LEVEL=WARNING
DATABASE_URL=postgresql://prism:${DATABASE_PASSWORD}@database:5432/prism_production
SSL_ENABLED=true
RATE_LIMIT_ENABLED=true
```

## GitHub Secrets Configuration

### Required Secrets

Configure the following secrets in your GitHub repository for each environment:

#### All Environments
- `API_SECRET_KEY` - Application secret key for JWT tokens and encryption

#### Staging & Production
- `DATABASE_PASSWORD` - Database password
- `SERVER_HOST` - Server hostname (e.g., staging.prism-dns.com)
- `SERVER_DOMAIN` - Server domain name for SSL certificates

#### Production Only
- `SSH_PRIVATE_KEY` - SSH private key for EC2 access (content of citadel.pem)
- `EC2_HOST` - Production EC2 instance IP/hostname
- `REDIS_PASSWORD` - Redis cache password

#### Optional Secrets
- `NOTIFICATION_WEBHOOK_URL` - Webhook for notifications
- `ALERT_EMAIL` - Email address for alerts
- `ALERT_SLACK_WEBHOOK` - Slack webhook for deployment notifications
- `SENTRY_DSN` - Sentry error tracking DSN
- `EXTERNAL_API_BASE_URL` - External API base URL

### Setting GitHub Secrets

1. Navigate to your repository on GitHub
2. Go to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add each secret with the appropriate name and value

For environment-specific secrets:
1. Go to Settings → Environments
2. Create environments: `development`, `staging`, `production`
3. Add environment-specific secrets to each environment

## Configuration Generation

### Using the Generate Config Script

```bash
# Generate development configuration
./scripts/generate-config.sh --environment development

# Generate production configuration with validation
./scripts/generate-config.sh --environment production --verbose

# Validate configuration without generating files
./scripts/generate-config.sh --environment staging --validate-only

# Dry run to see what would be generated
./scripts/generate-config.sh --environment production --dry-run
```

### Script Options

- `--environment ENV` - Target environment (development|staging|production)
- `--output DIR` - Output directory (default: environment directory)
- `--validate-only` - Only validate, don't generate files
- `--dry-run` - Show what would be generated without creating files
- `--verbose` - Enable verbose output

## Deployment with Environment Management

### Using the Deployment Script

```bash
# Deploy to development locally
./scripts/deploy-with-env.sh --environment development

# Deploy to production with backup and validation
./scripts/deploy-with-env.sh --environment production --target-host 35.170.180.10

# Deploy using registry images
./scripts/deploy-with-env.sh --environment production --deploy-type registry

# Dry run deployment
./scripts/deploy-with-env.sh --environment staging --dry-run --verbose
```

### Deployment Options

- `--environment ENV` - Target environment
- `--target-host HOST` - Target host for remote deployment
- `--deploy-type TYPE` - Deployment type (docker-compose|registry)
- `--no-backup` - Skip backup before deployment
- `--no-validate` - Skip configuration validation
- `--force` - Force deployment even if validation fails
- `--dry-run` - Show what would be deployed
- `--verbose` - Enable verbose output

## GitHub Actions Deployment

### Automatic Deployments

- **Push to `main`** → Deploy to production (requires approval)
- **Push to `develop`** → Deploy to staging
- **Other branches** → Deploy to development

### Manual Deployments

1. Go to Actions tab in GitHub
2. Select "Deploy to Environments" workflow
3. Click "Run workflow"
4. Choose target environment and options
5. Click "Run workflow"

### Environment Protection Rules

#### Production Environment
- **Required reviewers**: At least 1 reviewer required
- **Wait timer**: 5 minutes before deployment
- **Branch restrictions**: Only `main` branch can deploy

#### Staging Environment
- **Wait timer**: 2 minutes before deployment
- **Branch restrictions**: `main` and `develop` branches

## Security Best Practices

### Secrets Management

1. **Never commit secrets** to version control
2. **Use strong, unique passwords** for each environment
3. **Rotate secrets regularly** (every 90 days for production)
4. **Limit access** to production secrets
5. **Use environment-specific secrets** to prevent cross-environment contamination

### Configuration Security

1. **Validate all configurations** before deployment
2. **Use encrypted communication** for secret transmission
3. **Audit configuration changes** with Git history
4. **Monitor for configuration drift** with scheduled checks
5. **Backup configurations** before making changes

### Access Control

1. **Restrict GitHub repository access** to authorized personnel
2. **Use branch protection rules** for production deployments
3. **Require code reviews** for configuration changes
4. **Enable two-factor authentication** for all team members
5. **Regular access reviews** and permission audits

## Configuration Validation

### Automatic Validation

The system automatically validates:
- Required environment variables are set
- Configuration file syntax is correct
- No development secrets in production
- SSL/TLS settings are appropriate for environment
- Database connection strings are valid

### Manual Validation

```bash
# Validate specific environment
./scripts/generate-config.sh --environment production --validate-only

# Check for unsubstituted variables
grep '\${' environments/production/.env

# Verify database connectivity
docker-compose exec prism-server python -c "
import os
from server.database.connection import DatabaseManager
config = {'database': {'path': os.getenv('DATABASE_PATH')}}
db = DatabaseManager(config)
print('Database connection:', db.health_check())
"
```

## Troubleshooting

### Common Issues

#### Missing Environment Variables
```bash
# Error: Missing required environment variables
# Solution: Set the required variables in GitHub Secrets
export DATABASE_PASSWORD="your-secure-password"
export API_SECRET_KEY="your-api-secret"
```

#### Configuration Generation Fails
```bash
# Error: Template substitution failed
# Check for syntax errors in template files
./scripts/generate-config.sh --environment production --verbose
```

#### Deployment Validation Fails
```bash
# Error: Configuration validation failed
# Review the validation output and fix configuration issues
./scripts/generate-config.sh --environment production --validate-only
```

#### SSH Connection Issues
```bash
# Error: SSH connection to EC2 failed
# Verify SSH key and host configuration
ssh -i ~/.ssh/citadel.pem ubuntu@35.170.180.10
```

### Debugging Steps

1. **Check GitHub Secrets**: Verify all required secrets are set
2. **Validate Templates**: Ensure templates have correct syntax
3. **Test Locally**: Run configuration generation locally first
4. **Review Logs**: Check GitHub Actions logs for detailed errors
5. **Manual Deployment**: Try manual deployment to isolate issues

### Configuration Drift Detection

Monitor for configuration drift using:

```bash
# Compare current vs expected configuration
./scripts/generate-config.sh --environment production --validate-only

# Check for modified files
git status
git diff HEAD -- environments/

# Automated drift detection (runs daily via GitHub Actions)
# Check the "Deploy to Environments" workflow results
```

## Migration Guide

### From Manual Configuration

1. **Export current settings** to environment variables
2. **Create environment templates** using current configurations
3. **Test configuration generation** with existing values
4. **Deploy to staging** for validation
5. **Migrate production** with backup and rollback plan

### Adding New Environments

1. **Create environment directory**: `environments/new-environment/`
2. **Copy template files** from similar environment
3. **Customize configuration** for new environment
4. **Add GitHub environment** with protection rules
5. **Update deployment workflows** to include new environment
6. **Test deployment pipeline** with dry run

## Best Practices

### Configuration Management

1. **Use templates** for all environment configurations
2. **Document all variables** with comments in templates
3. **Version control** all configuration changes
4. **Test configurations** in staging before production
5. **Automate validation** in CI/CD pipeline

### Secrets Rotation

1. **Schedule regular rotation** (every 90 days)
2. **Update all environments** simultaneously
3. **Test after rotation** to ensure functionality
4. **Document rotation process** and schedule
5. **Monitor for failed authentications** after rotation

### Deployment Process

1. **Always backup** before production deployment
2. **Deploy during maintenance windows** for production
3. **Monitor deployments** with health checks
4. **Have rollback procedures** ready
5. **Communicate deployments** to stakeholders