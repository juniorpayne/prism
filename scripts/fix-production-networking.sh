#!/bin/bash
# Fix production networking to use unified configuration

set -e

echo "=== Fixing Production Networking Configuration ==="
echo "This will stop all services and restart with unified networking"
echo ""

# Step 1: Stop all current services
echo "1. Stopping all current services..."
docker compose -f docker-compose.production.yml down
docker compose -f docker-compose.powerdns.yml down
docker stop prism-server prism-nginx powerdns-server powerdns-database 2>/dev/null || true

# Step 2: Remove old containers (to ensure clean state)
echo "2. Removing old containers..."
docker rm prism-server prism-nginx powerdns-server powerdns-database 2>/dev/null || true

# Step 3: Create unified network if it doesn't exist
echo "3. Creating unified network..."
docker network create prism-network 2>/dev/null || echo "Network already exists"

# Step 4: Start services with unified configuration
echo "4. Starting services with unified configuration..."
docker compose -f docker-compose.production-unified.yml up -d

# Step 5: Wait for services to be healthy
echo "5. Waiting for services to be healthy..."
sleep 15

# Step 6: Verify connectivity
echo "6. Verifying connectivity between services..."
echo ""

# Check if PowerDNS API is accessible from Prism server
docker exec prism-server curl -s -f http://powerdns-server:8053/api/v1/servers/localhost \
  -H "X-API-Key: ${PDNS_API_KEY:-test-api-key-change-in-production}" \
  && echo "✅ PowerDNS API is accessible from Prism server" \
  || echo "❌ PowerDNS API is NOT accessible from Prism server"

# Check if Prism API is healthy
curl -s -f http://localhost:8081/api/health \
  && echo "✅ Prism API is healthy" \
  || echo "❌ Prism API is NOT healthy"

# Step 7: Show final status
echo ""
echo "7. Final status:"
docker compose -f docker-compose.production-unified.yml ps

echo ""
echo "=== Migration Complete ==="
echo "All services should now be on the unified 'prism-network'"
echo "Zone creation should work properly now!"