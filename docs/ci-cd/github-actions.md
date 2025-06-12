# GitHub Actions Deep Dive

## Overview

GitHub Actions powers our CI/CD pipeline, providing event-driven automation for builds, tests, and deployments. This guide covers our GitHub Actions implementation in detail.

## Workflow Structure

### Main Deployment Workflow

Location: `.github/workflows/deploy-direct.yml`

```yaml
name: Deploy to EC2

on:
  push:
    branches: [ main ]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Deployment environment'
        required: true
        default: 'production'
        type: choice
        options:
          - production
          - staging
          - development
```

## Key Components

### 1. Triggers

#### Automatic Triggers
- **Push to main**: Deploys to production (with approval)
- **Push to develop**: Deploys to staging
- **Pull Request**: Runs tests only

#### Manual Triggers
```yaml
workflow_dispatch:
  inputs:
    deploy_powerdns:
      description: 'Deploy PowerDNS'
      required: false
      default: true
      type: boolean
```

### 2. Jobs

#### Build Job
```yaml
build:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Build Docker images
      run: |
        docker build -t prism-server:latest .
        docker build -t prism-nginx:latest ./web
```

#### Test Job
```yaml
test:
  needs: build
  runs-on: ubuntu-latest
  services:
    postgres:
      image: postgres:15
      env:
        POSTGRES_PASSWORD: test
      options: >-
        --health-cmd pg_isready
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
```

#### Deploy Job
```yaml
deploy:
  needs: [build, test]
  runs-on: ubuntu-latest
  environment: production
  steps:
    - name: Deploy to EC2
      uses: appleboy/ssh-action@v1.0.0
      with:
        host: ${{ secrets.EC2_HOST }}
        username: ${{ secrets.EC2_USER }}
        key: ${{ secrets.EC2_SSH_KEY }}
        script: |
          cd ~/prism-deployment
          docker-compose pull
          docker-compose up -d
```

### 3. Secrets Management

#### Required Secrets
| Secret Name | Description | Example |
|------------|-------------|---------|
| `EC2_HOST` | EC2 instance IP | `35.170.180.10` |
| `EC2_USER` | SSH username | `ubuntu` |
| `EC2_SSH_KEY` | Private SSH key | `-----BEGIN RSA...` |
| `DOCKER_REGISTRY_TOKEN` | Registry auth | `ghp_xxxx` |
| `SLACK_WEBHOOK` | Notifications | `https://hooks...` |

#### Setting Secrets
```bash
# Via GitHub CLI
gh secret set EC2_HOST --body "35.170.180.10"

# Via UI
Settings → Secrets and variables → Actions → New repository secret
```

### 4. Environment Protection

#### Production Environment Rules
- Required reviewers: 2
- Deployment branches: main only
- Wait timer: 5 minutes
- Required status checks

#### Configuration
```yaml
environment:
  name: production
  url: https://prism.example.com
```

## Advanced Features

### 1. Matrix Builds

Test across multiple configurations:

```yaml
strategy:
  matrix:
    python-version: [3.8, 3.9, 3.10]
    os: [ubuntu-latest, macos-latest]
    
steps:
  - uses: actions/setup-python@v4
    with:
      python-version: ${{ matrix.python-version }}
```

### 2. Caching

Speed up builds with caching:

```yaml
- name: Cache Docker layers
  uses: actions/cache@v3
  with:
    path: /tmp/.buildx-cache
    key: ${{ runner.os }}-buildx-${{ github.sha }}
    restore-keys: |
      ${{ runner.os }}-buildx-

- name: Cache pip dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

### 3. Artifacts

Store build outputs:

```yaml
- name: Upload test results
  uses: actions/upload-artifact@v3
  if: always()
  with:
    name: test-results
    path: |
      coverage.xml
      test-results.xml
```

### 4. Conditional Execution

Run steps based on conditions:

```yaml
- name: Deploy to Production
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'
  run: ./deploy.sh production

- name: Notify on Failure
  if: failure()
  run: ./notify.sh "Deployment failed!"
```

## Workflow Examples

### Feature Branch Workflow

```yaml
name: Feature Branch CI

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run linters
        run: |
          black --check .
          flake8 .
          
      - name: Run tests
        run: pytest --cov
        
      - name: Comment PR
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '✅ All checks passed!'
            })
```

### Scheduled Maintenance

```yaml
name: Scheduled Maintenance

on:
  schedule:
    - cron: '0 2 * * SUN'  # 2 AM every Sunday

jobs:
  maintenance:
    runs-on: ubuntu-latest
    steps:
      - name: Database cleanup
        run: |
          ssh ${{ secrets.EC2_HOST }} \
            "docker exec postgres vacuumdb -U prism -d prism"
            
      - name: Log rotation
        run: |
          ssh ${{ secrets.EC2_HOST }} \
            "docker exec prism-server logrotate /etc/logrotate.conf"
```

### Release Workflow

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Create Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          draft: false
          prerelease: false
```

## Debugging Workflows

### 1. Enable Debug Logging

Add secret: `ACTIONS_RUNNER_DEBUG` = `true`

### 2. SSH Debug Session

```yaml
- name: Setup tmate session
  uses: mxschmitt/action-tmate@v3
  if: ${{ github.event_name == 'workflow_dispatch' && inputs.debug_enabled }}
```

### 3. Workflow Logs

```bash
# Download logs via CLI
gh run view <run-id> --log

# View specific job
gh run view <run-id> --log --job <job-id>
```

## Best Practices

### 1. Security

```yaml
# Never hardcode secrets
- name: Deploy
  env:
    API_KEY: ${{ secrets.API_KEY }}  # Good
    # API_KEY: "hardcoded-key"      # Bad!
    
# Use least privilege
- name: AWS Deploy
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789012:role/GitHubDeployRole
```

### 2. Performance

```yaml
# Run jobs in parallel
jobs:
  test-unit:
    runs-on: ubuntu-latest
    # ...
    
  test-integration:
    runs-on: ubuntu-latest
    # ...
    
  deploy:
    needs: [test-unit, test-integration]  # Wait for both
```

### 3. Reliability

```yaml
# Add timeouts
- name: Deploy
  timeout-minutes: 10
  run: ./deploy.sh
  
# Add retries
- name: Upload artifacts
  uses: actions/upload-artifact@v3
  with:
    name: build
    path: dist/
  continue-on-error: true
  id: upload
  
- name: Retry upload
  if: steps.upload.outcome == 'failure'
  uses: actions/upload-artifact@v3
  with:
    name: build
    path: dist/
```

## Monitoring Workflows

### Workflow Metrics

Track in GitHub Insights:
- Success rate
- Duration trends
- Failure patterns

### Custom Metrics

```yaml
- name: Report metrics
  run: |
    curl -X POST ${{ secrets.METRICS_ENDPOINT }} \
      -d '{
        "workflow": "${{ github.workflow }}",
        "duration": "${{ steps.timer.outputs.duration }}",
        "status": "${{ job.status }}"
      }'
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```yaml
   - name: Make executable
     run: chmod +x ./script.sh
   ```

2. **Cache Miss**
   ```yaml
   - name: Debug cache
     run: |
       echo "Cache key: ${{ hashFiles('**/package-lock.json') }}"
       ls -la ~/.npm/
   ```

3. **Timeout Issues**
   ```yaml
   jobs:
     deploy:
       timeout-minutes: 30  # Increase timeout
   ```

## Integration with Other Tools

### Slack Notifications

```yaml
- name: Slack Notification
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
  if: always()
```

### JIRA Integration

```yaml
- name: Update JIRA
  run: |
    curl -X POST https://jira.company.com/rest/api/2/issue/${{ env.JIRA_ISSUE }}/comment \
      -H "Authorization: Bearer ${{ secrets.JIRA_TOKEN }}" \
      -H "Content-Type: application/json" \
      -d '{"body": "Deployed to production: ${{ github.sha }}"}'
```

## Workflow Templates

Create reusable workflow templates in `.github/workflow-templates/`:

```yaml
name: Standard CI Template
on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string

jobs:
  standard-ci:
    uses: ./.github/workflows/standard-ci.yml
    with:
      environment: ${{ inputs.environment }}
```

---

*For more information, see the [GitHub Actions documentation](https://docs.github.com/en/actions)*