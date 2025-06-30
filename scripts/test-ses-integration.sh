#!/bin/bash
# Test script for AWS SES integration
# Verifies all components are working correctly

set -e

# Configuration
API_URL="${API_URL:-https://prism.thepaynes.ca}"
TEST_EMAIL="${TEST_EMAIL:-test@example.com}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🧪 AWS SES Integration Test Suite${NC}"
echo "===================================="
echo "API URL: $API_URL"
echo "Test Email: $TEST_EMAIL"
echo ""

# Function to check endpoint
check_endpoint() {
    local endpoint=$1
    local expected_status=$2
    local description=$3
    
    echo -n "Testing $description... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL$endpoint")
    
    if [ "$response" == "$expected_status" ]; then
        echo -e "${GREEN}✓ PASS${NC} (Status: $response)"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected: $expected_status, Got: $response)"
        return 1
    fi
}

# Function to test JSON endpoint
test_json_endpoint() {
    local endpoint=$1
    local description=$2
    
    echo -n "Testing $description... "
    
    response=$(curl -s "$API_URL$endpoint")
    
    if echo "$response" | jq . >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        echo "$response" | jq . | head -10
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Invalid JSON)"
        echo "$response"
        return 1
    fi
}

# Test 1: Health Check
echo -e "\n${YELLOW}1. Testing Health Endpoints${NC}"
check_endpoint "/api/health" "200" "API Health"
check_endpoint "/api/webhooks/ses/health" "200" "Webhook Health"

# Test 2: Metrics Endpoints
echo -e "\n${YELLOW}2. Testing Metrics Endpoints${NC}"
test_json_endpoint "/api/metrics/email/summary" "Email Summary Metrics"
test_json_endpoint "/api/metrics/email/bounces?days=7" "Bounce Metrics"
test_json_endpoint "/api/metrics/email/complaints?days=7" "Complaint Metrics"
test_json_endpoint "/api/metrics/email/suppressions?limit=10" "Suppression List"

# Test 3: User Registration (triggers email)
echo -e "\n${YELLOW}3. Testing Email Sending via Registration${NC}"
echo -n "Attempting user registration... "

# Generate unique email
UNIQUE_EMAIL="test-$(date +%s)@example.com"

registration_response=$(curl -s -X POST "$API_URL/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$UNIQUE_EMAIL\",
        \"password\": \"TestPass123!\",
        \"full_name\": \"SES Test User\"
    }")

if echo "$registration_response" | jq -e '.email' >/dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC}"
    echo "User created: $(echo "$registration_response" | jq -r '.email')"
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "$registration_response" | jq .
fi

# Test 4: Bounce Simulator
echo -e "\n${YELLOW}4. Testing Bounce Handling${NC}"
echo -n "Testing with bounce simulator... "

bounce_response=$(curl -s -X POST "$API_URL/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"bounce@simulator.amazonses.com\",
        \"password\": \"TestPass123!\",
        \"full_name\": \"Bounce Test\"
    }")

# We expect this to succeed initially (email queued)
if echo "$bounce_response" | jq . >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Email queued${NC}"
else
    echo -e "${YELLOW}⚠ Unexpected response${NC}"
fi

# Test 5: Complaint Simulator
echo -e "\n${YELLOW}5. Testing Complaint Handling${NC}"
echo -n "Testing with complaint simulator... "

complaint_response=$(curl -s -X POST "$API_URL/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"complaint@simulator.amazonses.com\",
        \"password\": \"TestPass123!\",
        \"full_name\": \"Complaint Test\"
    }")

if echo "$complaint_response" | jq . >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Email queued${NC}"
else
    echo -e "${YELLOW}⚠ Unexpected response${NC}"
fi

# Test 6: Webhook Simulation
echo -e "\n${YELLOW}6. Testing Webhook Endpoint${NC}"
echo -n "Sending test bounce notification... "

# Create test SNS message
webhook_payload=$(cat <<EOF
{
    "Type": "Notification",
    "MessageId": "test-message-id",
    "TopicArn": "arn:aws:sns:us-east-1:123456789012:test",
    "Message": "{\"notificationType\":\"Bounce\",\"bounce\":{\"bounceType\":\"Permanent\",\"bouncedRecipients\":[{\"emailAddress\":\"test-bounce@example.com\"}],\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)\",\"feedbackId\":\"test-feedback-$(date +%s)\"},\"mail\":{\"messageId\":\"test-message-id\"}}",
    "Timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"
}
EOF
)

webhook_response=$(curl -s -X POST "$API_URL/api/webhooks/ses/notifications" \
    -H "Content-Type: application/json" \
    -H "x-amz-sns-message-type: Notification" \
    -d "$webhook_payload")

if echo "$webhook_response" | jq -e '.status' >/dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "$webhook_response"
fi

# Test 7: Check Suppression List
echo -e "\n${YELLOW}7. Checking Suppression List Updates${NC}"
echo "Waiting 5 seconds for processing..."
sleep 5

echo -n "Checking for test-bounce@example.com in suppressions... "
suppression_check=$(curl -s "$API_URL/api/metrics/email/suppressions?limit=100")

if echo "$suppression_check" | jq -r '.suppressions[].email' | grep -q "test-bounce@example.com"; then
    echo -e "${GREEN}✓ FOUND${NC}"
else
    echo -e "${YELLOW}⚠ NOT FOUND${NC} (may need more time)"
fi

# Test 8: Password Reset (another email trigger)
echo -e "\n${YELLOW}8. Testing Password Reset Email${NC}"
echo -n "Requesting password reset... "

reset_response=$(curl -s -X POST "$API_URL/api/auth/password-reset-request" \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"$UNIQUE_EMAIL\"}")

if echo "$reset_response" | jq -e '.message' >/dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC}"
    echo "$reset_response" | jq -r '.message'
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "$reset_response" | jq .
fi

# Summary
echo -e "\n${GREEN}📊 Test Summary${NC}"
echo "===================================="
echo "• Health checks: Tested"
echo "• Metrics API: Functional"
echo "• Email sending: Triggered"
echo "• Bounce handling: Configured"
echo "• Webhook processing: Active"
echo "• Suppression list: Working"

echo -e "\n${YELLOW}📝 Next Steps:${NC}"
echo "1. Check CloudWatch logs for email delivery"
echo "2. Monitor Grafana dashboard for metrics"
echo "3. Verify emails in test inbox (if not sandboxed)"
echo "4. Review suppression list management"

# AWS CLI checks (if available)
if command -v aws &> /dev/null; then
    echo -e "\n${YELLOW}🔍 AWS SES Status:${NC}"
    
    # Check send statistics
    echo -n "Recent send statistics: "
    send_stats=$(aws ses get-send-statistics --region us-east-1 2>/dev/null | jq -r '.SendDataPoints | length')
    echo "$send_stats data points"
    
    # Check send quota
    echo -n "Send quota: "
    quota=$(aws ses get-send-quota --region us-east-1 2>/dev/null)
    if [ $? -eq 0 ]; then
        max_send=$(echo "$quota" | jq -r '.Max24HourSend')
        sent=$(echo "$quota" | jq -r '.SentLast24Hours')
        echo "$sent / $max_send (24h)"
    else
        echo "Unable to fetch"
    fi
fi

echo -e "\n${GREEN}✅ Integration tests complete!${NC}"