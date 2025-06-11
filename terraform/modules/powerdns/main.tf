terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

# PowerDNS Security Group
resource "aws_security_group" "powerdns" {
  name_prefix = "powerdns-${var.environment}-"
  description = "Security group for PowerDNS DNS server"
  vpc_id      = var.vpc_id

  # DNS UDP
  ingress {
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = var.dns_allowed_cidrs
    description = "DNS queries (UDP)"
  }

  # DNS TCP
  ingress {
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = var.dns_allowed_cidrs
    description = "DNS queries (TCP)"
  }

  # PowerDNS API
  ingress {
    from_port   = var.api_port
    to_port     = var.api_port
    protocol    = "tcp"
    cidr_blocks = var.api_allowed_cidrs
    description = "PowerDNS API"
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(var.tags, {
    Name        = "powerdns-${var.environment}"
    Environment = var.environment
    Service     = "PowerDNS"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Attach security group to existing EC2 instance
resource "aws_network_interface_sg_attachment" "powerdns" {
  count                = var.dns_instance_count
  security_group_id    = aws_security_group.powerdns.id
  network_interface_id = data.aws_instance.prism.network_interface_id
}

# Get existing EC2 instance details
data "aws_instance" "prism" {
  instance_id = var.instance_id
}

# S3 Bucket for DNS Backups
resource "aws_s3_bucket" "dns_backups" {
  count         = var.s3_backup_enabled ? 1 : 0
  bucket_prefix = "powerdns-backups-${var.environment}-"

  tags = merge(var.tags, {
    Name        = "powerdns-backups-${var.environment}"
    Environment = var.environment
    Service     = "PowerDNS"
  })
}

# S3 Bucket Versioning
resource "aws_s3_bucket_versioning" "dns_backups" {
  count  = var.s3_backup_enabled ? 1 : 0
  bucket = aws_s3_bucket.dns_backups[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "dns_backups" {
  count  = var.s3_backup_enabled ? 1 : 0
  bucket = aws_s3_bucket.dns_backups[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 Bucket Lifecycle
resource "aws_s3_bucket_lifecycle_configuration" "dns_backups" {
  count  = var.s3_backup_enabled ? 1 : 0
  bucket = aws_s3_bucket.dns_backups[0].id

  rule {
    id     = "delete-old-backups"
    status = "Enabled"

    expiration {
      days = var.backup_retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }
}

# IAM Role for EC2 to access S3 backups
resource "aws_iam_role" "powerdns_backup" {
  count              = var.s3_backup_enabled ? 1 : 0
  name_prefix        = "powerdns-backup-${var.environment}-"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json

  tags = merge(var.tags, {
    Name        = "powerdns-backup-${var.environment}"
    Environment = var.environment
    Service     = "PowerDNS"
  })
}

data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

# IAM Policy for S3 backup access
resource "aws_iam_role_policy" "powerdns_backup" {
  count  = var.s3_backup_enabled ? 1 : 0
  name   = "powerdns-backup-policy"
  role   = aws_iam_role.powerdns_backup[0].id
  policy = data.aws_iam_policy_document.powerdns_backup[0].json
}

data "aws_iam_policy_document" "powerdns_backup" {
  count = var.s3_backup_enabled ? 1 : 0

  statement {
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:ListBucket",
      "s3:DeleteObject"
    ]
    resources = [
      aws_s3_bucket.dns_backups[0].arn,
      "${aws_s3_bucket.dns_backups[0].arn}/*"
    ]
  }
}

# CloudWatch Log Group for PowerDNS
resource "aws_cloudwatch_log_group" "powerdns" {
  name              = "/aws/ec2/powerdns/${var.environment}"
  retention_in_days = var.cloudwatch_logs_retention

  tags = merge(var.tags, {
    Name        = "powerdns-logs-${var.environment}"
    Environment = var.environment
    Service     = "PowerDNS"
  })
}

# CloudWatch Log Stream
resource "aws_cloudwatch_log_stream" "powerdns" {
  name           = "powerdns-${var.environment}"
  log_group_name = aws_cloudwatch_log_group.powerdns.name
}

# SNS Topic for DNS Alerts
resource "aws_sns_topic" "dns_alerts" {
  name_prefix = "powerdns-alerts-${var.environment}-"

  tags = merge(var.tags, {
    Name        = "powerdns-alerts-${var.environment}"
    Environment = var.environment
    Service     = "PowerDNS"
  })
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "dns_health" {
  alarm_name          = "powerdns-health-${var.environment}"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "HealthCheck"
  namespace           = "PowerDNS/${var.environment}"
  period              = "300"
  statistic           = "Average"
  threshold           = "1"
  alarm_description   = "PowerDNS health check alarm"
  alarm_actions       = [aws_sns_topic.dns_alerts.arn]

  tags = merge(var.tags, {
    Name        = "powerdns-health-${var.environment}"
    Environment = var.environment
    Service     = "PowerDNS"
  })
}

