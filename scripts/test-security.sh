#!/bin/bash

# Security Testing Script for Prism DNS
# This script performs various security checks on the deployment

echo "🔍 Security Testing Script for Prism DNS"
echo "========================================"

# Configuration
DOMAIN="${1:-35.170.180.10}"
USE_HTTPS="${2:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_info() {
    echo -e "[INFO] $1"
}

# Determine protocol
if [ "$USE_HTTPS" = "true" ]; then
    PROTOCOL="https"
    PORT="443"
else
    PROTOCOL="http"
    PORT="80"
fi

BASE_URL="${PROTOCOL}://${DOMAIN}"

echo ""
echo "Testing URL: $BASE_URL"
echo ""

# Test 1: Security Headers
echo "1. Testing Security Headers..."
echo "------------------------------"

check_header() {
    local header="$1"
    local expected="$2"
    local response=$(curl -s -I "$BASE_URL" | grep -i "^$header:" | cut -d' ' -f2- | tr -d '\r\n')
    
    if [ -n "$response" ]; then
        if [ -n "$expected" ] && [[ "$response" == *"$expected"* ]]; then
            print_pass "$header: $response"
        else
            print_pass "$header present: $response"
        fi
    else
        print_fail "$header missing"
    fi
}

check_header "X-Frame-Options" "DENY"
check_header "X-Content-Type-Options" "nosniff"
check_header "X-XSS-Protection" "1; mode=block"
check_header "Strict-Transport-Security" "max-age="
check_header "Content-Security-Policy"
check_header "Referrer-Policy"
check_header "Permissions-Policy"

# Check for server information disclosure
SERVER_HEADER=$(curl -s -I "$BASE_URL" | grep -i "^Server:" | cut -d' ' -f2-)
if [[ "$SERVER_HEADER" == *"nginx"* ]] && [[ "$SERVER_HEADER" == *"/"* ]]; then
    print_fail "Server version exposed: $SERVER_HEADER"
else
    print_pass "Server version not exposed"
fi

echo ""

# Test 2: SSL/TLS Configuration (if HTTPS)
if [ "$USE_HTTPS" = "true" ]; then
    echo "2. Testing SSL/TLS Configuration..."
    echo "-----------------------------------"
    
    # Test SSL certificate
    print_info "Checking SSL certificate..."
    timeout 5 openssl s_client -connect "$DOMAIN:443" -servername "$DOMAIN" < /dev/null 2>/dev/null | grep -q "Verify return code: 0"
    if [ $? -eq 0 ]; then
        print_pass "SSL certificate valid"
    else
        print_fail "SSL certificate validation failed"
    fi
    
    # Test protocol versions
    print_info "Checking SSL/TLS protocols..."
    
    # Test SSLv3 (should fail)
    timeout 5 openssl s_client -connect "$DOMAIN:443" -ssl3 < /dev/null 2>/dev/null | grep -q "CONNECTED"
    if [ $? -eq 0 ]; then
        print_fail "SSLv3 enabled (vulnerable)"
    else
        print_pass "SSLv3 disabled"
    fi
    
    # Test TLS 1.0 (should fail)
    timeout 5 openssl s_client -connect "$DOMAIN:443" -tls1 < /dev/null 2>/dev/null | grep -q "CONNECTED"
    if [ $? -eq 0 ]; then
        print_fail "TLS 1.0 enabled (deprecated)"
    else
        print_pass "TLS 1.0 disabled"
    fi
    
    # Test TLS 1.2 (should pass)
    timeout 5 openssl s_client -connect "$DOMAIN:443" -tls1_2 < /dev/null 2>/dev/null | grep -q "CONNECTED"
    if [ $? -eq 0 ]; then
        print_pass "TLS 1.2 enabled"
    else
        print_warn "TLS 1.2 not available"
    fi
    
    echo ""
fi

# Test 3: Rate Limiting
echo "3. Testing Rate Limiting..."
echo "---------------------------"

print_info "Sending 20 rapid requests..."
RATE_LIMITED=false
for i in {1..20}; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/health")
    if [ "$STATUS" = "429" ] || [ "$STATUS" = "503" ]; then
        RATE_LIMITED=true
        print_pass "Rate limiting active (request $i returned $STATUS)"
        break
    fi
done

if [ "$RATE_LIMITED" = "false" ]; then
    print_warn "Rate limiting might not be configured"
fi

echo ""

# Test 4: Common Vulnerabilities
echo "4. Testing Common Vulnerabilities..."
echo "-----------------------------------"

# Test directory traversal
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/../../../etc/passwd")
if [ "$STATUS" = "400" ] || [ "$STATUS" = "403" ] || [ "$STATUS" = "404" ]; then
    print_pass "Directory traversal blocked"
else
    print_fail "Directory traversal might be possible (status: $STATUS)"
fi

# Test access to .git
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/.git/config")
if [ "$STATUS" = "403" ] || [ "$STATUS" = "404" ]; then
    print_pass ".git directory protected"
else
    print_fail ".git directory accessible (status: $STATUS)"
fi

# Test access to .env
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/.env")
if [ "$STATUS" = "403" ] || [ "$STATUS" = "404" ]; then
    print_pass ".env file protected"
else
    print_fail ".env file might be accessible (status: $STATUS)"
fi

# Test SQL injection (basic)
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/hosts?name=test'%20OR%20'1'='1")
if [ "$STATUS" = "400" ] || [ "$STATUS" = "422" ]; then
    print_pass "Basic SQL injection attempt blocked"
else
    print_warn "SQL injection protection needs verification (status: $STATUS)"
fi

echo ""

# Test 5: Authentication & Authorization
echo "5. Testing Authentication & Authorization..."
echo "-------------------------------------------"

# Test unauthorized API access
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/hosts")
if [ "$STATUS" = "200" ]; then
    print_info "API endpoint accessible without auth (might be intentional)"
elif [ "$STATUS" = "401" ] || [ "$STATUS" = "403" ]; then
    print_pass "API requires authentication"
else
    print_info "API returned status: $STATUS"
fi

echo ""

# Test 6: CORS Configuration
echo "6. Testing CORS Configuration..."
echo "--------------------------------"

# Test CORS headers
CORS_HEADERS=$(curl -s -I -H "Origin: https://evil.com" "$BASE_URL/api/health" | grep -i "access-control-")
if [ -n "$CORS_HEADERS" ]; then
    echo "$CORS_HEADERS" | while read -r line; do
        if [[ "$line" == *"Access-Control-Allow-Origin: *"* ]]; then
            print_warn "CORS allows all origins (*)  - might be too permissive"
        else
            print_info "$line"
        fi
    done
else
    print_pass "No CORS headers present (API not accessible cross-origin)"
fi

echo ""

# Test 7: Container Security
echo "7. Testing Container Security..."
echo "--------------------------------"

if command -v docker &> /dev/null; then
    # Check if containers are running as root
    print_info "Checking container user privileges..."
    
    # This would need to be run on the server
    print_info "Container security checks require server access"
else
    print_info "Docker not available for container security checks"
fi

echo ""

# Summary
echo "========================================"
echo "Security Test Summary"
echo "========================================"
echo ""
echo "✓ Completed security header checks"
if [ "$USE_HTTPS" = "true" ]; then
    echo "✓ Completed SSL/TLS configuration checks"
fi
echo "✓ Completed vulnerability checks"
echo "✓ Completed authentication checks"
echo ""
echo "Recommendations:"
echo "1. Review any [FAIL] items above"
echo "2. Consider implementing rate limiting if not active"
echo "3. Ensure all security headers are properly configured"
if [ "$USE_HTTPS" = "false" ]; then
    echo "4. Implement SSL/TLS for production use"
fi
echo ""
echo "For a comprehensive security scan, consider using:"
echo "- SSL Labs (https://www.ssllabs.com/ssltest/)"
echo "- Security Headers (https://securityheaders.com/)"
echo "- OWASP ZAP or Burp Suite for penetration testing"