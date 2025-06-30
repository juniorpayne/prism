# SES Deployment Guide

This guide walks through deploying AWS SES email functionality for Prism DNS in production.

## Prerequisites

- AWS account with appropriate permissions
- Access to DNS management for your domain
- EC2 instance with IAM role attached
- Docker and docker-compose installed
- AWS CLI configured

## Step 1: Initial Setup

### 1.1 Clone/Update Repository
```bash
cd ~/prism-deployment
git pull origin main
```

### 1.2 Set Environment Variables
Create or update `.env.production`:
```bash
# Email Configuration
EMAIL_PROVIDER=aws_ses
EMAIL_FROM=noreply@prism.thepaynes.ca
EMAIL_FROM_NAME="Prism DNS"
AWS_REGION=us-east-1
AWS_SES_CONFIGURATION_SET=prism-dns-production
AWS_SES_USE_IAM_ROLE=true

# Webhook URL (update after getting EC2 public IP)
WEBHOOK_URL=https://prism.thepaynes.ca
```

## Step 2: Run SES Setup Script

### 2.1 Execute Setup Script
```bash
cd ~/prism-deployment
chmod +x scripts/setup-ses-production.sh

# Run initial setup
./scripts/setup-ses-production.sh
```

### 2.2 Configure DNS Records
The script will output DNS records to add. Copy all records from `ses_dns_records.txt`:

```bash
cat ses_dns_records.txt
```

Add these records to your DNS provider:
- Domain verification TXT record
- 3 DKIM CNAME records
- Custom MAIL FROM MX and TXT records
- SPF TXT record
- DMARC TXT record

### 2.3 Wait for DNS Propagation
```bash
# Check domain verification
dig TXT _amazonses.prism.thepaynes.ca

# Check DKIM records
dig CNAME dkim1._domainkey.prism.thepaynes.ca
dig CNAME dkim2._domainkey.prism.thepaynes.ca
dig CNAME dkim3._domainkey.prism.thepaynes.ca

# Check MAIL FROM
dig MX mail.prism.thepaynes.ca
```

### 2.4 Verify Domain Status
```bash
# Check verification status
./scripts/setup-ses-production.sh verify
```

## Step 3: Configure IAM Permissions

### 3.1 Update EC2 Instance Role
Add the following policy to your EC2 instance's IAM role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ses:SendEmail",
        "ses:SendRawEmail"
      ],
      "Resource": [
        "arn:aws:ses:us-east-1:*:identity/prism.thepaynes.ca",
        "arn:aws:ses:us-east-1:*:configuration-set/prism-dns-production"
      ],
      "Condition": {
        "StringEquals": {
          "ses:FromAddress": [
            "noreply@prism.thepaynes.ca",
            "support@prism.thepaynes.ca",
            "alerts@prism.thepaynes.ca"
          ]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ses:GetSendQuota",
        "ses:DescribeConfigurationSet"
      ],
      "Resource": "*"
    }
  ]
}
```

## Step 4: Deploy Application Updates

### 4.1 Update Docker Images
```bash
cd ~/prism-deployment
docker compose -f docker-compose.production.yml build
```

### 4.2 Run Database Migrations
```bash
docker compose -f docker-compose.production.yml exec prism-server alembic upgrade head
```

### 4.3 Restart Services
```bash
docker compose -f docker-compose.production.yml down
docker compose -f docker-compose.production.yml up -d
```

### 4.4 Verify Deployment
```bash
# Check service health
curl https://prism.thepaynes.ca/api/health

# Check webhook endpoint
curl https://prism.thepaynes.ca/api/webhooks/ses/health

# View logs
docker compose -f docker-compose.production.yml logs -f prism-server
```

## Step 5: Configure SNS Webhook

### 5.1 Subscribe Webhook to SNS
```bash
# Update webhook URL in setup script
export WEBHOOK_URL="https://prism.thepaynes.ca"

# Run setup again to subscribe webhook
./scripts/setup-ses-production.sh
```

### 5.2 Confirm SNS Subscription
Check server logs for subscription confirmation:
```bash
docker compose -f docker-compose.production.yml logs prism-server | grep "subscription confirmed"
```

## Step 6: Request Production Access

### 6.1 Exit SES Sandbox
1. Go to [AWS SES Console](https://console.aws.amazon.com/ses/home?region=us-east-1#/account)
2. Click "Request production access"
3. Fill out the form:
   - **Mail Type**: Transactional
   - **Website URL**: https://prism.thepaynes.ca
   - **Use Case**: User authentication emails (verification, password reset)
   - **Additional Info**: Bounce/complaint handling implemented
4. Submit request

### 6.2 Wait for Approval
- Usually takes 24-48 hours
- Check email for approval notification
- Verify increased sending limits in console

## Step 7: Test Email Sending

### 7.1 Test in Sandbox Mode
```bash
# Test with verified email
export TEST_EMAIL="your-verified@email.com"
./scripts/setup-ses-production.sh test
```

### 7.2 Test via API
```bash
# Test user registration (triggers verification email)
curl -X POST https://prism.thepaynes.ca/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "full_name": "Test User"
  }'
```

### 7.3 Test Bounce Handling
```bash
# Test with SES simulator
curl -X POST https://prism.thepaynes.ca/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "bounce@simulator.amazonses.com",
    "password": "test123",
    "full_name": "Bounce Test"
  }'
```

## Step 8: Deploy Monitoring

### 8.1 Deploy CloudWatch Alarms
```bash
cd monitoring/cloudwatch
aws cloudformation create-stack \
  --stack-name prism-ses-alarms \
  --template-body file://ses-alarms.yaml \
  --parameters ParameterKey=AlarmEmail,ParameterValue=alerts@prism.thepaynes.ca
```

### 8.2 Import Grafana Dashboard
1. Access Grafana at https://prism.thepaynes.ca:3000
2. Go to Dashboards → Import
3. Upload `monitoring/grafana/dashboards/ses-email-metrics.json`
4. Select CloudWatch and Prometheus data sources
5. Save dashboard

### 8.3 Verify Metrics
```bash
# Check email metrics API
curl https://prism.thepaynes.ca/api/metrics/email/summary | jq .

# Check suppressions
curl https://prism.thepaynes.ca/api/metrics/email/suppressions | jq .
```

## Step 9: Production Checklist

Before marking deployment complete:

- [ ] All DNS records added and propagated
- [ ] Domain verified in SES console
- [ ] DKIM signing enabled and verified
- [ ] Configuration set created with events
- [ ] SNS topic created and webhook subscribed
- [ ] Database migrations completed
- [ ] Services restarted successfully
- [ ] Test emails sending correctly
- [ ] Bounce/complaint handling working
- [ ] CloudWatch alarms deployed
- [ ] Grafana dashboard imported
- [ ] Production access requested/approved

## Troubleshooting

### DNS Issues
```bash
# Force DNS refresh
sudo systemctl restart systemd-resolved

# Check specific nameserver
dig @8.8.8.8 TXT _amazonses.prism.thepaynes.ca
```

### Email Not Sending
```bash
# Check SES configuration
aws ses get-identity-verification-attributes --identities prism.thepaynes.ca

# Check send quota
aws ses get-send-quota

# Test with AWS CLI
aws ses send-email \
  --from noreply@prism.thepaynes.ca \
  --to verified@email.com \
  --subject "Test" \
  --text "Test email"
```

### Webhook Not Receiving Events
```bash
# Check SNS subscriptions
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:*:ses-prism-dns-production-events

# Manually confirm subscription
curl -X POST https://prism.thepaynes.ca/api/webhooks/ses/notifications \
  -H "Content-Type: application/json" \
  -d '{"Type": "SubscriptionConfirmation", "SubscribeURL": "..."}'
```

### High Bounce Rate
1. Check suppression list:
   ```bash
   curl https://prism.thepaynes.ca/api/metrics/email/bounces?days=7 | jq .
   ```
2. Review email content for spam triggers
3. Verify recipient email addresses
4. Check domain reputation

## Maintenance

### Daily Tasks
- Monitor CloudWatch alarms
- Check Grafana dashboard
- Review bounce/complaint rates

### Weekly Tasks
- Review suppression list
- Check sending quota usage
- Analyze email metrics

### Monthly Tasks
- Review and clean suppression list
- Update documentation
- Test disaster recovery

## Rollback Procedure

If issues occur:

1. **Revert to Console Provider**:
   ```bash
   # Update environment
   sed -i 's/EMAIL_PROVIDER=aws_ses/EMAIL_PROVIDER=console/' .env.production
   
   # Restart services
   docker compose -f docker-compose.production.yml restart prism-server
   ```

2. **Check Logs**:
   ```bash
   docker compose -f docker-compose.production.yml logs --tail=100 prism-server
   ```

3. **Restore Previous Version**:
   ```bash
   git checkout <previous-commit>
   docker compose -f docker-compose.production.yml build
   docker compose -f docker-compose.production.yml up -d
   ```

## Support

For issues:
1. Check CloudWatch logs
2. Review Grafana metrics
3. Check AWS SES console
4. Contact AWS support if needed

## Security Notes

- Never commit AWS credentials
- Use IAM roles for EC2 instances
- Regularly rotate access keys
- Monitor for unusual activity
- Keep suppression list updated