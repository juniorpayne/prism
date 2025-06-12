# Production Authentication Setup Guide

## Required Steps to Enable Authentication in Production

### 1. Database Migration
The authentication tables need to be created in the production database. Run these commands on the EC2 instance:

```bash
# SSH to production
ssh ubuntu@35.170.180.10

# Navigate to deployment directory
cd ~/prism-deployment

# Run migrations inside the container
docker compose exec server alembic upgrade head
```

### 2. Email Service Configuration
The email service requires SMTP credentials. Add these environment variables to your production docker-compose:

```yaml
environment:
  # Email Configuration (required for registration)
  - PRISM_EMAIL_HOST=smtp.gmail.com  # or your SMTP server
  - PRISM_EMAIL_PORT=587
  - PRISM_EMAIL_USERNAME=your-email@gmail.com
  - PRISM_EMAIL_PASSWORD=your-app-password  # Use app-specific password for Gmail
  - PRISM_EMAIL_FROM=noreply@prism.thepaynes.ca
  - PRISM_EMAIL_FROM_NAME=Prism DNS
  
  # Frontend URL for email links
  - PRISM_FRONTEND_URL=https://prism.thepaynes.ca
```

### 3. Gmail App Password Setup (if using Gmail)
1. Go to https://myaccount.google.com/security
2. Enable 2-factor authentication
3. Generate an app-specific password
4. Use this password in PRISM_EMAIL_PASSWORD

### 4. Alternative: Disable Email Temporarily
If you want to test without email, you can create a test user directly in the database:

```bash
# Access the database
docker compose exec server sqlite3 /data/prism.db

# Insert a test user (already verified)
INSERT INTO users (
  id, email, username, password_hash, 
  email_verified, email_verified_at, is_active,
  created_at, updated_at
) VALUES (
  '550e8400-e29b-41d4-a716-446655440000',
  'test@example.com',
  'testuser',
  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiGBQRSlBm6q',  -- password: Test123!
  1,  -- email_verified = true
  datetime('now'),
  1,  -- is_active = true
  datetime('now'),
  datetime('now')
);
```

### 5. Test Registration Without Email
For development/testing, you can modify the registration to auto-verify:

1. Set an environment variable: `PRISM_AUTO_VERIFY_EMAIL=true`
2. Or modify the code to skip email sending in development

## Testing the Setup

Once configured, test with:

```bash
# Test registration
curl -X POST https://prism.thepaynes.ca/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "SecurePassword123!"
  }'

# If email is working, check your inbox for verification link
# The link format: https://prism.thepaynes.ca/verify-email?token=TOKEN
```

## Current Status
- ✅ Authentication endpoints deployed
- ✅ Validation working (weak password returns 422)
- ❌ Email service not configured (causes 500 error)
- ❓ Database migrations may need to be run

## Next Steps
1. Configure email service OR
2. Create test users directly in database OR
3. Implement a development mode that bypasses email verification