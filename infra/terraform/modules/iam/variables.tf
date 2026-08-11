variable "project_name" {
  description = "Project/application name used for resource naming and tagging."
  type        = string
}

variable "environment" {
  description = "Deployment environment name (e.g. \"production\")."
  type        = string
}

variable "github_repository" {
  description = "GitHub \"owner/repo\" the CI OIDC trust policy is scoped to. Public repository identity, not a secret."
  type        = string
  default     = "hishamappraiserman29-oss/expert-smart"
}

variable "allowed_deploy_branch_ref" {
  description = "Git ref the apply/deploy IAM role's trust policy is scoped to."
  type        = string
  default     = "refs/heads/main"
}

variable "production_environment_name" {
  description = "GitHub Environment name whose OIDC \"environment\" claim the apply/deploy role's trust policy requires."
  type        = string
  default     = "production"
}

variable "eks_cluster_oidc_issuer_url" {
  description = "EKS cluster's own OIDC issuer URL (from the eks module) — used for Pod/workload identity trust policies. Distinct from the GitHub OIDC provider used for CI identity."
  type        = string
}

variable "tags" {
  description = "Common resource tags applied to all IAM resources."
  type        = map(string)
  default     = {}
}
