# ==============================================================================
# Terraform remote-state bootstrap — version constraints
# ==============================================================================
#
# This module intentionally declares NO backend block. It uses Terraform's
# default local state — it exists specifically to create the S3 bucket and
# KMS key that environments/production's remote backend will later point at,
# so it cannot itself use that backend (see README.md).
#
# required_version >= 1.11.0 matches the same floor already declared in
# environments/production/providers.tf, for consistency across the project
# even though this module's own state is local, not S3-backed.

terraform {
  required_version = ">= 1.11.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
