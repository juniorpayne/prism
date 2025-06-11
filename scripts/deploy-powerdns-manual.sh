#!/bin/bash
# Manual PowerDNS deployment script with proper port handling

echo "🚀 PowerDNS Manual Deployment Script"
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

echo "📦 Creating deployment package..."

# Create tarball with PowerDNS files
tar -czf powerdns-deploy.tar.gz \
    docker-compose.powerdns.yml \
    powerdns/ \
    scripts/setup-powerdns-port53.sh \
    .env.powerdns 2>/dev/null || true

echo "📤 Transferring files to EC2..."
scp -i $SSH_KEY -o StrictHostKeyChecking=no \
    powerdns-deploy.tar.gz \
    $EC2_USER@$EC2_HOST:~/

echo "🚀 Deploying PowerDNS on EC2..."
ssh -i $SSH_KEY -o StrictHostKeyChecking=no $EC2_USER@$EC2_HOST << 'EOF'
    set -e
    
    echo "📁 Extracting PowerDNS files..."
    cd ~/prism-deployment
    tar -xzf ~/powerdns-deploy.tar.gz
    
    echo "🔐 Setting up environment..."
    if [ ! -f .env.powerdns ]; then
        echo "Creating default .env.powerdns..."
        cat > .env.powerdns << 'ENV'
PDNS_API_KEY=changeme-in-production
PDNS_DB_PASSWORD=changeme-in-production
PDNS_DB_NAME=powerdns
PDNS_DB_USER=powerdns
PDNS_DEFAULT_ZONE=managed.prism.local
PDNS_API_ALLOW_FROM=127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
ENV
    fi
    
    echo "🔧 Setting up port 53..."
    chmod +x scripts/setup-powerdns-port53.sh
    sudo ./scripts/setup-powerdns-port53.sh
    
    echo "🐳 Creating Docker networks..."
    docker network create prism-backend 2>/dev/null || true
    docker network create prism-frontend 2>/dev/null || true
    
    echo "🛑 Stopping any existing PowerDNS containers..."
    docker compose -f docker-compose.powerdns.yml down || true
    
    echo "🔨 Building PowerDNS image..."
    docker compose -f docker-compose.powerdns.yml build powerdns
    
    echo "🚀 Starting PowerDNS services..."
    docker compose -f docker-compose.powerdns.yml up -d
    
    echo "⏳ Waiting for services to stabilize..."
    sleep 15
    
    echo "📊 Checking container status..."
    docker compose -f docker-compose.powerdns.yml ps
    
    echo "📋 Recent PowerDNS logs..."
    docker compose -f docker-compose.powerdns.yml logs --tail=20 powerdns
    
    echo "🔍 Testing PowerDNS API..."
    if curl -s -f -H "X-API-Key: changeme-in-production" http://localhost:8053/api/v1/servers/localhost > /dev/null 2>&1; then
        echo "✅ PowerDNS API is responding!"
    else
        echo "❌ PowerDNS API is not responding"
        echo "Checking container status..."
        docker ps | grep powerdns || echo "No PowerDNS containers running"
    fi
    
    # Clean up
    rm -f ~/powerdns-deploy.tar.gz
    
    echo "✅ PowerDNS deployment complete!"
EOF

# Clean up local file
rm -f powerdns-deploy.tar.gz

echo "✅ Deployment script complete!"
echo ""
echo "Next steps:"
echo "1. SSH to server: ssh -i $SSH_KEY $EC2_USER@$EC2_HOST"
echo "2. Check status: cd ~/prism-deployment && docker compose -f docker-compose.powerdns.yml ps"
echo "3. Test DNS: dig @$EC2_HOST test.managed.prism.local"