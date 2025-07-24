#!/bin/bash
# API Demo Commands for Sprint Review
# These commands demonstrate the API functionality

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}=== TCP Client Authentication API Demo ===${NC}"
echo

# You'll need to set these tokens after logging in
ALICE_TOKEN=""
BOB_TOKEN=""
ADMIN_TOKEN=""

echo -e "${YELLOW}Note: You need to set the JWT tokens in this script first!${NC}"
echo "Get them by logging into the web UI and checking browser developer tools."
echo

# Function to make API call with nice output
api_call() {
    local desc=$1
    local token=$2
    local endpoint=$3
    
    echo -e "${BLUE}>>> $desc${NC}"
    echo "curl -H \"Authorization: Bearer \$TOKEN\" http://localhost:8000$endpoint"
    echo
    
    if [ -n "$token" ]; then
        curl -s -H "Authorization: Bearer $token" http://localhost:8000$endpoint | python -m json.tool
    else
        echo "(Token not set - skipping actual call)"
    fi
    echo
    echo "---"
    echo
}

# Demo sequence
echo -e "${GREEN}1. Alice's View - Regular User${NC}"
api_call "Alice lists her hosts" "$ALICE_TOKEN" "/api/v1/hosts"
api_call "Alice checks her stats" "$ALICE_TOKEN" "/api/v1/hosts/stats/summary"

echo -e "${GREEN}2. Bob's View - Regular User${NC}"
api_call "Bob lists his hosts" "$BOB_TOKEN" "/api/v1/hosts"
api_call "Bob checks his stats" "$BOB_TOKEN" "/api/v1/hosts/stats/summary"

echo -e "${GREEN}3. Admin View - Without Override${NC}"
api_call "Admin lists their own hosts" "$ADMIN_TOKEN" "/api/v1/hosts"

echo -e "${GREEN}4. Admin View - With Override${NC}"
api_call "Admin lists ALL hosts" "$ADMIN_TOKEN" "/api/v1/hosts?all=true"
api_call "Admin checks system stats" "$ADMIN_TOKEN" "/api/v1/hosts/stats/summary"

echo -e "${GREEN}5. Security Demo - Access Control${NC}"
echo -e "${BLUE}>>> Alice tries to access Bob's host (should fail)${NC}"
echo "curl -H \"Authorization: Bearer \$ALICE_TOKEN\" http://localhost:8000/api/v1/hosts/2"
echo "(Should return 404 - Host not found)"
echo

echo -e "${GREEN}6. Token Management${NC}"
api_call "List API tokens" "$ALICE_TOKEN" "/api/v1/tokens"

# Helper to extract tokens from browser
cat << 'EOF' > get-jwt-token.js
// Run this in browser console after logging in
// It will extract your JWT token

const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
if (token) {
    console.log('Your JWT token:');
    console.log(token);
    console.log('\nSet it in the script like:');
    console.log(`ALICE_TOKEN="${token}"`);
} else {
    console.log('No token found. Make sure you are logged in.');
}
EOF

echo -e "${YELLOW}To get JWT tokens:${NC}"
echo "1. Log into the web UI as each user"
echo "2. Open browser developer tools (F12)"
echo "3. Go to Console tab"
echo "4. Paste and run the contents of get-jwt-token.js"
echo "5. Copy the token and set it in this script"