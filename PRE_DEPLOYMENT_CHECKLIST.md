# Pre-Deployment Testing Checklist

## 🚨 MANDATORY: Complete ALL checks before pushing to production

### 1. Local Development Testing

#### A. Start Full Stack Locally
```bash
# Start all services
docker compose up -d

# Verify all containers are running
docker compose ps

# Check logs for errors
docker compose logs -f
```

#### B. API Endpoint Testing
```bash
# Test core API endpoints
curl http://localhost:8081/api/health | jq .
curl http://localhost:8081/api/stats | jq .
curl http://localhost:8081/api/hosts | jq .

# Test any new endpoints added
# Example: curl http://localhost:8081/api/auth/register
```

#### C. Web Interface Testing
1. Open http://localhost:8090 in browser
2. Navigate to ALL pages:
   - Home page
   - Dashboard (#dashboard)
   - About page (#about)
   - Any new pages added
3. Verify:
   - All data loads correctly
   - No JavaScript console errors
   - All visual elements render properly
   - API calls succeed (check Network tab)

#### D. Database Migrations
```bash
# If database changes were made
docker compose exec server alembic upgrade head

# Verify migrations succeeded
docker compose exec server alembic current
```

### 2. Integration Testing

#### A. Client-Server Communication
```bash
# Test TCP server
python client/prism_client.py -c prism-client.yaml

# Verify registration and heartbeat work
```

#### B. Cross-Service Communication
- Test that web UI can fetch data from API
- Test that TCP server updates are reflected in API/web

### 3. Regression Testing

#### A. Run Test Suite
```bash
# Run all tests locally
source venv/bin/activate && pytest

# Run tests in Docker
./scripts/run-tests-docker.sh
```

#### B. Manual Regression Checks
- [ ] Existing hosts still register/heartbeat
- [ ] Dashboard displays uptime correctly
- [ ] All statistics calculate properly
- [ ] No existing features broken

### 4. Production Simulation

#### A. Build Production Images
```bash
docker compose -f docker-compose.production.yml build
```

#### B. Test with Production Config
```bash
# Use production-like environment variables
PRISM_ENV=production docker compose up
```

### 5. Pre-Push Checklist

- [ ] All local tests pass
- [ ] Web interface fully functional
- [ ] No console errors in browser
- [ ] API endpoints return expected data
- [ ] Database migrations tested
- [ ] Code linted and formatted
- [ ] Changes don't break existing features
- [ ] Production config reviewed

### 6. Rollback Plan

Before deploying:
1. Note current production version
2. Prepare rollback commands
3. Have monitoring ready
4. Know how to quickly revert

## 🛑 STOP: Did you complete ALL checks above?

If any check fails, DO NOT PUSH TO PRODUCTION until fixed.

## Common Issues to Check

1. **JavaScript/API Mismatches**
   - Field name differences (e.g., `uptime` vs `uptime_seconds`)
   - Response format changes
   - Missing CORS headers

2. **Configuration Differences**
   - Environment variables
   - Port mappings
   - Database paths

3. **Static Asset Issues**
   - File paths
   - nginx configuration
   - Cache problems

4. **Database Schema**
   - Missing migrations
   - Schema mismatches
   - Data compatibility

## Emergency Contacts

- Production URL: https://prism.thepaynes.ca
- EC2 Instance: 35.170.180.10
- Monitoring: Grafana dashboard (if available)

Remember: It's better to delay a deployment than to break production!