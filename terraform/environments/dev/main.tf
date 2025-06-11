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
      Environment = "dev"
      ManagedBy   = "Terraform"
    }
  }
}

# For dev, we'll use the default VPC
data "aws_vpc" "default" {
  default = true
}

# PowerDNS Infrastructure Module
module "powerdns" {
  source = "../../modules/powerdns"

  vpc_id             = data.aws_vpc.default.id
  instance_id        = var.ec2_instance_id
  environment        = "dev"
  dns_instance_count = 1

  # Dev API access - more permissive
  api_allowed_cidrs = ["0.0.0.0/0"] # Open for dev, restrict in production

  # DNS access - public
  dns_allowed_cidrs = ["0.0.0.0/0"]

  # Dev backup settings - minimal
  s3_backup_enabled     = false # Disable backups for dev
  backup_retention_days = 7

  # Dev monitoring - short retention
  cloudwatch_logs_retention = 3

  tags = {
    Owner = "Development"
  }
}

