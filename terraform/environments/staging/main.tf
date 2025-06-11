terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Prism-DNS"
      Environment = "staging"
      ManagedBy   = "Terraform"
    }
  }
}

# Data source to get existing VPC
data "aws_vpc" "main" {
  filter {
    name   = "tag:Name"
    values = ["*staging*", "*default*"]
  }
}

# PowerDNS Infrastructure Module
module "powerdns" {
  source = "../../modules/powerdns"

  vpc_id             = data.aws_vpc.main.id
  instance_id        = var.ec2_instance_id
  environment        = "staging"
  dns_instance_count = 1

  # Staging API access - moderately restricted
  api_allowed_cidrs = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16"
  ]

  # DNS access - public
  dns_allowed_cidrs = ["0.0.0.0/0"]

  # Staging backup settings
  s3_backup_enabled     = true
  backup_retention_days = 14

  # Staging monitoring
  cloudwatch_logs_retention = 7

  tags = {
    Owner = "DevOps"
  }
}

