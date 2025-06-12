#!/bin/bash
#
# Run authentication tests in Docker development environment
#
set -e

echo "🧪 Running auth tests in Docker environment..."

# Build and run auth tests only
docker compose --profile testing run --rm tests python -m pytest tests/test_auth/ -v

echo "✅ Auth tests completed!"