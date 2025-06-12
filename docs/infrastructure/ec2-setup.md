# EC2 Instance Setup Guide

## Overview

This guide details the complete setup process for AWS EC2 instances running Prism DNS, including initial configuration, security hardening, and optimization.

## Instance Specifications

### Production Instance
- **Type**: t3.medium (2 vCPU, 4 GB RAM)
- **OS**: Ubuntu 22.04 LTS
- **Storage**: 50 GB GP3 SSD
- **Network**: Single availability zone
- **IP**: Elastic IP attached

### Resource Requirements

| Component | CPU | Memory | Storage | Network |
|-----------|-----|--------|---------|---------|
| Prism Server | 0.5 | 512 MB | 5 GB | Low |
| PostgreSQL | 0.5 | 1 GB | 20 GB | Medium |
| PowerDNS | 0.5 | 512 MB | 5 GB | High |
| Nginx | 0.2 | 256 MB | 1 GB | High |
| Monitoring | 0.3 | 768 MB | 10 GB | Low |

## Initial Setup

### 1. Launch EC2 Instance

```bash
# Using AWS CLI
aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --instance-type t3.medium \
    --key-name prism-key \
    --security-group-ids sg-xxxxxxxxx \
    --subnet-id subnet-xxxxxxxxx \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=prism-dns-prod}]' \
    --user-data file://user-data.sh
```

### 2. User Data Script

```bash
#!/bin/bash
# user-data.sh - Initial instance configuration

# Update system
apt-get update
apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker ubuntu

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install essential tools
apt-get install -y \
    git \
    htop \
    iotop \
    netdata \
    fail2ban \
    ufw \
    certbot \
    python3-certbot-nginx

# Configure firewall
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8080/tcp
ufw allow 8081/tcp
ufw allow 53/udp
ufw allow 53/tcp
ufw --force enable

# Set up swap
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# Configure sysctl
cat >> /etc/sysctl.conf << EOF
# Network optimizations
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30

# Memory optimizations
vm.swappiness = 10
vm.vfs_cache_pressure = 50
EOF

sysctl -p

# Create deployment directory
mkdir -p /home/ubuntu/prism-deployment
chown ubuntu:ubuntu /home/ubuntu/prism-deployment
```

### 3. Security Group Configuration

```terraform
resource "aws_security_group" "prism_dns" {
  name_prefix = "prism-dns-"
  description = "Security group for Prism DNS"
  vpc_id      = var.vpc_id

  # SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.admin_ips
    description = "SSH from admin IPs"
  }

  # HTTP
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP"
  }

  # HTTPS
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS"
  }

  # Prism TCP
  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Prism TCP clients"
  }

  # DNS
  ingress {
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "DNS queries UDP"
  }

  ingress {
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "DNS queries TCP"
  }

  # Monitoring (restricted)
  ingress {
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = var.monitoring_ips
    description = "Prometheus"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "prism-dns-sg"
  }
}
```

## System Configuration

### 1. Create Prism User

```bash
# Create dedicated user
sudo useradd -m -s /bin/bash -G docker prism
sudo passwd prism

# Set up SSH keys
sudo -u prism mkdir -p /home/prism/.ssh
sudo cp ~/.ssh/authorized_keys /home/prism/.ssh/
sudo chown -R prism:prism /home/prism/.ssh
sudo chmod 700 /home/prism/.ssh
sudo chmod 600 /home/prism/.ssh/authorized_keys
```

### 2. Configure Fail2ban

```ini
# /etc/fail2ban/jail.local
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log

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
```

### 3. System Monitoring

```bash
# Install netdata for real-time monitoring
wget -O /tmp/netdata-kickstart.sh https://my-netdata.io/kickstart.sh
sh /tmp/netdata-kickstart.sh --non-interactive

# Configure netdata
cat > /etc/netdata/netdata.conf << EOF
[global]
    run as user = netdata
    web files owner = root
    web files group = root
    bind socket to IP = 127.0.0.1
    default port = 19999
    
[web]
    enable gzip compression = yes
    
[registry]
    enabled = no
EOF

# Restart netdata
systemctl restart netdata
```

### 4. Log Management

```bash
# Configure logrotate
cat > /etc/logrotate.d/prism << EOF
/home/ubuntu/prism-deployment/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 prism prism
    sharedscripts
    postrotate
        docker-compose -f /home/ubuntu/prism-deployment/docker-compose.yml kill -s USR1 nginx
    endscript
}
EOF

# Set up CloudWatch agent (optional)
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
dpkg -i amazon-cloudwatch-agent.deb
```

## Storage Configuration

### 1. EBS Volume Setup

```bash
# List available volumes
lsblk

# Format new volume
sudo mkfs.ext4 /dev/xvdf

# Mount volume
sudo mkdir /data
sudo mount /dev/xvdf /data

# Persistent mount
echo '/dev/xvdf /data ext4 defaults,nofail 0 2' | sudo tee -a /etc/fstab

# Set permissions
sudo chown -R ubuntu:ubuntu /data
```

### 2. Backup Configuration

```bash
# Create backup script
cat > /home/ubuntu/backup.sh << 'EOF'
#!/bin/bash
set -e

BACKUP_DIR="/data/backups"
DATE=$(date +%Y%m%d_%H%M%S)
S3_BUCKET="s3://prism-dns-backups"

# Create backup directory
mkdir -p ${BACKUP_DIR}

# Backup database
docker exec postgres pg_dump -U prism prism | gzip > ${BACKUP_DIR}/prism_${DATE}.sql.gz

# Backup Docker volumes
docker run --rm -v prism_data:/data -v ${BACKUP_DIR}:/backup \
    alpine tar czf /backup/volumes_${DATE}.tar.gz /data

# Backup configuration
tar czf ${BACKUP_DIR}/config_${DATE}.tar.gz /home/ubuntu/prism-deployment

# Upload to S3
aws s3 sync ${BACKUP_DIR} ${S3_BUCKET} --storage-class GLACIER_IR

# Clean up old backups (keep 7 days locally)
find ${BACKUP_DIR} -name "*.gz" -mtime +7 -delete

echo "Backup completed: ${DATE}"
EOF

chmod +x /home/ubuntu/backup.sh

# Add to crontab
(crontab -l 2>/dev/null; echo "0 2 * * * /home/ubuntu/backup.sh >> /var/log/backup.log 2>&1") | crontab -
```

## Performance Optimization

### 1. Kernel Tuning

```bash
# /etc/sysctl.d/99-prism.conf
# Network performance
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_congestion_control = bbr
net.core.default_qdisc = fq

# Connection tracking
net.netfilter.nf_conntrack_max = 131072
net.netfilter.nf_conntrack_tcp_timeout_established = 86400

# File descriptors
fs.file-max = 2097152
fs.nr_open = 1048576

# Apply settings
sudo sysctl -p /etc/sysctl.d/99-prism.conf
```

### 2. Docker Optimization

```json
# /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "5"
  },
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.override_kernel_check=true"
  ],
  "metrics-addr": "127.0.0.1:9323",
  "experimental": true,
  "features": {
    "buildkit": true
  },
  "default-ulimits": {
    "nofile": {
      "Hard": 64000,
      "Name": "nofile",
      "Soft": 64000
    }
  }
}
```

## Monitoring Setup

### 1. CloudWatch Integration

```bash
# Install CloudWatch agent config
cat > /opt/aws/amazon-cloudwatch-agent/etc/config.json << EOF
{
  "metrics": {
    "namespace": "PrismDNS",
    "metrics_collected": {
      "cpu": {
        "measurement": [
          "cpu_usage_idle",
          "cpu_usage_iowait",
          "cpu_usage_user",
          "cpu_usage_system"
        ],
        "metrics_collection_interval": 60
      },
      "disk": {
        "measurement": [
          "used_percent",
          "inodes_free"
        ],
        "metrics_collection_interval": 60,
        "resources": [
          "*"
        ]
      },
      "mem": {
        "measurement": [
          "mem_used_percent"
        ],
        "metrics_collection_interval": 60
      },
      "swap": {
        "measurement": [
          "swap_used_percent"
        ],
        "metrics_collection_interval": 60
      }
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/syslog",
            "log_group_name": "/aws/ec2/prism/syslog",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/home/ubuntu/prism-deployment/logs/*.log",
            "log_group_name": "/aws/ec2/prism/app",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
EOF

# Start CloudWatch agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json
```

### 2. Health Check Script

```bash
#!/bin/bash
# /home/ubuntu/health-check.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🏥 Prism DNS Health Check"
echo "========================="

# Check disk space
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo -e "${RED}❌ Disk usage critical: ${DISK_USAGE}%${NC}"
else
    echo -e "${GREEN}✅ Disk usage OK: ${DISK_USAGE}%${NC}"
fi

# Check memory
MEM_USAGE=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
if [ $MEM_USAGE -gt 80 ]; then
    echo -e "${RED}❌ Memory usage high: ${MEM_USAGE}%${NC}"
else
    echo -e "${GREEN}✅ Memory usage OK: ${MEM_USAGE}%${NC}"
fi

# Check Docker services
cd /home/ubuntu/prism-deployment
SERVICES=$(docker-compose ps --services)
for service in $SERVICES; do
    if docker-compose ps $service | grep -q "Up"; then
        echo -e "${GREEN}✅ $service is running${NC}"
    else
        echo -e "${RED}❌ $service is down${NC}"
    fi
done

# Check API endpoint
if curl -s -f https://prism.thepaynes.ca/api/health > /dev/null; then
    echo -e "${GREEN}✅ API is responsive${NC}"
else
    echo -e "${RED}❌ API is not responding${NC}"
fi

# Check DNS
if dig @localhost -p 53 test.managed.prism.local +short > /dev/null 2>&1; then
    echo -e "${GREEN}✅ DNS is resolving${NC}"
else
    echo -e "${YELLOW}⚠️  DNS resolution issue${NC}"
fi
```

## Disaster Recovery

### 1. AMI Creation

```bash
# Create AMI via AWS CLI
aws ec2 create-image \
    --instance-id i-xxxxxxxxx \
    --name "prism-dns-$(date +%Y%m%d)" \
    --description "Prism DNS backup AMI" \
    --no-reboot

# Automate with Lambda
cat > create-ami-lambda.py << 'EOF'
import boto3
import datetime

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    
    # Get instance ID from tag
    instances = ec2.describe_instances(
        Filters=[
            {'Name': 'tag:Name', 'Values': ['prism-dns-prod']},
            {'Name': 'instance-state-name', 'Values': ['running']}
        ]
    )
    
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            
            # Create AMI
            response = ec2.create_image(
                InstanceId=instance_id,
                Name=f"prism-dns-auto-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}",
                Description='Automated backup AMI',
                NoReboot=True
            )
            
            # Tag AMI
            ec2.create_tags(
                Resources=[response['ImageId']],
                Tags=[
                    {'Key': 'AutoBackup', 'Value': 'true'},
                    {'Key': 'InstanceId', 'Value': instance_id}
                ]
            )
            
    # Clean up old AMIs (keep last 7)
    # ... cleanup code ...
    
    return {'statusCode': 200, 'body': 'AMI created successfully'}
EOF
```

### 2. Recovery Procedures

```bash
# Quick recovery from AMI
aws ec2 run-instances \
    --image-id ami-xxxxxxxxx \
    --instance-type t3.medium \
    --key-name prism-key \
    --security-group-ids sg-xxxxxxxxx \
    --subnet-id subnet-xxxxxxxxx \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=prism-dns-recovery}]'

# Restore from backup
ssh ubuntu@new-instance-ip
cd /home/ubuntu/prism-deployment
aws s3 cp s3://prism-dns-backups/prism_20240115.sql.gz .
gunzip prism_20240115.sql.gz
docker exec -i postgres psql -U prism prism < prism_20240115.sql
```

## Maintenance Tasks

### Weekly Maintenance

```bash
#!/bin/bash
# weekly-maintenance.sh

echo "Starting weekly maintenance..."

# Update packages
sudo apt update
sudo apt upgrade -y

# Clean Docker
docker system prune -af --volumes
docker image prune -af

# Rotate logs
sudo logrotate -f /etc/logrotate.d/prism

# Check and repair permissions
sudo chown -R ubuntu:ubuntu /home/ubuntu/prism-deployment
sudo chmod -R 755 /home/ubuntu/prism-deployment

# Vacuum database
docker exec postgres vacuumdb -U prism -d prism -z

echo "Weekly maintenance completed"
```

### Security Updates

```bash
# Check for security updates
sudo unattended-upgrade --dry-run

# Apply security updates only
sudo unattended-upgrade

# Update Docker images
cd /home/ubuntu/prism-deployment
docker-compose pull
docker-compose up -d
```

---

*Remember: Always test changes in a development environment first!*