#!/bin/bash
# Commands to run on EC2 instance for SES setup

# 1. SSH into EC2
echo "SSH into EC2:"
echo "ssh ubuntu@35.170.180.10"

# 2. Navigate to deployment directory
echo -e "\nOn EC2, run:"
echo "cd ~/prism-deployment"

# 3. Pull latest changes
echo "git pull origin main"

# 4. Run SES setup script
echo "chmod +x scripts/setup-ses-production.sh"
echo "./scripts/setup-ses-production.sh"

# 5. Save DNS records
echo -e "\nThe script will output DNS records to add. Save them to a file:"
echo "cat ses_dns_records.txt"

# 6. Test commands after DNS setup
echo -e "\n# After adding DNS records, verify:"
echo "./scripts/setup-ses-production.sh verify"

# 7. Test email sending (after domain verification)
echo -e "\n# Test email (replace with your email):"
echo "TEST_EMAIL=your@email.com ./scripts/setup-ses-production.sh test"

# 8. Update production environment
echo -e "\n# Update production config:"
echo "cd ~/prism-deployment"
echo "cat >> .env.production << EOF"
echo "EMAIL_PROVIDER=aws_ses"
echo "AWS_REGION=us-east-1"
echo "AWS_SES_CONFIGURATION_SET=prism-dns-production"
echo "AWS_SES_USE_IAM_ROLE=true"
echo "EMAIL_FROM=noreply@prism.thepaynes.ca"
echo "EMAIL_FROM_NAME=\"Prism DNS\""
echo "EOF"

# 9. Restart services
echo -e "\n# Restart services with new config:"
echo "docker compose -f docker-compose.production.yml restart prism-server"

# 10. Check logs
echo -e "\n# Monitor logs:"
echo "docker compose -f docker-compose.production.yml logs -f prism-server"