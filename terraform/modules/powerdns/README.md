# PowerDNS Terraform Module

This module creates the AWS infrastructure required for running PowerDNS on EC2.

## Features

- Security group configuration for DNS (port 53) and API (port 8053)
- S3 bucket for DNS zone backups with encryption and lifecycle policies
- CloudWatch logs for monitoring and debugging
- SNS topic for alerts
- IAM roles and policies for backup access

## Usage

```hcl
module "powerdns" {
  source = "../../modules/powerdns"
  
  vpc_id              = var.vpc_id
  instance_id         = var.ec2_instance_id
  environment         = "production"
  dns_instance_count  = 1
  
  # API access - restrict to your IP ranges
  api_allowed_cidrs = [
    "10.0.0.0/8",
    "172.16.0.0/12"
  ]
  
  # DNS access - public by default
  dns_allowed_cidrs = ["0.0.0.0/0"]
  
  # Backup configuration
  s3_backup_enabled     = true
  backup_retention_days = 30
  
  # Monitoring
  cloudwatch_logs_retention = 7
  
  tags = {
    Project = "Prism-DNS"
    Owner   = "DevOps"
  }
}
```

## Variables

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| vpc_id | VPC ID where PowerDNS will be deployed | string | - | yes |
| instance_id | EC2 instance ID where PowerDNS will run | string | - | yes |
| environment | Environment name (dev/staging/production) | string | - | yes |
| dns_instance_count | Number of PowerDNS instances | number | 1 | no |
| api_allowed_cidrs | CIDR blocks allowed to access API | list(string) | Private networks | no |
| dns_allowed_cidrs | CIDR blocks allowed to query DNS | list(string) | ["0.0.0.0/0"] | no |
| api_port | PowerDNS API port | number | 8053 | no |
| enable_dnssec | Enable DNSSEC support | bool | false | no |
| s3_backup_enabled | Enable S3 backup for DNS zones | bool | true | no |
| backup_retention_days | Days to retain DNS backups | number | 30 | no |
| cloudwatch_logs_retention | CloudWatch logs retention in days | number | 7 | no |
| tags | Tags to apply to all resources | map(string) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| security_group_id | ID of the PowerDNS security group |
| security_group_name | Name of the PowerDNS security group |
| backup_bucket_name | Name of the S3 bucket for DNS backups |
| backup_bucket_arn | ARN of the S3 bucket for DNS backups |
| backup_role_arn | ARN of the IAM role for DNS backups |
| log_group_name | Name of the CloudWatch log group |
| sns_topic_arn | ARN of the SNS topic for DNS alerts |
| dns_ports | DNS service ports configuration |
| allowed_cidrs | Allowed CIDR blocks configuration |

## Security Considerations

1. **API Access**: The PowerDNS API is restricted to specific CIDR blocks. Update `api_allowed_cidrs` to match your network.

2. **DNS Queries**: By default, DNS queries are allowed from anywhere (0.0.0.0/0). Restrict this in private environments.

3. **Backup Encryption**: S3 backups are encrypted using AES256.

4. **IAM Permissions**: The module creates minimal IAM permissions for S3 backup access only.

## Monitoring

The module sets up:
- CloudWatch Log Group for PowerDNS logs
- SNS Topic for alerts
- CloudWatch Alarm for health checks

Subscribe to the SNS topic to receive alerts:
```bash
aws sns subscribe \
  --topic-arn <sns_topic_arn> \
  --protocol email \
  --notification-endpoint your-email@example.com
```

## Backup and Recovery

DNS zones are automatically backed up to S3 if `s3_backup_enabled` is true. To restore:

```bash
# List available backups
aws s3 ls s3://<backup_bucket_name>/

# Download a backup
aws s3 cp s3://<backup_bucket_name>/backup.sql.gz ./

# Restore to PowerDNS
gunzip -c backup.sql.gz | docker exec -i powerdns-database psql -U powerdns
```