#!/bin/bash
#
# Run tests in Docker development environment
#
set -e

echo "🧪 Running tests in Docker environment..."

# Build the test container
docker compose build tests

# Run tests using the test profile
docker compose --profile testing run --rm tests

echo "✅ Tests completed!"

# Show coverage report location
echo "📊 Coverage report available in ./htmlcov/"