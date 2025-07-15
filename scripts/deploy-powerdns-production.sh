#!/bin/bash
# Deploy PowerDNS to production with local-matching configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}PowerDNS Production Deployment Script${NC}"
echo "====================================="

# Check if we're on the production server
if [[ ! -f ~/.is_production_server ]]; then
    echo -e "${RED}This script should only be run on the production server${NC}"
    exit 1
fi

# Change to deployment directory
cd ~/prism-deployment

# Step 1: Stop existing PowerDNS if running
echo -e "\n${YELLOW}1. Checking for existing PowerDNS deployment...${NC}"
if docker ps -a | grep -q powerdns-server; then
    echo "Found existing PowerDNS containers. Stopping..."
    docker compose -f docker-compose.powerdns.yml down || true
    docker compose -f docker-compose.powerdns-production.yml down || true
fi

# Step 2: Ensure prism-backend network exists
echo -e "\n${YELLOW}2. Ensuring prism-backend network exists...${NC}"
if ! docker network ls | grep -q prism-backend; then
    echo "Creating prism-backend network..."
    docker network create prism-backend
else
    echo "prism-backend network already exists"
fi

# Step 3: Check for .env.powerdns
echo -e "\n${YELLOW}3. Checking PowerDNS environment configuration...${NC}"
if [[ ! -f .env.powerdns ]]; then
    echo -e "${RED}ERROR: .env.powerdns not found!${NC}"
    echo "Please create .env.powerdns from .env.powerdns.template"
    exit 1
fi

# Step 4: Deploy PowerDNS with production configuration
echo -e "\n${YELLOW}4. Deploying PowerDNS with production configuration...${NC}"
docker compose -f docker-compose.powerdns-production.yml --env-file .env.powerdns up -d --build

# Step 5: Wait for services to be healthy
echo -e "\n${YELLOW}5. Waiting for services to be healthy...${NC}"
sleep 10

# Check PowerDNS database
echo -n "Checking PowerDNS database... "
if docker compose -f docker-compose.powerdns-production.yml exec -T powerdns-db pg_isready -U powerdns &>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    docker compose -f docker-compose.powerdns-production.yml logs powerdns-db
    exit 1
fi

# Check PowerDNS server
echo -n "Checking PowerDNS server... "
if docker compose -f docker-compose.powerdns-production.yml exec -T powerdns pdns_control ping &>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    docker compose -f docker-compose.powerdns-production.yml logs powerdns
    exit 1
fi

# Step 6: Update Prism environment if needed
echo -e "\n${YELLOW}6. Updating Prism environment configuration...${NC}"
if ! grep -q "^POWERDNS_ENABLED=true" .env.production; then
    echo "Adding PowerDNS configuration to .env.production..."
    cat >> .env.production << EOF

# PowerDNS Integration
POWERDNS_ENABLED=true
POWERDNS_API_URL=http://powerdns-server:8053/api/v1
POWERDNS_API_KEY=$(grep PDNS_API_KEY .env.powerdns | cut -d= -f2)
EOF
else
    echo "PowerDNS configuration already in .env.production"
    # Update API URL to use container name
    sed -i 's|POWERDNS_API_URL=.*|POWERDNS_API_URL=http://powerdns-server:8053/api/v1|' .env.production
fi

# Step 7: Restart Prism to apply changes
echo -e "\n${YELLOW}7. Restarting Prism server...${NC}"
docker compose -f docker-compose.production.yml restart prism-server

# Step 8: Verify connectivity
echo -e "\n${YELLOW}8. Verifying PowerDNS API connectivity...${NC}"
sleep 5

# Get API key
API_KEY=$(grep PDNS_API_KEY .env.powerdns | cut -d= -f2)

# Test from inside Prism container
echo -n "Testing PowerDNS API from Prism container... "
if docker compose -f docker-compose.production.yml exec -T prism-server \
    curl -s -H "X-API-Key: ${API_KEY}" http://powerdns-server:8053/api/v1/servers/localhost | grep -q authoritative; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "Debugging information:"
    docker compose -f docker-compose.production.yml exec -T prism-server \
        curl -v -H "X-API-Key: ${API_KEY}" http://powerdns-server:8053/api/v1/servers/localhost
fi

# Step 9: Show status
echo -e "\n${YELLOW}9. Deployment Status:${NC}"
docker compose -f docker-compose.powerdns-production.yml ps
echo ""
docker compose -f docker-compose.production.yml ps | grep prism-server

echo -e "\n${GREEN}PowerDNS deployment complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Test DNS config endpoint: curl https://prism.thepaynes.ca/api/dns/config"
echo "2. Create a test zone through the UI"
echo "3. Monitor logs: docker compose -f docker-compose.powerdns-production.yml logs -f"