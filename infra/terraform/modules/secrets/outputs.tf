# Placeholder interface contract — values are null/empty until this module's
# resources are implemented under a separate, explicitly authorized phase.
# No output here ever contains a secret VALUE — only ARNs/names/metadata.

output "secrets_manager_secret_arns" {
  description = "Map of logical secret name to its Secrets Manager ARN (metadata only, never a secret value)."
  value       = {}
}

output "external_secrets_target_namespace" {
  description = "Kubernetes namespace External Secrets Operator targets."
  value       = null
}

output "external_secrets_target_secret_name" {
  description = "Name of the native Kubernetes Secret External Secrets Operator produces."
  value       = null
}
