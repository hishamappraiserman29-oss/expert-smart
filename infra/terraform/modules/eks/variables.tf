variable "project_name" {
  description = "Project/application name used for resource naming and tagging."
  type        = string
}

variable "environment" {
  description = "Deployment environment name (e.g. \"production\")."
  type        = string
}

variable "cluster_name" {
  description = "Name of the EKS cluster."
  type        = string
  default     = ""
}

variable "kubernetes_version" {
  description = "EKS Kubernetes version."
  type        = string
  default     = "1.31"
}

variable "vpc_id" {
  description = "VPC ID the cluster is provisioned into (from the network module)."
  type        = string
}

variable "private_app_subnet_ids" {
  description = "Private application subnet IDs for node group placement (from the network module)."
  type        = list(string)
}

variable "node_instance_types" {
  description = "EC2 instance types for the managed node group."
  type        = list(string)
  default     = ["m6i.large"]
}

variable "node_min_size" {
  description = "Minimum node count. Matches the existing HPA's minReplicas so baseline capacity can always host it."
  type        = number
  default     = 2
}

variable "node_desired_size" {
  description = "Desired node count. Recommend 3 (one per AZ) for genuine per-AZ resilience."
  type        = number
  default     = 3
}

variable "node_max_size" {
  description = "Maximum node count for autoscaling."
  type        = number
  default     = 6
}

variable "enable_karpenter" {
  description = "Whether to install Karpenter for cluster autoscaling (recommended over Cluster Autoscaler)."
  type        = bool
  default     = true
}

variable "enable_control_plane_logging" {
  description = "Whether to enable EKS control-plane (api/audit/authenticator) logging to CloudWatch."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Common resource tags applied to all EKS resources."
  type        = map(string)
  default     = {}
}
