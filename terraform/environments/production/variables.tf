variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "ec2_instance_id" {
  description = "Existing EC2 instance ID where PowerDNS will run"
  type        = string
}

variable "office_cidr" {
  description = "Office network CIDR for API access"
  type        = string
  default     = "0.0.0.0/0" # Update with your office IP range
}

variable "monitoring_cidr" {
  description = "Monitoring network CIDR (Prometheus, etc)"
  type        = string
  default     = "10.0.0.0/16" # Update based on your monitoring setup
}

