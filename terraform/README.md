# Terraform Infrastructure for Prism DNS

This directory contains Terraform configurations for deploying PowerDNS infrastructure on AWS.

## Directory Structure

```
terraform/
├── modules/
│   └── powerdns/          # PowerDNS infrastructure module
├── environments/
│   ├── dev/               # Development environment
│   ├── staging/           # Staging environment
│   └── production/        # Production environment
└── README.md              # This file
```

## Prerequisites

1. **Terraform**: Version 1.0 or higher
   ```bash
   brew install terraform  # macOS
   # or download from https://www.terraform.io/downloads
   ```

2. **AWS CLI**: Configured with appropriate credentials
   ```bash
   aws configure
   ```

3. **Required AWS Permissions**: Your AWS IAM user/role needs permissions to:
   - Create/modify security groups
   - Create/modify S3 buckets
   - Create/modify IAM roles and policies
   - Create/modify CloudWatch resources
   - Create/modify SNS topics
   - Describe EC2 instances and VPCs

## Quick Start

### 1. Development Environment

```bash
cd environments/dev

# Initialize Terraform
terraform init

# Create terraform.tfvars with your instance ID
echo 'ec2_instance_id = "i-XXXXXXXXXXXXXXXXX"' > terraform.tfvars

# Review the plan
terraform plan

# Apply the configuration
terraform apply
```

### 2. Production Environment

```bash
cd environments/production

# Initialize Terraform
terraform init

# Copy and edit the example variables file
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Review the plan
terraform plan

# Apply the configuration
terraform apply
```

## What Gets Created

The PowerDNS module creates the following AWS resources:

1. **Security Group**: Opens ports 53 (DNS) and 8053 (API)
2. **S3 Bucket**: For DNS zone backups (optional)
3. **IAM Role & Policy**: For EC2 to access S3 backups
4. **CloudWatch Log Group**: For PowerDNS logs
5. **SNS Topic**: For alerts
6. **CloudWatch Alarms**: For monitoring

## Port Configuration

| Service | Port | Protocol | Description |
|---------|------|----------|-------------|
| DNS | 53 | UDP/TCP | DNS queries |
| API | 8053 | TCP | PowerDNS REST API |

**Note**: PowerDNS API uses port 8053 instead of the default 8081 to avoid conflicts with the Prism API.

## Environment Differences

### Development
- API access open to all (0.0.0.0/0)
- No S3 backups
- Short log retention (3 days)
- Minimal tags

### Production
- API access restricted to specific CIDRs
- S3 backups enabled with 30-day retention
- Longer log retention (30 days)
- Comprehensive tagging for cost tracking

## Common Operations

### View Current State
```bash
terraform show
```

### Update Infrastructure
```bash
terraform plan
terraform apply
```

### Destroy Infrastructure
```bash
terraform destroy
```

### Import Existing Resources
```bash
# Import an existing security group
terraform import module.powerdns.aws_security_group.powerdns sg-XXXXXXXXX
```

## Troubleshooting

### "Instance not found" Error
Make sure the `ec2_instance_id` in your `terraform.tfvars` is correct:
```bash
aws ec2 describe-instances --query 'Reservations[*].Instances[*].[InstanceId,State.Name,Tags[?Key==`Name`].Value]' --output table
```

### "VPC not found" Error
For production, ensure your VPC is tagged appropriately. The module looks for VPCs tagged with "production" or "main".

### Permission Errors
Ensure your AWS credentials have the necessary permissions. You can test with:
```bash
aws sts get-caller-identity
```

## Security Best Practices

1. **Restrict API Access**: Always limit `api_allowed_cidrs` to known IP ranges
2. **Enable Backups**: Use S3 backups in production
3. **Monitor Alerts**: Subscribe to the SNS topic for notifications
4. **Review Security Groups**: Regularly audit security group rules
5. **Use Remote State**: For team environments, use S3 backend for state

## Cost Estimates

Approximate monthly costs (us-east-1):
- Security Group: Free
- S3 Backup Storage: ~$0.023/GB
- CloudWatch Logs: ~$0.50/GB ingested
- SNS: ~$0.50/million notifications

## Next Steps

After applying the Terraform configuration:

1. Deploy PowerDNS containers using docker-compose
2. Configure PowerDNS zones and records
3. Set up monitoring dashboards
4. Subscribe to SNS alerts
5. Test DNS resolution

## Support

For issues or questions:
1. Check the module README in `modules/powerdns/`
2. Review AWS CloudWatch logs
3. Check Terraform state with `terraform show`