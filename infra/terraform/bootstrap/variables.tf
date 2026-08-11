variable "project_name" {
  description = "Project name used in resource naming and tagging."
  type        = string
  default     = "expert-smart"

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,18}[a-z0-9]$", var.project_name))
    error_message = "project_name must be 3-20 lowercase alphanumeric characters or hyphens, and must start and end with a letter or digit — required for a valid, deterministic S3 bucket name once combined with the account ID and region."
  }
}

variable "aws_region" {
  description = "AWS region the state bucket and KMS key are created in."
  type        = string
  default     = "me-central-1"

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]$", var.aws_region))
    error_message = "aws_region must be a valid AWS region identifier (e.g. me-central-1)."
  }
}

variable "aws_account_id" {
  description = "Target AWS account ID. Must be verified via a read-only identity check (e.g. `aws sts get-caller-identity`) immediately before this module is ever applied — never assumed or hardcoded. No default is provided deliberately."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must be exactly 12 digits, matching the Account field returned by aws sts get-caller-identity."
  }
}

variable "kms_deletion_window_days" {
  description = "Waiting period, in days, before the KMS key would be permanently deleted if deletion is ever scheduled. AWS requires a value between 7 and 30."
  type        = number
  default     = 30

  validation {
    condition     = var.kms_deletion_window_days >= 7 && var.kms_deletion_window_days <= 30
    error_message = "kms_deletion_window_days must be between 7 and 30 (AWS KMS constraint)."
  }
}

variable "tags" {
  description = "Common resource tags applied to the state bucket and KMS key."
  type        = map(string)
  default = {
    Project   = "expert-smart"
    Component = "terraform-state-bootstrap"
    ManagedBy = "terraform"
  }
}
