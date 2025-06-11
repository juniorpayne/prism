#!/bin/bash
# Manual PowerDNS deployment script

echo "🌐 Manual PowerDNS Deployment Script"
echo "===================================="

# Configuration
EC2_HOST="35.170.180.10"
EC2_USER="ubuntu"
SSH_KEY="citadel.pem"

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ SSH key $SSH_KEY not found!"
    exit 1
fi

echo "📦 Preparing PowerDNS files..."

# Create a temporary directory
TEMP_DIR=$(mktemp -d)
cd $TEMP_DIR

# Copy PowerDNS files
cp -r /home/junior/managedDns/docker-compose.powerdns.yml .
cp -r /home/junior/managedDns/powerdns .
cp -r /home/junior/managedDns/.env.powerdns .

# Create tarball
tar -czf powerdns-deploy.tar.gz docker-compose.powerdns.yml powerdns .env.powerdns

echo "📤 Transferring files to EC2..."
scp -i ../$SSH_KEY -o StrictHostKeyChecking=no \
    powerdns-deploy.tar.gz \
    $EC2_USER@$EC2_HOST:~/

echo "🚀 Deploying PowerDNS on EC2..."
ssh -i ../$SSH_KEY -o StrictHostKeyChecking=no $EC2_USER@$EC2_HOST << 'EOF'
    set -e
    echo "🔄 Extracting PowerDNS files..."
    cd ~/prism-deployment
    tar -xzf ~/powerdns-deploy.tar.gz
    
    echo "🔐 Setting up environment..."
    if [ ! -f .env.powerdns ]; then
        cp .env.powerdns.example .env.powerdns 2>/dev/null || true
    fi
    
    echo "🐳 Creating networks..."
    docker network create prism-backend 2>/dev/null || true
    docker network create prism-frontend 2>/dev/null || true
    
    echo "🚀 Starting PowerDNS..."
    docker compose -f docker-compose.powerdns.yml --env-file .env.powerdns up -d
    
    echo "⏳ Waiting for services to start..."
    sleep 15
    
    echo "📊 Checking status..."
    docker compose -f docker-compose.powerdns.yml ps
    
    echo "✅ PowerDNS deployment complete!"
    
    # Clean up
    rm -f ~/powerdns-deploy.tar.gz
EOF

# Clean up local temp files
cd ..
rm -rf $TEMP_DIR

echo "✅ Manual deployment complete!"
echo ""
echo "Next steps:"
echo "1. Check PowerDNS status: ssh -i $SSH_KEY $EC2_USER@$EC2_HOST 'cd ~/prism-deployment && docker compose -f docker-compose.powerdns.yml ps'"
echo "2. View logs: ssh -i $SSH_KEY $EC2_USER@$EC2_HOST 'cd ~/prism-deployment && docker compose -f docker-compose.powerdns.yml logs'"
echo "3. Test DNS: dig @$EC2_HOST test.managed.prism.local"