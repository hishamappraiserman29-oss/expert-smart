variable "project_name" {
  description = "Project/application name used for resource naming and tagging."
  type        = string
}

variable "environment" {
  description = "Deployment environment name (e.g. \"production\")."
  type        = string
}

variable "eks_cluster_name" {
  description = "Name of the EKS cluster (from the eks module) — used for log group / alarm naming."
  type        = string
  default     = ""
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention period, in days."
  type        = number
  default     = 30
}

variable "enable_container_insights" {
  description = "Whether to enable CloudWatch Container Insights for the EKS cluster."
  type        = bool
  default     = true
}

variable "enable_eks_control_plane_logs" {
  description = "Whether to enable EKS control-plane (api/audit/authenticator) logging to CloudWatch."
  type        = bool
  default     = true
}

variable "alarm_notification_topic_arn" {
  description = "SNS topic ARN alarms notify. Apply-time input — no default; no notification target exists yet."
  type        = string
  default     = null
}

variable "tags" {
  description = "Common resource tags applied to all observability resources."
  type        = map(string)
  default     = {}
}
