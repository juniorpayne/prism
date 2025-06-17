# Sprint 8 Demo: Account Management and Authentication Enforcement
## Date: June 2025

## Overview
This sprint delivered a complete account management system with authentication enforcement, user profiles, settings, password management, and activity tracking.

## Demo Environment Setup
1. Ensure Docker is running: `docker compose up -d`
2. Access the application at: http://localhost:8090
3. Create demo accounts: `./create_demo_account.py`

## Demo Accounts
**Primary Account:**
- Email: demo@example.com
- Username: demouser
- Password: DemoPass123!

**Secondary Account:**
- Email: admin@example.com
- Username: adminuser
- Password: AdminPass123!

## Demo Flow

### Part 1: Authentication and Registration (5 minutes)

#### 1.1 User Registration
- Navigate to http://localhost:8090
- Click "Register" link
- Show password requirements:
  - Real-time password strength indicator
  - Character requirements (12+ chars, uppercase, lowercase, numbers, special)
  - Password visibility toggle
  - Matching password validation
- Create a new account
- Show email verification sent page
- Note: Email verification is simulated in dev environment

#### 1.2 Login Features
- Navigate to login page
- Show "Remember Me" checkbox functionality
- Show password visibility toggle
- Login with test account
- Show session timer in navbar
- Demonstrate "Forgot Password" link (UI only)

### Part 2: Protected Routes and Navigation (3 minutes)

#### 2.1 Route Protection
- While logged out, try to access:
  - /dashboard (redirects to login)
  - /profile (redirects to login)
  - /settings (redirects to login)
- Show redirect after login feature
- While logged in, try to access:
  - /login (redirects to dashboard)
  - /register (redirects to dashboard)

#### 2.2 Navigation and User Menu
- Show avatar with user initials
- Show dropdown menu with:
  - User email display
  - Profile link
  - Settings link
  - Logout option
- Show session timer counting down

### Part 3: Dashboard and Core Features (5 minutes)

#### 3.1 Dashboard Overview
- Show statistics cards:
  - Total Hosts
  - Online/Offline counts
  - Response times
- Show recent activity chart
- Show system health indicators

#### 3.2 Host Management
- Navigate to Hosts page
- Show host list with:
  - Status indicators (online/offline)
  - IP addresses
  - Last seen times
  - Search functionality
  - Sorting options
- Click on a host to see details modal

### Part 4: User Profile Management (5 minutes)

#### 4.1 Profile View
- Navigate to My Profile
- Show profile information:
  - Avatar placeholder
  - Username, email, full name
  - Bio section
  - Account creation date
  - Last login time

#### 4.2 Profile Editing
- Click "Edit Profile" button
- Show edit form with:
  - Full name field
  - Bio with character counter (500 char limit)
  - Real-time character counting
  - Color changes as limit approaches
- Save changes and show success message
- Show immediate update in navbar avatar

### Part 5: Account Settings (7 minutes)

#### 5.1 Settings Navigation
- Navigate to Settings
- Show collapsible sidebar (mobile responsive)
- Navigate through sections:
  - General
  - Security
  - Notifications
  - Account

#### 5.2 General Settings
- Show language preference (UI ready)
- Show timezone selection
- Show date format options
- Save changes

#### 5.3 Security Settings
- Show Two-Factor Authentication option
- Show active sessions list:
  - Current session marked
  - Browser and OS detection
  - IP addresses
  - Revoke other sessions option
- Show "Change Password" button

#### 5.4 Notification Settings
- Show email notification preferences:
  - Security alerts
  - Host status changes
  - System updates
  - Marketing emails
- Show notification frequency options

#### 5.5 Account Management
- Show account export option
- Show "View Activity Log" button
- Show "Delete Account" danger zone

### Part 6: Password Change Flow (3 minutes)

#### 6.1 Password Change
- Click "Change Password" from security settings
- Show password change form:
  - Current password field
  - New password with requirements
  - Real-time strength indicator
  - Password visibility toggles
  - Confirm password field
- Submit change (mock success)
- Show auto-logout warning
- Note: Would log out after 3 seconds in real implementation

### Part 7: Activity Logging (3 minutes)

#### 7.1 Activity Log
- Navigate to Activity Log
- Show activity list with:
  - Event types (login, logout, profile updates, etc.)
  - Timestamps with relative time ("2 hours ago")
  - IP addresses
  - Device information
  - Status badges for failed attempts

#### 7.2 Activity Filtering
- Show date range filter (default: last 30 days)
- Show event type filter dropdown
- Apply filters and show results
- Show pagination controls

### Part 8: Account Deletion Flow (5 minutes)

#### 8.1 Account Deletion Process
- Navigate to Settings > Account
- Click "Delete My Account" button
- **Step 1**: Warning screen
  - Show consequences list
  - Show what will be deleted
  - Require checkbox confirmation
- **Step 2**: Identity verification
  - Enter password
  - Type username to confirm
  - Show validation in real-time
- **Step 3**: Final confirmation
  - Large warning icon
  - "Last chance" message
  - Final delete button
- Show success message with countdown
- Note: Would redirect after 5 seconds

### Part 9: Session Management (3 minutes)

#### 9.1 Session Features
- Show session timer in navbar
- Demonstrate session warning modal (at 5 minutes)
- Show "Stay Logged In" option
- Show auto-logout notification
- Show remember me persistence

#### 9.2 Logout
- Click logout
- Show redirect to login
- Show cleared session
- Try to access protected route (redirects to login)

## Technical Highlights

### Security Features Implemented
- JWT-based authentication
- Protected routes with guards
- Session timeout management
- Password strength validation
- Multi-factor confirmation for deletion
- CSRF protection ready
- XSS protection in inputs

### User Experience Features
- Responsive design (test on mobile)
- Real-time form validation
- Loading states and spinners
- Success/error notifications
- Smooth transitions
- Accessible UI components
- Character counting
- Password visibility toggles

### Architecture Highlights
- Single Page Application (SPA)
- Client-side routing
- Token management with refresh
- API integration ready
- Modular JavaScript components
- Bootstrap 5 UI framework

## Questions to Address
1. Any specific features to prioritize for next sprint?
2. Feedback on UX/UI design?
3. Additional security requirements?
4. Integration points needed?

## Next Sprint Preview
Potential features for next sprint:
- Two-factor authentication implementation
- Email verification system
- API key management
- Advanced activity analytics
- Bulk operations for hosts
- DNS zone management
- User roles and permissions

## Demo Notes
- Use mock data where backend isn't implemented
- Have backup plan if services are down
- Prepare test data in advance
- Keep browser console open for technical audience
- Have this document open for reference

---

## Quick Demo Checklist

### Pre-Demo Setup
- [ ] Docker containers running
- [ ] Test account created
- [ ] Browser cache cleared
- [ ] Multiple browser tabs ready
- [ ] Mobile device/emulator ready

### During Demo
- [ ] Registration flow
- [ ] Login with Remember Me
- [ ] Route protection demo
- [ ] Dashboard overview
- [ ] Host management
- [ ] Profile view/edit
- [ ] Settings sections
- [ ] Password change
- [ ] Activity log
- [ ] Account deletion
- [ ] Session management
- [ ] Responsive design

### Post-Demo
- [ ] Gather feedback
- [ ] Note improvement requests
- [ ] Document any bugs found
- [ ] Update backlog