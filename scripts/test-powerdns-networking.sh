#!/bin/bash
# Test PowerDNS networking setup locally

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Testing PowerDNS Networking Configuration${NC}"
echo "========================================"

# Step 1: Check current PowerDNS setup
echo -e "\n${YELLOW}1. Current PowerDNS containers:${NC}"
docker ps -a | grep -E "powerdns|prism" || echo "No containers found"

# Step 2: Check networks
echo -e "\n${YELLOW}2. Docker networks:${NC}"
docker network ls | grep -E "prism|powerdns"

# Step 3: Start PowerDNS with production-like config
echo -e "\n${YELLOW}3. Starting PowerDNS with production config...${NC}"
docker compose -f docker-compose.powerdns-test.yml down 2>/dev/null || true

# Create a test network if needed
if ! docker network ls | grep -q "test-prism-backend"; then
    docker network create test-prism-backend
fi

# Start PowerDNS
docker compose -f docker-compose.powerdns-test.yml up -d

# Wait for startup
sleep 5

# Step 4: Test API from different contexts
echo -e "\n${YELLOW}4. Testing PowerDNS API accessibility:${NC}"

# Direct test
echo -n "Direct API test (localhost:8053): "
if curl -s -H "X-API-Key: changeme" http://localhost:8053/api/v1/servers/localhost | grep -q authoritative; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

# Test from container on same network
echo -n "Container network test (powerdns-server:8053): "
docker run --rm --network manageddns_powerdns-net alpine/curl \
    -s -H "X-API-Key: changeme" http://powerdns-server:8053/api/v1/servers/localhost | grep -q authoritative && \
    echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}"

# Test DNS resolution
echo -n "DNS resolution test (port 5353): "
dig @localhost -p 5353 test.local SOA +short >/dev/null 2>&1 && \
    echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}"

# Step 5: Show container details
echo -e "\n${YELLOW}5. Container network details:${NC}"
docker inspect powerdns-server | jq '.[0].NetworkSettings.Networks'

echo -e "\n${GREEN}Test complete!${NC}"