# EC2 Security Group Configuration

This document describes the required AWS Security Group settings for the Prism DNS Server deployment.

## Required Inbound Rules

The EC2 instance hosting the Prism DNS Server requires the following inbound rules in its security group:

| Type | Protocol | Port Range | Source | Description |
|------|----------|------------|--------|-------------|
| SSH | TCP | 22 | GitHub Actions IP ranges | SSH access for deployment |
| Custom TCP | TCP | 8080 | 0.0.0.0/0 | TCP server for client connections |
| Custom TCP | TCP | 8081 | 0.0.0.0/0 | REST API for health checks |
| Custom TCP | TCP | 8090 | 0.0.0.0/0 | Web interface (nginx) |

## GitHub Actions IP Ranges

For SSH access from GitHub Actions, you should allow the GitHub Actions IP ranges. These can be obtained from:
https://api.github.com/meta

Alternatively, you can temporarily allow SSH from anywhere (0.0.0.0/0) during deployment, but this is less secure.

## AWS Console Configuration

1. Navigate to EC2 Console → Security Groups
2. Find the security group attached to your EC2 instance
3. Edit inbound rules
4. Add the rules from the table above
5. Save the rules

## AWS CLI Configuration

```bash
# Get the security group ID
SECURITY_GROUP_ID=$(aws ec2 describe-instances \
  --instance-ids <your-instance-id> \
  --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' \
  --output text)

# Add the required rules
aws ec2 authorize-security-group-ingress \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 8080 \
  --cidr 0.0.0.0/0 \
  --group-rule-description "Prism TCP server"

aws ec2 authorize-security-group-ingress \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 8081 \
  --cidr 0.0.0.0/0 \
  --group-rule-description "Prism REST API"

aws ec2 authorize-security-group-ingress \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 8090 \
  --cidr 0.0.0.0/0 \
  --group-rule-description "Prism Web Interface"
```

## Terraform Configuration

```hcl
resource "aws_security_group_rule" "prism_tcp_server" {
  type              = "ingress"
  from_port         = 8080
  to_port           = 8080
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.prism.id
  description       = "Prism TCP server for client connections"
}

resource "aws_security_group_rule" "prism_api" {
  type              = "ingress"
  from_port         = 8081
  to_port           = 8081
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.prism.id
  description       = "Prism REST API for health checks"
}

resource "aws_security_group_rule" "prism_web" {
  type              = "ingress"
  from_port         = 8090
  to_port           = 8090
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.prism.id
  description       = "Prism Web Interface"
}
```

## Verification

After configuring the security group, verify the rules:

```bash
# From your local machine or GitHub Actions
nc -zv <ec2-ip> 8080  # Should show "succeeded"
nc -zv <ec2-ip> 8081  # Should show "succeeded"
nc -zv <ec2-ip> 8090  # Should show "succeeded"

# Or using curl
curl -I http://<ec2-ip>:8081/api/health
curl -I http://<ec2-ip>:8090/
```

## Security Considerations

1. **Restrict SSH Access**: Instead of allowing SSH from 0.0.0.0/0, restrict it to:
   - Your office IP ranges
   - GitHub Actions IP ranges
   - Your home IP (if working remotely)

2. **Use Application Load Balancer**: For production, consider using an ALB with:
   - SSL/TLS termination
   - Single port exposure (443)
   - Backend services on private subnets

3. **Network Segmentation**: Place the EC2 instance in a private subnet with:
   - NAT Gateway for outbound internet access
   - Load balancer in public subnet
   - Restrict direct internet access

## Troubleshooting

If the deployment verification fails with connection errors:

1. Check security group rules are applied
2. Verify the EC2 instance is running
3. Check Docker containers are running on the instance
4. Verify no host-based firewall is blocking ports (iptables/ufw)
5. Check VPC network ACLs aren't blocking traffic