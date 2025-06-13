#!/bin/bash
#
# Pre-deployment test script - RUN THIS BEFORE PUSHING!
#
set -e

echo "🚨 PRE-DEPLOYMENT TESTING"
echo "========================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a command succeeded
check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1${NC}"
    else
        echo -e "${RED}✗ $1${NC}"
        echo -e "${RED}FAILED! Do not deploy!${NC}"
        exit 1
    fi
}

# 1. Check Docker services
echo -e "\n${YELLOW}1. Starting Docker services...${NC}"
docker compose down
docker compose up -d --build
sleep 10  # Wait for services to start
check_status "Docker services started"

# 2. Check API endpoints
echo -e "\n${YELLOW}2. Testing API endpoints...${NC}"
curl -s http://localhost:8081/api/health > /dev/null
check_status "Health endpoint"

curl -s http://localhost:8081/api/stats > /dev/null
check_status "Stats endpoint"

curl -s http://localhost:8081/api/hosts > /dev/null
check_status "Hosts endpoint"

# 3. Check web interface
echo -e "\n${YELLOW}3. Testing web interface...${NC}"
# Test if index.html loads from nginx container
curl -s http://localhost:8090/ > /dev/null
check_status "Web interface loads"

# 4. Run linting
echo -e "\n${YELLOW}4. Running linting checks...${NC}"
cd /home/junior/managedDns
source venv/bin/activate
python -m black --check . > /dev/null 2>&1
check_status "Black formatting"

python -m isort --check-only . > /dev/null 2>&1
check_status "Import sorting"

python -m flake8 --select=E722 . > /dev/null 2>&1
check_status "Flake8 checks"

# 5. Run basic tests
echo -e "\n${YELLOW}5. Running tests...${NC}"
python -m pytest tests/test_api/ -q > /dev/null 2>&1
check_status "API tests"

# Final check
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✅ ALL TESTS PASSED! Safe to deploy.${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${YELLOW}Remember to also:${NC}"
echo "- Open http://localhost:8081/docs to check API documentation"
echo "- Manually test the dashboard at http://localhost:8090/#dashboard"
echo "- Check browser console for JavaScript errors"

echo -e "\n${YELLOW}Stopping services...${NC}"
docker compose down