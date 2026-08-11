# Placeholder interface contract — values are null/empty until this module's
# resources are implemented under a separate, explicitly authorized phase.
# The iam module consumes cluster_oidc_issuer_url for IRSA trust policies.

output "cluster_name" {
  description = "Name of the EKS cluster."
  value       = null
}

output "cluster_endpoint" {
  description = "EKS control-plane API endpoint."
  value       = null
}

output "cluster_oidc_issuer_url" {
  description = "OIDC issuer URL for the cluster — consumed by the iam module for IRSA / EKS Pod Identity trust policies. Distinct from the GitHub Actions OIDC provider (CI identity)."
  value       = null
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS control plane."
  value       = null
}

output "node_security_group_id" {
  description = "Security group ID attached to the managed node group."
  value       = null
}
