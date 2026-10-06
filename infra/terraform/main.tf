locals {
  name = "carevia-${var.environment}"
  common_tags = {
    Application = "Carevia"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "carevia" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(local.common_tags, { Name = "${local.name}-vpc" })
}

resource "aws_internet_gateway" "carevia" {
  vpc_id = aws_vpc.carevia.id

  tags = merge(local.common_tags, { Name = "${local.name}-igw" })
}

resource "aws_subnet" "database" {
  count = 2

  vpc_id                  = aws_vpc.carevia.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = false

  tags = merge(local.common_tags, { Name = "${local.name}-db-${count.index + 1}" })
}

resource "aws_route_table" "database" {
  vpc_id = aws_vpc.carevia.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.carevia.id
  }

  tags = merge(local.common_tags, { Name = "${local.name}-db-public" })
}

resource "aws_route_table_association" "database" {
  count = 2

  subnet_id      = aws_subnet.database[count.index].id
  route_table_id = aws_route_table.database.id
}

resource "aws_db_subnet_group" "carevia" {
  name       = "${local.name}-db-subnets"
  subnet_ids = aws_subnet.database[*].id

  tags = merge(local.common_tags, { Name = "${local.name}-db-subnets" })
}

resource "aws_security_group" "database" {
  name        = "${local.name}-postgres"
  description = "Restricted PostgreSQL access for Carevia development"
  vpc_id      = aws_vpc.carevia.id

  tags = merge(local.common_tags, { Name = "${local.name}-postgres" })
}

resource "aws_vpc_security_group_ingress_rule" "postgres" {
  for_each = toset(var.allowed_postgres_cidrs)

  security_group_id = aws_security_group.database.id
  description       = "PostgreSQL access from an explicitly approved IP"
  cidr_ipv4         = each.value
  from_port         = 5432
  to_port           = 5432
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "database" {
  security_group_id = aws_security_group.database.id
  description       = "Allow database outbound traffic"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_db_instance" "carevia" {
  identifier = local.name

  engine         = "postgres"
  engine_version = var.postgres_engine_version
  instance_class = var.db_instance_class

  allocated_storage = var.db_allocated_storage_gb
  storage_type      = "gp3"
  storage_encrypted = true

  db_name                     = var.database_name
  username                    = var.database_master_username
  manage_master_user_password = true
  port                        = 5432

  db_subnet_group_name   = aws_db_subnet_group.carevia.name
  vpc_security_group_ids = [aws_security_group.database.id]
  publicly_accessible    = var.database_publicly_accessible
  multi_az               = false

  backup_retention_period      = var.backup_retention_days
  copy_tags_to_snapshot        = true
  delete_automated_backups     = false
  skip_final_snapshot          = var.database_skip_final_snapshot
  final_snapshot_identifier    = var.database_skip_final_snapshot ? null : "${local.name}-final"
  deletion_protection          = var.database_deletion_protection
  auto_minor_version_upgrade   = true
  apply_immediately            = true
  performance_insights_enabled = false
  monitoring_interval          = 0

  tags = merge(local.common_tags, { Name = local.name })

  lifecycle {
    precondition {
      condition     = length(var.allowed_postgres_cidrs) > 0
      error_message = "allowed_postgres_cidrs must contain at least one trusted /32 address."
    }
  }
}

resource "aws_budgets_budget" "carevia_monthly" {
  name         = "carevia-development-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.budget_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_email]
  }
}

resource "aws_sns_topic" "carevia_alerts" {
  name = "${local.name}-alerts"
  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "carevia_alert_email" {
  topic_arn = aws_sns_topic.carevia_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email != "" ? var.alert_email : var.budget_email
}

resource "aws_cloudwatch_metric_alarm" "database_high_cpu" {
  alarm_name          = "${local.name}-database-high-cpu"
  alarm_description   = "Carevia RDS CPU has remained above 80 percent."
  namespace           = "AWS/RDS"
  metric_name         = "CPUUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 80
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.carevia_alerts.arn]
  ok_actions          = [aws_sns_topic.carevia_alerts.arn]

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.carevia.identifier
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "database_low_storage" {
  alarm_name          = "${local.name}-database-low-storage"
  alarm_description   = "Carevia RDS has less than 5 GiB of free storage."
  namespace           = "AWS/RDS"
  metric_name         = "FreeStorageSpace"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 5368709120
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.carevia_alerts.arn]
  ok_actions          = [aws_sns_topic.carevia_alerts.arn]

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.carevia.identifier
  }

  tags = local.common_tags
}
