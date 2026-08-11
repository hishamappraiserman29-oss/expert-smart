variable "project_name" {
  description = "Project/application name used for resource naming and tagging."
  type        = string
}

variable "environment" {
  description = "Deployment environment name (e.g. \"production\")."
  type        = string
}

variable "engine" {
  description = "Database engine. Proven by application evidence (see main.tf) to be postgres."
  type        = string
  default     = "postgres"
}

variable "engine_version" {
  description = "PostgreSQL engine version."
  type        = string
  default     = "16"
}

variable "database_name" {
  description = "Initial database name, matching the application's default (core_engine/database/connection.py)."
  type        = string
  default     = "expert_smart"
}

variable "instance_class" {
  description = "RDS instance class. Apply-time owner input — no default; sizing depends on production business requirements not yet supplied."
  type        = string
  default     = null
}

variable "allocated_storage_gb" {
  description = "Allocated storage in GB. Apply-time owner input — no default."
  type        = number
  default     = null
}

variable "multi_az" {
  description = "Whether the RDS instance is Multi-AZ. Locked architecture decision — true for production."
  type        = bool
  default     = true
}

variable "publicly_accessible" {
  description = "Whether the RDS instance has a public endpoint. Locked architecture decision — always false."
  type        = bool
  default     = false
}

variable "backup_retention_days" {
  description = "Automated backup retention period, in days. Apply-time owner input (RPO/RTO) — no default."
  type        = number
  default     = null
}

variable "private_db_subnet_ids" {
  description = "Private database subnet IDs (from the network module)."
  type        = list(string)
}

variable "vpc_security_group_ids" {
  description = "Security group IDs permitted to reach the database (from the eks module's node/pod security group)."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Common resource tags applied to all database resources."
  type        = map(string)
  default     = {}
}
