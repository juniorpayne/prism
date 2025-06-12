# Hands-On Workshop: Prism DNS Deployment

## Workshop Overview

**Duration**: 2 hours  
**Skill Level**: Intermediate  
**Prerequisites**: Basic Docker and Linux knowledge

### Learning Objectives

By the end of this workshop, you will be able to:
- Deploy Prism DNS to AWS EC2
- Configure monitoring and alerting
- Perform basic operational tasks
- Troubleshoot common issues

## Workshop Agenda

1. **Introduction** (15 min)
2. **Environment Setup** (30 min)
3. **Deployment Exercise** (45 min)
4. **Monitoring Setup** (20 min)
5. **Troubleshooting Practice** (30 min)
6. **Q&A and Wrap-up** (10 min)

## Part 1: Introduction

### System Architecture Review

```mermaid
graph LR
    A[GitHub] -->|Push| B[GitHub Actions]
    B -->|Deploy| C[EC2 Instance]
    C --> D[Docker Containers]
    D --> E[Prism Server]
    D --> F[PostgreSQL]
    D --> G[PowerDNS]
    D --> H[Nginx]
```

### Key Components
- **Prism Server**: Main application handling registrations
- **PostgreSQL**: Data persistence
- **PowerDNS**: DNS record management
- **Nginx**: Reverse proxy and SSL termination

## Part 2: Environment Setup

### 2.1 AWS Account Setup

```bash
# Configure AWS CLI
aws configure
AWS Access Key ID: <your-key>
AWS Secret Access Key: <your-secret>
Default region: us-east-1
Default output format: json

# Verify access
aws sts get-caller-identity
```

### 2.2 Create EC2 Instance

```bash
# Create key pair
aws ec2 create-key-pair \
    --key-name prism-workshop \
    --query 'KeyMaterial' \
    --output text > prism-workshop.pem

chmod 400 prism-workshop.pem

# Launch instance
aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --instance-type t3.medium \
    --key-name prism-workshop \
    --subnet-id <your-subnet> \
    --security-group-ids <your-sg> \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=prism-workshop}]'
```

### 2.3 Security Group Configuration

```bash
# Create security group
aws ec2 create-security-group \
    --group-name prism-workshop-sg \
    --description "Security group for Prism workshop"

# Add rules
# SSH
aws ec2 authorize-security-group-ingress \
    --group-name prism-workshop-sg \
    --protocol tcp --port 22 --cidr 0.0.0.0/0

# HTTP/HTTPS
aws ec2 authorize-security-group-ingress \
    --group-name prism-workshop-sg \
    --protocol tcp --port 80 --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
    --group-name prism-workshop-sg \
    --protocol tcp --port 443 --cidr 0.0.0.0/0

# Prism TCP
aws ec2 authorize-security-group-ingress \
    --group-name prism-workshop-sg \
    --protocol tcp --port 8080 --cidr 0.0.0.0/0

# DNS
aws ec2 authorize-security-group-ingress \
    --group-name prism-workshop-sg \
    --protocol udp --port 53 --cidr 0.0.0.0/0
```

## Part 3: Deployment Exercise

### 3.1 Connect to Instance

```bash
# Get instance IP
INSTANCE_IP=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=prism-workshop" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

# SSH to instance
ssh -i prism-workshop.pem ubuntu@$INSTANCE_IP
```

### 3.2 Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login for group changes
exit
ssh -i prism-workshop.pem ubuntu@$INSTANCE_IP
```

### 3.3 Deploy Application

```bash
# Clone repository
git clone https://github.com/yourorg/prism-dns.git
cd prism-dns

# Create environment file
cat > .env << EOF
POSTGRES_PASSWORD=$(openssl rand -base64 32)
PRISM_SECRET_KEY=$(openssl rand -base64 32)
PDNS_API_KEY=$(openssl rand -base64 32)
EOF

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

### 3.4 Verify Deployment

```bash
# Check API health
curl http://localhost:8081/api/health

# Test client connection
docker run --rm --network host \
    ghcr.io/yourorg/prism-client:latest \
    -h localhost -p 8080 register test-host

# Check DNS
dig @localhost -p 53 test-host.managed.prism.local
```

## Part 4: Monitoring Setup

### 4.1 Deploy Monitoring Stack

```bash
# Deploy Prometheus and Grafana
docker-compose -f docker-compose.monitoring.yml up -d

# Check monitoring services
docker-compose -f docker-compose.monitoring.yml ps
```

### 4.2 Configure Grafana

1. Access Grafana at `http://<instance-ip>:3000`
2. Login with admin/admin
3. Add Prometheus data source:
   - URL: `http://prometheus:9090`
   - Access: Server (default)

### 4.3 Import Dashboard

```bash
# Import pre-built dashboard
curl -X POST http://admin:admin@localhost:3000/api/dashboards/import \
    -H "Content-Type: application/json" \
    -d @monitoring/dashboards/prism-overview.json
```

### 4.4 Set Up Alerts

```yaml
# Create alert for high error rate
cat > alerts.yml << EOF
groups:
  - name: workshop
    rules:
      - alert: HighErrorRate
        expr: rate(prism_errors_total[5m]) > 0.1
        annotations:
          summary: "High error rate detected"
EOF

docker cp alerts.yml prometheus:/etc/prometheus/alerts.yml
docker restart prometheus
```

## Part 5: Troubleshooting Practice

### 5.1 Scenario 1: Service Won't Start

```bash
# Break something
docker-compose stop prism-server
docker-compose rm -f prism-server

# Now troubleshoot:
# 1. Check service status
docker-compose ps

# 2. Check logs
docker-compose logs prism-server

# 3. Fix issue
docker-compose up -d prism-server
```

### 5.2 Scenario 2: Database Connection Issues

```bash
# Simulate database issue
docker-compose exec postgres psql -U prism -c "ALTER USER prism WITH PASSWORD 'wrong';"

# Observe error
docker-compose logs -f prism-server

# Fix issue
docker-compose exec postgres psql -U postgres -c "ALTER USER prism WITH PASSWORD 'correct-password';"
docker-compose restart prism-server
```

### 5.3 Scenario 3: High Load

```bash
# Generate load
for i in {1..1000}; do
    curl -X POST http://localhost:8081/api/hosts \
        -H "Content-Type: application/json" \
        -d "{\"hostname\": \"load-test-$i\"}" &
done

# Monitor impact
docker stats

# Check metrics
curl http://localhost:8081/metrics | grep prism_

# Implement rate limiting (discussed in workshop)
```

## Workshop Exercises

### Exercise 1: SSL Setup

Configure HTTPS for the deployment:

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate (replace with your domain)
sudo certbot certonly --standalone \
    -d workshop.yourdomain.com \
    --agree-tos \
    --email your-email@example.com

# Update nginx configuration
# Edit nginx/nginx.conf to include SSL
```

### Exercise 2: Backup Implementation

Create a backup script:

```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/backups/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup database
docker exec postgres pg_dump -U prism prism | gzip > $BACKUP_DIR/database.sql.gz

# Backup configurations
tar -czf $BACKUP_DIR/configs.tar.gz .env docker-compose.yml

echo "Backup completed to $BACKUP_DIR"
```

### Exercise 3: Monitoring Alert

Create a custom alert:

```yaml
# Add to Prometheus alerts
- alert: DiskSpaceLow
  expr: node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} < 0.1
  for: 5m
  annotations:
    summary: "Low disk space on {{ $labels.instance }}"
```

## Best Practices Review

### Deployment Checklist
- [ ] Environment variables secured
- [ ] Firewall configured
- [ ] Backups scheduled
- [ ] Monitoring enabled
- [ ] SSL certificates installed
- [ ] Health checks verified

### Security Checklist
- [ ] SSH key authentication only
- [ ] Fail2ban configured
- [ ] Secrets rotated
- [ ] Ports restricted
- [ ] Updates scheduled

### Operational Checklist
- [ ] Logging configured
- [ ] Alerts set up
- [ ] Runbooks available
- [ ] Contact list updated
- [ ] Backup tested

## Common Issues and Solutions

### Issue 1: Container Fails to Start

```bash
# Check logs
docker-compose logs <service>

# Common causes:
# - Port already in use
# - Missing environment variables
# - Incorrect permissions

# Debug interactively
docker run -it --entrypoint /bin/bash <image>
```

### Issue 2: Network Connectivity

```bash
# Test internal networking
docker exec prism-server ping postgres

# Check network configuration
docker network ls
docker network inspect prism-dns_default

# Restart Docker networking
sudo systemctl restart docker
```

### Issue 3: Performance Issues

```bash
# Check resource usage
docker stats
htop

# Analyze slow queries
docker exec postgres psql -U prism -c "
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC LIMIT 10;"

# Scale services
docker-compose up -d --scale prism-server=2
```

## Additional Resources

### Documentation
- [Deployment Guide](../operations/deployment.md)
- [Monitoring Guide](../operations/monitoring.md)
- [Troubleshooting Guide](../operations/troubleshooting.md)

### Tools
- **k9s**: Kubernetes CLI dashboard
- **lazydocker**: Terminal UI for Docker
- **ctop**: Container metrics viewer

### Community
- Slack: #prism-dns-help
- Forum: community.prism-dns.org
- Office Hours: Wednesdays 2-3pm EST

## Workshop Evaluation

Please provide feedback:
1. What was most helpful?
2. What needs more clarification?
3. Suggested improvements?
4. Additional topics to cover?

## Next Steps

1. **Practice**: Deploy in your test environment
2. **Explore**: Try different configurations
3. **Share**: Document your learnings
4. **Contribute**: Submit improvements

---

*Thank you for participating! Remember: practice makes perfect.*