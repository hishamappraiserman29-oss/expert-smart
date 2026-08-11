# Locked architecture decisions get safe defaults. Genuine apply-time owner
# inputs (account ID, domain, hostname, database sizing, RPO/RTO) have no
# default — they must be supplied via terraform.tfvars at apply time, never
# committed here. See infra/README.md and the R1 architecture review for the
# reconciled classification of which values block scaffolding (none) versus
# which block a real apply (these).

variable "project_name" {
  description = "Project/application name used for resource naming and tagging."
  type        = string
  default     = "expert-smart"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "production"
}

variable "aws_region" {
  description = "AWS region."
  type        = string
  default     = "me-central-1"
}

variable "aws_account_id" {
  description = "AWS account ID this environment is provisioned into. Apply-time owner input — no default."
  type        = string
  default     = null
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability Zones to use. me-central-1 has three AZs."
  type        = list(string)
  default     = ["me-central-1a", "me-central-1b", "me-central-1c"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets, one per AZ."
  type        = list(string)
  default     = []
}

variable "private_app_subnet_cidrs" {
  description = "CIDR blocks for private application subnets, one per AZ."
  type        = list(string)
  default     = []
}

variable "private_db_subnet_cidrs" {
  description = "CIDR blocks for private database subnets, one per AZ."
  type        = list(string)
  default     = []
}

variable "domain_name" {
  description = "Root domain name. Apply-time owner input — no default."
  type        = string
  default     = null
}

variable "production_hostname" {
  description = "Production hostname. Apply-time owner input — no default."
  type        = string
  default     = null
}

variable "database_instance_class" {
  description = "RDS instance class. Apply-time owner input — no default; depends on production sizing/business requirements not yet supplied."
  type        = string
  default     = null
}

variable "database_allocated_storage_gb" {
  description = "RDS allocated storage in GB. Apply-time owner input — no default."
  type        = number
  default     = null
}

variable "database_backup_retention_days" {
  description = "RDS automated backup retention, in days. Apply-time owner input (RPO/RTO) — no default."
  type        = number
  default     = null
}

variable "tags" {
  description = "Common resource tags applied across all modules."
  type        = map(string)
  default = {
    Project     = "expert-smart"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}
