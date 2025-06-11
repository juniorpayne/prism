# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Prism DNS - A managed DNS solution with automatic host registration and heartbeat monitoring. Clients register their hostnames and IPs with the server, which maintains an up-to-date registry of active hosts.

## Architecture

- **Server**: Python-based TCP server (port 8080) and REST API (port 8081)
- **Client**: Python client that registers and sends heartbeats
- **Web Interface**: Static HTML/JS frontend served by nginx (port 8090)
- **Database**: SQLite for development, PostgreSQL ready for production
- **Deployment**: Docker-based with docker-compose

## Development Status

- ✅ Core functionality implemented (registration, heartbeat, API, web UI)
- ✅ Production deployment on AWS EC2
- ✅ HTTPS enabled with Let's Encrypt
- ✅ CI/CD pipeline with GitHub Actions
- ✅ Monitoring stack (Prometheus, Grafana, AlertManager)
- ✅ Security hardening implemented

## Current State

- **Production URL**: https://prism.thepaynes.ca
- **EC2 Instance**: 35.170.180.10
- We use venv in python for this project

## Production Ports and Services

### Public-Facing Ports
- **443 (HTTPS)**: Main nginx reverse proxy at prism.thepaynes.ca
  - Serves web interface from `/`
  - Proxies API requests from `/api/*` to internal nginx on port 8090
- **8080**: TCP server for client connections (MUST be open in AWS security group)
  - Direct client-to-server communication for registration and heartbeats

### Internal Ports (Docker containers on EC2)
- **8081**: REST API (FastAPI) - NOT exposed externally
  - Only accessible within Docker network
  - Proxied by nginx container
  - Prometheus metrics available at `/metrics` (not proxied by nginx)
- **8090**: Nginx container serving web interface
  - Proxies `/api/*` requests to API server on port 8081
  - Serves static web files
  - Only exposed to localhost for reverse proxy access
  - Note: `/metrics` endpoint is NOT proxied (only `/api/*` paths)

### Port Flow in Production
```
[Internet]
    |
    ├── HTTPS (443) ──→ [Reverse Proxy @ prism.thepaynes.ca]
    |                            |
    |                            └──→ localhost:8090 ──→ [Nginx Container]
    |                                                            |
    |                                                            ├── /api/* ──→ prism-server:8081 [API]
    |                                                            └── /* ──→ Static Files
    |
    └── TCP (8080) ──→ [TCP Server Container] ← Direct client connections

[Prometheus Scraping]
    |
    └── Direct to EC2:8081/metrics (requires security group access)
```

1. User visits https://prism.thepaynes.ca → Reverse proxy (443)
2. Reverse proxy forwards to → Nginx container (8090)
3. Nginx container serves static files OR proxies `/api/*` to → API server (8081)
4. Clients connect directly to → TCP server (8080)

## Key Project Specifics

### Testing
- Run tests with: `pytest`
- Coverage report: `pytest --cov=server --cov=client`
- Integration tests may fail in CI due to Docker networking

### Local Development

#### Docker Development Environment
```bash
# Start all services (server, web, database)
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down

# Rebuild after code changes
docker compose build
docker compose up -d

# Clean rebuild (removes volumes)
docker compose down -v
docker compose up -d --build
```

#### Service Ports (Local Development)
- **8080**: TCP Server (client connections)
- **8081**: REST API (direct access)
- **8090**: Web Interface (nginx) - NOT used in dev by default
- **5432**: PostgreSQL (if using production docker-compose)

#### Development Files
- `docker-compose.yml`: Main development stack
- `docker-compose.override.yml`: Local overrides
- `docker-compose.production.yml`: Production config (on EC2)
- `docker-compose.monitoring.yml`: Monitoring stack
- `Dockerfile`: Multi-stage build for server
- `Dockerfile.production`: Production server image
- `web/Dockerfile`: Nginx web interface

#### Quick Testing
```bash
# Test endpoints
curl http://localhost:8081/api/health
curl http://localhost:8081/metrics

# Run client locally against Docker server
python3 prism_client.py -c prism-client.yaml

# Access web interface (dev mode - no nginx)
# The API is served directly from FastAPI on port 8081
# To use the web interface in dev, open index.html directly or use a local server
```

#### Docker Commands
```bash
# Execute commands in running container
docker compose exec server bash
docker compose exec server sqlite3 /data/prism.db

# View real-time logs
docker compose logs -f server
docker compose logs -f nginx

# Check container status
docker compose ps

# Restart specific service
docker compose restart server
```

### Deployment
- All deployments go through GitHub Actions (not manual scripts)
- Main branch auto-deploys to production
- Deployment workflow: `.github/workflows/deploy-direct.yml`
- Monitoring can be deployed separately or with main app

### Configuration
- Server config: Environment variables (PRISM_SERVER_TCP_PORT, PRISM_SERVER_API_PORT, etc.)
- Client config: YAML file (prism-client.yaml)
- Port 8080 must be open in AWS security group for clients (TCP connections)

### Nginx Configuration Differences

#### Development Environment
- No nginx container by default in `docker-compose.yml`
- API served directly from FastAPI on port 8081
- Web interface can be accessed via file:// or python http.server
- No reverse proxy needed for local development

#### Production Environment
- Nginx container (`prism-nginx`) runs on port 8090
- Uses `nginx.simple.conf` configuration
- Proxies `/api/*` requests to `prism-server:8081`
- Serves static web files from `/usr/share/nginx/html`
- Service names in docker-compose MUST match nginx upstream config:
  - Service name: `prism-server` (not `server`)
  - Nginx expects: `prism-server:8081`

#### HTTPS Reverse Proxy (prism.thepaynes.ca)
- Runs on the host system (not in Docker)
- Configured in `/etc/nginx/sites-available/prism`
- Forwards all requests to `localhost:8090` (nginx container)
- Handles SSL termination with Let's Encrypt certificates
- Must proxy `/api/*` to port 8090, NOT 8080 (common mistake!)

### Known Issues
- AsyncDatabaseManager not implemented (SCRUM-41)
- Response builder missing custom fields support (SCRUM-44)
- Some integration tests are flaky in CI environment

### Environment Variables
- `PRISM_SERVER_HOST`: Server bind address (default: 0.0.0.0)
- `PRISM_SERVER_TCP_PORT`: TCP server port (default: 8080)
- `PRISM_SERVER_API_PORT`: API server port (default: 8081)
- `PRISM_DATABASE_PATH`: Database file path
- `PRISM_LOGGING_LEVEL`: Log level (DEBUG, INFO, WARNING, ERROR)

## Development Practices

- Each user story requires the following: 
  1. definition of done
  2. testable 
  3. TDD driven
  4. Unit Tests
  5. Acceptance criteria

## Jira Workflow Notes

- When updating a Jira issue using jira:update_issue you need to use ADF (Atlassian Document Format)
- After you finish reviewing a jira ticket and it has passed its review you need to change the status to done.
- Jira workflow: todo -> in progress -> waiting for review -> in review -> done

## Review Process

- Once you have finished a user story you should put it in the "WAITING FOR REVIEW" column for someone to pick it up and do a code and functionality review.

## User Story Review Guidelines

- When reviewing a user story:
  1. Fully understand the contents of the user story
  2. Ensure you can run the code with no errors
  3. Review the code and verify it behaves as expected
  4. Think critically about any potential missing elements
  5. Check the acceptance criteria
  6. Provide feedback only if required
  7. Once verified, move the issue status to "DONE"

## Development Workflow

### Docker-based Development
1. Make code changes locally
2. Rebuild and test in Docker: `docker compose up -d --build`
3. Run tests: `docker compose exec server pytest`
4. Check logs: `docker compose logs -f`
5. Commit and push changes
6. CI/CD automatically deploys to production

### Hot Reload Development
For faster development without rebuilding:
```bash
# Mount local code into container (add to docker-compose.override.yml)
volumes:
  - ./server:/app/server
  - ./client:/app/client
```

### Database Access
```bash
# Development (SQLite)
docker compose exec server sqlite3 /data/prism.db ".tables"
docker compose exec server sqlite3 /data/prism.db "SELECT * FROM hosts;"

# View database file
ls -la data/prism.db
```

- Make sure to check in your code into github after each task has been completed.

## User Story Management

- Make sure you always are updating user stories before, during and after doing issues.

## Linting Checks

- Always run the standard linting check command before finishing a coding task:
  ```
  source venv/bin/activate && \
  echo "🔍 Pre-completion linting checks..." && \
  python -m black --check --diff . && \
  python -m isort --check-only --diff . && \
  python -m flake8 --select=E722 . && \
  echo "✅ All linting passed!"
  ```

## Project-Specific Commands

### Quick Health Checks
```bash
# Check API health
curl https://prism.thepaynes.ca/api/health | jq .

# Check registered hosts
curl https://prism.thepaynes.ca/api/hosts | jq .

# View metrics (only accessible directly on EC2, not through HTTPS proxy)
# From EC2 or with security group access:
curl http://35.170.180.10:8081/metrics | grep prism_

# If you need metrics exposed publicly, add to nginx config:
# location /metrics {
#     proxy_pass http://prism_api/metrics;
#     # Add authentication here for security!
# }
```

### Troubleshooting

#### Docker Development Issues
- **Ports already in use**: `docker compose down` then `sudo lsof -i :8080`
- **Container won't start**: Check logs with `docker compose logs server`
- **Database locked**: Remove volume with `docker compose down -v`
- **Code changes not reflected**: Rebuild with `docker compose build --no-cache`
- **Permission issues**: Check file ownership, use `sudo chown -R $USER:$USER .`

#### Production Issues
- If client can't connect: Check port 8080 is open in AWS security group
- If web UI shows no data: Check browser console for API errors
- If deployment fails: Check GitHub Actions logs
- Container logs: `ssh ubuntu@35.170.180.10 "cd ~/prism-deployment && docker compose logs"`

#### Common Port Confusion
- **8080**: TCP server (clients connect here), NOT the API!
- **8081**: REST API (internal only, never exposed directly)
- **8090**: Nginx container (proxies API and serves web files)
- **Easy to remember**: Lower port (8080) = Lower level (TCP), Higher port (8081) = Higher level (HTTP API)

#### Common Docker Commands for Debugging
```bash
# Check what's using a port
sudo lsof -i :8080

# Remove all stopped containers
docker container prune

# Remove unused images
docker image prune -a

# Full cleanup (warning: removes everything)
docker system prune -a --volumes

# Inspect container
docker compose exec server sh -c "ps aux"
docker compose exec server sh -c "netstat -tlnp"
```

### Important Files
- `server/main.py`: Main server entry point
- `client/connection_manager.py`: Client TCP connection logic
- `server/tcp_server.py`: TCP server implementation
- `server/api/app.py`: FastAPI application
- `web/js/api.js`: Frontend API client
- `.github/workflows/deploy-direct.yml`: Main deployment workflow

### Security Notes
- Never commit secrets or API keys
- All production config via environment variables
- SSL certificates auto-renew via Let's Encrypt
- Monitoring endpoints should be secured in production

### Prometheus Monitoring Setup

#### Metrics Endpoint
- **Location**: `http://35.170.180.10:8081/metrics`
- **Access**: Direct to API server, NOT proxied through nginx
- **Security**: Currently requires AWS security group access to port 8081
- **Format**: Prometheus text format with custom prism_* metrics

#### Available Metrics
- `prism_registered_hosts_total`: Total number of registered hosts
- `prism_online_hosts`: Number of currently online hosts
- `prism_offline_hosts`: Number of currently offline hosts
- `prism_heartbeats_received_total`: Total heartbeats received
- `prism_registrations_total`: Total host registrations
- `prism_api_requests_total`: API request count by endpoint
- `prism_api_request_duration_seconds`: API request duration histogram
- Plus standard Python process metrics

#### Prometheus Configuration
To scrape metrics, add to `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'prism-dns'
    static_configs:
      - targets: ['35.170.180.10:8081']
    metrics_path: '/metrics'
```

#### Security Recommendation
If exposing metrics publicly, add authentication to nginx:
```nginx
location /metrics {
    auth_basic "Prometheus Metrics";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://prism_api/metrics;
}
```

### Common Tasks
- Add new API endpoint: Update `server/api/routes/` and `server/api/app.py`
- Add new metric: Update `server/monitoring.py`
- Update client: Modify `client/` modules and test with `prism_client.py`
- Add dashboard: Create JSON in `monitoring/grafana/dashboards/`