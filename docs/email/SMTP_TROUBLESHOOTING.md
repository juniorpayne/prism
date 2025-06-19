# SMTP Email Troubleshooting Guide

This guide helps diagnose and resolve common SMTP email configuration issues in Prism DNS.

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Common Issues](#common-issues)
3. [Provider-Specific Issues](#provider-specific-issues)
4. [Testing Tools](#testing-tools)
5. [Debug Mode](#debug-mode)
6. [FAQ](#faq)

## Quick Diagnostics

### 1. Run the Configuration Validator

```bash
# Test with validation only
./scripts/test-smtp.sh --validate-only

# Test with MailHog (local)
./scripts/test-smtp.sh --mailhog --to test@example.com

# Test with your configured provider
python -m server.commands.test_email --to your-email@example.com
```

### 2. Check Basic Connectivity

```bash
# Test DNS resolution
nslookup smtp.gmail.com

# Test port connectivity
telnet smtp.gmail.com 587

# For SSL connections
openssl s_client -connect smtp.gmail.com:465
```

## Common Issues

### Authentication Failed (535)

**Symptoms:**
- Error: "535 Authentication failed"
- "Invalid credentials"
- "Authentication unsuccessful"

**Solutions:**

1. **Gmail**:
   - Enable 2-factor authentication
   - Generate app-specific password at https://myaccount.google.com/apppasswords
   - Use app password instead of regular password
   - Ensure "Less secure app access" is not the issue (deprecated)

2. **SendGrid**:
   - Username must be literally "apikey"
   - Password should be your API key (starts with "SG.")
   - Verify API key has "Mail Send" permission

3. **Office 365**:
   - Enable SMTP AUTH for the mailbox
   - May need to use app password
   - Check if legacy authentication is disabled

### Connection Timeout

**Symptoms:**
- "Connection timeout"
- "Could not connect to SMTP server"
- Test hangs with no response

**Solutions:**

1. **Check Firewall**:
   ```bash
   # Check if outbound SMTP ports are blocked
   sudo iptables -L -n | grep -E "587|465|25"
   ```

2. **Verify Port**:
   - Port 25: Often blocked by ISPs
   - Port 587: Standard TLS port (recommended)
   - Port 465: Legacy SSL port
   - Port 2525: Alternative (SendGrid, others)

3. **Docker Networking**:
   ```bash
   # For Docker environments
   docker network ls
   docker network inspect prism-network
   ```

### TLS/SSL Errors

**Symptoms:**
- "SSL handshake failed"
- "STARTTLS failed"
- "Certificate verify failed"

**Solutions:**

1. **Port Mismatch**:
   - Port 587 requires STARTTLS (use_tls=true, use_ssl=false)
   - Port 465 requires SSL (use_ssl=true, use_tls=false)

2. **Certificate Issues**:
   ```python
   # Disable certificate validation (development only!)
   SMTP_VALIDATE_CERTS=false
   ```

3. **Protocol Version**:
   - Some servers require specific TLS versions
   - Update Python/OpenSSL if outdated

### Relay Access Denied (550)

**Symptoms:**
- "550 Relay access denied"
- "Sender address rejected"
- "Domain not verified"

**Solutions:**

1. **Verify Sender Address**:
   - Must use verified domain/address
   - Check SPF records
   - Verify domain in provider console

2. **Authentication Required**:
   - Ensure credentials are provided
   - Check if IP whitelisting is required

## Provider-Specific Issues

### Gmail

**Common Issues:**
1. "Please log in via your web browser"
   - Sign in to Gmail account
   - Visit https://accounts.google.com/DisplayUnlockCaptcha
   - Enable access for the app

2. Daily sending limits:
   - Regular accounts: 500 recipients/day
   - Google Workspace: 2,000 recipients/day

### SendGrid

**Common Issues:**
1. "Unauthenticated senders not allowed"
   - Verify sender domain
   - Complete sender authentication

2. IP not whitelisted:
   - Check IP Access Management
   - Add server IP if required

### AWS SES

**Common Issues:**
1. Still in sandbox mode:
   - Can only send to verified addresses
   - Request production access

2. Region mismatch:
   - Ensure using correct AWS region
   - SES not available in all regions

### Office 365

**Common Issues:**
1. "5.7.57 Client not authenticated"
   - Enable SMTP AUTH
   - Check security defaults
   - May need to disable MFA for SMTP

2. Tenant restrictions:
   - Check conditional access policies
   - Verify SMTP is allowed

## Testing Tools

### 1. MailHog (Local Development)

```bash
# Start MailHog
docker compose --profile development up -d mailhog

# Configure
export EMAIL_PROVIDER=smtp
export SMTP_HOST=localhost
export SMTP_PORT=1025
export SMTP_USE_TLS=false

# View emails at http://localhost:8025
```

### 2. Command Line Testing

```bash
# Test SMTP manually with swaks
swaks --to test@example.com \
      --from sender@example.com \
      --server smtp.gmail.com:587 \
      --auth LOGIN \
      --auth-user your-email@gmail.com \
      --tls

# Test with Python
python -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('user', 'pass')
print('Success!')
server.quit()
"
```

### 3. Online Tools

- https://www.mail-tester.com/ - Test email deliverability
- https://toolbox.googleapps.com/apps/messageheader/ - Analyze email headers
- https://mxtoolbox.com/smtp.aspx - SMTP diagnostics

## Debug Mode

### Enable Detailed Logging

```bash
# Set debug mode
export EMAIL_DEBUG=true
export PRISM_LOGGING_LEVEL=DEBUG

# Python SMTP debugging
export PYTHONVERBOSE=1
```

### Capture SMTP Protocol

```python
# In your code, enable debug mode
import smtplib
smtplib._debug = True
```

### Docker Logs

```bash
# View container logs
docker compose logs -f server

# View specific timeframe
docker compose logs --since 10m server
```

## FAQ

### Q: Why does Gmail keep rejecting my password?

**A:** Gmail requires app-specific passwords when 2FA is enabled. Regular passwords won't work for SMTP.

### Q: Can I use port 25?

**A:** Port 25 is often blocked by ISPs and cloud providers. Use 587 (TLS) or 465 (SSL) instead.

### Q: How do I test without sending real emails?

**A:** Use MailHog for local testing or set EMAIL_PROVIDER=console to output emails to the console.

### Q: Why am I getting "Connection refused"?

**A:** Check if:
- The SMTP host is correct
- The port is open (firewall/security groups)
- You're not behind a corporate proxy
- Docker container can reach external networks

### Q: How do I fix "certificate verify failed"?

**A:** 
- Ensure your system's CA certificates are up to date
- For development only, you can disable certificate validation
- Check if you need to specify a custom CA bundle

### Q: What are the rate limits?

**A:** Varies by provider:
- Gmail: 500-2000/day
- SendGrid: Based on plan
- AWS SES: Starts at 200/day (sandbox)
- Office 365: 10,000/day

### Q: How do I monitor email delivery?

**A:** 
- Use provider dashboards (SendGrid, SES console)
- Implement webhook handlers for bounce/complaint notifications
- Check email logs and metrics
- Use email testing services

## Need More Help?

1. Check provider documentation:
   - [Gmail SMTP](https://support.google.com/mail/answer/7126229)
   - [SendGrid SMTP](https://docs.sendgrid.com/for-developers/sending-email/integrating-with-the-smtp-api)
   - [AWS SES](https://docs.aws.amazon.com/ses/latest/dg/send-email-smtp.html)
   - [Office 365](https://docs.microsoft.com/en-us/exchange/mail-flow-best-practices/how-to-set-up-a-multifunction-device-or-application-to-send-email-using-microsoft-365-or-office-365)

2. Enable debug logging and capture the full error
3. Test with a known working service (MailHog)
4. Verify network connectivity and DNS resolution
5. Check service status pages for outages