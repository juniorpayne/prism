#!/bin/bash
# Hotfix script to fix the import issue in production

echo "Building hotfix image..."

# Create a temporary Dockerfile that fixes the import issue
cat > Dockerfile.hotfix << 'EOF'
FROM prism-server:latest

# Fix the models/__init__.py file
RUN echo '"""Auth models package - for email event models only."""' > /app/server/auth/models/__init__.py && \
    echo '' >> /app/server/auth/models/__init__.py && \
    echo '# This directory contains additional model modules like email_events' >> /app/server/auth/models/__init__.py && \
    echo '# The main auth models are in server/auth/models.py' >> /app/server/auth/models/__init__.py && \
    echo 'from .email_events import *' >> /app/server/auth/models/__init__.py

CMD ["python", "-m", "server.main"]
EOF

# Build the hotfix image
docker build -f Dockerfile.hotfix -t prism-server:hotfix .

# Save it
docker save prism-server:hotfix | gzip > prism-server-hotfix.tar.gz

echo "Hotfix image built and saved to prism-server-hotfix.tar.gz"
echo "Transfer and load with:"
echo "scp -i citadel.pem prism-server-hotfix.tar.gz ubuntu@35.170.180.10:~/"
echo "ssh -i citadel.pem ubuntu@35.170.180.10 'docker load < prism-server-hotfix.tar.gz'"