#!/bin/bash

# Deployment script for Prism DNS to EC2
# Usage: ./deploy.sh [environment]

set -e

# Configuration
EC2_HOST="35.170.180.10"
EC2_USER="ubuntu"
SSH_KEY="citadel.pem"
REMOTE_DIR="/opt/prism-dns/app"
ENVIRONMENT="${1:-production}"

echo "🚀 Deploying Prism DNS to EC2 (Environment: $ENVIRONMENT)"

# Function to run commands on EC2
run_remote() {
    ssh -i "$SSH_KEY" "$EC2_USER@$EC2_HOST" "$1"
}

# Function to copy files to EC2
copy_to_ec2() {
    scp -i "$SSH_KEY" -r "$1" "$EC2_USER@$EC2_HOST:$2"
}

echo "📦 Copying application files..."

# Create remote app directory
run_remote "mkdir -p $REMOTE_DIR"

# Copy application code
copy_to_ec2 "server/" "$REMOTE_DIR/"
copy_to_ec2 "web/" "$REMOTE_DIR/"
copy_to_ec2 "config/" "$REMOTE_DIR/"
copy_to_ec2 "Dockerfile.production" "$REMOTE_DIR/"
copy_to_ec2 "docker-compose.production.yml" "$REMOTE_DIR/"
copy_to_ec2 ".env.$ENVIRONMENT.template" "$REMOTE_DIR/"

echo "⚙️ Setting up environment configuration..."

# Create environment file from template
run_remote "cd $REMOTE_DIR && cp .env.$ENVIRONMENT.template .env.$ENVIRONMENT"

# Set proper permissions
run_remote "sudo chown -R ubuntu:ubuntu /opt/prism-dns/"

echo "🐳 Building and starting Docker containers..."

# Navigate to app directory and start services
run_remote "cd $REMOTE_DIR && docker compose -f docker-compose.production.yml --env-file .env.$ENVIRONMENT build --no-cache"

echo "✅ Deployment completed!"
echo "🌐 Application should be available at: http://$EC2_HOST"
echo "📊 API health check: http://$EC2_HOST/api/health"

echo "🔧 To start the services, run:"
echo "   ssh -i $SSH_KEY $EC2_USER@$EC2_HOST 'cd $REMOTE_DIR && docker compose -f docker-compose.production.yml up -d'"