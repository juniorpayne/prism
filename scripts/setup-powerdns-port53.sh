#!/bin/bash
# Script to handle port 53 conflicts with systemd-resolved

echo "🔍 Checking current DNS configuration..."

# Check if systemd-resolved is running
if systemctl is-active --quiet systemd-resolved; then
    echo "⚠️  systemd-resolved is running and using port 53"
    
    echo "📝 Creating systemd-resolved configuration to free port 53..."
    
    # Create directory if it doesn't exist
    sudo mkdir -p /etc/systemd/resolved.conf.d/
    
    # Create configuration to disable DNS stub listener
    sudo tee /etc/systemd/resolved.conf.d/99-disable-stub.conf > /dev/null << 'EOF'
[Resolve]
DNSStubListener=no
DNS=8.8.8.8 8.8.4.4
EOF
    
    echo "🔄 Restarting systemd-resolved..."
    sudo systemctl restart systemd-resolved
    
    # Update resolv.conf to use actual DNS servers
    echo "📝 Updating /etc/resolv.conf..."
    sudo rm -f /etc/resolv.conf
    sudo tee /etc/resolv.conf > /dev/null << 'EOF'
# Managed by PowerDNS setup script
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF
    
    # Make it immutable to prevent systemd from overwriting
    sudo chattr +i /etc/resolv.conf
    
    echo "✅ Port 53 should now be available for PowerDNS"
else
    echo "✅ systemd-resolved is not running, port 53 should be available"
fi

# Verify port 53 is free
echo -e "\n🔍 Checking if port 53 is now free..."
if sudo netstat -tulnp | grep -q ':53 '; then
    echo "⚠️  Warning: Something is still using port 53:"
    sudo netstat -tulnp | grep ':53 '
else
    echo "✅ Port 53 is free and ready for PowerDNS"
fi

echo -e "\n📌 Note: After PowerDNS is running, you may want to update /etc/resolv.conf to use 127.0.0.1"
echo "   This will make the local system use PowerDNS for DNS resolution."