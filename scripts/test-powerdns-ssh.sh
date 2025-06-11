#!/bin/bash
# Test PowerDNS deployment via SSH

echo "🔍 PowerDNS Testing via SSH"
echo "==========================="

# Configuration
EC2_HOST="35.170.180.10"
EC2_USER="ubuntu"

# Check PowerDNS containers
echo -e "\n📦 Checking PowerDNS containers..."
ssh -i citadel.pem $EC2_USER@$EC2_HOST << 'EOF'
cd ~/prism-deployment
if [ -f docker-compose.powerdns.yml ]; then
    echo "✅ PowerDNS compose file found"
    docker compose -f docker-compose.powerdns.yml ps
else
    echo "❌ PowerDNS compose file not found"
    echo "Contents of deployment directory:"
    ls -la
fi
EOF

# Check if PowerDNS is running
echo -e "\n🐳 Checking Docker containers..."
ssh -i citadel.pem $EC2_USER@$EC2_HOST 'docker ps | grep -E "(powerdns|CONTAINER)" | head -5'

# Test PowerDNS API locally on the server
echo -e "\n🔌 Testing PowerDNS API (localhost)..."
ssh -i citadel.pem $EC2_USER@$EC2_HOST << 'EOF'
# Check if API is responding
if curl -f -s -H "X-API-Key: changeme-in-production" http://localhost:8053/api/v1/servers/localhost > /dev/null 2>&1; then
    echo "✅ PowerDNS API is responding"
    
    # Get server info
    echo "Server info:"
    curl -s -H "X-API-Key: changeme-in-production" http://localhost:8053/api/v1/servers/localhost | jq -r '.version' 2>/dev/null || echo "Unable to get version"
else
    echo "❌ PowerDNS API is not responding"
    echo "Checking if PowerDNS container is running:"
    docker ps | grep powerdns || echo "No PowerDNS containers found"
fi
EOF

# Test DNS resolution locally
echo -e "\n🌐 Testing DNS resolution (localhost)..."
ssh -i citadel.pem $EC2_USER@$EC2_HOST << 'EOF'
# Install dig if not present
which dig > /dev/null 2>&1 || sudo apt-get install -y dnsutils > /dev/null 2>&1

# Test DNS query
echo "Testing DNS query to localhost..."
dig @localhost -p 53 test.managed.prism.local +short +timeout=2 || echo "DNS query failed (this is normal if no zones are configured yet)"

# Check if port 53 is listening
echo -e "\nChecking if port 53 is listening:"
sudo netstat -tulnp | grep :53 || echo "Port 53 not found"
EOF

# Check PowerDNS logs
echo -e "\n📋 Recent PowerDNS logs..."
ssh -i citadel.pem $EC2_USER@$EC2_HOST << 'EOF'
cd ~/prism-deployment
if [ -f docker-compose.powerdns.yml ]; then
    echo "=== PowerDNS Server Logs ==="
    docker compose -f docker-compose.powerdns.yml logs --tail=20 powerdns 2>/dev/null || echo "No logs available"
    
    echo -e "\n=== PowerDNS Database Logs ==="
    docker compose -f docker-compose.powerdns.yml logs --tail=10 powerdns-db 2>/dev/null || echo "No logs available"
fi
EOF

echo -e "\n✅ Testing complete!"
echo ""
echo "Next steps if PowerDNS is running:"
echo "1. Create a test zone using the API"
echo "2. Add DNS records"
echo "3. Test resolution"
echo ""
echo "To create a test zone, run this on the server:"
echo 'curl -X POST -H "X-API-Key: changeme-in-production" -H "Content-Type: application/json" -d '"'"'{"name": "test.com.", "kind": "Native", "nameservers": ["ns1.test.com.", "ns2.test.com."]}'"'"' http://localhost:8053/api/v1/servers/localhost/zones'