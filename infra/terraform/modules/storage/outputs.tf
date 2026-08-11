# Placeholder interface contract — values are null/empty until this module's
# resources are implemented under a separate, explicitly authorized phase.

output "efs_file_system_id" {
  description = "ID of the EFS file system backing shared uploads storage."
  value       = null
}

output "efs_access_point_id" {
  description = "ID of the EFS access point scoped to the uploads path."
  value       = null
}

output "efs_mount_target_ids" {
  description = "IDs of the EFS mount targets, one per AZ."
  value       = []
}

output "efs_security_group_id" {
  description = "Security group ID attached to the EFS mount targets."
  value       = null
}
