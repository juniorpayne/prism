# Sprint 6 Demo Checklist

## Pre-Demo Setup (15 minutes before)

- [ ] **Environment Check**
  - [ ] Docker is running
  - [ ] No containers using ports 8080, 8081, 8090
  - [ ] Clean git status (all changes committed)
  
- [ ] **Clean Start**
  ```bash
  docker compose down -v
  docker compose up -d --build
  ```

- [ ] **Browser Preparation**
  - [ ] Clear cookies/cache for localhost
  - [ ] Close unnecessary tabs
  - [ ] Open developer tools (but minimize)
  - [ ] Disable password manager prompts

- [ ] **Test Critical Flows**
  - [ ] Registration works
  - [ ] Login works
  - [ ] Navigation works
  - [ ] Session timer visible

## Demo Flow Checklist

### Opening (2 min)
- [ ] Welcome and introduce sprint goal
- [ ] Show completed stories list
- [ ] Open web interface

### Part 1: Authentication (10 min)
- [ ] **Registration**
  - [ ] Show validation
  - [ ] Show password strength
  - [ ] Complete registration
  
- [ ] **Email Verification**
  - [ ] Show email sent page
  - [ ] Demo resend with rate limit
  
- [ ] **Login**
  - [ ] Show form features
  - [ ] Password toggle
  - [ ] Successful login

### Part 2: Navigation (5 min)
- [ ] Click nav links (no refresh)
- [ ] Use back/forward buttons
- [ ] Deep link to protected route
- [ ] Show redirect with return URL

### Part 3: Password Recovery (5 min)
- [ ] **Forgot Password**
  - [ ] Show form
  - [ ] Submit request
  - [ ] Show rate limiting
  
- [ ] **Reset Password**
  - [ ] Show token validation
  - [ ] Password requirements
  - [ ] Success flow

### Part 4: Session Management (5 min)
- [ ] Point out session timer
- [ ] Show activity reset
- [ ] Demo warning modal
- [ ] Show auto-logout

### Part 5: Remember Me (5 min)
- [ ] Login with remember me
- [ ] Close browser
- [ ] Show auto-login
- [ ] Demo cross-tab sync
- [ ] Logout clears everything

### Part 6: Technical (3 min)
- [ ] Show network tab
- [ ] Point out auth headers
- [ ] Explain token strategy

### Closing (5 min)
- [ ] Summarize achievements
- [ ] Metrics and quality
- [ ] Q&A
- [ ] Next sprint preview

## Troubleshooting Guide

### If registration fails:
- Check API is running: `curl http://localhost:8081/api/health`
- Check logs: `docker compose logs server`

### If login doesn't work:
- Verify user exists in database
- Check browser console for errors
- Ensure tokens are being stored

### If session timer not showing:
- Refresh page after login
- Check if authenticated: `window.api.tokenManager.isAuthenticated()`

### If auto-login fails:
- Check localStorage for persistent session
- Verify token not expired
- Try different browser

### If rate limiting not working:
- Clear rate limit: `localStorage.removeItem('forgotPasswordLastRequest')`
- Wait 5 minutes or use different email

## Key Talking Points

### Security
- "JWT tokens with secure storage"
- "Automatic token refresh"
- "Session timeout for security"
- "Rate limiting prevents abuse"

### User Experience
- "Real-time validation"
- "Clear error messages"
- "Loading states throughout"
- "Mobile responsive"

### Technical Excellence
- "Modular architecture"
- "Comprehensive testing"
- "Clean, maintainable code"
- "Performance optimized"

## Post-Demo

- [ ] Thank participants
- [ ] Share demo recording (if recorded)
- [ ] Send follow-up with:
  - [ ] Completed stories
  - [ ] Key features
  - [ ] Next sprint plans
- [ ] Update sprint documentation
- [ ] Celebrate team success! 🎉