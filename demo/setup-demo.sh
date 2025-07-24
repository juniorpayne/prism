#!/bin/bash
# Sprint Demo Setup Script
# This script helps set up the demo environment

echo "=== TCP Client Authentication Demo Setup ==="
echo

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if server is running
echo -e "${BLUE}Checking if Prism server is running...${NC}"
if curl -s http://localhost:8000/api/health > /dev/null; then
    echo -e "${GREEN}✓ Server is running${NC}"
else
    echo -e "${RED}✗ Server is not running. Please start it with: docker compose up${NC}"
    exit 1
fi

echo
echo -e "${BLUE}Demo Users to Create:${NC}"
echo "1. Alice (alice@example.com) - Regular user"
echo "2. Bob (bob@example.com) - Regular user"
echo "3. Admin (admin@example.com) - Admin user"
echo
echo "Please create these users in the web UI and generate API tokens for Alice and Bob."
echo "Web UI: http://localhost:8000"
echo

# Create demo run script
cat > run-demo.sh << 'EOF'
#!/bin/bash
# Run the demo clients

# Function to run client in background
run_client() {
    local name=$1
    local config=$2
    echo "Starting $name client..."
    python prism_client.py -c $config start
    sleep 2
    if [ -f /tmp/prism-client-$name.pid ]; then
        echo "✓ $name client started successfully"
    else
        echo "✗ Failed to start $name client"
    fi
}

# Run Alice's client
run_client "alice" "demo/alice-prism-client.yaml"

# Run Bob's client
run_client "bob" "demo/bob-prism-client.yaml"

echo
echo "Clients are running. Check the web UI to see user-specific hosts."
echo "Logs:"
echo "  tail -f /tmp/prism-client-alice.log"
echo "  tail -f /tmp/prism-client-bob.log"
EOF

chmod +x run-demo.sh

# Create cleanup script
cat > cleanup-demo.sh << 'EOF'
#!/bin/bash
# Clean up demo environment

echo "Stopping demo clients..."
python prism_client.py -c demo/alice-prism-client.yaml stop 2>/dev/null
python prism_client.py -c demo/bob-prism-client.yaml stop 2>/dev/null

echo "Removing PID files..."
rm -f /tmp/prism-client-*.pid

echo "Removing log files..."
rm -f /tmp/prism-client-*.log

echo "Demo cleanup complete!"
EOF

chmod +x cleanup-demo.sh

echo -e "${GREEN}Demo setup complete!${NC}"
echo
echo "Next steps:"
echo "1. Update the auth_token in alice-prism-client.yaml and bob-prism-client.yaml"
echo "2. Run ./run-demo.sh to start the demo clients"
echo "3. Use ./cleanup-demo.sh when done"
echo
echo "Demo files created:"
ls -la *.yaml
echo
echo "Scripts created:"
ls -la *.sh