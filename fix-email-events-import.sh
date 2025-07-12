#!/bin/bash
# Fix the email_events import path issue in production

echo "🔧 Fixing email_events import path in production..."

# Create a patch script to fix the import
cat > fix-imports.sh << 'SCRIPT'
#!/bin/bash
cd /app

# Fix the import in aws_ses.py
if [ -f server/auth/email_providers/aws_ses.py ]; then
    echo "Fixing imports in aws_ses.py..."
    sed -i 's/from server.auth.models.email_events import/from server.auth.email_events import/g' server/auth/email_providers/aws_ses.py
fi

# Fix the import in email_metrics.py
if [ -f server/api/routes/email_metrics.py ]; then
    echo "Fixing imports in email_metrics.py..."
    sed -i 's/from server.auth.models.email_events import/from server.auth.email_events import/g' server/api/routes/email_metrics.py
fi

# Fix the import in ses_webhooks.py
if [ -f server/api/routes/ses_webhooks.py ]; then
    echo "Fixing imports in ses_webhooks.py..."
    sed -i 's/from server.auth.models.email_events import/from server.auth.email_events import/g' server/api/routes/ses_webhooks.py
fi

echo "✅ Import paths fixed"
SCRIPT

# Copy and execute the fix script on production
scp -i citadel.pem fix-imports.sh ubuntu@35.170.180.10:~/
ssh -i citadel.pem ubuntu@35.170.180.10 << 'EOF'
chmod +x ~/fix-imports.sh

# Execute inside the container
cd ~/prism-deployment
docker compose -f docker-compose.production.yml exec -T prism-server /bin/bash < ~/fix-imports.sh

# Restart the container to apply changes
echo "🔄 Restarting container..."
docker compose -f docker-compose.production.yml restart prism-server

# Wait for service to start
sleep 10

# Check status
echo "🔍 Checking container status..."
docker compose -f docker-compose.production.yml ps

# Clean up
rm ~/fix-imports.sh

echo "✅ Import paths fixed and container restarted!"
EOF

# Clean up local script
rm fix-imports.sh

echo "✅ Fix completed!"