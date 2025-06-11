#!/bin/bash
# PowerDNS Health Check Script

set -e

echo "🔍 PowerDNS Health Check"
echo "========================"

# Configuration
DNS_SERVER="${1:-localhost}"
API_PORT="${2:-8053}"
API_KEY="${PDNS_API_KEY:-changeme}"
TEST_DOMAIN="${3:-test.managed.prism.local}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if PowerDNS containers are running
echo -e "\n${YELLOW}Checking container status...${NC}"
if docker ps | grep -q powerdns-server; then
    echo -e "${GREEN}✓ PowerDNS server container is running${NC}"
else
    echo -e "${RED}✗ PowerDNS server container is not running${NC}"
    exit 1
fi

if docker ps | grep -q powerdns-database; then
    echo -e "${GREEN}✓ PowerDNS database container is running${NC}"
else
    echo -e "${RED}✗ PowerDNS database container is not running${NC}"
    exit 1
fi

# Check PowerDNS API health
echo -e "\n${YELLOW}Checking PowerDNS API...${NC}"
if curl -f -s -H "X-API-Key: ${API_KEY}" \
    http://${DNS_SERVER}:${API_PORT}/api/v1/servers/localhost > /dev/null; then
    echo -e "${GREEN}✓ PowerDNS API is responding${NC}"
    
    # Get server info
    echo -e "\n${YELLOW}Server Information:${NC}"
    curl -s -H "X-API-Key: ${API_KEY}" \
        http://${DNS_SERVER}:${API_PORT}/api/v1/servers/localhost | \
        jq -r '"\tVersion: \(.version)\n\tType: \(.type)\n\tID: \(.id)"' 2>/dev/null || echo "Unable to parse server info"
else
    echo -e "${RED}✗ PowerDNS API is not responding${NC}"
    echo "  Check API key and port configuration"
fi

# Check DNS resolution
echo -e "\n${YELLOW}Checking DNS resolution...${NC}"
if command -v dig &> /dev/null; then
    # Test DNS query
    if dig @${DNS_SERVER} -p 53 ${TEST_DOMAIN} +short +timeout=2 &> /dev/null; then
        echo -e "${GREEN}✓ DNS queries are working${NC}"
    else
        echo -e "${YELLOW}⚠ DNS queries not responding (may need zone configuration)${NC}"
    fi
else
    echo -e "${YELLOW}⚠ 'dig' command not found, skipping DNS query test${NC}"
fi

# Check port accessibility
echo -e "\n${YELLOW}Checking port accessibility...${NC}"
for port in 53 ${API_PORT}; do
    if nc -zv -w2 ${DNS_SERVER} ${port} &> /dev/null; then
        echo -e "${GREEN}✓ Port ${port} is accessible${NC}"
    else
        echo -e "${RED}✗ Port ${port} is not accessible${NC}"
    fi
done

# List configured zones (if API is working)
if curl -f -s -H "X-API-Key: ${API_KEY}" \
    http://${DNS_SERVER}:${API_PORT}/api/v1/servers/localhost > /dev/null; then
    echo -e "\n${YELLOW}Configured DNS Zones:${NC}"
    zones=$(curl -s -H "X-API-Key: ${API_KEY}" \
        http://${DNS_SERVER}:${API_PORT}/api/v1/servers/localhost/zones | \
        jq -r '.[] | .name' 2>/dev/null)
    
    if [ -n "$zones" ]; then
        echo "$zones" | while read -r zone; do
            echo -e "\t• ${zone}"
        done
    else
        echo -e "\t${YELLOW}No zones configured yet${NC}"
    fi
fi

# Summary
echo -e "\n${YELLOW}Health Check Summary:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "• DNS Server: ${DNS_SERVER}"
echo "• API Port: ${API_PORT}"
echo "• DNS Port: 53"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check docker logs for any errors
echo -e "\n${YELLOW}Recent PowerDNS logs:${NC}"
docker logs --tail=10 powerdns-server 2>&1 | grep -E "(error|Error|ERROR|fatal|Fatal)" || echo "No recent errors found"

echo -e "\n${GREEN}✅ PowerDNS health check complete!${NC}"