#!/bin/bash
# Quick SES setup commands to run locally if you have AWS CLI configured

echo "🚀 Quick SES Setup for prism.thepaynes.ca"
echo "========================================"
echo ""
echo "This script will help you set up SES if you have AWS CLI configured locally."
echo "Otherwise, follow the manual steps in SES_SETUP_GUIDE.md"
echo ""

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &>/dev/null; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    echo "   Or SSH to EC2 and run: ./scripts/setup-ses-production.sh"
    exit 1
fi

echo "✅ AWS CLI is configured"
echo ""

# Run the setup script if it exists
if [ -f "scripts/setup-ses-production.sh" ]; then
    echo "Running SES setup script..."
    ./scripts/setup-ses-production.sh
else
    echo "❌ Setup script not found. Please run from the project root directory."
    exit 1
fi