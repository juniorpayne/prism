#!/bin/bash

echo "🔐 GitHub Secret Setup Script"
echo "============================"
echo ""

# Check if GitHub CLI is installed
if command -v gh &> /dev/null; then
    echo "✅ GitHub CLI detected"
    echo ""
    echo "Setting up EC2_SSH_KEY secret using GitHub CLI..."
    
    # Check if authenticated
    if gh auth status &> /dev/null; then
        # Set the secret
        if gh secret set EC2_SSH_KEY < citadel.pem; then
            echo "✅ Secret EC2_SSH_KEY has been successfully added to GitHub!"
            echo ""
            echo "You can now trigger the deployment workflow."
        else
            echo "❌ Failed to set secret. Please check your permissions."
        fi
    else
        echo "❌ GitHub CLI is not authenticated."
        echo "Run: gh auth login"
    fi
else
    echo "⚠️  GitHub CLI not found. Please install it or add the secret manually."
    echo ""
    echo "Option 1: Install GitHub CLI"
    echo "------------------------"
    echo "Visit: https://cli.github.com/"
    echo ""
    echo "Option 2: Manual Setup"
    echo "---------------------"
    echo "1. Go to: https://github.com/juniorpayne/prism/settings/secrets/actions"
    echo "2. Click 'New repository secret'"
    echo "3. Name: EC2_SSH_KEY"
    echo "4. Value: Copy and paste the content below (including BEGIN and END lines):"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    cat citadel.pem
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "5. Click 'Add secret'"
    echo ""
    echo "⚠️  IMPORTANT: Make sure to copy everything between the lines above,"
    echo "   including the -----BEGIN RSA PRIVATE KEY----- and -----END RSA PRIVATE KEY----- lines!"
fi

echo ""
echo "📝 Additional Secrets (Optional)"
echo "================================"
echo ""
echo "For alternative deployment methods, you may also want to set:"
echo ""
echo "1. DOCKERHUB_USERNAME - Your Docker Hub username"
echo "2. DOCKERHUB_TOKEN - Your Docker Hub access token"
echo "3. DEPLOYMENT_WEBHOOK_URL - Webhook URL for automated deployments"
echo "4. DEPLOYMENT_WEBHOOK_SECRET - Secret for webhook authentication"
echo ""
echo "These enable other deployment workflows if SSH continues to have issues."