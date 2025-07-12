# SES Setup Guide for Prism DNS

## Prerequisites
- AWS CLI installed locally or on EC2
- AWS credentials configured
- Access to DNS management for prism.thepaynes.ca

## Step 1: SSH to EC2 Instance
```bash
ssh ubuntu@35.170.180.10
```

## Step 2: Navigate to Deployment Directory
```bash
cd ~/prism-deployment
git pull origin main
```

## Step 3: Run SES Setup Script
```bash
# Make script executable
chmod +x scripts/setup-ses-production.sh

# Run the setup script
./scripts/setup-ses-production.sh

# This will output all DNS records needed
```

## Step 4: Add DNS Records
Add all DNS records output by the script to your DNS provider:

### Required Records:
1. **Domain Verification** (TXT record)
   - Name: `_amazonses.prism.thepaynes.ca`
   - Type: TXT
   - Value: (provided by script)

2. **DKIM Records** (3 CNAME records)
   - `dkim1._domainkey.prism.thepaynes.ca` → `dkim1.amazonses.com`
   - `dkim2._domainkey.prism.thepaynes.ca` → `dkim2.amazonses.com`
   - `dkim3._domainkey.prism.thepaynes.ca` → `dkim3.amazonses.com`

3. **SPF Record**
   - Name: `prism.thepaynes.ca`
   - Type: TXT
   - Value: `"v=spf1 include:amazonses.com ~all"`

4. **DMARC Record**
   - Name: `_dmarc.prism.thepaynes.ca`
   - Type: TXT
   - Value: `"v=DMARC1; p=quarantine; rua=mailto:dmarc@prism.thepaynes.ca"`

5. **Custom MAIL FROM**
   - Name: `mail.prism.thepaynes.ca`
   - Type: MX
   - Priority: 10
   - Value: `feedback-smtp.us-east-1.amazonses.com`
   
   - Name: `mail.prism.thepaynes.ca`
   - Type: TXT
   - Value: `"v=spf1 include:amazonses.com ~all"`

## Step 5: Verify Domain
After adding DNS records (wait 5-30 minutes for propagation):
```bash
./scripts/setup-ses-production.sh verify
```

## Step 6: Update Production Configuration
```bash
cd ~/prism-deployment

# Add SES configuration to production environment
cat >> .env.production << EOF
EMAIL_PROVIDER=aws_ses
AWS_REGION=us-east-1
AWS_SES_CONFIGURATION_SET=prism-dns-production
AWS_SES_USE_IAM_ROLE=true
EMAIL_FROM=noreply@prism.thepaynes.ca
EMAIL_FROM_NAME="Prism DNS"
EOF
```

## Step 7: Restart Services
```bash
docker compose -f docker-compose.production.yml down
docker compose -f docker-compose.production.yml up -d
```

## Step 8: Test Email Sending
Once domain is verified:
```bash
TEST_EMAIL=your@email.com ./scripts/setup-ses-production.sh test
```

## Step 9: Request Production Access
1. Go to AWS SES Console: https://console.aws.amazon.com/ses/home?region=us-east-1#/account
2. Click "Request production access"
3. Fill out the form explaining:
   - Use case: Authentication emails for Prism DNS users
   - Expected volume: < 1000 emails/day
   - Bounce handling: Automated via SNS webhooks

## Step 10: Monitor Logs
```bash
docker compose -f docker-compose.production.yml logs -f prism-server
```

## Troubleshooting

### Check DNS Propagation
```bash
# On EC2 or locally:
dig TXT _amazonses.prism.thepaynes.ca
dig CNAME dkim1._domainkey.prism.thepaynes.ca
```

### Check SES Verification Status
```bash
aws ses get-identity-verification-attributes --identities prism.thepaynes.ca --region us-east-1
```

### Common Issues
- DNS propagation can take up to 72 hours (usually 5-30 minutes)
- Make sure to include quotes around TXT record values
- IAM role on EC2 needs SES permissions

## Next Steps
1. Set up CloudWatch alarms for bounce rates
2. Configure SNS topic for bounce/complaint handling
3. Test email templates
4. Monitor sending reputation