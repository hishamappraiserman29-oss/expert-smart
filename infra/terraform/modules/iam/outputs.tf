# Placeholder interface contract — values are null until this module's
# resources are implemented under a separate, explicitly authorized phase.

# ── CI identity (GitHub Actions -> AWS) ──────────────────────────────────
output "github_oidc_provider_arn" {
  description = "ARN of the GitHub Actions OIDC provider."
  value       = null
}

output "terraform_plan_role_arn" {
  description = "ARN of the broad-read/zero-write role used by the infra-plan workflow. Assumable from any PR."
  value       = null
}

output "terraform_apply_role_arn" {
  description = "ARN of the narrowly-scoped apply/deploy role. Assumable only from main + the production GitHub Environment claim."
  value       = null
}

# ── Pod / workload identity (EKS Pods -> AWS) — distinct from CI identity ─
output "aws_load_balancer_controller_role_arn" {
  description = "IRSA/Pod Identity role ARN for the AWS Load Balancer Controller ServiceAccount."
  value       = null
}

output "efs_csi_driver_role_arn" {
  description = "IRSA/Pod Identity role ARN for the EFS CSI driver ServiceAccount."
  value       = null
}

output "external_secrets_operator_role_arn" {
  description = "IRSA/Pod Identity role ARN for the External Secrets Operator ServiceAccount."
  value       = null
}
