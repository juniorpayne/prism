variable "vpc_id" {
  description = "The VPC ID where PowerDNS will be deployed"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be dev, staging, or production."
  }
}

variable "dns_instance_count" {
  description = "Number of PowerDNS instances"
  type        = number
  default     = 1
}

variable "api_allowed_cidrs" {
  description = "CIDR blocks allowed to access PowerDNS API"
  type        = list(string)
  default     = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
}

variable "dns_allowed_cidrs" {
  description = "CIDR blocks allowed to query DNS (0.0.0.0/0 for public)"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "enable_dnssec" {
  description = "Enable DNSSEC support"
  type        = bool
  default     = false
}

variable "backup_retention_days" {
  description = "Days to retain DNS backups"
  type        = number
  default     = 30
}

variable "instance_id" {
  description = "EC2 instance ID where PowerDNS will run"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "s3_backup_enabled" {
  description = "Enable S3 backup for DNS zones"
  type        = bool
  default     = true
}

variable "cloudwatch_logs_retention" {
  description = "CloudWatch logs retention in days"
  type        = number
  default     = 7
}

variable "api_port" {
  description = "PowerDNS API port"
  type        = number
  default     = 8053
}

