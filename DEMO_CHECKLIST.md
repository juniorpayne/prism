# Sprint 8 Demo Quick Checklist

## Pre-Demo (15 minutes before)
- [ ] Run `docker compose down && docker compose up -d --build`
- [ ] Clear browser cache and cookies
- [ ] Open http://localhost:8090 in main browser
- [ ] Open incognito window for logged-out demos
- [ ] Create fresh test account or verify existing one works
- [ ] Have this checklist printed or on second screen
- [ ] Close unnecessary applications
- [ ] Prepare backup slides in case of technical issues

## Demo Flow Checklist

### 1. Authentication & Registration ✓
- [ ] Show registration page
- [ ] Type weak password → show "Very Weak"
- [ ] Type strong password → show "Strong" 
- [ ] Toggle password visibility
- [ ] Submit registration
- [ ] Show email verification page
- [ ] Go to login
- [ ] Check "Remember Me"
- [ ] Login successfully

### 2. Protected Routes ✓
- [ ] In incognito: try /dashboard → redirects to login
- [ ] Login with redirect → goes back to dashboard
- [ ] While logged in: try /login → redirects to dashboard
- [ ] Show session timer in navbar

### 3. Dashboard & Hosts ✓
- [ ] Show 3 stat cards
- [ ] Mention activity chart (if visible)
- [ ] Navigate to Hosts
- [ ] Search for a host
- [ ] Sort by status
- [ ] Click host for details modal

### 4. Profile Management ✓
- [ ] Click avatar → My Profile
- [ ] Show current profile info
- [ ] Edit Profile
- [ ] Type in bio field
- [ ] Show character count changing color
- [ ] Save changes
- [ ] Show success toast

### 5. Settings ✓
- [ ] Navigate to Settings
- [ ] Click through each section
- [ ] In Security: show active sessions
- [ ] In Notifications: toggle some options
- [ ] Save changes in any section

### 6. Password Change ✓
- [ ] Click "Change Password"
- [ ] Enter current password
- [ ] Type new password slowly
- [ ] Show strength indicator
- [ ] Show requirements updating
- [ ] Cancel (don't submit)

### 7. Activity Log ✓
- [ ] Navigate to Activity
- [ ] Show date filters
- [ ] Change event type filter
- [ ] Apply filters
- [ ] Navigate pagination

### 8. Account Deletion ✓
- [ ] Settings → Account → Delete
- [ ] Step 1: Check understanding box
- [ ] Step 2: Enter password & username
- [ ] Step 3: Show final warning
- [ ] CANCEL (don't delete\!)

### 9. Session & Logout ✓
- [ ] Point out session timer
- [ ] Click Logout
- [ ] Show redirect to login
- [ ] Try protected route again

## Common Issues & Solutions

**Docker not running:**
```bash
docker compose down -v
docker compose up -d --build
```

**Port 8090 in use:**
```bash
sudo lsof -i :8090
kill -9 <PID>
```

**Blank page:**
- Check browser console
- Hard refresh (Ctrl+Shift+R)
- Check docker logs: `docker compose logs`

**Login not working:**
- Check API is running: `curl http://localhost:8081/api/health`
- Check for CORS errors in console
- Try incognito mode

## Key Points to Emphasize

1. **Security**: JWT tokens, password strength, multi-step deletion
2. **UX**: Real-time validation, loading states, responsive design  
3. **Architecture**: SPA, client-side routing, modular components
4. **Future**: 2FA, email verification, API keys, roles

## Questions to Ask

- What features would you prioritize for next sprint?
- Any concerns about the security implementation?
- How does the UX feel? Any pain points?
- Integration requirements with existing systems?

## Post-Demo

- [ ] Stop screen share
- [ ] Thank attendees
- [ ] Ask for questions
- [ ] Note feedback
- [ ] Schedule follow-up if needed
- [ ] Update Jira with feedback
- [ ] Plan next sprint based on input
EOF < /dev/null
