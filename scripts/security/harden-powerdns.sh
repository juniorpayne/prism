#!/bin/bash
# PowerDNS Security Hardening Script
# This script applies security best practices to PowerDNS installation

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root"
   exit 1
fi

log_info "Starting PowerDNS security hardening..."

# 1. System-level security
log_info "Applying system-level security settings..."

# Create dedicated user if not exists
if ! id -u pdns >/dev/null 2>&1; then
    log_info "Creating pdns user..."
    useradd -r -s /bin/false -d /var/lib/powerdns -c "PowerDNS User" pdns
fi

# Set file permissions
log_info "Setting file permissions..."
chown -R pdns:pdns /etc/powerdns || log_warn "Could not change ownership of /etc/powerdns"
chmod 750 /etc/powerdns || log_warn "Could not set permissions on /etc/powerdns"
chmod 640 /etc/powerdns/*.conf || log_warn "Could not set permissions on config files"

# 2. Network security with iptables/nftables
log_info "Configuring firewall rules..."

# Check if iptables is available
if command -v iptables &> /dev/null; then
    # Rate limiting for DNS queries
    iptables -A INPUT -p udp --dport 53 -m recent --set --name DNS --rsource
    iptables -A INPUT -p udp --dport 53 -m recent --update --seconds 1 --hitcount 10 --name DNS --rsource -j DROP
    
    # Allow only from specific networks (adjust as needed)
    iptables -A INPUT -p udp --dport 53 -s 10.0.0.0/8 -j ACCEPT
    iptables -A INPUT -p udp --dport 53 -s 172.16.0.0/12 -j ACCEPT
    iptables -A INPUT -p udp --dport 53 -s 192.168.0.0/16 -j ACCEPT
    iptables -A INPUT -p udp --dport 53 -j DROP
    
    log_info "Firewall rules applied"
else
    log_warn "iptables not found, skipping firewall configuration"
fi

# 3. Configure fail2ban for PowerDNS
log_info "Setting up fail2ban rules..."

if command -v fail2ban-client &> /dev/null; then
    cat > /etc/fail2ban/filter.d/powerdns.conf << 'EOF'
[Definition]
failregex = ^.*Remote <HOST> wants .*$
            ^.*Refused TCP connection from <HOST>$
            ^.*Failed to update .* for <HOST>:.*$
ignoreregex =
EOF

    cat > /etc/fail2ban/jail.d/powerdns.conf << 'EOF'
[powerdns]
enabled = true
port = 53
protocol = udp
filter = powerdns
logpath = /var/log/powerdns/pdns.log
maxretry = 5
findtime = 600
bantime = 3600
EOF

    # Restart fail2ban
    systemctl restart fail2ban || log_warn "Could not restart fail2ban"
    log_info "Fail2ban configuration applied"
else
    log_warn "fail2ban not installed, skipping"
fi

# 4. SELinux/AppArmor configuration (if applicable)
if command -v getenforce &> /dev/null; then
    if [ "$(getenforce)" != "Disabled" ]; then
        log_info "Configuring SELinux contexts..."
        semanage port -a -t dns_port_t -p udp 53 2>/dev/null || true
        semanage port -a -t dns_port_t -p tcp 53 2>/dev/null || true
        restorecon -Rv /etc/powerdns
    fi
fi

# 5. Kernel hardening
log_info "Applying kernel hardening parameters..."

cat >> /etc/sysctl.d/99-powerdns-security.conf << 'EOF'
# DNS Security Hardening
net.ipv4.tcp_syncookies = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.conf.all.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
EOF

sysctl -p /etc/sysctl.d/99-powerdns-security.conf

# 6. Create security audit script
log_info "Creating security audit script..."

cat > /usr/local/bin/powerdns-security-check.sh << 'EOF'
#!/bin/bash
# PowerDNS Security Audit Script

echo "PowerDNS Security Audit Report"
echo "=============================="
echo

# Check if running as non-root
if ps aux | grep -E "[p]dns_server|[p]owerdns" | grep -v root > /dev/null; then
    echo "[PASS] PowerDNS is running as non-root user"
else
    echo "[FAIL] PowerDNS is running as root!"
fi

# Check file permissions
if [ $(stat -c %a /etc/powerdns/pdns.conf 2>/dev/null || echo 777) -le 640 ]; then
    echo "[PASS] Config file permissions are secure"
else
    echo "[FAIL] Config file permissions are too permissive"
fi

# Check for API key
if grep -q "api-key=" /etc/powerdns/pdns.conf && ! grep -q "api-key=$" /etc/powerdns/pdns.conf; then
    echo "[PASS] API key is configured"
else
    echo "[FAIL] API key is not configured or empty"
fi

# Check for query logging (should be disabled in production)
if grep -E "^query-logging=yes|^log-dns-queries=yes" /etc/powerdns/pdns.conf > /dev/null; then
    echo "[WARN] Query logging is enabled (privacy concern)"
else
    echo "[PASS] Query logging is disabled"
fi

# Check for AXFR restrictions
if grep -E "^disable-axfr=yes" /etc/powerdns/pdns.conf > /dev/null; then
    echo "[PASS] AXFR is disabled"
else
    echo "[FAIL] AXFR is not explicitly disabled"
fi

# Check listening addresses
if grep -E "^local-address=0\.0\.0\.0" /etc/powerdns/pdns.conf > /dev/null; then
    echo "[WARN] Listening on all interfaces (consider restricting)"
fi

echo
echo "Audit complete. Address any [FAIL] items immediately."
EOF

chmod +x /usr/local/bin/powerdns-security-check.sh

# 7. Set up log rotation with security in mind
log_info "Configuring secure log rotation..."

cat > /etc/logrotate.d/powerdns << 'EOF'
/var/log/powerdns/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 640 pdns pdns
    sharedscripts
    postrotate
        /usr/bin/pdns_control cycle >/dev/null 2>&1 || true
    endscript
}
EOF

# 8. Create monitoring script
log_info "Creating security monitoring script..."

cat > /usr/local/bin/powerdns-monitor-security.sh << 'EOF'
#!/bin/bash
# Monitor PowerDNS for security events

# Check for suspicious query patterns
tail -n 1000 /var/log/powerdns/pdns.log 2>/dev/null | grep -E "(ANY|AXFR)" | wc -l > /tmp/suspicious_queries.count

# Check for repeated queries from same source
tail -n 1000 /var/log/powerdns/pdns.log 2>/dev/null | awk '{print $NF}' | sort | uniq -c | sort -rn | head -10 > /tmp/top_queriers.log

# Alert if thresholds exceeded
if [ $(cat /tmp/suspicious_queries.count) -gt 100 ]; then
    logger -p daemon.warn "PowerDNS: High number of suspicious queries detected"
fi
EOF

chmod +x /usr/local/bin/powerdns-monitor-security.sh

# Add to cron
echo "*/5 * * * * root /usr/local/bin/powerdns-monitor-security.sh" > /etc/cron.d/powerdns-security

log_info "Security hardening complete!"
log_info "Run /usr/local/bin/powerdns-security-check.sh to verify security settings"

# Run the security check
/usr/local/bin/powerdns-security-check.sh