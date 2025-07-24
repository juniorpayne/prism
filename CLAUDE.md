# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## API Endpoint Standards

The web application uses a centralized API client (window.api) initialized with base URL `/api`. All API endpoints must follow these patterns:

### Endpoint Patterns
- **User endpoints**: `/users/...` (e.g., `/users/me`, `/users/me/settings`)
- **Auth endpoints**: `/auth/...` (e.g., `/auth/login`, `/auth/register`)
- **Token endpoints**: `v1/tokens` (no leading slash)
- **Host endpoints**: `/hosts/...`
- **DNS endpoints**: `/dns/...`

### Important Rules
1. **NO leading `/api/` in endpoint paths** - The API client already has `/api` as base URL
2. **NO absolute paths** - All paths should be relative to the base URL
3. **Versioned endpoints** should not have a leading slash (e.g., `v1/tokens` not `/v1/tokens`)

### Examples
```javascript
// CORRECT
await window.api.get('/users/me');
await window.api.post('/auth/login', credentials);
await window.api.request('v1/tokens', { method: 'GET' });

// INCORRECT - will result in /api/api/... paths
await window.api.get('/api/users/me');
await window.api.request('/v1/tokens', { method: 'GET' });
```

## Environment Variable Standards

### PowerDNS Configuration
All PowerDNS-related environment variables use the `POWERDNS_` prefix (without `PRISM_`):
- `POWERDNS_ENABLED` - Enable/disable PowerDNS integration
- `POWERDNS_API_URL` - PowerDNS API endpoint
- `POWERDNS_API_KEY` - API authentication key
- `POWERDNS_DEFAULT_ZONE` - Default DNS zone
- `POWERDNS_DEFAULT_TTL` - Default TTL for records
- `POWERDNS_TIMEOUT` - API request timeout
- `POWERDNS_RETRY_ATTEMPTS` - Number of retry attempts
- `POWERDNS_FEATURE_FLAG_PERCENTAGE` - Gradual rollout percentage
- `POWERDNS_FALLBACK_TO_MOCK` - Fall back to mock service if PowerDNS fails

The server's `config.py` is the single source of truth for configuration.

## Jira Workflow Notes

- When updating a Jira issue using jira:update_issue you need to use ADF (Atlassian Document Format), But not when createing new issues, ONLY when updating issues.
- After you finish reviewing a jira ticket and it has passed its review you need to change the status to done.
- Jira workflow: todo -> in progress -> waiting for review -> in review -> done
- Always update the status of jira issues when your work affects it.
- **Always update the jira issue status for the current issue you are working on.**

## Development Environment Notes

- Always run tests and execute code in our docker dev container environments.
- We always run tests and code in the docker container environment
- **CRITICAL**: Always use `docker compose --profile with-powerdns up -d` for development
- **DO NOT USE** old docker-compose files from archive/ directory
- All services must be on the same Docker network (prism-network)

## Production Deployment Guidelines

### Development/Production Parity
- **CRITICAL**: Local development environment must match production configuration exactly
- Use the same Docker networking mode in both environments (bridge networks, not host mode)
- Container names must be consistent between environments for service discovery
- Always test service connectivity between containers before assuming code issues

### Deployment Verification
- **Verify assumptions before making code changes** - issues are often configuration, not code
- When services can't connect, check:
  1. Are containers on the same Docker network?
  2. Are environment variables correctly set and loaded?
  3. Are services using container names (not localhost) for internal communication?
- Container restarts are required to pick up environment variable changes
- Use `docker logs` and `docker inspect` to debug networking issues

### PowerDNS Specific
- PowerDNS must be on the same network as Prism server
- Use `powerdns-server` as the hostname in configurations, not `localhost`
- API URL for internal communication: `http://powerdns-server:8053/api/v1`