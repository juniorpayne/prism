#!/bin/bash
set -e

# Deploy Monitoring Stack for Prism DNS (SCRUM-38)
# Deploys Prometheus, Grafana, and AlertManager

echo "🚀 Deploying Prism DNS Monitoring Stack"
echo "======================================"

# Configuration
EC2_HOST="35.170.180.10"
EC2_USER="ubuntu"
SSH_KEY="citadel.pem"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if running locally or on EC2
if [ "$1" == "local" ]; then
    print_info "Deploying monitoring stack locally..."
    
    # Start monitoring stack
    docker compose -f docker-compose.monitoring.yml up -d
    
    print_status "Monitoring stack deployed locally"
    echo ""
    echo "Access points:"
    echo "- Prometheus: http://localhost:9090"
    echo "- Grafana: http://localhost:3000 (admin/admin)"
    echo "- AlertManager: http://localhost:9093"
    
else
    print_info "Deploying monitoring stack to EC2..."
    
    # Copy monitoring files to EC2
    print_status "Copying monitoring configuration to EC2..."
    ssh -o StrictHostKeyChecking=no -i ${SSH_KEY} ${EC2_USER}@${EC2_HOST} "mkdir -p ~/prism-monitoring"
    
    scp -r -o StrictHostKeyChecking=no -i ${SSH_KEY} \
        docker-compose.monitoring.yml \
        monitoring/ \
        ${EC2_USER}@${EC2_HOST}:~/prism-monitoring/
    
    # Deploy on EC2
    print_status "Starting monitoring stack on EC2..."
    ssh -o StrictHostKeyChecking=no -i ${SSH_KEY} ${EC2_USER}@${EC2_HOST} << 'EOF'
cd ~/prism-monitoring

# Update Prometheus config for production
sed -i 's/host.docker.internal/prism-server/g' monitoring/prometheus.yml

# Create directories if they don't exist
mkdir -p monitoring/rules

# Copy alert rules
if [ ! -f monitoring/rules/prism-alerts.yml ]; then
    cp monitoring/rules/prism-alerts.yml monitoring/rules/ 2>/dev/null || true
fi

# Start monitoring stack
docker compose -f docker-compose.monitoring.yml up -d

# Wait for services to start
sleep 30

# Check status
docker compose -f docker-compose.monitoring.yml ps
EOF
    
    print_status "Monitoring stack deployed to EC2"
    echo ""
    echo "Access points:"
    echo "- Prometheus: http://${EC2_HOST}:9090"
    echo "- Grafana: http://${EC2_HOST}:3000 (admin/admin)"
    echo "- AlertManager: http://${EC2_HOST}:9093"
    
    # Configure nginx reverse proxy for monitoring
    print_info "Configuring nginx reverse proxy for monitoring..."
    ssh -o StrictHostKeyChecking=no -i ${SSH_KEY} ${EC2_USER}@${EC2_HOST} << 'EOF'
# Add monitoring locations to nginx config
sudo tee -a /etc/nginx/sites-available/prism > /dev/null << 'NGINX'

    # Prometheus
    location /prometheus/ {
        proxy_pass http://localhost:9090/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Grafana
    location /grafana/ {
        proxy_pass http://localhost:3000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
NGINX

# Test and reload nginx
sudo nginx -t && sudo systemctl reload nginx
EOF
    
    print_status "Nginx reverse proxy configured"
    echo ""
    echo "Secure access points:"
    echo "- Prometheus: https://prism.thepaynes.ca/prometheus/"
    echo "- Grafana: https://prism.thepaynes.ca/grafana/"
fi

echo ""
print_status "Monitoring deployment complete!"
echo ""
echo "Next steps:"
echo "1. Access Grafana and change the default password"
echo "2. Import additional dashboards as needed"
echo "3. Configure alert notification channels in AlertManager"
echo "4. Test alerts by stopping services"

# Show example alert test
echo ""
echo "To test alerts, try:"
echo "docker stop prism-server  # Triggers ServiceDown alert"