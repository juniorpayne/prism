#!/bin/bash
#
# Test authentication endpoints in production
#

API_URL="https://prism.thepaynes.ca/api"

echo "🧪 Testing Authentication in Production"
echo "======================================="

# 1. Test health endpoint first
echo -e "\n1️⃣ Testing API Health:"
curl -s "$API_URL/health" | jq .

# 2. Test registration endpoint
echo -e "\n2️⃣ Testing User Registration:"
TIMESTAMP=$(date +%s)
TEST_EMAIL="test${TIMESTAMP}@example.com"
TEST_USER="testuser${TIMESTAMP}"

echo "Registering user: $TEST_USER ($TEST_EMAIL)"
RESPONSE=$(curl -s -X POST "$API_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$TEST_EMAIL\",
    \"username\": \"$TEST_USER\",
    \"password\": \"TestPassword123!\"
  }")

echo "$RESPONSE" | jq .

# 3. Test invalid registration (weak password)
echo -e "\n3️⃣ Testing Invalid Registration (weak password):"
curl -s -X POST "$API_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "invalid@example.com",
    "username": "invaliduser",
    "password": "weak"
  }' | jq .

# 4. Test duplicate registration
echo -e "\n4️⃣ Testing Duplicate Registration:"
curl -s -X POST "$API_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$TEST_EMAIL\",
    \"username\": \"anotheruser\",
    \"password\": \"TestPassword123!\"
  }" | jq .

echo -e "\n✅ Production tests complete!"
echo "Note: Email verification requires checking the email inbox."
echo "The verification link format is: https://prism.thepaynes.ca/verify-email?token=TOKEN"