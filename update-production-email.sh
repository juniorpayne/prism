#!/bin/bash
# Script to update production deployment with email configuration

echo "🚀 Updating production deployment with SES email configuration..."

# SSH into production and update docker-compose.production.yml
ssh -i citadel.pem ubuntu@35.170.180.10 << 'EOF'
cd ~/prism-deployment

# Backup current configuration
cp docker-compose.production.yml docker-compose.production.yml.backup

# Create new docker-compose file with email configuration
cat > docker-compose.production.yml << 'COMPOSE'

services:
  prism-server:
    image: prism-server:latest
    container_name: prism-server
    restart: unless-stopped
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
      - SES_USE_IAM_ROLE=true
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

echo "✅ docker-compose.production.yml updated with email configuration"

# Restart the containers to apply changes
echo "🔄 Restarting containers..."
docker compose -f docker-compose.production.yml down
docker compose -f docker-compose.production.yml up -d

# Wait for services to start
sleep 10

# Check container status
echo "🔍 Checking container status..."
docker compose -f docker-compose.production.yml ps

# Check if email config is loaded
echo "🔍 Checking email configuration..."
docker compose -f docker-compose.production.yml exec prism-server env | grep -E 'EMAIL|SES|AWS' | sort

echo "✅ Production deployment updated!"
EOF

echo "✅ Script completed!"