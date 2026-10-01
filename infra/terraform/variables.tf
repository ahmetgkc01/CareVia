variable "aws_region" {
  description = "Carevia development AWS region."
  type        = string
  default     = "eu-central-1"
}

variable "monthly_budget_usd" {
  description = "Monthly AWS cost budget for the Carevia development environment."
  type        = number
  default     = 20
}

variable "budget_email" {
  description = "Email address that receives AWS Budget notifications."
  type        = string
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "development"
}

variable "vpc_cidr" {
  description = "CIDR block for the isolated Carevia development VPC."
  type        = string
  default     = "10.42.0.0/16"
}

variable "allowed_postgres_cidrs" {
  description = "Trusted public IPv4 CIDRs allowed to connect to PostgreSQL. Use /32 entries only."
  type        = list(string)

  validation {
    condition = alltrue([
      for cidr in var.allowed_postgres_cidrs : can(cidrhost(cidr, 0)) && endswith(cidr, "/32")
    ])
    error_message = "Every PostgreSQL source must be a valid IPv4 /32 CIDR."
  }
}

variable "postgres_engine_version" {
  description = "Amazon RDS PostgreSQL major version."
  type        = string
  default     = "17"
}

variable "db_instance_class" {
  description = "Small development RDS instance class."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage_gb" {
  description = "Allocated gp3 database storage in GiB."
  type        = number
  default     = 20
}

variable "database_name" {
  description = "Initial PostgreSQL database name."
  type        = string
  default     = "carevia"
}

variable "database_master_username" {
  description = "RDS master username; the password is managed by AWS Secrets Manager."
  type        = string
  default     = "carevia_admin"
}

variable "backup_retention_days" {
  description = "Automated backup retention for the development database."
  type        = number
  default     = 7

  validation {
    condition     = var.backup_retention_days >= 1 && var.backup_retention_days <= 35
    error_message = "backup_retention_days must be between 1 and 35."
  }
}

variable "database_publicly_accessible" {
  description = "Expose an RDS endpoint publicly; ingress remains limited to approved /32 CIDRs."
  type        = bool
  default     = true
}

variable "database_deletion_protection" {
  description = "Prevent accidental deletion of the RDS instance."
  type        = bool
  default     = true
}

variable "database_skip_final_snapshot" {
  description = "Skip the final snapshot when deleting RDS. Keep false outside disposable environments."
  type        = bool
  default     = false
}
