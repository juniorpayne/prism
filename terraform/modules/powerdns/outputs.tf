output "security_group_id" {
  description = "ID of the PowerDNS security group"
  value       = aws_security_group.powerdns.id
}

output "security_group_name" {
  description = "Name of the PowerDNS security group"
  value       = aws_security_group.powerdns.name
}

output "backup_bucket_name" {
  description = "Name of the S3 bucket for DNS backups"
  value       = var.s3_backup_enabled ? aws_s3_bucket.dns_backups[0].id : null
}

output "backup_bucket_arn" {
  description = "ARN of the S3 bucket for DNS backups"
  value       = var.s3_backup_enabled ? aws_s3_bucket.dns_backups[0].arn : null
}

output "backup_role_arn" {
  description = "ARN of the IAM role for DNS backups"
  value       = var.s3_backup_enabled ? aws_iam_role.powerdns_backup[0].arn : null
}

output "log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.powerdns.name
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for DNS alerts"
  value       = aws_sns_topic.dns_alerts.arn
}

output "dns_ports" {
  description = "DNS service ports"
  value = {
    dns_udp = 53
    dns_tcp = 53
    api     = var.api_port
  }
}

output "allowed_cidrs" {
  description = "Allowed CIDR blocks"
  value = {
    dns = var.dns_allowed_cidrs
    api = var.api_allowed_cidrs
  }
}

