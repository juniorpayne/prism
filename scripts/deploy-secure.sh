#!/bin/bash
set -e

# Secure Deployment Script for Prism DNS
# This script deploys the application with security hardening

echo "🔒 Secure Deployment Script for Prism DNS"
echo "========================================="

# Configuration
DOMAIN="prism.thepaynes.ca"
EMAIL="admin@thepaynes.ca"
EC2_HOST="35.170.180.10"
EC2_USER="ubuntu"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Step 1: Deploy security scripts to EC2
print_status "Copying security scripts to EC2..."
scp -o StrictHostKeyChecking=no \
    scripts/setup-ssl.sh \
    scripts/harden-system.sh \
    scripts/test-security.sh \
    ${EC2_USER}@${EC2_HOST}:~/

# Step 2: Copy security configurations
print_status "Copying security configurations..."
scp -r nginx docker-compose.security.yml \
    ${EC2_USER}@${EC2_HOST}:~/prism-deployment/

# Step 3: Execute system hardening
print_info "Starting system hardening (this will take a few minutes)..."
ssh ${EC2_USER}@${EC2_HOST} << 'EOF'
cd ~
echo "Running system hardening..."
sudo ./harden-system.sh

echo "Setting up Docker security..."
cd ~/prism-deployment

# Apply security overlay to Docker Compose
if [ -f docker-compose.production.yml ] && [ -f docker-compose.security.yml ]; then
    echo "Applying security configuration to containers..."
    docker compose -f docker-compose.production.yml -f docker-compose.security.yml down
    docker compose -f docker-compose.production.yml -f docker-compose.security.yml up -d
fi
EOF

# Step 4: Install and configure nginx as reverse proxy
print_info "Setting up Nginx reverse proxy..."
ssh ${EC2_USER}@${EC2_HOST} << 'EOF'
# Install nginx if not present
if ! command -v nginx &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y nginx
fi

# Create basic nginx config for reverse proxy
sudo tee /etc/nginx/sites-available/prism-proxy > /dev/null << 'NGINX'
server {
    listen 80;
    server_name prism.thepaynes.ca;

    location / {
        proxy_pass http://localhost:80;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
    
    location /api/ {
        proxy_pass http://localhost:8080/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

sudo ln -sf /etc/nginx/sites-available/prism-proxy /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
EOF

# Step 5: Set up SSL certificates
print_info "Setting up SSL certificates for ${DOMAIN}..."
print_info "Note: Make sure DNS A record points to ${EC2_HOST}"

read -p "Is the DNS configured and pointing to the EC2 instance? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ssh ${EC2_USER}@${EC2_HOST} "sudo ./setup-ssl.sh ${DOMAIN} ${EMAIL}"
else
    print_info "Skipping SSL setup. Run './setup-ssl.sh ${DOMAIN} ${EMAIL}' on the server when DNS is ready."
fi

# Step 6: Run security tests
print_status "Running security tests..."
./scripts/test-security.sh ${EC2_HOST} false

# Step 7: Display summary
echo ""
print_status "Secure deployment complete!"
echo ""
echo "Security measures implemented:"
echo "✓ System hardening applied"
echo "✓ Docker security constraints enabled"
echo "✓ Nginx reverse proxy configured"
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "✓ SSL certificates configured"
fi
echo ""
echo "Next steps:"
echo "1. Verify DNS is pointing to ${EC2_HOST}"
echo "2. Test HTTPS access at https://${DOMAIN}"
echo "3. Run security scan: ./scripts/test-security.sh ${DOMAIN} true"
echo "4. Check SSL Labs rating: https://www.ssllabs.com/ssltest/analyze.html?d=${DOMAIN}"
echo ""
echo "Important security notes:"
echo "- SSH is now key-only authentication"
echo "- Firewall is active with minimal ports open"
echo "- Automatic security updates are enabled"
echo "- Fail2ban is protecting against brute force attacks"