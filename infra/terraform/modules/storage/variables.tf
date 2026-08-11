variable "project_name" {
  description = "Project/application name used for resource naming and tagging."
  type        = string
}

variable "environment" {
  description = "Deployment environment name (e.g. \"production\")."
  type        = string
}

variable "private_app_subnet_ids" {
  description = "Private application subnet IDs for EFS mount target placement, one per AZ (from the network module)."
  type        = list(string)
}

variable "vpc_security_group_ids" {
  description = "Security group IDs permitted to reach the EFS mount targets over NFS (from the eks module's node/pod security group)."
  type        = list(string)
  default     = []
}

variable "throughput_mode" {
  description = "EFS throughput mode."
  type        = string
  default     = "bursting"
}

variable "uploads_access_point_path" {
  description = "Root path exposed by the EFS access point, matching the application's upload directory semantics (EXPERT_SMART_UPLOAD_DIR / /app/uploads)."
  type        = string
  default     = "/uploads"
}

variable "tags" {
  description = "Common resource tags applied to all storage resources."
  type        = map(string)
  default     = {}
}
