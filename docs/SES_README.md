# AWS SES Email Provider Implementation

This directory contains the AWS Simple Email Service (SES) implementation for Prism DNS authentication emails.

## Overview

The AWS SES provider enables production-grade email delivery with:
- High deliverability rates
- Bounce and complaint handling
- Automatic suppression list management
- Detailed metrics and monitoring
- DKIM signing and SPF/DMARC support

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Application   │────▶│   AWS SES       │────▶│  Email Servers  │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │
         │                       │ SNS Events
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│  Suppressions   │◀────│    Webhooks     │
│   Database      │     │                 │
└─────────────────┘     └─────────────────┘
```

## Components

### 1. AWS SES Email Provider (`server/auth/email_providers/aws_ses.py`)
- Sends emails via AWS SES API
- Checks suppression list before sending
- Supports IAM role authentication
- Handles configuration sets for tracking

### 2. Webhook Handler (`server/api/routes/ses_webhooks.py`)
- Receives bounce/complaint notifications from SNS
- Updates suppression list automatically
- Records email events for analysis

### 3. Email Event Models (`server/auth/models/email_events.py`)
- `EmailBounce`: Records bounce events
- `EmailComplaint`: Records complaint events
- `EmailSuppression`: Maintains suppression list

### 4. Metrics API (`server/api/routes/email_metrics.py`)
- Provides bounce/complaint statistics
- Manages suppression list
- Offers email health insights

## Configuration

### Environment Variables
```bash
# Required
EMAIL_PROVIDER=aws_ses
AWS_REGION=us-east-1
EMAIL_FROM=noreply@prism.thepaynes.ca
EMAIL_FROM_NAME="Prism DNS"

# Optional
AWS_SES_CONFIGURATION_SET=prism-dns-production
AWS_SES_USE_IAM_ROLE=true  # For EC2 instances
AWS_ACCESS_KEY_ID=xxx       # For local development
AWS_SECRET_ACCESS_KEY=xxx   # For local development
```

### Configuration File
```python
# server/config.py
email_config = {
    "provider": "aws_ses",
    "aws_ses": {
        "region": "us-east-1",
        "from_email": "noreply@prism.thepaynes.ca",
        "from_name": "Prism DNS",
        "configuration_set": "prism-dns-production",
        "use_iam_role": True
    }
}
```

## Setup Process

### 1. Domain Verification
```bash
# Run setup script
./scripts/setup-ses-production.sh

# Add DNS records from output
# Wait for verification
```

### 2. DKIM Configuration
- Add 3 CNAME records for DKIM signing
- Enables email authentication
- Improves deliverability

### 3. SPF and DMARC
- Add SPF record to authorize SES
- Configure DMARC for policy enforcement
- Monitor email authentication

### 4. Production Access
- Request exit from SES sandbox
- Provide use case details
- Wait for AWS approval

## API Endpoints

### Webhook Endpoints
- `POST /api/webhooks/ses/notifications` - Receive SNS notifications
- `GET /api/webhooks/ses/health` - Health check

### Metrics Endpoints
- `GET /api/metrics/email/bounces` - Bounce statistics
- `GET /api/metrics/email/complaints` - Complaint statistics
- `GET /api/metrics/email/suppressions` - Suppression list
- `DELETE /api/metrics/email/suppressions/{email}` - Remove suppression
- `GET /api/metrics/email/summary` - Overall metrics

## Database Schema

### Email Bounces Table
```sql
CREATE TABLE email_bounces (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    bounce_type ENUM('permanent', 'transient', 'undetermined'),
    bounce_subtype VARCHAR(50),
    message_id VARCHAR(255),
    feedback_id VARCHAR(255) UNIQUE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    diagnostic_code TEXT,
    reporting_mta VARCHAR(255),
    suppressed BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_email_bounces_email ON email_bounces(email);
```

### Email Suppressions Table
```sql
CREATE TABLE email_suppressions (
    email VARCHAR(255) PRIMARY KEY,
    reason VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);
```

## Monitoring

### CloudWatch Metrics
- Send rate
- Bounce rate (alarm at >5%)
- Complaint rate (alarm at >0.1%)
- Daily send quota usage

### Grafana Dashboard
- Real-time email metrics
- Bounce/complaint trends
- Suppression list size
- Recent bounce details

### Prometheus Metrics
- `prism_email_sent_total` - Total emails sent
- `prism_email_bounces_total` - Total bounces
- `prism_email_complaints_total` - Total complaints
- `prism_email_suppressions_total` - Suppression list size

## Testing

### Unit Tests
```bash
# Run SES provider tests
pytest tests/test_aws_ses_provider.py -v

# Run webhook tests
pytest tests/test_ses_webhooks.py -v
```

### Integration Testing
```bash
# Test with SES simulators
curl -X POST /api/auth/register \
  -d '{"email": "bounce@simulator.amazonses.com"}'

curl -X POST /api/auth/register \
  -d '{"email": "complaint@simulator.amazonses.com"}'
```

### Manual Testing
```bash
# Send test email
TEST_EMAIL=your@email.com ./scripts/setup-ses-production.sh test

# Check metrics
curl https://prism.thepaynes.ca/api/metrics/email/summary
```

## Troubleshooting

### Common Issues

1. **Emails not sending**
   - Check domain verification status
   - Verify IAM permissions
   - Ensure not in sandbox mode
   - Check suppression list

2. **High bounce rate**
   - Review email list quality
   - Check email content
   - Verify recipient addresses
   - Monitor specific domains

3. **Webhooks not working**
   - Confirm SNS subscription
   - Check webhook URL accessibility
   - Verify signature validation
   - Review server logs

### Debug Commands
```bash
# Check SES configuration
aws ses get-identity-verification-attributes --identities prism.thepaynes.ca

# View send statistics
aws ses get-send-statistics

# List suppressed addresses
curl /api/metrics/email/suppressions

# Check recent bounces
curl /api/metrics/email/bounces?days=1
```

## Best Practices

1. **List Hygiene**
   - Regularly clean email lists
   - Remove invalid addresses
   - Honor unsubscribe requests
   - Monitor engagement rates

2. **Content Quality**
   - Avoid spam trigger words
   - Include unsubscribe links
   - Use proper HTML structure
   - Test with spam checkers

3. **Sending Patterns**
   - Warm up new domains gradually
   - Avoid sudden volume spikes
   - Spread sends over time
   - Monitor reputation metrics

4. **Error Handling**
   - Implement retry logic
   - Handle rate limits
   - Log all errors
   - Alert on failures

## Security Considerations

1. **Authentication**
   - Use IAM roles in production
   - Never commit credentials
   - Rotate access keys regularly
   - Limit permissions to minimum required

2. **Webhook Security**
   - Verify SNS signatures
   - Use HTTPS only
   - Validate message format
   - Rate limit endpoints

3. **Data Protection**
   - Encrypt email addresses at rest
   - Implement retention policies
   - Audit access logs
   - Comply with privacy laws

## Maintenance

### Daily
- Monitor bounce/complaint rates
- Check CloudWatch alarms
- Review error logs

### Weekly
- Analyze email metrics
- Clean suppression list
- Update documentation

### Monthly
- Review sending patterns
- Audit security settings
- Test disaster recovery

## References

- [AWS SES Documentation](https://docs.aws.amazon.com/ses/)
- [SES Best Practices](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/best-practices.html)
- [Email Deliverability Guide](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/deliverability.html)
- [SNS Event Format](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/event-publishing-retrieving-sns-contents.html)