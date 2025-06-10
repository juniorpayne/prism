# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Prism DNS - A managed DNS solution with automatic host registration and heartbeat monitoring. Clients register their hostnames and IPs with the server, which maintains an up-to-date registry of active hosts.

## Architecture

- **Server**: Python-based TCP server (port 8081) and REST API (port 8080)
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
- **Ports**:
  - 8080: REST API (internal, proxied through nginx)
  - 8081: TCP server for client connections
  - 8090: Web interface (internal, proxied through nginx)
  - 80/443: Nginx reverse proxy (public)
- We use venv in python for this project

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
- **8080**: REST API (direct access)
- **8081**: TCP Server (client connections)
- **8090**: Web Interface (nginx)
- **5432**: PostgreSQL (if using docker-compose.yml)

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
curl http://localhost:8080/api/health
curl http://localhost:8080/metrics

# Run client locally against Docker server
python3 prism_client.py -c prism-client.yaml

# Access web interface
open http://localhost:8090
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
- Port 8081 must be open in AWS security group for clients

### Known Issues
- AsyncDatabaseManager not implemented (SCRUM-41)
- Response builder missing custom fields support (SCRUM-44)
- Some integration tests are flaky in CI environment

### Environment Variables
- `PRISM_SERVER_HOST`: Server bind address (default: 0.0.0.0)
- `PRISM_SERVER_TCP_PORT`: TCP server port (default: 8081)
- `PRISM_SERVER_API_PORT`: API server port (default: 8080)
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

# View metrics
curl https://prism.thepaynes.ca/metrics | grep prism_
```

### Troubleshooting

#### Docker Development Issues
- **Ports already in use**: `docker compose down` then `sudo lsof -i :8080`
- **Container won't start**: Check logs with `docker compose logs server`
- **Database locked**: Remove volume with `docker compose down -v`
- **Code changes not reflected**: Rebuild with `docker compose build --no-cache`
- **Permission issues**: Check file ownership, use `sudo chown -R $USER:$USER .`

#### Production Issues
- If client can't connect: Check port 8081 is open in AWS security group
- If web UI shows no data: Check browser console for API errors
- If deployment fails: Check GitHub Actions logs
- Container logs: `ssh ubuntu@35.170.180.10 "cd ~/prism-deployment && docker compose logs"`

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

### Common Tasks
- Add new API endpoint: Update `server/api/routes/` and `server/api/app.py`
- Add new metric: Update `server/monitoring.py`
- Update client: Modify `client/` modules and test with `prism_client.py`
- Add dashboard: Create JSON in `monitoring/grafana/dashboards/`