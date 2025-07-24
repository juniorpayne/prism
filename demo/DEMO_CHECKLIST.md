# Sprint Demo Checklist

## Pre-Demo Preparation (30 min before)

### Environment Setup
- [ ] Docker containers running (`docker compose up`)
- [ ] Server accessible at http://localhost:8000
- [ ] Database has clean state (or known demo data)
- [ ] Terminal windows ready:
  - [ ] Terminal 1: For running Alice's client
  - [ ] Terminal 2: For running Bob's client  
  - [ ] Terminal 3: For showing logs
  - [ ] Terminal 4: For API commands

### User Accounts
- [ ] Create Alice account (alice@example.com)
- [ ] Create Bob account (bob@example.com)
- [ ] Create Admin account (admin@example.com)
- [ ] Verify admin has is_admin = true

### API Tokens
- [ ] Generate token for Alice (name: "Alice Demo Client")
- [ ] Generate token for Bob (name: "Bob Demo Client")
- [ ] Update demo/alice-prism-client.yaml with Alice's token
- [ ] Update demo/bob-prism-client.yaml with Bob's token
- [ ] Get JWT tokens for API demos

### Test Run
- [ ] Test Alice's client starts successfully
- [ ] Test Bob's client starts successfully
- [ ] Verify hosts appear in web UI
- [ ] Run cleanup script

## Demo Flow

### 1. Introduction (2 min)
- [ ] Show DEMO_SLIDES.md slide 1-2 (The Problem)
- [ ] Explain why authentication was needed

### 2. Solution Overview (2 min)
- [ ] Show solution architecture diagram
- [ ] Highlight key benefits

### 3. Token Generation Demo (3 min)
- [ ] Log in as Alice
- [ ] Navigate to Profile → API Tokens
- [ ] Generate new token
- [ ] Show token warning (save it!)
- [ ] Show token in list (can't see actual token)

### 4. Client Configuration (3 min)
- [ ] Show old client config (no auth)
- [ ] Show new client config with auth_token
- [ ] Highlight it's a required field
- [ ] Show what happens without token (error)

### 5. Live Demo - Running Clients (5 min)
- [ ] Start Alice's client
- [ ] Show successful authentication in logs
- [ ] Start Bob's client
- [ ] Show both running simultaneously

### 6. User Isolation Demo (5 min)
- [ ] Alice's view:
  - [ ] Login as Alice
  - [ ] Show dashboard - only 1 host
  - [ ] Show hosts list - only alice-laptop
  - [ ] Try to access Bob's host ID - 404
- [ ] Bob's view:
  - [ ] Login as Bob
  - [ ] Show dashboard - only 1 host
  - [ ] Show hosts list - only bob-server
- [ ] Admin view:
  - [ ] Login as Admin
  - [ ] Show normal view first
  - [ ] Toggle "Show all users' hosts"
  - [ ] Show Owner column appears
  - [ ] Show system statistics

### 7. API Demonstration (3 min)
- [ ] Show Alice's API call - only her hosts
- [ ] Show Admin API call without ?all=true
- [ ] Show Admin API call with ?all=true
- [ ] Show statistics endpoint differences

### 8. Security Features (3 min)
- [ ] Token revocation demo
- [ ] Show invalid token behavior
- [ ] Show audit trail (last used)

### 9. Summary (2 min)
- [ ] Recap what was delivered
- [ ] Highlight business value
- [ ] Show completed user stories

### 10. Q&A (5 min)
- [ ] Be ready for common questions
- [ ] Have backup demos ready

## Troubleshooting

### If clients won't start:
- Check token is correct in YAML file
- Check server is running
- Check no old PIDs in /tmp
- Look at client logs

### If web UI issues:
- Clear browser cache
- Check browser console for errors
- Verify user is logged in
- Check JWT token hasn't expired

### If API calls fail:
- Verify JWT token is current
- Check authorization header format
- Ensure endpoints are correct
- Look at server logs

## Post-Demo
- [ ] Run cleanup script
- [ ] Stop all demo clients
- [ ] Save any feedback
- [ ] Note any bugs found
- [ ] Plan fixes if needed

## Backup Plans

### If live demo fails:
- Have screenshots ready
- Show the demo video (if recorded)
- Walk through code changes
- Focus on architecture/design

### Key files to have open:
- `/server/api/routes/hosts.py` (show filtering)
- `/server/auth/models.py` (show APIToken model)
- `/client/heartbeat_manager.py` (show auth_token usage)
- Web UI token management page

## Success Metrics
- [ ] Audience understands the problem solved
- [ ] Authentication flow is clear
- [ ] User isolation is demonstrated
- [ ] Security benefits are apparent
- [ ] Questions are answered satisfactorily