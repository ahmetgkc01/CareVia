output "budget_name" {
  description = "AWS Budget managed for the Carevia development environment."
  value       = aws_budgets_budget.carevia_monthly.name
}

output "rds_endpoint" {
  description = "Carevia RDS PostgreSQL endpoint."
  value       = aws_db_instance.carevia.address
}

output "rds_port" {
  description = "Carevia RDS PostgreSQL port."
  value       = aws_db_instance.carevia.port
}

output "database_name" {
  description = "Initial Carevia database name."
  value       = aws_db_instance.carevia.db_name
}

output "database_master_username" {
  description = "RDS master username."
  value       = aws_db_instance.carevia.username
  sensitive   = true
}

output "database_secret_arn" {
  description = "AWS Secrets Manager ARN containing the RDS master credentials."
  value       = aws_db_instance.carevia.master_user_secret[0].secret_arn
  sensitive   = true
}

output "vpc_id" {
  description = "Carevia development VPC ID."
  value       = aws_vpc.carevia.id
}

output "database_security_group_id" {
  description = "Security group controlling PostgreSQL access."
  value       = aws_security_group.database.id
}
