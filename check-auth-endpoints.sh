#!/bin/bash
#
# Check authentication endpoints status
#

echo "🔍 Checking Authentication Endpoints"
echo "===================================="

# Check if auth routes are available
echo -e "\n1️⃣ Checking API root:"
curl -s https://prism.thepaynes.ca/api/ | jq .

# Check OpenAPI docs to see if auth endpoints are registered
echo -e "\n2️⃣ Checking if auth endpoints are in OpenAPI:"
curl -s https://prism.thepaynes.ca/api/openapi.json | jq '.paths | keys[] | select(. | contains("auth"))'

# Try a simple GET request to auth (should return 404 or method not allowed)
echo -e "\n3️⃣ Testing auth route availability:"
curl -s -I https://prism.thepaynes.ca/api/auth/

# Check metrics endpoint to see if it's accessible
echo -e "\n4️⃣ Checking metrics (may require direct access):"
curl -s http://35.170.180.10:8081/metrics | grep -E "prism_|python_info" | head -10

echo -e "\n💡 Possible issues:"
echo "- Email service may not be configured with valid SMTP credentials"
echo "- Database migrations may not have run in production"
echo "- Environment variables for email service may be missing"