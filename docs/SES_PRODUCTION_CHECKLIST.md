# SES Production Deployment Checklist

This checklist ensures proper configuration of AWS SES for production email delivery with optimal deliverability and monitoring.

## Pre-Production Requirements

### AWS Account Setup
- [ ] AWS account has SES service enabled in us-east-1 region
- [ ] IAM user/role has necessary SES permissions
- [ ] AWS CLI configured with appropriate credentials
- [ ] Production AWS account (not development/sandbox)

### Domain Prerequisites
- [ ] Domain ownership verified (you control DNS)
- [ ] Access to DNS management interface
- [ ] Domain is not on any major blacklists
- [ ] Domain has existing website/service (helps reputation)

## Domain Configuration

### Domain Verification
- [ ] Run `./scripts/setup-ses-production.sh` to generate records
- [ ] Add domain verification TXT record:
  ```
  _amazonses.prism.thepaynes.ca  TXT  "verification-token-here"
  ```
- [ ] Wait for DNS propagation (verify with `dig TXT _amazonses.prism.thepaynes.ca`)
- [ ] Confirm domain verified in SES console

### DKIM Configuration
- [ ] Add all 3 DKIM CNAME records:
  ```
  dkim1._domainkey.prism.thepaynes.ca  CNAME  dkim1.amazonses.com
  dkim2._domainkey.prism.thepaynes.ca  CNAME  dkim2.amazonses.com
  dkim3._domainkey.prism.thepaynes.ca  CNAME  dkim3.amazonses.com
  ```
- [ ] Verify DKIM records: `dig CNAME dkim1._domainkey.prism.thepaynes.ca`
- [ ] Confirm DKIM verified in SES console

### Mail FROM Domain
- [ ] Add custom MAIL FROM records:
  ```
  mail.prism.thepaynes.ca  MX  10 feedback-smtp.us-east-1.amazonses.com
  mail.prism.thepaynes.ca  TXT  "v=spf1 include:amazonses.com ~all"
  ```
- [ ] Verify MX record: `dig MX mail.prism.thepaynes.ca`

### SPF and DMARC
- [ ] Add/update SPF record:
  ```
  prism.thepaynes.ca  TXT  "v=spf1 include:amazonses.com ~all"
  ```
- [ ] Add DMARC record:
  ```
  _dmarc.prism.thepaynes.ca  TXT  "v=DMARC1; p=quarantine; rua=mailto:dmarc@prism.thepaynes.ca; ruf=mailto:dmarc@prism.thepaynes.ca; fo=1"
  ```
- [ ] Verify records are resolving correctly

## SES Configuration

### Configuration Set
- [ ] Configuration set `prism-dns-production` created
- [ ] Reputation tracking enabled
- [ ] Event publishing configured

### Event Destinations
- [ ] SNS topic created for bounce/complaint notifications
- [ ] CloudWatch destination configured for metrics
- [ ] Webhook endpoint subscribed to SNS topic

### Suppression List
- [ ] Bounce handling webhook deployed and tested
- [ ] Complaint handling webhook deployed and tested
- [ ] Suppression list integration verified
- [ ] Database tables created for email events

## Production Access

### Exit SES Sandbox
- [ ] Navigate to [SES Account Dashboard](https://console.aws.amazon.com/ses/home?region=us-east-1#/account)
- [ ] Click "Request production access"
- [ ] Fill out the form with:
  - **Mail Type**: Transactional
  - **Website URL**: https://prism.thepaynes.ca
  - **Use Case Description**: 
    ```
    Prism DNS is a managed DNS service that sends transactional emails for:
    1. User account verification emails
    2. Password reset emails
    3. Service alerts and notifications
    
    We implement proper bounce and complaint handling with automatic
    suppression list management. All emails are opt-in only.
    ```
  - **Additional Contacts**: Only to users who sign up
  - **Compliance**: Confirm all compliance requirements

### After Approval
- [ ] Production access granted (check email)
- [ ] Sending quota increased from 200/day
- [ ] Maximum send rate increased from 1/second

## IAM Configuration

### EC2 Instance Role
- [ ] Update EC2 instance IAM role with SES permissions:
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
- [ ] Test IAM permissions from EC2 instance

## Application Configuration

### Environment Variables
- [ ] Set production environment variables:
  ```bash
  AWS_REGION=us-east-1
  AWS_SES_CONFIGURATION_SET=prism-dns-production
  EMAIL_PROVIDER=aws_ses
  EMAIL_FROM=noreply@prism.thepaynes.ca
  EMAIL_FROM_NAME="Prism DNS"
  AWS_SES_USE_IAM_ROLE=true
  ```

### Code Deployment
- [ ] Deploy latest code with SES provider
- [ ] Webhook endpoints accessible
- [ ] Database migrations run
- [ ] Application restarted

## Testing

### Email Delivery Tests
- [ ] Send test verification email
- [ ] Check email headers for:
  - [ ] DKIM-Signature present
  - [ ] SPF pass
  - [ ] DMARC pass
- [ ] Test with multiple providers:
  - [ ] Gmail
  - [ ] Outlook/Hotmail
  - [ ] Yahoo
  - [ ] Corporate email

### Bounce/Complaint Testing
- [ ] Test bounce handling with `bounce@simulator.amazonses.com`
- [ ] Test complaint handling with `complaint@simulator.amazonses.com`
- [ ] Verify suppression list updated
- [ ] Confirm webhooks receiving notifications

### Monitoring Tests
- [ ] CloudWatch metrics appearing
- [ ] Email metrics API endpoints working
- [ ] Grafana dashboards showing data

## Monitoring Setup

### CloudWatch Alarms
- [ ] Create high bounce rate alarm (>5%)
- [ ] Create high complaint rate alarm (>0.1%)
- [ ] Create send quota usage alarm (>80%)
- [ ] Configure alarm notifications

### Grafana Dashboards
- [ ] Import SES dashboard
- [ ] Configure data sources
- [ ] Set up email delivery panels
- [ ] Create bounce/complaint rate graphs

### Daily Monitoring
- [ ] Set up daily email report
- [ ] Configure reputation monitoring
- [ ] Enable send quota alerts

## Documentation

### Runbook
- [ ] Create SES troubleshooting guide
- [ ] Document common issues and solutions
- [ ] Include escalation procedures

### Support Procedures
- [ ] Document how to handle bounces
- [ ] Document how to remove suppressions
- [ ] Create email template guidelines

## Post-Deployment

### Reputation Management
- [ ] Monitor initial sending reputation
- [ ] Gradually increase sending volume
- [ ] Watch for deliverability issues
- [ ] Join feedback loops if available

### Ongoing Maintenance
- [ ] Regular suppression list review
- [ ] Monitor bounce/complaint rates
- [ ] Keep DNS records up to date
- [ ] Review CloudWatch logs weekly

## Emergency Procedures

### If Emails Stop Sending
1. Check CloudWatch metrics for quota limits
2. Verify IAM permissions haven't changed
3. Check for account suspension notifications
4. Review recent bounce/complaint rates
5. Verify DNS records still resolving

### If High Bounce Rate
1. Check email list quality
2. Review recent changes
3. Investigate specific bounce reasons
4. Temporarily reduce sending volume
5. Clean email lists

### If Account Suspended
1. Check AWS support cases
2. Review suspension reason
3. Create remediation plan
4. Submit appeal with fixes
5. Implement preventive measures

## Sign-off

- [ ] DevOps Engineer: _________________ Date: _______
- [ ] Team Lead: _____________________ Date: _______
- [ ] Security Review: ________________ Date: _______