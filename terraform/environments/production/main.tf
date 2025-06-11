terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Optional: Configure remote state
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "prism-dns/production/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Prism-DNS"
      Environment = "production"
      ManagedBy   = "Terraform"
    }
  }
}

# Data source to get existing VPC
data "aws_vpc" "main" {
  filter {
    name   = "tag:Name"
    values = ["*production*", "*main*"]
  }
}

# PowerDNS Infrastructure Module
module "powerdns" {
  source = "../../modules/powerdns"

  vpc_id             = data.aws_vpc.main.id
  instance_id        = var.ec2_instance_id
  environment        = "production"
  dns_instance_count = 1

  # Production API access - restrict to known IPs
  api_allowed_cidrs = [
    "10.0.0.0/8",       # Internal VPC
    "172.16.0.0/12",    # Docker networks
    var.office_cidr,    # Office IP range
    var.monitoring_cidr # Prometheus/monitoring
  ]

  # DNS access - public
  dns_allowed_cidrs = ["0.0.0.0/0"]

  # Production backup settings
  s3_backup_enabled     = true
  backup_retention_days = 30

  # Production monitoring
  cloudwatch_logs_retention = 30

  tags = {
    CostCenter = "Infrastructure"
    Owner      = "DevOps"
    Backup     = "Daily"
  }
}

