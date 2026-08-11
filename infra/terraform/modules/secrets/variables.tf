variable "project_name" {
  description = "Project/application name used for resource naming and tagging."
  type        = string
}

variable "environment" {
  description = "Deployment environment name (e.g. \"production\")."
  type        = string
}

variable "secret_logical_names" {
  description = "Logical names of secrets to create metadata entries for in Secrets Manager. These are the existing key names already present in kubernetes/deployment.yaml's secretKeyRef — key NAMES only, never values."
  type        = list(string)
  default     = ["database-url", "secret-key"]
}

variable "kubernetes_namespace" {
  description = "Kubernetes namespace External Secrets Operator projects secrets into."
  type        = string
  default     = "expert-smart"
}

variable "kubernetes_secret_name" {
  description = "Name of the native Kubernetes Secret produced by External Secrets Operator, matching the existing Deployment's secretKeyRef target."
  type        = string
  default     = "expert-smart-secrets"
}

variable "tags" {
  description = "Common resource tags applied to all secrets-related resources."
  type        = map(string)
  default     = {}
}
