output "powerdns_security_group_id" {
  description = "Security group ID for PowerDNS"
  value       = module.powerdns.security_group_id
}

output "powerdns_backup_bucket" {
  description = "S3 bucket for DNS backups"
  value       = module.powerdns.backup_bucket_name
}

output "powerdns_log_group" {
  description = "CloudWatch log group for PowerDNS"
  value       = module.powerdns.log_group_name
}

output "powerdns_sns_topic" {
  description = "SNS topic for PowerDNS alerts"
  value       = module.powerdns.sns_topic_arn
}

output "dns_configuration" {
  description = "DNS configuration details"
  value = {
    ports         = module.powerdns.dns_ports
    allowed_cidrs = module.powerdns.allowed_cidrs
  }
}

