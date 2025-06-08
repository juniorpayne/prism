# Direct Deployment to EC2

This document describes the direct deployment approach for the Prism project, which bypasses the need for a Docker registry.

## Overview

The direct deployment workflow builds Docker images in GitHub Actions and transfers them directly to the EC2 instance via SSH/SCP. This approach:

- Eliminates the need for Docker Hub or GitHub Container Registry authentication
- Reduces external dependencies
- Simplifies the deployment process
- Maintains security through SSH key authentication

## Workflow Files

### 1. CI Pipeline (`ci.yml`)
- Runs on all pushes and pull requests
- Performs linting, testing, and security scanning
- Builds Docker images locally using the `load: true` option
- Does not push images to any registry

### 2. Direct Deploy (`deploy-direct.yml`)
- Triggered on pushes to the `main` branch
- Builds production Docker images
- Compresses images as tarballs
- Transfers images directly to EC2 via SCP
- Loads and runs containers on EC2

## Deployment Process

1. **Build Phase**
   - GitHub Actions builds Docker images locally
   - Images are saved as compressed tarballs

2. **Transfer Phase**
   - Images are transferred to EC2 using SCP
   - Uses SSH key authentication (stored in GitHub Secrets)

3. **Deploy Phase**
   - Images are loaded into Docker on EC2
   - Docker Compose is used to orchestrate containers
   - Old containers are stopped before starting new ones

4. **Verification Phase**
   - Health checks verify the deployment
   - API and web interface are tested

## Required GitHub Secrets

- `EC2_SSH_KEY`: Private SSH key for EC2 access
- `EC2_HOST`: EC2 instance IP address (currently hardcoded as 35.170.180.10)
- `EC2_USER`: SSH username (currently hardcoded as ubuntu)

## Advantages

1. **No Registry Dependencies**: No need for Docker Hub or GitHub Container Registry accounts
2. **Simplified Authentication**: Only SSH key needed
3. **Cost Effective**: No registry storage costs
4. **Direct Control**: Full control over the deployment process

## Limitations

1. **Transfer Time**: Large images take time to transfer
2. **Bandwidth**: Uses GitHub Actions and EC2 bandwidth
3. **No Version History**: No registry to store historical image versions

## Usage

To deploy manually:
```bash
# Trigger the workflow from GitHub UI
# Go to Actions -> Direct Deploy to EC2 -> Run workflow
```

To deploy automatically:
```bash
# Push to main branch
git push origin main
```

## Monitoring

Check deployment status:
- GitHub Actions UI for workflow status
- EC2 instance logs for container status
- Health endpoints for service status

## Rollback

Currently, rollback is manual:
1. SSH into EC2 instance
2. Use previous Docker images if available
3. Or trigger a deployment from a previous commit

## Future Improvements

- Add automatic rollback on deployment failure
- Implement blue-green deployments
- Add deployment notifications
- Cache Docker layers on EC2 for faster deployments