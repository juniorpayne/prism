#!/bin/bash
# Test registration

curl -X POST http://localhost:8081/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"demouser","email":"demo@example.com","password":"DemoPassword123!","full_name":"Demo User"}' | jq .