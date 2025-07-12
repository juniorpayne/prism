#!/bin/bash
# Check if EC2 instance has SES permissions

echo "🔍 Checking SES permissions on EC2 instance..."

ssh -i citadel.pem ubuntu@35.170.180.10 << 'EOF'
# Test SES access from within the container
echo "Testing SES access..."

docker run --rm \
  -e AWS_REGION=us-east-1 \
  amazon/aws-cli:latest \
  ses list-identities 2>&1 | head -20

echo ""
echo "If you see 'Unable to locate credentials', the EC2 instance needs:"
echo "1. An IAM role with SES permissions attached, OR"
echo "2. AWS credentials configured in the container"
EOF