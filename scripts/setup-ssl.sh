#!/bin/bash
set -e

# SSL/TLS Setup Script for Prism DNS
# This script configures Let's Encrypt SSL certificates for the production deployment

echo "🔐 SSL/TLS Setup Script for Prism DNS"
echo "===================================="

# Configuration
DOMAIN="${1:-prism.thepaynes.ca}"
EMAIL="${2:-admin@thepaynes.ca}"
NGINX_CONFIG="/etc/nginx/sites-available/prism-ssl"
DEPLOYMENT_DIR="/home/ubuntu/prism-deployment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root or with sudo"
   exit 1
fi

# Step 1: Install Certbot and Nginx plugin
print_status "Installing Certbot and dependencies..."
apt-get update
apt-get install -y certbot python3-certbot-nginx

# Step 2: Create strong Diffie-Hellman parameters
print_status "Generating Diffie-Hellman parameters (this may take a few minutes)..."
if [ ! -f /etc/ssl/certs/dhparam.pem ]; then
    openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048
else
    print_warning "Diffie-Hellman parameters already exist, skipping..."
fi

# Step 3: Create Nginx SSL configuration
print_status "Creating Nginx SSL configuration..."

cat > "$NGINX_CONFIG" << 'EOF'
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name DOMAIN_PLACEHOLDER;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS Server
server {
    listen 443 ssl http2;
    server_name DOMAIN_PLACEHOLDER;

    # SSL Certificate (will be updated by Certbot)
    ssl_certificate /etc/letsencrypt/live/DOMAIN_PLACEHOLDER/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/DOMAIN_PLACEHOLDER/privkey.pem;
    
    # Strong SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Diffie-Hellman parameters
    ssl_dhparam /etc/ssl/certs/dhparam.pem;
    
    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self' https:; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; font-src 'self' https://cdn.jsdelivr.net; img-src 'self' data: https:; connect-src 'self'" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
    
    # Remove server version header
    server_tokens off;
    
    # Client body size
    client_max_body_size 10M;
    
    # Proxy to application
    location / {
        proxy_pass http://localhost:80;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # API endpoints
    location /api/ {
        proxy_pass http://localhost:8080/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # API-specific headers
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-Frame-Options "DENY" always;
        
        # CORS headers (adjust origin as needed)
        add_header Access-Control-Allow-Origin "$http_origin" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type, Accept" always;
        add_header Access-Control-Max-Age "3600" always;
        
        if ($request_method = 'OPTIONS') {
            return 204;
        }
    }
    
    # Static files caching
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|woff|woff2|ttf|svg)$ {
        proxy_pass http://localhost:80;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Replace domain placeholder
sed -i "s/DOMAIN_PLACEHOLDER/$DOMAIN/g" "$NGINX_CONFIG"

# Step 4: Test Nginx configuration
print_status "Testing Nginx configuration..."
nginx -t

# Step 5: Enable the site configuration
print_status "Enabling SSL site configuration..."
ln -sf "$NGINX_CONFIG" /etc/nginx/sites-enabled/prism-ssl

# Step 6: Create webroot directory for Certbot
mkdir -p /var/www/certbot

# Step 7: Reload Nginx to apply HTTP configuration
print_status "Reloading Nginx..."
systemctl reload nginx

# Step 8: Obtain SSL certificate
print_status "Obtaining SSL certificate from Let's Encrypt..."
certbot certonly --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d "$DOMAIN"

# Step 9: Update Nginx configuration to use the certificate
print_status "Updating Nginx configuration with SSL certificate..."
systemctl reload nginx

# Step 10: Set up automatic renewal
print_status "Setting up automatic certificate renewal..."
cat > /etc/systemd/system/certbot-renewal.service << 'EOF'
[Unit]
Description=Certbot Renewal
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/certbot renew --quiet --post-hook "systemctl reload nginx"
EOF

cat > /etc/systemd/system/certbot-renewal.timer << 'EOF'
[Unit]
Description=Run Certbot twice daily
After=network.target

[Timer]
OnCalendar=*-*-* 00,12:00:00
RandomizedDelaySec=3600
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable certbot-renewal.timer
systemctl start certbot-renewal.timer

# Step 11: Test SSL configuration
print_status "Testing SSL configuration..."
sleep 5
if curl -sSf "https://$DOMAIN" > /dev/null 2>&1; then
    print_status "SSL configuration successful! Site is accessible via HTTPS."
else
    print_warning "Could not verify HTTPS access. Please check your DNS settings and firewall rules."
fi

# Step 12: Display SSL Labs test URL
echo ""
print_status "SSL/TLS configuration complete!"
echo ""
echo "Next steps:"
echo "1. Test your SSL configuration: https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
echo "2. Verify security headers: https://securityheaders.com/?q=$DOMAIN"
echo "3. Monitor certificate expiration and renewal"
echo ""
echo "Automatic renewal is configured to run twice daily via systemd timer."
echo "You can check renewal status with: systemctl status certbot-renewal.timer"
echo ""
echo "To manually test renewal: certbot renew --dry-run"