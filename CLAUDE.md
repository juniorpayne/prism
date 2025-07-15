# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

[... existing content remains unchanged ...]

## Jira Workflow Notes

- When updating a Jira issue using jira:update_issue you need to use ADF (Atlassian Document Format), But not when createing new issues, ONLY when updating issues.
- After you finish reviewing a jira ticket and it has passed its review you need to change the status to done.
- Jira workflow: todo -> in progress -> waiting for review -> in review -> done
- Always update the status of jira issues when your work affects it.
- **Always update the jira issue status for the current issue you are working on.**

## Development Environment Notes

- Always run tests and execute code in our docker dev container environments.

[... rest of the existing content remains unchanged ...]