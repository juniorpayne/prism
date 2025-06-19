# Email Configuration Guide

This guide covers how to configure email providers for Prism DNS.

## Quick Start

### 1. Using MailHog (Development)

```bash
# Start MailHog
docker compose --profile development up -d mailhog

# Set environment variables
export EMAIL_PROVIDER=smtp
export SMTP_HOST=mailhog  # or localhost if not using Docker
export SMTP_PORT=1025
export SMTP_USE_TLS=false
export EMAIL_FROM_ADDRESS=dev@prism.local

# Test
./scripts/test-smtp.sh --mailhog --to test@example.com

# View emails at http://localhost:8025
```

### 2. Using Gmail

```bash
# Copy template
cp config/email-providers/gmail.env.example .env

# Edit with your credentials
# 1. Enable 2FA on your Google account
# 2. Generate app password at https://myaccount.google.com/apppasswords
# 3. Update .env with your email and app password

# Test
python -m server.commands.test_email --to your-email@example.com
```

### 3. Using SendGrid

```bash
# Copy template
cp config/email-providers/sendgrid.env.example .env

# Edit with your API key
# Username is always "apikey"
# Password is your SendGrid API key

# Test
python -m server.commands.test_email --to your-email@example.com
```

## Configuration Methods

### Method 1: Environment Variables

```bash
# Basic configuration
export EMAIL_PROVIDER=smtp
export EMAIL_FROM_ADDRESS=noreply@yourdomain.com
export EMAIL_FROM_NAME="Your App"

# SMTP specific
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USERNAME=your-email@gmail.com
export SMTP_PASSWORD=your-app-password
export SMTP_USE_TLS=true

# Advanced features (optional)
export SMTP_POOL_SIZE=5
export SMTP_RETRY_MAX_ATTEMPTS=3
export SMTP_CIRCUIT_BREAKER_ENABLED=true
```

### Method 2: Configuration File

Create `config/email.yaml`:

```yaml
provider: smtp
from_email: noreply@yourdomain.com
from_name: "Your App"

# SMTP configuration
host: smtp.gmail.com
port: 587
username: your-email@gmail.com
password: your-app-password
use_tls: true
use_ssl: false

# Advanced features
pool_size: 5
retry_max_attempts: 3
circuit_breaker_enabled: true
```

### Method 3: Direct Python Configuration

```python
from server.auth.email_providers.config import SMTPEmailConfig
from server.auth.email_providers.factory import EmailProviderFactory

config = SMTPEmailConfig(
    provider="smtp",
    from_email="noreply@yourdomain.com",
    from_name="Your App",
    host="smtp.gmail.com",
    port=587,
    username="your-email@gmail.com",
    password="your-app-password",
    use_tls=True,
)

provider = EmailProviderFactory.create_provider(config)
```

## Provider Templates

Pre-configured templates are available in `config/email-providers/`:

- `gmail.env.example` - Gmail configuration
- `sendgrid.env.example` - SendGrid configuration  
- `mailhog.env.example` - MailHog (local development)
- `aws-ses.env.example` - AWS SES configuration
- `office365.env.example` - Office 365 configuration

## Testing Your Configuration

### 1. Validate Configuration Only

```bash
python -m server.commands.test_email --validate-only
```

### 2. Send Test Email

```bash
python -m server.commands.test_email --to recipient@example.com
```

### 3. Use Testing Script

```bash
# With MailHog
./scripts/test-smtp.sh --mailhog --to test@example.com

# With configured provider
./scripts/test-smtp.sh --to test@example.com
```

## Advanced Features

### Connection Pooling

Improve performance with connection pooling:

```bash
export SMTP_POOL_SIZE=10  # Number of connections to maintain
export SMTP_POOL_MAX_IDLE_TIME=300  # Seconds before closing idle connections
```

### Retry Logic

Automatic retry with exponential backoff:

```bash
export SMTP_RETRY_MAX_ATTEMPTS=3
export SMTP_RETRY_INITIAL_DELAY=1.0
export SMTP_RETRY_MAX_DELAY=60.0
```

### Circuit Breaker

Prevent cascading failures:

```bash
export SMTP_CIRCUIT_BREAKER_ENABLED=true
export SMTP_CIRCUIT_BREAKER_THRESHOLD=5  # Failures before opening
export SMTP_CIRCUIT_BREAKER_TIMEOUT=60  # Seconds before retry
```

## Security Best Practices

1. **Never commit credentials**:
   - Use environment variables
   - Use `.env` files (add to `.gitignore`)
   - Use secrets management in production

2. **Use app-specific passwords**:
   - Gmail: Generate at myaccount.google.com/apppasswords
   - Office 365: Use app passwords or OAuth2

3. **Enable TLS/SSL**:
   - Always use encryption in production
   - Port 587 with STARTTLS is recommended
   - Port 465 for implicit SSL

4. **Verify sender domains**:
   - Set up SPF records
   - Configure DKIM signing
   - Implement DMARC policy

## Monitoring

### Check Email Logs

```bash
# View recent email attempts
docker compose logs -f server | grep -i email

# Check for errors
docker compose logs server | grep -E "(ERROR|FAIL|535|550)"
```

### Provider Dashboards

- **Gmail**: Check account activity and quotas
- **SendGrid**: Monitor via app.sendgrid.com
- **AWS SES**: CloudWatch metrics and SES console
- **Office 365**: Message trace in Exchange admin

## Troubleshooting

See [SMTP_TROUBLESHOOTING.md](./SMTP_TROUBLESHOOTING.md) for detailed troubleshooting steps.

Common issues:
- Authentication failures → Check credentials and 2FA
- Connection timeouts → Verify firewall and ports
- TLS errors → Match port with TLS/SSL settings
- Rate limits → Monitor sending quotas