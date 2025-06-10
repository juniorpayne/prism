#!/bin/bash
set -e

# System Hardening Script for Prism DNS
# This script implements security best practices for the Ubuntu server

echo "🔒 System Hardening Script for Prism DNS"
echo "========================================"

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

# Create backup directory for original configs
BACKUP_DIR="/root/security-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
print_status "Created backup directory: $BACKUP_DIR"

# Step 1: Update system packages
print_status "Updating system packages..."
apt-get update
apt-get upgrade -y
apt-get dist-upgrade -y
apt-get autoremove -y

# Step 2: Install security tools
print_status "Installing security tools..."
apt-get install -y \
    ufw \
    fail2ban \
    unattended-upgrades \
    aide \
    rkhunter \
    logwatch \
    auditd \
    libpam-pwquality \
    apt-listchanges

# Step 3: Configure SSH hardening
print_status "Hardening SSH configuration..."
cp /etc/ssh/sshd_config "$BACKUP_DIR/sshd_config.backup"

cat > /etc/ssh/sshd_config.d/99-hardening.conf << 'EOF'
# SSH Hardening Configuration
Port 22
Protocol 2
HostKey /etc/ssh/ssh_host_rsa_key
HostKey /etc/ssh/ssh_host_ecdsa_key
HostKey /etc/ssh/ssh_host_ed25519_key

# Authentication
PermitRootLogin no
PubkeyAuthentication yes
PasswordAuthentication no
ChallengeResponseAuthentication no
UsePAM yes
MaxAuthTries 3
MaxSessions 10

# Security
PermitEmptyPasswords no
X11Forwarding no
IgnoreRhosts yes
HostbasedAuthentication no
PermitUserEnvironment no
StrictModes yes

# Login restrictions
LoginGraceTime 60
ClientAliveInterval 300
ClientAliveCountMax 2
AllowUsers ubuntu

# Logging
SyslogFacility AUTH
LogLevel INFO

# Ciphers and MACs
Ciphers chacha20-poly1305@openssh.com,aes128-ctr,aes192-ctr,aes256-ctr,aes128-gcm@openssh.com,aes256-gcm@openssh.com
MACs hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com,umac-128-etm@openssh.com,hmac-sha2-256,hmac-sha2-512,umac-128@openssh.com
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group-exchange-sha256
EOF

# Step 4: Configure fail2ban
print_status "Configuring fail2ban..."
cp /etc/fail2ban/jail.conf "$BACKUP_DIR/jail.conf.backup"

cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
destemail = admin@example.com
action = %(action_mwl)s

[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 7200

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log

[nginx-noscript]
enabled = true
port = http,https
filter = nginx-noscript
logpath = /var/log/nginx/access.log
maxretry = 6

[nginx-badbots]
enabled = true
port = http,https
filter = nginx-badbots
logpath = /var/log/nginx/access.log
maxretry = 2

[nginx-noproxy]
enabled = true
port = http,https
filter = nginx-noproxy
logpath = /var/log/nginx/access.log
maxretry = 2
EOF

# Step 5: Configure UFW firewall
print_status "Configuring UFW firewall..."
ufw --force disable
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (rate limited)
ufw limit 22/tcp comment 'SSH rate limited'

# Allow HTTP and HTTPS
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

# Allow DNS TCP server (rate limited)
ufw limit 8081/tcp comment 'DNS TCP Server'

# Enable UFW
ufw --force enable

# Step 6: Configure automatic security updates
print_status "Configuring automatic security updates..."
cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}";
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
    "${distro_id}ESM:${distro_codename}-infra-security";
};
Unattended-Upgrade::DevRelease "false";
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::InstallOnShutdown "false";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Automatic-Reboot-WithUsers "false";
Unattended-Upgrade::Automatic-Reboot-Time "02:00";
EOF

cat > /etc/apt/apt.conf.d/20auto-upgrades << 'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
APT::Periodic::Unattended-Upgrade "1";
EOF

# Step 7: Configure kernel parameters
print_status "Hardening kernel parameters..."
cp /etc/sysctl.conf "$BACKUP_DIR/sysctl.conf.backup"

cat >> /etc/sysctl.d/99-security.conf << 'EOF'
# IP Spoofing protection
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Ignore ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0

# Ignore send redirects
net.ipv4.conf.all.send_redirects = 0

# Disable source packet routing
net.ipv4.conf.all.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0

# Log Martians
net.ipv4.conf.all.log_martians = 1

# Ignore ICMP ping requests
net.ipv4.icmp_echo_ignore_broadcasts = 1

# Ignore Directed pings
net.ipv4.icmp_ignore_bogus_error_responses = 1

# Enable syn cookies
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_synack_retries = 2
net.ipv4.tcp_syn_retries = 5

# Disable IPv6 if not needed
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
net.ipv6.conf.lo.disable_ipv6 = 1

# Controls the use of TCP syncookies
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048

# Increase system file descriptor limit
fs.file-max = 65535

# Restrict core dumps
kernel.core_uses_pid = 1
fs.suid_dumpable = 0

# Restrict access to kernel logs
kernel.dmesg_restrict = 1

# Restrict ptrace scope
kernel.yama.ptrace_scope = 1
EOF

sysctl -p /etc/sysctl.d/99-security.conf

# Step 8: Set up file integrity monitoring
print_status "Setting up file integrity monitoring..."
aideinit
cp /var/lib/aide/aide.db.new /var/lib/aide/aide.db

# Step 9: Configure audit rules
print_status "Configuring audit rules..."
cat > /etc/audit/rules.d/prism-audit.rules << 'EOF'
# Delete all rules
-D

# Buffer Size
-b 8192

# Failure Mode
-f 1

# Monitor authentication
-w /etc/passwd -p wa -k passwd_changes
-w /etc/group -p wa -k group_changes
-w /etc/shadow -p wa -k shadow_changes
-w /etc/sudoers -p wa -k sudoers_changes

# Monitor SSH
-w /etc/ssh/sshd_config -p wa -k sshd_config

# Monitor system calls
-a always,exit -F arch=b64 -S chmod -S fchmod -S fchmodat -F auid>=1000 -F auid!=4294967295 -k perm_mod
-a always,exit -F arch=b64 -S chown -S fchown -S fchownat -S lchown -F auid>=1000 -F auid!=4294967295 -k perm_mod
-a always,exit -F arch=b64 -S setxattr -S lsetxattr -S fsetxattr -S removexattr -S lremovexattr -S fremovexattr -F auid>=1000 -F auid!=4294967295 -k perm_mod

# Monitor Docker
-w /usr/bin/docker -p wa -k docker
-w /var/lib/docker -p wa -k docker
-w /etc/docker -p wa -k docker

# Monitor application
-w /home/ubuntu/prism-deployment -p wa -k prism_app
EOF

service auditd restart

# Step 10: Set up logwatch
print_status "Configuring logwatch..."
cat > /etc/logwatch/conf/logwatch.conf << 'EOF'
LogDir = /var/log
TmpDir = /var/cache/logwatch
Output = mail
Format = html
Encode = none
MailTo = admin@example.com
MailFrom = Logwatch
Range = yesterday
Detail = Med
Service = All
Service = -zz-network
Service = -zz-sys
Service = -eximstats
EOF

# Step 11: Configure password policies
print_status "Configuring password policies..."
cat > /etc/security/pwquality.conf << 'EOF'
# Password quality configuration
minlen = 12
dcredit = -1
ucredit = -1
ocredit = -1
lcredit = -1
maxrepeat = 3
maxsequence = 3
gecoscheck = 1
EOF

# Step 12: Disable unnecessary services
print_status "Disabling unnecessary services..."
systemctl disable --now avahi-daemon 2>/dev/null || true
systemctl disable --now cups 2>/dev/null || true
systemctl disable --now bluetooth 2>/dev/null || true

# Step 13: Set up daily security scan
print_status "Setting up daily security scan..."
cat > /etc/cron.daily/security-scan << 'EOF'
#!/bin/bash
# Daily security scan

# Update rkhunter database
rkhunter --update > /dev/null 2>&1

# Run rkhunter scan
rkhunter --check --skip-keypress --report-warnings-only > /var/log/rkhunter-daily.log 2>&1

# Check for rootkits
if grep -q "Warning" /var/log/rkhunter-daily.log; then
    mail -s "RKHunter Warning on $(hostname)" admin@example.com < /var/log/rkhunter-daily.log
fi

# Run AIDE check
aide --check > /var/log/aide-daily.log 2>&1 || true

# Check for changes
if grep -q "changed" /var/log/aide-daily.log; then
    mail -s "AIDE Changes Detected on $(hostname)" admin@example.com < /var/log/aide-daily.log
fi
EOF

chmod +x /etc/cron.daily/security-scan

# Step 14: Restart services
print_status "Restarting services..."
systemctl restart ssh
systemctl restart fail2ban

# Step 15: Display summary
echo ""
print_status "System hardening complete!"
echo ""
echo "Security measures implemented:"
echo "✓ SSH hardened (key-only auth, rate limiting)"
echo "✓ Firewall configured (UFW with minimal ports)"
echo "✓ Fail2ban active (SSH and nginx protection)"
echo "✓ Automatic security updates enabled"
echo "✓ Kernel parameters hardened"
echo "✓ File integrity monitoring (AIDE)"
echo "✓ Audit logging configured"
echo "✓ Daily security scans scheduled"
echo ""
echo "⚠️  IMPORTANT: Make sure you have SSH key access before disconnecting!"
echo ""
echo "Next steps:"
echo "1. Review firewall rules: ufw status verbose"
echo "2. Check fail2ban status: fail2ban-client status"
echo "3. Update email addresses in configuration files"
echo "4. Test SSH access with your key"
echo "5. Run a security scan: lynis audit system"