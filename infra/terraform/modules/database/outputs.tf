# Placeholder interface contract — values are null until this module's
# resources are implemented under a separate, explicitly authorized phase.

output "db_instance_endpoint" {
  description = "Connection endpoint (host:port) of the RDS instance."
  value       = null
}

output "db_instance_arn" {
  description = "ARN of the RDS instance."
  value       = null
}

output "db_subnet_group_name" {
  description = "Name of the DB subnet group."
  value       = null
}

output "db_security_group_id" {
  description = "Security group ID attached to the RDS instance."
  value       = null
}
