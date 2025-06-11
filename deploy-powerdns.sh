#\!/bin/bash
# Direct PowerDNS deployment

echo "🚀 Deploying PowerDNS directly to EC2..."

# First, let's create the files locally and transfer them
tar -czf powerdns-files.tar.gz \
  docker-compose.powerdns.yml \
  powerdns/ \
  .env.powerdns

echo "📤 Transferring PowerDNS files to EC2..."
scp -i citadel.pem -o StrictHostKeyChecking=no \
  powerdns-files.tar.gz \
  ubuntu@35.170.180.10:~/

echo "🔧 Setting up PowerDNS on EC2..."
ssh -i citadel.pem -o StrictHostKeyChecking=no ubuntu@35.170.180.10 << 'EOF'
  set -e
  
  echo "📁 Extracting PowerDNS files..."
  cd ~/prism-deployment
  tar -xzf ~/powerdns-files.tar.gz
  
  echo "🔐 Setting up environment..."
  if [ \! -f .env.powerdns ]; then
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
  
  echo "🐳 Creating Docker networks..."
  docker network create prism-backend 2>/dev/null || true
  docker network create prism-frontend 2>/dev/null || true
  
  echo "🚀 Starting PowerDNS containers..."
  docker compose -f docker-compose.powerdns.yml --env-file .env.powerdns up -d
  
  echo "⏳ Waiting for services to start..."
  sleep 20
  
  echo "📊 Checking container status..."
  docker compose -f docker-compose.powerdns.yml ps
  
  echo "🔍 Checking PowerDNS logs..."
  docker compose -f docker-compose.powerdns.yml logs --tail=20
  
  # Clean up
  rm -f ~/powerdns-files.tar.gz
  
  echo "✅ PowerDNS deployment complete\!"
EOF

rm -f powerdns-files.tar.gz
