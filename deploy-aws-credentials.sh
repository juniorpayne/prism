#!/bin/bash
# Script to securely deploy AWS credentials to production

set -e

echo "🔐 Deploying AWS credentials to production..."

# Check if AWS credentials are available
if [ -z "$(aws configure get aws_access_key_id)" ] || [ -z "$(aws configure get aws_secret_access_key)" ]; then
    echo "❌ Error: AWS credentials not found in AWS CLI configuration"
    echo "Please run 'aws configure' to set up your credentials"
    exit 1
fi

# Get credentials from AWS CLI config
AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id)
AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)

echo "📤 Deploying credentials to EC2..."

# SSH into production and set up credentials
ssh -i citadel.pem ubuntu@35.170.180.10 << EOF
cd ~/prism-deployment

# Create .env.production file with AWS credentials
cat > .env.production << 'ENVFILE'
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
ENVFILE

# Set secure permissions
chmod 600 .env.production

echo "✅ Credentials file created with secure permissions"

# Update docker-compose.production.yml to use env_file and disable IAM role
cat > docker-compose.production.yml << 'COMPOSE'

services:
  prism-server:
    image: prism-server:latest
    container_name: prism-server
    restart: unless-stopped
    env_file:
      - .env.production
    environment:
      - PRISM_SERVER_HOST=0.0.0.0
      - PRISM_SERVER_TCP_PORT=8080
      - PRISM_SERVER_API_PORT=8081
      - PRISM_LOGGING_LEVEL=INFO
      - PRISM_DATABASE_PATH=/data/prism.db
      # Email configuration
      - EMAIL_PROVIDER=aws_ses
      - EMAIL_FROM_ADDRESS=noreply@prism.thepaynes.ca
      - EMAIL_FROM_NAME=Prism DNS
      - EMAIL_ENABLED=true
      - EMAIL_DEBUG=false
      - AWS_REGION=us-east-1
      - SES_USE_IAM_ROLE=false
      - SES_CONFIGURATION_SET=prism-email-events
    volumes:
      - ./data:/data
      - ./config:/app/config
    ports:
      - "8080:8080"  # TCP server for client connections
      - "8081:8081"  # REST API for health checks
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  nginx:
    image: prism-web:latest
    container_name: prism-nginx
    restart: unless-stopped
    ports:
      - "8090:80"
    depends_on:
      - prism-server
    environment:
      - API_URL=http://server:8081
COMPOSE

echo "✅ docker-compose.production.yml updated"

# Restart containers to apply changes
echo "🔄 Restarting containers..."
docker compose -f docker-compose.production.yml down
docker compose -f docker-compose.production.yml up -d

# Wait for services to start
sleep 10

# Verify credentials are loaded
echo "🔍 Verifying AWS credentials..."
docker compose -f docker-compose.production.yml exec prism-server sh -c 'if [ -n "\$AWS_ACCESS_KEY_ID" ]; then echo "✅ AWS credentials are loaded"; else echo "❌ AWS credentials not found"; fi'

# Check container status
echo "📊 Container status:"
docker compose -f docker-compose.production.yml ps

echo "✅ Deployment complete!"
EOF

echo "✅ AWS credentials deployed to production!"
echo ""
echo "⚠️  Important: The credentials are now stored in .env.production on the EC2 instance"
echo "   Make sure to add .env.production to .gitignore if you ever commit from there"