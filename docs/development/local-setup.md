# Local Development Setup Guide

## Overview

This guide helps developers set up a complete Prism DNS development environment on their local machine, including all dependencies and tools.

## Prerequisites

### System Requirements

- **OS**: Ubuntu 20.04+, macOS 12+, or Windows with WSL2
- **RAM**: 8GB minimum (16GB recommended)
- **Storage**: 20GB free space
- **CPU**: 4 cores minimum

### Required Software

1. **Git**
   ```bash
   # Ubuntu/Debian
   sudo apt update && sudo apt install git
   
   # macOS
   brew install git
   
   # Verify
   git --version
   ```

2. **Docker & Docker Compose**
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   
   # Add user to docker group
   sudo usermod -aG docker $USER
   newgrp docker
   
   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   
   # Verify
   docker --version
   docker-compose --version
   ```

3. **Python 3.8+**
   ```bash
   # Ubuntu/Debian
   sudo apt install python3 python3-pip python3-venv
   
   # macOS
   brew install python@3.11
   
   # Verify
   python3 --version
   ```

4. **Node.js (for frontend development)**
   ```bash
   # Install via nvm
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
   source ~/.bashrc
   nvm install 18
   nvm use 18
   
   # Verify
   node --version
   npm --version
   ```

## Repository Setup

### 1. Clone Repository

```bash
# Clone with SSH (recommended)
git clone git@github.com:yourorg/prism-dns.git
cd prism-dns

# Or with HTTPS
git clone https://github.com/yourorg/prism-dns.git
cd prism-dns
```

### 2. Configure Git

```bash
# Set up user info
git config user.name "Your Name"
git config user.email "your.email@example.com"

# Set up commit signing (optional but recommended)
git config commit.gpgsign true
git config user.signingkey YOUR_GPG_KEY

# Configure git hooks
cp scripts/pre-commit .git/hooks/
chmod +x .git/hooks/pre-commit
```

### 3. Install Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Set up hooks
pre-commit install
pre-commit install --hook-type commit-msg

# Run against all files
pre-commit run --all-files
```

## Development Environment

### 1. Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install package in development mode
pip install -e .
```

### 2. Environment Variables

```bash
# Copy example environment
cp .env.example .env.development

# Edit with your values
nano .env.development
```

Required environment variables:
```bash
# Database
POSTGRES_PASSWORD=localdev123
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=prism_dev

# Application
PRISM_ENV=development
PRISM_DEBUG=true
PRISM_SECRET_KEY=dev-secret-key-change-in-production
PRISM_LOG_LEVEL=DEBUG

# PowerDNS
POWERDNS_ENABLED=true
POWERDNS_API_URL=http://localhost:8053/api/v1
POWERDNS_API_KEY=dev-api-key
POWERDNS_DEFAULT_ZONE=dev.prism.local.

# Monitoring (optional)
PROMETHEUS_ENABLED=false
GRAFANA_ENABLED=false
```

### 3. Docker Compose Setup

```bash
# Start all services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Create `docker-compose.dev.yml` for local overrides:
```yaml
version: '3.8'

services:
  postgres:
    ports:
      - "5432:5432"
    environment:
      POSTGRES_PASSWORD: localdev123

  prism-server:
    build:
      context: .
      dockerfile: Dockerfile.dev
    volumes:
      - ./server:/app/server
      - ./client:/app/client
    environment:
      FLASK_ENV: development
      FLASK_DEBUG: 1
    command: python -m flask run --host=0.0.0.0 --port=8081 --reload

  nginx:
    volumes:
      - ./web/static:/usr/share/nginx/html
      - ./nginx/nginx.dev.conf:/etc/nginx/nginx.conf

  powerdns:
    ports:
      - "5353:53/udp"
      - "5353:53/tcp"
      - "8053:8053"
```

## IDE Setup

### Visual Studio Code

1. **Install Extensions**
   ```bash
   # Install recommended extensions
   code --install-extension ms-python.python
   code --install-extension ms-python.vscode-pylance
   code --install-extension ms-azuretools.vscode-docker
   code --install-extension eamodio.gitlens
   code --install-extension dbaeumer.vscode-eslint
   code --install-extension esbenp.prettier-vscode
   ```

2. **Workspace Settings**
   Create `.vscode/settings.json`:
   ```json
   {
     "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
     "python.linting.enabled": true,
     "python.linting.pylintEnabled": true,
     "python.linting.flake8Enabled": true,
     "python.formatting.provider": "black",
     "python.testing.pytestEnabled": true,
     "editor.formatOnSave": true,
     "editor.rulers": [88],
     "files.exclude": {
       "**/__pycache__": true,
       "**/*.pyc": true,
       ".pytest_cache": true,
       ".coverage": true
     }
   }
   ```

3. **Launch Configuration**
   Create `.vscode/launch.json`:
   ```json
   {
     "version": "0.2.0",
     "configurations": [
       {
         "name": "Python: Prism Server",
         "type": "python",
         "request": "launch",
         "module": "server.main",
         "env": {
           "PYTHONPATH": "${workspaceFolder}",
           "PRISM_ENV": "development"
         }
       },
       {
         "name": "Python: Debug Tests",
         "type": "python",
         "request": "launch",
         "module": "pytest",
         "args": ["-v", "-s", "${file}"]
       }
     ]
   }
   ```

### PyCharm

1. **Project Setup**
   - Open project root
   - Configure Python interpreter: `venv/bin/python`
   - Mark directories:
     - `server` as Sources Root
     - `tests` as Test Sources Root

2. **Run Configurations**
   - Add Python configuration for `server.main`
   - Add pytest configuration for tests
   - Set environment variables in run configs

## Database Setup

### 1. Local PostgreSQL

```bash
# Option 1: Using Docker
docker run -d \
  --name postgres-dev \
  -e POSTGRES_USER=prism \
  -e POSTGRES_PASSWORD=localdev123 \
  -e POSTGRES_DB=prism_dev \
  -p 5432:5432 \
  postgres:15-alpine

# Option 2: Native installation
sudo apt install postgresql postgresql-contrib
sudo -u postgres createuser --interactive prism
sudo -u postgres createdb prism_dev
```

### 2. Database Migrations

```bash
# Initialize database
python -m server.database.init_db

# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Add new table"

# Downgrade
alembic downgrade -1
```

### 3. Seed Data

```bash
# Load development data
python scripts/seed_data.py

# Or via SQL
psql -U prism -d prism_dev < scripts/seed_data.sql
```

## Running the Application

### 1. Start Backend Services

```bash
# Using Docker
docker-compose up -d postgres powerdns

# Start Prism server
python -m server.main

# Or with hot reload
FLASK_ENV=development python -m flask run --reload
```

### 2. Start Frontend (if applicable)

```bash
cd web
npm install
npm run dev
```

### 3. Run Client

```bash
# Test client connection
python prism_client.py -c config/client-dev.yaml

# Or programmatically
python
>>> from client import PrismClient
>>> client = PrismClient("localhost", 8080)
>>> client.connect()
>>> client.register("test-host")
```

## Testing

### 1. Unit Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=server --cov=client --cov-report=html

# Run specific test
pytest tests/test_server.py::TestServer::test_connection

# Run with debugging
pytest -v -s --pdb
```

### 2. Integration Tests

```bash
# Start test environment
docker compose --profile with-powerdns up -d

# Run integration tests
pytest tests/integration/ -m integration

# Cleanup
docker compose --profile with-powerdns down -v
```

### 3. Load Testing

```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load/locustfile.py --host=http://localhost:8081

# Open browser to http://localhost:8089
```

## Debugging

### 1. Debug Server

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use IDE debugger with launch config
```

### 2. Debug Docker Containers

```bash
# Attach to running container
docker exec -it prism-server bash

# View real-time logs
docker-compose logs -f prism-server

# Debug networking
docker network inspect prism-dns_default
```

### 3. Database Debugging

```bash
# Connect to database
docker exec -it postgres psql -U prism -d prism_dev

# Common queries
\dt  -- List tables
\d hosts  -- Describe table
SELECT * FROM hosts WHERE status = 'online';

# Query logs
docker exec postgres tail -f /var/log/postgresql/postgresql.log
```

## Common Development Tasks

### 1. Adding a New API Endpoint

```python
# 1. Add route in server/api/routes.py
@app.route('/api/new-endpoint', methods=['GET'])
async def new_endpoint():
    return jsonify({"status": "ok"})

# 2. Add test in tests/test_api.py
def test_new_endpoint(client):
    response = client.get('/api/new-endpoint')
    assert response.status_code == 200

# 3. Update API documentation
# docs/api/endpoints.md
```

### 2. Adding a Database Model

```python
# 1. Create model in server/models/new_model.py
class NewModel(Base):
    __tablename__ = 'new_table'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)

# 2. Create migration
alembic revision --autogenerate -m "Add new_table"

# 3. Add tests
def test_new_model():
    model = NewModel(name="test")
    assert model.name == "test"
```

### 3. Updating Dependencies

```bash
# Update requirements
pip install --upgrade package-name
pip freeze > requirements.txt

# Test with new dependencies
pytest

# Update Docker images
docker-compose build --no-cache
```

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Find process using port
   lsof -i :8080
   
   # Kill process
   kill -9 <PID>
   
   # Or change port in docker-compose.override.yml
   ```

2. **Database Connection Failed**
   ```bash
   # Check PostgreSQL is running
   docker ps | grep postgres
   
   # Check connection
   psql -h localhost -U prism -d prism_dev
   
   # Reset database
   docker-compose down -v
   docker-compose up -d postgres
   ```

3. **Module Import Errors**
   ```bash
   # Ensure virtual env is activated
   which python  # Should show venv path
   
   # Reinstall dependencies
   pip install -r requirements.txt
   
   # Check PYTHONPATH
   export PYTHONPATH="${PYTHONPATH}:${PWD}"
   ```

### Debug Checklist

- [ ] Virtual environment activated?
- [ ] All Docker containers running?
- [ ] Environment variables set?
- [ ] Database migrations run?
- [ ] Ports available?
- [ ] Dependencies installed?

## Development Best Practices

### Code Style

```bash
# Format code
black server/ tests/
isort server/ tests/

# Lint
flake8 server/ tests/
pylint server/

# Type check
mypy server/
```

### Commit Guidelines

```bash
# Good commit messages
git commit -m "feat: Add DNS record validation"
git commit -m "fix: Resolve connection timeout issue"
git commit -m "docs: Update API documentation"
git commit -m "test: Add integration tests for auth"
git commit -m "refactor: Simplify database queries"
```

### Security in Development

- Never commit secrets or credentials
- Use `.env` files for configuration
- Rotate development credentials regularly
- Use HTTPS even in development
- Scan dependencies for vulnerabilities

```bash
# Security scanning
pip install safety
safety check

# Secret scanning
pip install detect-secrets
detect-secrets scan --all-files
```

---

*Happy coding! If you encounter issues, check the troubleshooting section or ask in #dev-help channel.*