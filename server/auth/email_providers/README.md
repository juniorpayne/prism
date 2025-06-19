# Email Providers Module

This module provides a flexible email sending system with support for multiple providers and advanced features.

## Features

- **Multiple Providers**: Console (development), SMTP, AWS SES
- **Connection Pooling**: Reuse SMTP connections for better performance
- **Retry Logic**: Automatic retry with exponential backoff
- **Circuit Breaker**: Prevent cascading failures
- **Configuration Validation**: Test configurations before use
- **Async Support**: Non-blocking email sending

## Architecture

```
email_providers/
├── base.py              # Base classes and interfaces
├── config.py            # Configuration models (Pydantic)
├── config_loader.py     # Configuration loading logic
├── factory.py           # Provider factory
├── console.py           # Console email provider (dev)
├── smtp.py              # Basic SMTP provider
├── smtp_enhanced.py     # SMTP with advanced features
├── smtp_pool.py         # Connection pooling
├── smtp_validator.py    # Configuration validator
├── retry.py             # Retry decorator
├── circuit_breaker.py   # Circuit breaker pattern
└── aws_ses.py           # AWS SES provider
```

## Usage

### Basic Usage

```python
from server.auth.email_providers.factory import EmailProviderFactory
from server.auth.email_providers.config_loader import EmailConfigLoader
from server.auth.email_providers.base import EmailMessage

# Load configuration
config = EmailConfigLoader().load_config()

# Create provider
provider = EmailProviderFactory.create_provider(config)

# Send email
message = EmailMessage(
    to=["user@example.com"],
    subject="Test Email",
    text_body="This is a test email.",
    html_body="<p>This is a test email.</p>"
)

result = await provider.send_email(message)
if result.success:
    print(f"Email sent! ID: {result.message_id}")
else:
    print(f"Failed: {result.error}")
```

### With Configuration Validation

```python
from server.auth.email_providers.smtp_validator import validate_smtp_config

# Validate before use
if config.provider == "smtp":
    valid, results = await validate_smtp_config(config)
    if not valid:
        print("Configuration errors:", results)
        return
```

### Advanced SMTP Features

```python
# SMTP with connection pooling and retry
config = SMTPEmailConfig(
    # ... basic config ...
    pool_size=10,  # Maintain 10 connections
    retry_max_attempts=3,  # Retry up to 3 times
    circuit_breaker_enabled=True,  # Enable circuit breaker
)

# The factory automatically uses enhanced provider when needed
provider = EmailProviderFactory.create_provider(config)
```

## Configuration

### Environment Variables

```bash
# Provider selection
EMAIL_PROVIDER=smtp  # console, smtp, aws_ses

# Common settings
EMAIL_FROM_ADDRESS=noreply@example.com
EMAIL_FROM_NAME="My App"

# SMTP settings
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=user@gmail.com
SMTP_PASSWORD=app-specific-password
SMTP_USE_TLS=true

# Advanced features
SMTP_POOL_SIZE=5
SMTP_RETRY_MAX_ATTEMPTS=3
SMTP_CIRCUIT_BREAKER_ENABLED=true
```

### Configuration File

```yaml
# config/email.yaml
provider: smtp
from_email: noreply@example.com
host: smtp.gmail.com
port: 587
username: user@gmail.com
password: ${SMTP_PASSWORD}  # From environment
use_tls: true
pool_size: 5
```

## Providers

### Console Provider

Outputs emails to console/logs. Perfect for development.

```python
config = ConsoleEmailConfig(
    provider="console",
    from_email="dev@example.com",
    format="pretty",  # text, json, pretty
    use_colors=True,
)
```

### SMTP Provider

Supports any SMTP server (Gmail, SendGrid, etc.).

```python
config = SMTPEmailConfig(
    provider="smtp",
    from_email="noreply@example.com",
    host="smtp.sendgrid.net",
    port=587,
    username="apikey",
    password="SG.xxxxx",
    use_tls=True,
)
```

### AWS SES Provider

For production use with AWS.

```python
config = AWSSESConfig(
    provider="aws_ses",
    from_email="noreply@example.com",
    region="us-east-1",
    use_iam_role=True,  # For EC2
    configuration_set="my-config-set",
)
```

## Testing

### Unit Tests

```bash
# Run all email provider tests
pytest tests/test_email_providers.py -v

# Run specific test
pytest tests/test_smtp_pool.py -v
```

### Integration Testing

```bash
# Test with MailHog
docker compose --profile development up -d mailhog
./scripts/test-smtp.sh --mailhog --to test@example.com
```

### Manual Testing

```bash
# Test configuration
python -m server.commands.test_email --validate-only

# Send test email
python -m server.commands.test_email --to recipient@example.com
```

## Error Handling

The module provides detailed error messages:

```python
result = await provider.send_email(message)
if not result.success:
    print(f"Error: {result.error}")
    # Provider-specific error codes in metadata
    if result.metadata:
        print(f"Details: {result.metadata}")
```

## Performance Considerations

1. **Use Connection Pooling**: For high-volume SMTP
2. **Enable Circuit Breaker**: Prevent cascade failures  
3. **Configure Retry Logic**: Handle transient failures
4. **Async Operations**: Non-blocking email sending
5. **Batch Sending**: Use provider-specific batch APIs when available

## Security

1. **Environment Variables**: Never hardcode credentials
2. **TLS/SSL**: Always use encryption in production
3. **Sender Verification**: Verify domains with providers
4. **Rate Limiting**: Respect provider limits
5. **Input Validation**: Sanitize email content

## Troubleshooting

See [docs/email/SMTP_TROUBLESHOOTING.md](../../../docs/email/SMTP_TROUBLESHOOTING.md) for detailed troubleshooting guide.

## Future Enhancements

- [ ] OAuth2 support for providers
- [ ] Template engine integration
- [ ] Batch sending optimization
- [ ] Webhook handling for bounces/complaints
- [ ] More providers (Mailgun, Postmark, etc.)
- [ ] Email queuing system
- [ ] Attachment support