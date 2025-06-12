#!/bin/bash
#
# Setup Git hooks for the project
#

echo "Setting up Git hooks..."

# Configure Git to use our hooks directory
git config core.hooksPath .githooks

echo "✅ Git hooks configured!"
echo "The pre-push hook will now remind you to test before pushing to main/master."