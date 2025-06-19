#!/bin/bash
# SMTP Email Testing Script
# Tests email configuration with optional MailHog for local testing

set -e

echo "🧪 SMTP Email Testing Script"
echo "============================"

# Function to check if MailHog is running
check_mailhog() {
    if docker compose ps | grep -q mailhog; then
        return 0
    else
        return 1
    fi
}

# Function to start MailHog
start_mailhog() {
    echo "📮 Starting MailHog..."
    docker compose --profile development up -d mailhog
    sleep 3
    echo "✅ MailHog started at http://localhost:8025"
}

# Parse command line arguments
USE_MAILHOG=false
VALIDATE_ONLY=false
TO_EMAIL=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --mailhog)
            USE_MAILHOG=true
            shift
            ;;
        --validate-only)
            VALIDATE_ONLY=true
            shift
            ;;
        --to)
            TO_EMAIL="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--mailhog] [--validate-only] [--to email@example.com]"
            exit 1
            ;;
    esac
done

# If using MailHog, ensure it's running
if [ "$USE_MAILHOG" = true ]; then
    if ! check_mailhog; then
        start_mailhog
    else
        echo "✅ MailHog is already running"
    fi
    
    # Configure for MailHog
    export EMAIL_PROVIDER=smtp
    export SMTP_HOST=localhost
    export SMTP_PORT=1025
    export SMTP_USE_TLS=false
    export SMTP_USE_SSL=false
    export EMAIL_FROM_ADDRESS=test@prism.local
    export EMAIL_FROM_NAME="Prism DNS Test"
    
    echo ""
    echo "📧 Using MailHog configuration:"
    echo "   Host: localhost:1025"
    echo "   No authentication required"
    echo ""
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Build the command
CMD="python -m server.commands.test_email"

if [ "$VALIDATE_ONLY" = true ]; then
    CMD="$CMD --validate-only"
fi

if [ -n "$TO_EMAIL" ]; then
    CMD="$CMD --to $TO_EMAIL"
fi

# Run the test
echo "🚀 Running email test..."
echo ""
$CMD

# If using MailHog, show how to view emails
if [ "$USE_MAILHOG" = true ] && [ "$VALIDATE_ONLY" = false ]; then
    echo ""
    echo "🌐 View emails at: http://localhost:8025"
    echo ""
    echo "Press Ctrl+C to stop MailHog"
    
    # Keep script running and cleanup on exit
    trap "echo ''; echo '🛑 Stopping MailHog...'; docker compose --profile development down mailhog" EXIT
    
    # Wait for interrupt
    while true; do
        sleep 1
    done
fi