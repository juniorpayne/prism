#!/bin/bash
# Script to update production with AWS credentials for SES

echo "🚀 Updating production with AWS credentials for SES..."

# Check if we have AWS credentials
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "❌ Error: AWS credentials not found in environment"
    echo "Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables"
    exit 1
fi

# SSH into production and update docker-compose.production.yml
ssh -i citadel.pem ubuntu@35.170.180.10 << EOF
cd ~/prism-deployment

# Create .env file with AWS credentials (secure)
cat > .env.production << 'ENVFILE'
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
ENVFILE

# Set proper permissions
chmod 600 .env.production

# Update docker-compose to use env file and disable IAM role
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

echo "✅ Configuration updated with AWS credentials"

# Restart the containers
echo "🔄 Restarting containers..."
docker compose -f docker-compose.production.yml down
docker compose -f docker-compose.production.yml up -d

# Wait for services
sleep 10

# Check status
echo "🔍 Checking container status..."
docker compose -f docker-compose.production.yml ps

echo "✅ Production updated with AWS credentials!"
EOF

echo "✅ Script completed!"