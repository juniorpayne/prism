variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "ec2_instance_id" {
  description = "Existing EC2 instance ID where PowerDNS will run"
  type        = string
}

